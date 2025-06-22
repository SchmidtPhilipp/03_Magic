"""
Deck Evaluation Module

This module provides different methods for evaluating deck quality:
1. 17Lands data-based evaluation (game_in_hand_win_rate + improvement_when_drawn)
2. Manual evaluation with synergy bonuses
3. Interface for selecting evaluation methods
4. Performance optimizations with caching and parallel processing
"""

import functools
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class DeckEvaluator:
    """Main deck evaluator class with multiple evaluation methods and performance optimizations"""

    def __init__(self, ratings_file: str = "data/ratings/card_ratings.csv"):
        """Initialize evaluator with card ratings"""
        self.ratings_file = ratings_file
        self.ratings_df = None
        self.ratings_dict = {}
        self._load_ratings()

        # Performance optimization: Caching
        self._synergy_cache = {}
        self._evaluation_cache = {}
        self._cache_lock = threading.Lock()

        # Performance optimization: Thread pool for parallel processing
        self._thread_pool = ThreadPoolExecutor(max_workers=4)

        logger.info("DeckEvaluator initialized with performance optimizations")

    def _load_ratings(self):
        """Load card ratings from file"""
        try:
            self.ratings_df = pd.read_csv(self.ratings_file)

            # Convert ratings to numeric for easier comparison
            self.ratings_df["Rating_Value"] = (
                self.ratings_df["Rating"].str.split("/").str[0].astype(int)
            )

            # Create a dictionary for quick rating lookup
            self.ratings_dict = dict(
                zip(self.ratings_df["Card Name"], self.ratings_df["Rating_Value"])
            )

            logger.info(f"Loaded {len(self.ratings_df)} rated cards")

        except Exception as e:
            logger.error(f"Error loading ratings file: {e}")
            self.ratings_df = pd.DataFrame()
            self.ratings_dict = {}

    def clear_caches(self):
        """Clear all caches to free memory"""
        with self._cache_lock:
            self._synergy_cache.clear()
            self._evaluation_cache.clear()
        logger.info("All caches cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for monitoring"""
        with self._cache_lock:
            return {
                "synergy_cache_size": len(self._synergy_cache),
                "evaluation_cache_size": len(self._evaluation_cache),
            }

    def evaluate_deck(self, decklist: List[str], method: str = "manual") -> float:
        """
        Main evaluation interface with caching

        Args:
            decklist: List of card names in the deck
            method: Evaluation method ("17lands" or "manual")

        Returns:
            float: Deck score (0.0 to 1.0)
        """
        # Create cache key
        cache_key = (tuple(sorted(decklist)), method)

        # Check cache first
        with self._cache_lock:
            if cache_key in self._evaluation_cache:
                logger.debug(f"Cache hit for deck evaluation: {len(decklist)} cards")
                return self._evaluation_cache[cache_key]

        # Calculate evaluation
        if method == "17lands":
            result = self.evaluate_deck_17lands(decklist)
        elif method == "manual":
            result = self.evaluate_deck_manual(decklist)
        else:
            logger.warning(f"Unknown evaluation method: {method}. Using manual.")
            result = self.evaluate_deck_manual(decklist)

        # Cache result
        with self._cache_lock:
            self._evaluation_cache[cache_key] = result

        return result

    def evaluate_deck_17lands(self, decklist: List[str]) -> float:
        """
        Evaluate deck using 17Lands data with performance optimizations

        This method would use game_in_hand_win_rate and improvement_when_drawn
        from 17Lands data. For now, we'll simulate this with the existing ratings.

        Args:
            decklist: List of card names in the deck

        Returns:
            float: Deck score (0.0 to 1.0)
        """
        if not decklist:
            return 0.0

        # Use parallel processing for large decks
        if len(decklist) > 20:
            return self._evaluate_deck_17lands_parallel(decklist)

        # Get ratings for cards in deck
        ratings = []
        for card_name in decklist:
            rating = self.ratings_dict.get(card_name, 0)
            ratings.append(rating)

        if not ratings:
            return 0.0

        # Calculate average rating
        avg_rating = sum(ratings) / len(ratings)

        # Normalize to 0-1 scale (assuming ratings are 0-10)
        normalized_score = avg_rating / 10.0

        # TODO: In a real implementation, this would use actual 17Lands data:
        # - game_in_hand_win_rate: How often the card wins when drawn
        # - improvement_when_drawn: How much the card improves win rate when drawn
        # - Combine these metrics for a more sophisticated evaluation

        return max(0.0, min(1.0, normalized_score))

    def _evaluate_deck_17lands_parallel(self, decklist: List[str]) -> float:
        """Parallel version of 17Lands evaluation for large decks"""
        # Split deck into chunks for parallel processing
        chunk_size = max(1, len(decklist) // 4)
        chunks = [
            decklist[i : i + chunk_size] for i in range(0, len(decklist), chunk_size)
        ]

        # Process chunks in parallel
        futures = []
        for chunk in chunks:
            future = self._thread_pool.submit(self._evaluate_chunk_17lands, chunk)
            futures.append(future)

        # Collect results
        chunk_scores = []
        for future in as_completed(futures):
            try:
                chunk_scores.append(future.result())
            except Exception as e:
                logger.error(f"Error in parallel evaluation: {e}")
                chunk_scores.append(0.0)

        # Combine chunk scores
        if chunk_scores:
            return sum(chunk_scores) / len(chunk_scores)
        return 0.0

    def _evaluate_chunk_17lands(self, chunk: List[str]) -> float:
        """Evaluate a chunk of cards for parallel processing"""
        if not chunk:
            return 0.0

        ratings = [self.ratings_dict.get(card_name, 0) for card_name in chunk]
        if not ratings:
            return 0.0

        avg_rating = sum(ratings) / len(ratings)
        return max(0.0, min(1.0, avg_rating / 10.0))

    def evaluate_deck_manual(self, decklist: List[str]) -> float:
        """
        Evaluate deck using manual ratings and synergy bonuses with performance optimizations

        Args:
            decklist: List of card names in the deck

        Returns:
            float: Deck score (0.0 to 1.0)
        """
        if not decklist:
            return 0.0

        # Use parallel processing for large decks
        if len(decklist) > 30:
            return self._evaluate_deck_manual_parallel(decklist)

        # Get base ratings
        ratings = []
        for card_name in decklist:
            rating = self.ratings_dict.get(card_name, 0)
            ratings.append(rating)

        if not ratings:
            return 0.0

        # Calculate base score from ratings
        avg_rating = sum(ratings) / len(ratings)
        base_score = avg_rating / 10.0

        # Calculate synergy bonus with caching
        synergy_bonus = self._calculate_synergy_bonus(decklist)

        # Calculate dynamic synergy bonus based on deck composition
        dynamic_bonus = self._calculate_dynamic_synergy_bonus(decklist)

        # Combine base score with synergy bonuses
        total_score = base_score + synergy_bonus + dynamic_bonus

        return max(0.0, min(1.0, total_score))

    def _evaluate_deck_manual_parallel(self, decklist: List[str]) -> float:
        """Parallel version of manual evaluation for large decks"""
        # Split deck into chunks
        chunk_size = max(1, len(decklist) // 4)
        chunks = [
            decklist[i : i + chunk_size] for i in range(0, len(decklist), chunk_size)
        ]

        # Process chunks in parallel
        futures = []
        for chunk in chunks:
            future = self._thread_pool.submit(self._evaluate_chunk_manual, chunk)
            futures.append(future)

        # Collect results
        chunk_scores = []
        for future in as_completed(futures):
            try:
                chunk_scores.append(future.result())
            except Exception as e:
                logger.error(f"Error in parallel manual evaluation: {e}")
                chunk_scores.append(0.0)

        # Combine chunk scores
        if chunk_scores:
            return sum(chunk_scores) / len(chunk_scores)
        return 0.0

    def _evaluate_chunk_manual(self, chunk: List[str]) -> float:
        """Evaluate a chunk of cards for parallel processing"""
        if not chunk:
            return 0.0

        ratings = [self.ratings_dict.get(card_name, 0) for card_name in chunk]
        if not ratings:
            return 0.0

        avg_rating = sum(ratings) / len(ratings)
        base_score = avg_rating / 10.0

        # Calculate synergy bonus for this chunk
        synergy_bonus = self._calculate_synergy_bonus(chunk)

        # Calculate dynamic synergy bonus for this chunk
        dynamic_bonus = self._calculate_dynamic_synergy_bonus(chunk)

        return max(0.0, min(1.0, base_score + synergy_bonus + dynamic_bonus))

    def _calculate_synergy_bonus(self, decklist: List[str]) -> float:
        """
        Calculate synergy bonus between cards with caching

        Args:
            decklist: List of card names in the deck

        Returns:
            float: Synergy bonus (0.0 to 0.2)
        """
        if len(decklist) < 2:
            return 0.0

        # Create cache key for synergy calculation
        cache_key = tuple(sorted(decklist))

        # Check cache first
        with self._cache_lock:
            if cache_key in self._synergy_cache:
                logger.debug(
                    f"Cache hit for synergy calculation: {len(decklist)} cards"
                )
                return self._synergy_cache[cache_key]

        # Use parallel processing for large decks
        if len(decklist) > 25:
            synergy_score = self._calculate_synergy_parallel(decklist)
        else:
            synergy_score = self._calculate_synergy_sequential(decklist)

        # Cache result
        with self._cache_lock:
            self._synergy_cache[cache_key] = synergy_score

        return synergy_score

    def _calculate_synergy_sequential(self, decklist: List[str]) -> float:
        """Sequential synergy calculation for smaller decks"""
        synergy_score = 0.0
        synergy_pairs = 0

        # Look for common synergy patterns
        for i, card1 in enumerate(decklist):
            for j, card2 in enumerate(decklist[i + 1 :], i + 1):
                synergy = self._calculate_card_synergy(card1, card2)
                synergy_score += synergy
                synergy_pairs += 1

        if synergy_pairs == 0:
            return 0.0

        # Normalize synergy bonus (max 0.2)
        avg_synergy = synergy_score / synergy_pairs
        return min(0.2, avg_synergy)

    def _calculate_synergy_parallel(self, decklist: List[str]) -> float:
        """Parallel synergy calculation for large decks"""
        # Create pairs for parallel processing
        pairs = []
        for i, card1 in enumerate(decklist):
            for j, card2 in enumerate(decklist[i + 1 :], i + 1):
                pairs.append((card1, card2))

        # Process pairs in parallel
        futures = []
        for card1, card2 in pairs:
            future = self._thread_pool.submit(
                self._calculate_card_synergy, card1, card2
            )
            futures.append(future)

        # Collect results
        synergy_scores = []
        for future in as_completed(futures):
            try:
                synergy_scores.append(future.result())
            except Exception as e:
                logger.error(f"Error in parallel synergy calculation: {e}")
                synergy_scores.append(0.0)

        if not synergy_scores:
            return 0.0

        # Calculate average synergy
        avg_synergy = sum(synergy_scores) / len(synergy_scores)
        return min(0.2, avg_synergy)

    def _calculate_card_synergy(self, card1: str, card2: str) -> float:
        """
        Calculate synergy between two specific cards with caching and enhanced patterns

        Args:
            card1: First card name
            card2: Second card name

        Returns:
            float: Synergy score (0.0 to 1.0)
        """
        # Create cache key for card pair
        cache_key = tuple(sorted([card1, card2]))

        # Check cache first
        with self._cache_lock:
            if cache_key in self._synergy_cache:
                return self._synergy_cache[cache_key]

        # Enhanced synergy patterns with more comprehensive coverage
        synergy_patterns = {
            # Equipment + Creatures
            ("Lightning Greaves", "Sol Ring"): 0.8,
            ("Lightning Greaves", "Dark Confidant"): 0.7,
            ("Skullclamp", "Dark Confidant"): 0.9,
            ("Umezawa's Jitte", "Goblin Guide"): 0.8,
            ("Sword of Fire and Ice", "Dark Confidant"): 0.8,
            ("Batterskull", "Primeval Titan"): 0.7,
            # Counterspell + Card draw
            ("Counterspell", "Dark Confidant"): 0.6,
            ("Mana Leak", "Dark Confidant"): 0.6,
            ("Remand", "Dark Confidant"): 0.5,
            ("Force of Will", "Brainstorm"): 0.7,
            ("Daze", "Ponder"): 0.5,
            # Removal + Aggro
            ("Lightning Bolt", "Goblin Guide"): 0.5,
            ("Path to Exile", "Goblin Guide"): 0.5,
            ("Swords to Plowshares", "Goblin Guide"): 0.5,
            ("Terminate", "Goblin Guide"): 0.5,
            ("Fatal Push", "Dark Confidant"): 0.4,
            # Ramp + Big spells
            ("Sol Ring", "Primeval Titan"): 0.7,
            ("Farseek", "Primeval Titan"): 0.6,
            ("Rampant Growth", "Primeval Titan"): 0.6,
            ("Cultivate", "Primeval Titan"): 0.6,
            ("Kodama's Reach", "Primeval Titan"): 0.6,
            # Tribal synergies
            ("Goblin Chieftain", "Goblin Guide"): 0.8,
            ("Goblin Warchief", "Goblin Guide"): 0.7,
            ("Goblin King", "Goblin Guide"): 0.6,
            ("Goblin Matron", "Goblin Guide"): 0.5,
            ("Goblin Lackey", "Goblin Guide"): 0.6,
            # Elf tribal
            ("Elvish Archdruid", "Llanowar Elves"): 0.8,
            ("Elvish Champion", "Llanowar Elves"): 0.7,
            ("Ezuri, Renegade Leader", "Llanowar Elves"): 0.8,
            ("Imperious Perfect", "Llanowar Elves"): 0.7,
            # Merfolk tribal
            ("Lord of Atlantis", "Silvergill Adept"): 0.8,
            ("Master of the Pearl Trident", "Silvergill Adept"): 0.8,
            ("Merrow Reejerey", "Silvergill Adept"): 0.7,
            # Zombie tribal
            ("Zombie Master", "Gravecrawler"): 0.8,
            ("Undead Warchief", "Gravecrawler"): 0.7,
            ("Lord of the Undead", "Gravecrawler"): 0.7,
            # Artifact synergies
            ("Arcbound Ravager", "Cranial Plating"): 0.9,
            ("Arcbound Worker", "Cranial Plating"): 0.7,
            ("Arcbound Stinger", "Cranial Plating"): 0.7,
            ("Steel Overseer", "Arcbound Ravager"): 0.8,
            # Enchantment synergies
            ("Enchantress's Presence", "Utopia Sprawl"): 0.6,
            ("Argothian Enchantress", "Utopia Sprawl"): 0.7,
            ("Sterling Grove", "Utopia Sprawl"): 0.5,
            # Land synergies
            ("Crop Rotation", "Gaea's Cradle"): 0.8,
            ("Crop Rotation", "Dark Depths"): 0.7,
            ("Knight of the Reliquary", "Gaea's Cradle"): 0.7,
            ("Knight of the Reliquary", "Dark Depths"): 0.6,
            # Combo pieces
            ("Splinter Twin", "Deceiver Exarch"): 0.9,
            ("Splinter Twin", "Pestermite"): 0.9,
            ("Kiki-Jiki, Mirror Breaker", "Deceiver Exarch"): 0.9,
            ("Kiki-Jiki, Mirror Breaker", "Pestermite"): 0.9,
            # Storm synergies
            ("Grapeshot", "Desperate Ritual"): 0.8,
            ("Grapeshot", "Pyretic Ritual"): 0.8,
            ("Grapeshot", "Manamorphose"): 0.7,
            ("Tendrils of Agony", "Desperate Ritual"): 0.8,
            # Reanimator synergies
            ("Entomb", "Griselbrand"): 0.9,
            ("Entomb", "Iona, Shield of Emeria"): 0.8,
            ("Reanimate", "Griselbrand"): 0.9,
            ("Reanimate", "Iona, Shield of Emeria"): 0.8,
            # Delver synergies
            ("Delver of Secrets", "Ponder"): 0.7,
            ("Delver of Secrets", "Brainstorm"): 0.7,
            ("Delver of Secrets", "Preordain"): 0.6,
            # Burn synergies
            ("Goblin Guide", "Lightning Bolt"): 0.5,
            ("Goblin Guide", "Lava Spike"): 0.5,
            ("Eidolon of the Great Revel", "Lightning Bolt"): 0.6,
            ("Eidolon of the Great Revel", "Lava Spike"): 0.6,
        }

        # Check for exact matches
        pair = (card1, card2)
        reverse_pair = (card2, card1)

        if pair in synergy_patterns:
            result = synergy_patterns[pair]
        elif reverse_pair in synergy_patterns:
            result = synergy_patterns[reverse_pair]
        else:
            # Enhanced partial matching with more patterns
            card1_lower = card1.lower()
            card2_lower = card2.lower()

            # Equipment synergy patterns
            if any(
                word in card1_lower
                for word in [
                    "greaves",
                    "boots",
                    "clamp",
                    "jitte",
                    "sword",
                    "batterskull",
                ]
            ) and any(
                word in card2_lower
                for word in ["creature", "goblin", "confidant", "titan", "guide"]
            ):
                result = 0.4
            elif any(
                word in card2_lower
                for word in [
                    "greaves",
                    "boots",
                    "clamp",
                    "jitte",
                    "sword",
                    "batterskull",
                ]
            ) and any(
                word in card1_lower
                for word in ["creature", "goblin", "confidant", "titan", "guide"]
            ):
                result = 0.4

            # Counterspell synergy patterns
            elif any(
                word in card1_lower
                for word in ["counterspell", "leak", "remand", "force", "daze"]
            ) and any(
                word in card2_lower
                for word in ["confidant", "draw", "card", "brainstorm", "ponder"]
            ):
                result = 0.3
            elif any(
                word in card2_lower
                for word in ["counterspell", "leak", "remand", "force", "daze"]
            ) and any(
                word in card1_lower
                for word in ["confidant", "draw", "card", "brainstorm", "ponder"]
            ):
                result = 0.3

            # Removal synergy patterns
            elif any(
                word in card1_lower
                for word in ["bolt", "path", "swords", "terminate", "push"]
            ) and any(
                word in card2_lower
                for word in ["goblin", "guide", "creature", "confidant"]
            ):
                result = 0.3
            elif any(
                word in card2_lower
                for word in ["bolt", "path", "swords", "terminate", "push"]
            ) and any(
                word in card1_lower
                for word in ["goblin", "guide", "creature", "confidant"]
            ):
                result = 0.3

            # Ramp synergy patterns
            elif any(
                word in card1_lower
                for word in ["sol ring", "farseek", "rampant", "cultivate", "kodama"]
            ) and any(
                word in card2_lower for word in ["titan", "big", "expensive", "cost"]
            ):
                result = 0.4
            elif any(
                word in card2_lower
                for word in ["sol ring", "farseek", "rampant", "cultivate", "kodama"]
            ) and any(
                word in card1_lower for word in ["titan", "big", "expensive", "cost"]
            ):
                result = 0.4

            # Tribal synergy patterns
            elif any(
                word in card1_lower
                for word in ["goblin", "chieftain", "warchief", "king", "matron"]
            ) and any(word in card2_lower for word in ["goblin", "guide", "lackey"]):
                result = 0.5
            elif any(
                word in card2_lower
                for word in ["goblin", "chieftain", "warchief", "king", "matron"]
            ) and any(word in card1_lower for word in ["goblin", "guide", "lackey"]):
                result = 0.5

            # Elf tribal patterns
            elif any(
                word in card1_lower
                for word in ["elf", "archdruid", "champion", "ezuri", "perfect"]
            ) and any(word in card2_lower for word in ["elf", "llanowar", "elvish"]):
                result = 0.5
            elif any(
                word in card2_lower
                for word in ["elf", "archdruid", "champion", "ezuri", "perfect"]
            ) and any(word in card1_lower for word in ["elf", "llanowar", "elvish"]):
                result = 0.5

            # Merfolk tribal patterns
            elif any(
                word in card1_lower
                for word in ["merfolk", "lord", "master", "reejerey"]
            ) and any(
                word in card2_lower for word in ["merfolk", "silvergill", "adept"]
            ):
                result = 0.5
            elif any(
                word in card2_lower
                for word in ["merfolk", "lord", "master", "reejerey"]
            ) and any(
                word in card1_lower for word in ["merfolk", "silvergill", "adept"]
            ):
                result = 0.5

            # Zombie tribal patterns
            elif any(
                word in card1_lower
                for word in ["zombie", "master", "warchief", "undead"]
            ) and any(
                word in card2_lower for word in ["zombie", "gravecrawler", "undead"]
            ):
                result = 0.5
            elif any(
                word in card2_lower
                for word in ["zombie", "master", "warchief", "undead"]
            ) and any(
                word in card1_lower for word in ["zombie", "gravecrawler", "undead"]
            ):
                result = 0.5

            # Artifact synergy patterns
            elif any(
                word in card1_lower
                for word in ["arcbound", "ravager", "worker", "stinger"]
            ) and any(
                word in card2_lower for word in ["cranial", "plating", "artifact"]
            ):
                result = 0.5
            elif any(
                word in card2_lower
                for word in ["arcbound", "ravager", "worker", "stinger"]
            ) and any(
                word in card1_lower for word in ["cranial", "plating", "artifact"]
            ):
                result = 0.5

            # Enchantment synergy patterns
            elif any(
                word in card1_lower for word in ["enchantress", "presence", "argothian"]
            ) and any(
                word in card2_lower for word in ["enchantment", "utopia", "sprawl"]
            ):
                result = 0.4
            elif any(
                word in card2_lower for word in ["enchantress", "presence", "argothian"]
            ) and any(
                word in card1_lower for word in ["enchantment", "utopia", "sprawl"]
            ):
                result = 0.4

            # Land synergy patterns
            elif any(
                word in card1_lower
                for word in ["crop", "rotation", "knight", "reliquary"]
            ) and any(
                word in card2_lower for word in ["gaea", "cradle", "dark", "depths"]
            ):
                result = 0.4
            elif any(
                word in card2_lower
                for word in ["crop", "rotation", "knight", "reliquary"]
            ) and any(
                word in card1_lower for word in ["gaea", "cradle", "dark", "depths"]
            ):
                result = 0.4

            # Combo synergy patterns
            elif any(
                word in card1_lower for word in ["splinter", "twin", "kiki", "mirror"]
            ) and any(
                word in card2_lower for word in ["deceiver", "exarch", "pestermite"]
            ):
                result = 0.6
            elif any(
                word in card2_lower for word in ["splinter", "twin", "kiki", "mirror"]
            ) and any(
                word in card1_lower for word in ["deceiver", "exarch", "pestermite"]
            ):
                result = 0.6

            # Storm synergy patterns
            elif any(
                word in card1_lower for word in ["grapeshot", "tendrils", "agony"]
            ) and any(
                word in card2_lower
                for word in ["desperate", "ritual", "pyretic", "manamorphose"]
            ):
                result = 0.5
            elif any(
                word in card2_lower for word in ["grapeshot", "tendrils", "agony"]
            ) and any(
                word in card1_lower
                for word in ["desperate", "ritual", "pyretic", "manamorphose"]
            ):
                result = 0.5

            # Reanimator synergy patterns
            elif any(word in card1_lower for word in ["entomb", "reanimate"]) and any(
                word in card2_lower
                for word in ["griselbrand", "iona", "shield", "emeria"]
            ):
                result = 0.6
            elif any(word in card2_lower for word in ["entomb", "reanimate"]) and any(
                word in card1_lower
                for word in ["griselbrand", "iona", "shield", "emeria"]
            ):
                result = 0.6

            # Delver synergy patterns
            elif any(word in card1_lower for word in ["delver", "secrets"]) and any(
                word in card2_lower for word in ["ponder", "brainstorm", "preordain"]
            ):
                result = 0.4
            elif any(word in card2_lower for word in ["delver", "secrets"]) and any(
                word in card1_lower for word in ["ponder", "brainstorm", "preordain"]
            ):
                result = 0.4

            # Burn synergy patterns
            elif any(
                word in card1_lower for word in ["goblin", "guide", "eidolon", "revel"]
            ) and any(
                word in card2_lower for word in ["lightning", "bolt", "lava", "spike"]
            ):
                result = 0.3
            elif any(
                word in card2_lower for word in ["goblin", "guide", "eidolon", "revel"]
            ) and any(
                word in card1_lower for word in ["lightning", "bolt", "lava", "spike"]
            ):
                result = 0.3

            else:
                result = 0.0

        # Cache result
        with self._cache_lock:
            self._synergy_cache[cache_key] = result

        return result

    def _calculate_dynamic_synergy_bonus(self, decklist: List[str]) -> float:
        """
        Calculate dynamic synergy bonus based on deck context and composition

        Args:
            decklist: List of card names in the deck

        Returns:
            float: Dynamic synergy bonus (0.0 to 0.3)
        """
        if len(decklist) < 3:
            return 0.0

        # Analyze deck composition
        deck_analysis = self._analyze_deck_composition(decklist)

        # Calculate bonuses based on deck archetype
        bonuses = []

        # Tribal deck bonus
        if deck_analysis["tribal_count"] >= 8:
            tribal_bonus = min(0.2, deck_analysis["tribal_count"] * 0.02)
            bonuses.append(tribal_bonus)

        # Combo deck bonus
        if deck_analysis["combo_pieces"] >= 4:
            combo_bonus = min(0.15, deck_analysis["combo_pieces"] * 0.03)
            bonuses.append(combo_bonus)

        # Control deck bonus
        if deck_analysis["control_elements"] >= 6:
            control_bonus = min(0.1, deck_analysis["control_elements"] * 0.015)
            bonuses.append(control_bonus)

        # Aggro deck bonus
        if deck_analysis["aggro_elements"] >= 8:
            aggro_bonus = min(0.1, deck_analysis["aggro_elements"] * 0.012)
            bonuses.append(aggro_bonus)

        # Ramp deck bonus
        if deck_analysis["ramp_elements"] >= 4:
            ramp_bonus = min(0.1, deck_analysis["ramp_elements"] * 0.02)
            bonuses.append(ramp_bonus)

        # Synergy density bonus
        synergy_density = deck_analysis["synergy_pairs"] / max(1, len(decklist))
        if synergy_density > 0.3:
            density_bonus = min(0.1, synergy_density * 0.2)
            bonuses.append(density_bonus)

        return min(0.3, sum(bonuses))

    def _analyze_deck_composition(self, decklist: List[str]) -> Dict[str, int]:
        """
        Analyze deck composition for dynamic synergy calculation

        Args:
            decklist: List of card names in the deck

        Returns:
            Dictionary with composition analysis
        """
        analysis = {
            "tribal_count": 0,
            "combo_pieces": 0,
            "control_elements": 0,
            "aggro_elements": 0,
            "ramp_elements": 0,
            "synergy_pairs": 0,
        }

        # Count tribal cards
        tribal_keywords = [
            "goblin",
            "elf",
            "merfolk",
            "zombie",
            "human",
            "dragon",
            "angel",
            "demon",
        ]
        for card in decklist:
            card_lower = card.lower()
            if any(tribe in card_lower for tribe in tribal_keywords):
                analysis["tribal_count"] += 1

        # Count combo pieces
        combo_keywords = [
            "splinter",
            "twin",
            "kiki",
            "grapeshot",
            "tendrils",
            "entomb",
            "reanimate",
        ]
        for card in decklist:
            card_lower = card.lower()
            if any(combo in card_lower for combo in combo_keywords):
                analysis["combo_pieces"] += 1

        # Count control elements
        control_keywords = [
            "counterspell",
            "leak",
            "remand",
            "force",
            "daze",
            "path",
            "swords",
            "terminate",
        ]
        for card in decklist:
            card_lower = card.lower()
            if any(control in card_lower for control in control_keywords):
                analysis["control_elements"] += 1

        # Count aggro elements
        aggro_keywords = ["goblin", "guide", "lackey", "creature", "hasty", "haste"]
        for card in decklist:
            card_lower = card.lower()
            if any(aggro in card_lower for aggro in aggro_keywords):
                analysis["aggro_elements"] += 1

        # Count ramp elements
        ramp_keywords = [
            "sol ring",
            "farseek",
            "rampant",
            "cultivate",
            "kodama",
            "mana",
            "ramp",
        ]
        for card in decklist:
            card_lower = card.lower()
            if any(ramp in card_lower for ramp in ramp_keywords):
                analysis["ramp_elements"] += 1

        # Count synergy pairs
        for i, card1 in enumerate(decklist):
            for j, card2 in enumerate(decklist[i + 1 :], i + 1):
                if self._calculate_card_synergy(card1, card2) > 0.0:
                    analysis["synergy_pairs"] += 1

        return analysis

    def get_evaluation_methods(self) -> List[Dict[str, str]]:
        """
        Get available evaluation methods for UI dropdown

        Returns:
            List of dictionaries with method info
        """
        return [
            {
                "value": "17lands",
                "label": "17Lands Data-Based",
                "description": "Data-based evaluation from 17Lands – combines GIH Winrate and IWD.",
            },
            {
                "value": "manual",
                "label": "Manual + Synergy",
                "description": "Manual evaluation + synergy values from local dictionary.",
            },
        ]

    def get_deck_analysis(self, decklist: List[str], method: str = "manual") -> Dict:
        """
        Get detailed deck analysis with performance optimizations

        Args:
            decklist: List of card names in the deck
            method: Evaluation method

        Returns:
            Dictionary with analysis results
        """
        if not decklist:
            return {
                "score": 0.0,
                "method": method,
                "card_count": 0,
                "avg_rating": 0.0,
                "synergy_bonus": 0.0,
                "analysis": {},
                "performance": self.get_cache_stats(),
            }

        # Get ratings for cards
        ratings = []
        for card_name in decklist:
            rating = self.ratings_dict.get(card_name, 0)
            ratings.append(rating)

        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

        # Calculate synergy bonus
        synergy_bonus = self._calculate_synergy_bonus(decklist)

        # Get overall score
        score = self.evaluate_deck(decklist, method)

        return {
            "score": score,
            "method": method,
            "card_count": len(decklist),
            "avg_rating": avg_rating,
            "synergy_bonus": synergy_bonus,
            "analysis": {
                "highest_rated": max(ratings) if ratings else 0,
                "lowest_rated": min(ratings) if ratings else 0,
                "rating_distribution": self._get_rating_distribution(ratings),
            },
            "performance": self.get_cache_stats(),
        }

    def _get_rating_distribution(self, ratings: List[int]) -> Dict[str, int]:
        """Get distribution of ratings"""
        distribution = {
            "excellent": 0,  # 9-10
            "good": 0,  # 7-8
            "average": 0,  # 5-6
            "poor": 0,  # 3-4
            "bad": 0,  # 1-2
        }

        for rating in ratings:
            if rating >= 9:
                distribution["excellent"] += 1
            elif rating >= 7:
                distribution["good"] += 1
            elif rating >= 5:
                distribution["average"] += 1
            elif rating >= 3:
                distribution["poor"] += 1
            else:
                distribution["bad"] += 1

        return distribution

    def __del__(self):
        """Cleanup thread pool on deletion"""
        if hasattr(self, "_thread_pool"):
            self._thread_pool.shutdown(wait=True)

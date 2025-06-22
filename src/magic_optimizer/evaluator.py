"""
Deck Evaluation Module

This module provides different methods for evaluating deck quality:
1. 17Lands data-based evaluation (game_in_hand_win_rate + improvement_when_drawn)
2. Manual evaluation with synergy bonuses
3. Interface for selecting evaluation methods
"""

import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class DeckEvaluator:
    """Main deck evaluator class with multiple evaluation methods"""

    def __init__(self, ratings_file: str = "data/ratings/card_ratings.csv"):
        """Initialize evaluator with card ratings"""
        self.ratings_file = ratings_file
        self.ratings_df = None
        self.ratings_dict = {}
        self._load_ratings()

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

    def evaluate_deck(self, decklist: List[str], method: str = "manual") -> float:
        """
        Main evaluation interface

        Args:
            decklist: List of card names in the deck
            method: Evaluation method ("17lands" or "manual")

        Returns:
            float: Deck score (0.0 to 1.0)
        """
        if method == "17lands":
            return self.evaluate_deck_17lands(decklist)
        elif method == "manual":
            return self.evaluate_deck_manual(decklist)
        else:
            logger.warning(f"Unknown evaluation method: {method}. Using manual.")
            return self.evaluate_deck_manual(decklist)

    def evaluate_deck_17lands(self, decklist: List[str]) -> float:
        """
        Evaluate deck using 17Lands data

        This method would use game_in_hand_win_rate and improvement_when_drawn
        from 17Lands data. For now, we'll simulate this with the existing ratings.

        Args:
            decklist: List of card names in the deck

        Returns:
            float: Deck score (0.0 to 1.0)
        """
        if not decklist:
            return 0.0

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

    def evaluate_deck_manual(self, decklist: List[str]) -> float:
        """
        Evaluate deck using manual ratings and synergy bonuses

        Args:
            decklist: List of card names in the deck

        Returns:
            float: Deck score (0.0 to 1.0)
        """
        if not decklist:
            return 0.0

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

        # Calculate synergy bonus
        synergy_bonus = self._calculate_synergy_bonus(decklist)

        # Combine base score with synergy bonus
        total_score = base_score + synergy_bonus

        return max(0.0, min(1.0, total_score))

    def _calculate_synergy_bonus(self, decklist: List[str]) -> float:
        """
        Calculate synergy bonus between cards

        Args:
            decklist: List of card names in the deck

        Returns:
            float: Synergy bonus (0.0 to 0.2)
        """
        if len(decklist) < 2:
            return 0.0

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

    def _calculate_card_synergy(self, card1: str, card2: str) -> float:
        """
        Calculate synergy between two specific cards

        Args:
            card1: First card name
            card2: Second card name

        Returns:
            float: Synergy score (0.0 to 1.0)
        """
        # Define synergy patterns
        synergy_patterns = {
            # Creature + Equipment
            ("Lightning Greaves", "Sol Ring"): 0.8,
            ("Lightning Greaves", "Dark Confidant"): 0.7,
            ("Skullclamp", "Dark Confidant"): 0.9,
            # Counterspell + Card draw
            ("Counterspell", "Dark Confidant"): 0.6,
            ("Mana Leak", "Dark Confidant"): 0.6,
            # Removal + Aggro
            ("Lightning Bolt", "Goblin Guide"): 0.5,
            ("Path to Exile", "Goblin Guide"): 0.5,
            # Ramp + Big spells
            ("Sol Ring", "Primeval Titan"): 0.7,
            ("Farseek", "Primeval Titan"): 0.6,
        }

        # Check for exact matches
        pair = (card1, card2)
        reverse_pair = (card2, card1)

        if pair in synergy_patterns:
            return synergy_patterns[pair]
        elif reverse_pair in synergy_patterns:
            return synergy_patterns[reverse_pair]

        # Check for partial matches (cards with similar functions)
        card1_lower = card1.lower()
        card2_lower = card2.lower()

        # Equipment synergy
        if any(word in card1_lower for word in ["greaves", "boots", "clamp"]) and any(
            word in card2_lower for word in ["creature", "goblin", "confidant"]
        ):
            return 0.3

        # Counterspell synergy
        if any(
            word in card1_lower for word in ["counterspell", "leak", "remand"]
        ) and any(word in card2_lower for word in ["confidant", "draw", "card"]):
            return 0.2

        # Removal synergy
        if any(word in card1_lower for word in ["bolt", "path", "swords"]) and any(
            word in card2_lower for word in ["goblin", "guide", "creature"]
        ):
            return 0.2

        return 0.0

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
                "description": "Datenbasierte Bewertung aus 17Lands – kombiniert GIH Winrate und IWD.",
            },
            {
                "value": "manual",
                "label": "Manual + Synergy",
                "description": "Manuelle Bewertung + Synergiewerte aus lokalem Dictionary.",
            },
        ]

    def get_deck_analysis(self, decklist: List[str], method: str = "manual") -> Dict:
        """
        Get detailed deck analysis

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

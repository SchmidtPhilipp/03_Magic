"""
Base optimizer class for deck optimization algorithms.
"""

import itertools
import random
from abc import ABC, abstractmethod
from typing import Dict, List, Set, Tuple, Optional

import numpy as np
import pandas as pd

from ..card import Card
from ..evaluators.base_evaluator import BaseCardEvaluator
from ..validator import CardValidator


class BaseOptimizer(ABC):
    """Base class for all deck optimization algorithms."""
    
    def __init__(self, evaluator: BaseCardEvaluator):
        """Initialize base optimizer with evaluation system."""
        self.evaluator = evaluator
        self.validator = CardValidator()
        
        # Cache for card data to avoid repeated API calls
        self.card_data_cache = {}

    def get_card_data(self, card_name: str) -> Dict:
        """Get complete card data using Scryfall API with caching"""
        if card_name in self.card_data_cache:
            return self.card_data_cache[card_name]

        try:
            card_data = self.validator.search_card(card_name)
            if card_data:
                self.card_data_cache[card_name] = card_data
                return card_data
            else:
                self.card_data_cache[card_name] = {}
                return {}
        except Exception as e:
            self.card_data_cache[card_name] = {}
            return {}

    def calculate_deck_score(
        self,
        deck: List[Card],
        target_colors: List[str],
        deck_size: int = 40,
        max_colors: int = 2,
        lambda_penalty: float = 0.5,
    ) -> float:
        """
        Calculate comprehensive deck score based on multiple factors
        """
        if not deck:
            return 0.0

        # Extract card names for the evaluator
        card_names = [card.name for card in deck]

        # 1. Rating Score (35% weight) - now uses the evaluator
        rating_score = self.evaluator.get_deck_rating(card_names) * 0.35

        # 2. Mana Curve Score (20% weight)
        mana_curve = self.calculate_mana_curve(deck)
        curve_score = self.evaluate_mana_curve(mana_curve, deck_size) * 0.20

        # 3. Color Balance Score (15% weight) - now uses actual colors in deck
        actual_colors = self.get_deck_colors(deck)
        color_score = self.evaluate_color_balance_dynamic(deck, actual_colors) * 0.15

        # 4. Synergy Score (10% weight)
        synergy_score = self.calculate_synergy_score(deck) * 0.10

        # 5. Card Type Balance Score (5% weight)
        type_score = self.evaluate_card_type_balance(deck) * 0.05

        # 6. Dynamic Color Constraint Penalty
        color_penalty = (
            self.calculate_dynamic_color_penalty(deck, max_colors, lambda_penalty)
            * 0.30
        )

        total_score = (
            rating_score
            + curve_score
            + color_score
            + synergy_score
            + type_score
            - color_penalty
        )

        return max(0.0, total_score)  # Ensure non-negative score

    def calculate_normalized_deck_score(
        self,
        deck: List[Card],
        target_colors: List[str],
        deck_size: int = 40,
        max_colors: int = 2,
        lambda_penalty: float = 0.5,
    ) -> float:
        """
        Calculate normalized deck score where all components are on 0-1 scale
        This ensures lambda penalty is effective regardless of rating scale
        """
        if not deck:
            return 0.0

        # Extract card names for the evaluator
        card_names = [card.name for card in deck]

        # 1. Normalized Rating Score (35% weight)
        raw_rating = self.evaluator.get_deck_rating(card_names)
        # Normalize to 0-1 scale (assuming ratings are typically 0-10)
        normalized_rating = min(1.0, raw_rating / 10.0) if raw_rating > 0 else 0.0
        rating_score = normalized_rating * 0.35

        # 2. Mana Curve Score (20% weight) - already 0-1
        mana_curve = self.calculate_mana_curve(deck)
        curve_score = self.evaluate_mana_curve(mana_curve, deck_size) * 0.20

        # 3. Color Balance Score (15% weight) - already 0-1
        actual_colors = self.get_deck_colors(deck)
        color_score = self.evaluate_color_balance_dynamic(deck, actual_colors) * 0.15

        # 4. Synergy Score (10% weight) - already 0-1
        synergy_score = self.calculate_synergy_score(deck) * 0.10

        # 5. Card Type Balance Score (5% weight) - already 0-1
        type_score = self.evaluate_card_type_balance(deck) * 0.05

        # 6. Normalized Color Constraint Penalty (15% weight)
        # This is now more significant since all components are normalized
        color_penalty = (
            self.calculate_dynamic_color_penalty(deck, max_colors, lambda_penalty)
            * 0.15
        )

        total_score = (
            rating_score
            + curve_score
            + color_score
            + synergy_score
            + type_score
            - color_penalty
        )

        return max(0.0, total_score)  # Ensure non-negative score

    def calculate_mana_curve(self, deck: List[Card]) -> Dict[int, int]:
        """Calculate the mana curve distribution"""
        curve = {i: 0 for i in range(8)}  # 0-7+ CMC

        for card in deck:
            cmc = card.cmc
            if cmc >= 7:
                curve[7] += 1
            else:
                curve[int(cmc)] += 1

        return curve

    def evaluate_mana_curve(self, curve: Dict[int, int], deck_size: int) -> float:
        """Evaluate mana curve quality"""
        non_land_cards = deck_size - (deck_size // 3)  # 33% lands

        # Ideal curve distribution (percentages)
        ideal_curve = {
            0: 0.05,  # 5% 0-drops
            1: 0.15,  # 15% 1-drops
            2: 0.25,  # 25% 2-drops
            3: 0.25,  # 25% 3-drops
            4: 0.20,  # 20% 4-drops
            5: 0.08,  # 8% 5-drops
            6: 0.02,  # 2% 6-drops
            7: 0.00,  # 0% 7+ drops
        }

        score = 0.0
        for cmc in range(8):
            actual_ratio = curve[cmc] / non_land_cards if non_land_cards > 0 else 0
            ideal_ratio = ideal_curve[cmc]

            # Penalty for deviation from ideal
            deviation = abs(actual_ratio - ideal_ratio)
            score += (1.0 - deviation) * ideal_ratio

        return max(0.0, score)

    def get_deck_colors(self, deck: List[Card]) -> List[str]:
        """Get the actual colors used in the deck"""
        colors_used = set()
        for card in deck:
            colors_used.update(card.colors)
        return sorted(list(colors_used))

    def evaluate_color_balance_dynamic(
        self, deck: List[Card], actual_colors: List[str]
    ) -> float:
        """Evaluate color balance using the actual colors in the deck"""
        if not actual_colors:
            return 0.0

        color_counts = {color: 0 for color in actual_colors}
        colorless_count = 0

        for card in deck:
            colors = card.colors
            if not colors:
                colorless_count += 1
            else:
                for color in colors:
                    if color in actual_colors:
                        color_counts[color] += 1

        # Calculate balance score
        total_colored = sum(color_counts.values())
        if total_colored == 0:
            return 0.0

        # Penalty for uneven distribution
        avg_per_color = total_colored / len(actual_colors)
        variance = sum((count - avg_per_color) ** 2 for count in color_counts.values())
        balance_score = 1.0 / (1.0 + variance)

        # Bonus for having cards in all colors
        color_coverage = sum(1 for count in color_counts.values() if count > 0) / len(
            actual_colors
        )

        return (balance_score + color_coverage) / 2.0

    def calculate_synergy_score(self, deck: List[Card]) -> float:
        """Calculate synergy between cards"""
        synergy_score = 0.0
        synergy_pairs = 0

        # Look for common synergy patterns
        for i, card1 in enumerate(deck):
            for j, card2 in enumerate(deck[i + 1 :], i + 1):
                synergy = self.calculate_card_synergy(card1, card2)
                synergy_score += synergy
                synergy_pairs += 1

        return synergy_score / max(1, synergy_pairs)

    def calculate_card_synergy(self, card1: Card, card2: Card) -> float:
        """Calculate synergy between two specific cards"""
        synergy = 0.0

        # Tribal synergies
        if self.has_tribal_synergy(card1, card2):
            synergy += 0.3

        # Spell synergies
        if self.has_spell_synergy(card1, card2):
            synergy += 0.2

        # Color synergies
        if self.has_color_synergy(card1, card2):
            synergy += 0.1

        # Mana curve synergies
        if self.has_curve_synergy(card1, card2):
            synergy += 0.1

        return min(1.0, synergy)

    def has_tribal_synergy(self, card1: Card, card2: Card) -> bool:
        """Check if two cards have tribal synergy"""
        creature_types = ["Human", "Elf", "Goblin", "Zombie", "Dragon", "Merfolk"]

        type1 = card1.main_type
        type2 = card2.main_type

        for creature_type in creature_types:
            if creature_type in type1 and creature_type in type2:
                return True
        return False

    def has_spell_synergy(self, card1: Card, card2: Card) -> bool:
        """Check for synergies between spells and permanents"""
        if "Instant" in card1.main_type or "Sorcery" in card1.main_type:
            return False
        return False

    def has_color_synergy(self, card1: Card, card2: Card) -> bool:
        """Check for cards that benefit from sharing colors"""
        if card1.colors and card1.colors == card2.colors:
            return True
        return False

    def has_curve_synergy(self, card1: Card, card2: Card) -> bool:
        """Check for cards that curve well into each other"""
        if card1.cmc == card2.cmc - 1:
            return True
        return False

    def evaluate_card_type_balance(self, deck: List[Card]) -> float:
        """Evaluate the balance of card types (creatures, spells, etc.)"""
        creatures = 0
        spells = 0
        lands = 0

        for card in deck:
            card_type = card.main_type
            if "Creature" in card_type:
                creatures += 1
            elif "Land" not in card_type:
                spells += 1
            elif "Land" in card_type:
                lands += 1

        total_non_land = creatures + spells
        if total_non_land == 0:
            return 0.0

        creature_ratio = creatures / total_non_land
        spell_ratio = spells / total_non_land

        # Ideal ratios for a 40-card deck (23 non-lands)
        ideal_creature_ratio = 17 / 23
        ideal_spell_ratio = 6 / 23

        creature_score = 1.0 - abs(creature_ratio - ideal_creature_ratio)
        spell_score = 1.0 - abs(spell_ratio - ideal_spell_ratio)

        return (creature_score + spell_score) / 2.0

    def calculate_dynamic_color_penalty(
        self, deck: List[Card], max_colors: int, lambda_penalty: float = 0.5
    ) -> float:
        """Calculate a penalty for exceeding the desired number of colors."""
        colors_in_deck = self.get_deck_colors(deck)
        num_colors_in_deck = len(colors_in_deck)

        if num_colors_in_deck <= max_colors:
            return 0.0  # No penalty

        # Calculate how many pips of "extra" colors are present
        color_pips = {color: 0 for color in "WUBRG"}
        for card in deck:
            for color in card.colors:
                if color in color_pips:
                    color_pips[color] += 1

        # Sort colors by pip count
        sorted_colors = sorted(color_pips.items(), key=lambda item: item[1], reverse=True)

        # Main colors are the `max_colors` with the most pips
        main_colors = {color for color, count in sorted_colors[:max_colors]}

        # Penalty is based on pips from non-main colors
        penalty_pips = 0
        for color, count in sorted_colors[max_colors:]:
            penalty_pips += count

        total_pips = sum(color_pips.values())
        if total_pips == 0:
            return 0.0

        penalty_ratio = penalty_pips / total_pips

        # Apply lambda to control the penalty harshness
        return penalty_ratio * lambda_penalty

    def prepare_eligible_cards(
        self,
        collection_df: pd.DataFrame,
        num_colors: int,
    ) -> List[Card]:
        """Prepare a list of all cards from the collection with necessary data."""
        print(f"Preparing eligible cards...")

        # Handle different possible column names for card name
        card_name_col = "Name" if "Name" in collection_df.columns else "Card Name"

        card_list: List[Card] = []
        total_cards = 0

        for _, row in collection_df.iterrows():
            card_name = row[card_name_col]
            if not isinstance(card_name, str):
                continue
                
            # Get quantity - default to 1 if not specified
            quantity = 1
            if "Quantity" in collection_df.columns:
                try:
                    quantity = int(row["Quantity"])
                    if quantity < 1:
                        quantity = 1
                except (ValueError, TypeError):
                    quantity = 1
            
            card_data = self.get_card_data(card_name)
            if not card_data:
                continue

            # Add the card the specified number of times
            for _ in range(quantity):
                card_obj = Card(card_data)
                # Use game mechanics evaluator if selected
                if hasattr(self.evaluator, 'evaluate_card'):
                    card_obj.rating = int(self.evaluator.evaluate_card(card_obj))
                else:
                    card_obj.rating = int(self.evaluator.get_card_rating(card_name))
                card_obj.optimization_score = card_obj.rating  # Use rating as optimization score
                card_list.append(card_obj)
            
            total_cards += quantity

        print(f"Prepared {len(card_list)} card objects from {total_cards} total cards in collection")
        return card_list

    def select_target_colors(
        self,
        eligible_cards: List[Card],
        num_colors: int,
        fixed_colors: Optional[List[str]] = None,
    ) -> List[str]:
        """Select the best color combination based on card ratings."""
        if fixed_colors:
            print(f"Using fixed colors: {fixed_colors}")
            
            # If we have fewer fixed colors than requested, find additional colors
            if len(fixed_colors) < num_colors:
                print(f"Need {num_colors - len(fixed_colors)} more colors to reach {num_colors} total")
                
                # Get all available colors from eligible cards
                all_colors = set()
                for card in eligible_cards:
                    all_colors.update(card.colors)
                
                # Remove already fixed colors
                available_colors = all_colors - set(fixed_colors)
                
                if available_colors:
                    # Find the best additional colors by evaluating combinations
                    best_additional_colors = []
                    remaining_slots = num_colors - len(fixed_colors)
                    
                    # Try all combinations of available colors
                    for combo in itertools.combinations(available_colors, min(remaining_slots, len(available_colors))):
                        test_colors = list(fixed_colors) + list(combo)
                        combo_score = self.evaluate_color_combo(eligible_cards, test_colors)
                        
                        if len(best_additional_colors) == 0 or combo_score > best_score:
                            best_additional_colors = list(combo)
                            best_score = combo_score
                    
                    # Add the best additional colors
                    if best_additional_colors:
                        final_colors = fixed_colors + best_additional_colors
                        print(f"Added colors: {best_additional_colors}")
                        print(f"Final color combination: {final_colors}")
                        return sorted(final_colors)
                    else:
                        print(f"Could not find additional colors, using only fixed colors: {fixed_colors}")
                        return sorted(fixed_colors)
                else:
                    print(f"No additional colors available, using only fixed colors: {fixed_colors}")
                    return sorted(fixed_colors)
            else:
                # We have enough or too many fixed colors, return the requested number
                return sorted(fixed_colors[:num_colors])

        # No fixed colors, find the best combination
        color_combinations = self.get_color_combinations(eligible_cards, num_colors)

        best_combo = []
        max_score = -1.0

        for combo in color_combinations:
            combo_score = self.evaluate_color_combo(eligible_cards, combo)
            if combo_score > max_score:
                max_score = combo_score
                best_combo = combo

        return sorted(list(best_combo))

    def get_color_combinations(self, eligible_cards: List[Card], num_colors) -> List[List[str]]:
        """Get all possible color combinations"""
        all_colors = set()
        for card in eligible_cards:
            all_colors.update(card.colors)

        if not all_colors:
            return [[]]  # No colors found

        # Generate combinations of size up to num_colors
        combos = []
        for i in range(1, num_colors + 1):
            combos.extend(itertools.combinations(sorted(list(all_colors)), i))

        return [list(c) for c in combos]

    def evaluate_color_combo(self, eligible_cards: List[Card], combo: List[str]) -> float:
        """Evaluate a color combination by summing the top card ratings"""
        combo_cards = [
            card
            for card in eligible_cards
            if not card.colors or card.colors.issubset(set(combo))
        ]
        combo_cards.sort(key=lambda x: x.rating, reverse=True)
        return sum(c.rating for c in combo_cards[:40])  # Top 40 cards

    @abstractmethod
    def optimize_deck(
        self,
        collection_df: pd.DataFrame,
        num_colors: int = 2,
        deck_size: int = 40,
        lambda_penalty: float = 0.5,
        fixed_colors: Optional[List[str]] = None,
    ) -> Dict:
        """Main optimization method to be implemented by each algorithm."""
        pass 
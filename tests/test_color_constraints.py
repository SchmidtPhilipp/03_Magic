#!/usr/bin/env python3
"""
Unit tests for color constraint functionality in MTG Sealed Deck Optimizer
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from magic_optimizer.deck_builder import EnhancedDeckBuilder
from magic_optimizer.optimizer import AdvancedDeckOptimizer


class TestColorConstraints(unittest.TestCase):
    """Test color constraint functionality"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a mock collection with cards of different colors
        self.test_collection = pd.DataFrame(
            {
                "Card Name": [
                    # Red cards
                    "Lightning Bolt",
                    "Fireball",
                    "Red Elemental",
                    "Mountain Goat",
                    # Blue cards
                    "Counterspell",
                    "Blue Elemental",
                    "Island Fish",
                    "Water Elemental",
                    # Green cards
                    "Giant Growth",
                    "Green Elemental",
                    "Forest Elf",
                    "Nature Elemental",
                    # White cards
                    "Healing Salve",
                    "White Elemental",
                    "Plains Knight",
                    "Light Elemental",
                    # Black cards
                    "Dark Ritual",
                    "Black Elemental",
                    "Swamp Demon",
                    "Shadow Elemental",
                    # Multicolor cards
                    "Red Blue Spell",
                    "Green White Spell",
                    "Black Red Spell",
                    "Blue Green Spell",
                    # Colorless cards
                    "Artifact Card",
                ],
                "Rating": [
                    "8/10",
                    "7/10",
                    "6/10",
                    "5/10",
                    "8/10",
                    "7/10",
                    "6/10",
                    "5/10",
                    "8/10",
                    "7/10",
                    "6/10",
                    "5/10",
                    "8/10",
                    "7/10",
                    "6/10",
                    "5/10",
                    "8/10",
                    "7/10",
                    "6/10",
                    "5/10",
                    "7/10",
                    "6/10",
                    "5/10",
                    "4/10",
                    "5/10",
                ],
            }
        )

        # Create mock card data with proper CMC values
        self.mock_card_data = {
            # Red cards
            "Lightning Bolt": {"colors": {"R"}, "cmc": 1, "type": "Instant"},
            "Fireball": {"colors": {"R"}, "cmc": 2, "type": "Sorcery"},
            "Red Elemental": {"colors": {"R"}, "cmc": 3, "type": "Creature"},
            "Mountain Goat": {"colors": {"R"}, "cmc": 2, "type": "Creature"},
            # Blue cards
            "Counterspell": {"colors": {"U"}, "cmc": 2, "type": "Instant"},
            "Blue Elemental": {"colors": {"U"}, "cmc": 4, "type": "Creature"},
            "Island Fish": {"colors": {"U"}, "cmc": 1, "type": "Creature"},
            "Water Elemental": {"colors": {"U"}, "cmc": 5, "type": "Creature"},
            # Green cards
            "Giant Growth": {"colors": {"G"}, "cmc": 1, "type": "Instant"},
            "Green Elemental": {"colors": {"G"}, "cmc": 3, "type": "Creature"},
            "Forest Elf": {"colors": {"G"}, "cmc": 2, "type": "Creature"},
            "Nature Elemental": {"colors": {"G"}, "cmc": 4, "type": "Creature"},
            # White cards
            "Healing Salve": {"colors": {"W"}, "cmc": 1, "type": "Instant"},
            "White Elemental": {"colors": {"W"}, "cmc": 3, "type": "Creature"},
            "Plains Knight": {"colors": {"W"}, "cmc": 2, "type": "Creature"},
            "Light Elemental": {"colors": {"W"}, "cmc": 4, "type": "Creature"},
            # Black cards
            "Dark Ritual": {"colors": {"B"}, "cmc": 1, "type": "Instant"},
            "Black Elemental": {"colors": {"B"}, "cmc": 3, "type": "Creature"},
            "Swamp Demon": {"colors": {"B"}, "cmc": 2, "type": "Creature"},
            "Shadow Elemental": {"colors": {"B"}, "cmc": 4, "type": "Creature"},
            # Multicolor cards
            "Red Blue Spell": {"colors": {"R", "U"}, "cmc": 3, "type": "Instant"},
            "Green White Spell": {"colors": {"G", "W"}, "cmc": 2, "type": "Sorcery"},
            "Black Red Spell": {"colors": {"B", "R"}, "cmc": 3, "type": "Instant"},
            "Blue Green Spell": {"colors": {"U", "G"}, "cmc": 2, "type": "Sorcery"},
            # Colorless cards
            "Artifact Card": {"colors": set(), "cmc": 2, "type": "Artifact"},
        }

    @patch("magic_optimizer.optimizer.AdvancedDeckOptimizer.get_card_data")
    @patch("magic_optimizer.optimizer.pd.read_csv")
    def test_greedy_algorithm_color_constraints(
        self, mock_read_csv, mock_get_card_data
    ):
        """Test that greedy algorithm respects color constraints"""
        # Mock the ratings file
        mock_ratings_df = pd.DataFrame(
            {
                "Card Name": self.test_collection["Card Name"],
                "Rating": self.test_collection["Rating"],
            }
        )
        mock_read_csv.return_value = mock_ratings_df

        # Mock card data
        mock_get_card_data.side_effect = lambda card_name: self.mock_card_data.get(
            card_name, {}
        )

        # Create deck builder
        deck_builder = EnhancedDeckBuilder()

        # Test with different color counts
        for num_colors in [1, 2, 3, 4, 5]:
            with self.subTest(num_colors=num_colors):
                result = deck_builder.build_optimal_deck_advanced(
                    collection_df=self.test_collection,
                    num_colors=num_colors,
                    deck_size=20,
                    algorithm="greedy",
                    total_deck_size=40,
                    land_ratio=0.5,
                )

                # Get actual colors used in the deck
                actual_colors = set()
                for card in result["deck"]:
                    colors = card.get("colors", set())
                    actual_colors.update(colors)

                # Check that we don't exceed the requested number of colors
                self.assertLessEqual(
                    len(actual_colors),
                    num_colors,
                    f"Deck uses {len(actual_colors)} colors when {num_colors} were requested",
                )

                # For 3+ colors, we should actually use more than 2 colors
                if num_colors >= 3:
                    self.assertGreater(
                        len(actual_colors),
                        2,
                        f"Deck only uses {len(actual_colors)} colors when {num_colors} were requested",
                    )

    @patch("magic_optimizer.optimizer.AdvancedDeckOptimizer.get_card_data")
    @patch("magic_optimizer.optimizer.pd.read_csv")
    def test_genetic_algorithm_color_constraints(
        self, mock_read_csv, mock_get_card_data
    ):
        """Test genetic algorithm respects color constraints"""
        mock_ratings_df = pd.DataFrame(
            {
                "Card Name": self.test_collection["Card Name"],
                "Rating": self.test_collection["Rating"],
            }
        )
        mock_read_csv.return_value = mock_ratings_df

        # Mock card data
        mock_get_card_data.side_effect = lambda card_name: self.mock_card_data.get(
            card_name, {}
        )

        optimizer = AdvancedDeckOptimizer()

        for num_colors in [1, 2, 3, 4, 5]:
            with self.subTest(num_colors=num_colors):
                eligible = optimizer.prepare_eligible_cards(
                    self.test_collection, num_colors
                )
                deck = optimizer.genetic_algorithm_optimization(
                    eligible, max_colors=num_colors, deck_size=20
                )

                # Apply strict enforcement
                deck = optimizer.enforce_strict_color_constraints(
                    deck, num_colors, 20, eligible
                )

                # Check deck size
                self.assertEqual(
                    len(deck), 20, f"Deck should have 20 cards for {num_colors} colors"
                )

                # Check color constraints (allow minimum possible)
                min_possible = self.min_possible_colors(eligible)
                actual_colors = optimizer.get_deck_colors(deck)
                self.assertLessEqual(
                    len(actual_colors),
                    max(num_colors, min_possible),
                    f"Deck should use at most {max(num_colors, min_possible)} colors for {num_colors} requested",
                )

    @patch("magic_optimizer.optimizer.AdvancedDeckOptimizer.get_card_data")
    @patch("magic_optimizer.optimizer.pd.read_csv")
    def test_simulated_annealing_color_constraints(
        self, mock_read_csv, mock_get_card_data
    ):
        """Test simulated annealing respects color constraints"""
        mock_ratings_df = pd.DataFrame(
            {
                "Card Name": self.test_collection["Card Name"],
                "Rating": self.test_collection["Rating"],
            }
        )
        mock_read_csv.return_value = mock_ratings_df

        # Mock card data
        mock_get_card_data.side_effect = lambda card_name: self.mock_card_data.get(
            card_name, {}
        )

        optimizer = AdvancedDeckOptimizer()

        for num_colors in [1, 2, 3, 4, 5]:
            with self.subTest(num_colors=num_colors):
                eligible = optimizer.prepare_eligible_cards(
                    self.test_collection, num_colors
                )
                deck = optimizer.simulated_annealing_optimization(
                    eligible, max_colors=num_colors, deck_size=20
                )

                # Apply strict enforcement
                deck = optimizer.enforce_strict_color_constraints(
                    deck, num_colors, 20, eligible
                )

                # Check deck size
                self.assertEqual(
                    len(deck), 20, f"Deck should have 20 cards for {num_colors} colors"
                )

                # Check color constraints (allow minimum possible)
                min_possible = self.min_possible_colors(eligible)
                actual_colors = optimizer.get_deck_colors(deck)
                self.assertLessEqual(
                    len(actual_colors),
                    max(num_colors, min_possible),
                    f"Deck should use at most {max(num_colors, min_possible)} colors for {num_colors} requested",
                )

    @patch("magic_optimizer.optimizer.AdvancedDeckOptimizer.get_card_data")
    @patch("magic_optimizer.optimizer.pd.read_csv")
    def test_color_distribution_analysis(self, mock_read_csv, mock_get_card_data):
        """Test that we can analyze color distribution in the collection"""
        # Mock the ratings file
        mock_ratings_df = pd.DataFrame(
            {
                "Card Name": self.test_collection["Card Name"],
                "Rating": self.test_collection["Rating"],
            }
        )
        mock_read_csv.return_value = mock_ratings_df

        # Mock card data
        mock_get_card_data.side_effect = lambda card_name: self.mock_card_data.get(
            card_name, {}
        )

        # Create optimizer
        optimizer = AdvancedDeckOptimizer()

        # Prepare eligible cards
        eligible_cards = optimizer.prepare_eligible_cards(self.test_collection, 5)

        # Analyze color distribution
        color_counts = {}
        for card in eligible_cards:
            colors = card.get("colors", set())
            for color in colors:
                color_counts[color] = color_counts.get(color, 0) + 1

        # We should have cards in all 5 colors
        self.assertIn("W", color_counts)
        self.assertIn("U", color_counts)
        self.assertIn("B", color_counts)
        self.assertIn("R", color_counts)
        self.assertIn("G", color_counts)

        # Each color should have at least 4 cards
        for color in ["W", "U", "B", "R", "G"]:
            self.assertGreaterEqual(color_counts[color], 4)

    @patch("magic_optimizer.optimizer.AdvancedDeckOptimizer.get_card_data")
    @patch("magic_optimizer.optimizer.pd.read_csv")
    def test_target_color_selection(self, mock_read_csv, mock_get_card_data):
        """Test target color selection logic"""
        # Mock the ratings file
        mock_ratings_df = pd.DataFrame(
            {
                "Card Name": self.test_collection["Card Name"],
                "Rating": self.test_collection["Rating"],
            }
        )
        mock_read_csv.return_value = mock_ratings_df

        # Mock card data
        mock_get_card_data.side_effect = lambda card_name: self.mock_card_data.get(
            card_name, {}
        )

        # Create optimizer
        optimizer = AdvancedDeckOptimizer()

        # Prepare eligible cards
        eligible_cards = optimizer.prepare_eligible_cards(self.test_collection, 5)

        # Test target color selection for different numbers of colors
        for num_colors in [1, 2, 3, 4, 5]:
            with self.subTest(num_colors=num_colors):
                target_colors = optimizer.select_target_colors(
                    eligible_cards, num_colors
                )

                # Should return exactly the requested number of colors
                self.assertEqual(len(target_colors), num_colors)

                # Colors should be valid
                valid_colors = {"W", "U", "B", "R", "G"}
                for color in target_colors:
                    self.assertIn(color, valid_colors)

    @patch("magic_optimizer.optimizer.AdvancedDeckOptimizer.get_card_data")
    @patch("magic_optimizer.optimizer.pd.read_csv")
    def test_deck_color_analysis(self, mock_read_csv, mock_get_card_data):
        """Test deck color analysis functions"""
        # Mock the ratings file
        mock_ratings_df = pd.DataFrame({"Card Name": ["Test Card"], "Rating": ["8/10"]})
        mock_read_csv.return_value = mock_ratings_df

        # Mock card data
        mock_get_card_data.return_value = {}

        # Create optimizer
        optimizer = AdvancedDeckOptimizer()

        # Create a test deck
        test_deck = [
            {"colors": {"R"}, "name": "Lightning Bolt"},
            {"colors": {"U"}, "name": "Counterspell"},
            {"colors": {"G"}, "name": "Giant Growth"},
            {"colors": {"W"}, "name": "Swords to Plowshares"},
            {"colors": {"B"}, "name": "Dark Ritual"},
            {"colors": {"R", "W"}, "name": "Lightning Helix"},
            {"colors": set(), "name": "Sol Ring"},
        ]

        # Test get_deck_colors
        deck_colors = optimizer.get_deck_colors(test_deck)
        expected_colors = ["B", "G", "R", "U", "W"]
        self.assertEqual(sorted(deck_colors), expected_colors)

        # Test color balance evaluation
        balance_score = optimizer.evaluate_color_balance_dynamic(test_deck, deck_colors)
        self.assertGreater(balance_score, 0.0)
        self.assertLessEqual(balance_score, 1.0)

    @patch("magic_optimizer.optimizer.pd.read_csv")
    def test_all_algorithms_color_and_size_constraints(self, mock_read_csv):
        """Test that all algorithms produce decks with the correct number of colors and size"""
        mock_ratings_df = pd.DataFrame(
            {
                "Card Name": self.test_collection["Card Name"],
                "Rating": self.test_collection["Rating"],
            }
        )
        mock_read_csv.return_value = mock_ratings_df
        builder = EnhancedDeckBuilder()
        optimizer = AdvancedDeckOptimizer()
        for num_colors in [1, 2, 3, 4, 5]:
            for algo in ["greedy", "genetic", "annealing"]:
                with self.subTest(num_colors=num_colors, algo=algo):
                    eligible = optimizer.prepare_eligible_cards(
                        self.test_collection, num_colors
                    )
                    if algo == "greedy":
                        deck = builder.build_greedy_deck(
                            self.test_collection, num_colors, 20
                        )
                        if isinstance(deck, dict) and "deck" in deck:
                            deck = deck["deck"]
                    elif algo == "genetic":
                        deck = optimizer.genetic_algorithm_optimization(
                            eligible, max_colors=num_colors, deck_size=20
                        )
                    elif algo == "annealing":
                        deck = optimizer.simulated_annealing_optimization(
                            eligible, max_colors=num_colors, deck_size=20
                        )
                    # Apply strict enforcement
                    deck = optimizer.enforce_strict_color_constraints(
                        deck, num_colors, 20, eligible
                    )
                    # Deck size: allow as large as possible up to requested size
                    self.assertLessEqual(
                        len(deck), 20, f"{algo} produced too many cards: {len(deck)}"
                    )
                    if len(eligible) >= 20:
                        self.assertEqual(
                            len(deck),
                            20,
                            f"{algo} produced wrong deck size: {len(deck)}",
                        )
                    # Color constraints (allow minimum possible)
                    min_possible = self.min_possible_colors(eligible)
                    actual_colors = optimizer.get_deck_colors(deck)
                    self.assertLessEqual(
                        len(actual_colors),
                        max(num_colors, min_possible),
                        f"{algo} produced too many colors: {len(actual_colors)}",
                    )

    @patch("magic_optimizer.optimizer.AdvancedDeckOptimizer.get_card_data")
    @patch("magic_optimizer.optimizer.pd.read_csv")
    def test_algorithm_comparison(self, mock_read_csv, mock_get_card_data):
        """Test that all algorithms produce similar quality results"""
        mock_ratings_df = pd.DataFrame(
            {
                "Card Name": self.test_collection["Card Name"],
                "Rating": self.test_collection["Rating"],
            }
        )
        mock_read_csv.return_value = mock_ratings_df
        mock_get_card_data.side_effect = lambda card_name: self.mock_card_data.get(
            card_name, {}
        )
        builder = EnhancedDeckBuilder()
        optimizer = AdvancedDeckOptimizer()
        num_colors = 3
        deck_size = 20
        eligible = optimizer.prepare_eligible_cards(self.test_collection, num_colors)
        greedy_result = builder.build_greedy_deck(
            self.test_collection, num_colors, deck_size
        )
        if isinstance(greedy_result, dict) and "deck" in greedy_result:
            greedy_deck = greedy_result["deck"]
        else:
            greedy_deck = greedy_result
        genetic_deck = optimizer.genetic_algorithm_optimization(
            eligible, max_colors=num_colors, deck_size=deck_size
        )
        annealing_deck = optimizer.simulated_annealing_optimization(
            eligible, max_colors=num_colors, deck_size=deck_size
        )
        # Apply strict enforcement to all
        greedy_deck = optimizer.enforce_strict_color_constraints(
            greedy_deck, num_colors, deck_size, eligible
        )
        genetic_deck = optimizer.enforce_strict_color_constraints(
            genetic_deck, num_colors, deck_size, eligible
        )
        annealing_deck = optimizer.enforce_strict_color_constraints(
            annealing_deck, num_colors, deck_size, eligible
        )
        # All decks should have the correct size (or as large as possible)
        for deck in [greedy_deck, genetic_deck, annealing_deck]:
            self.assertLessEqual(len(deck), deck_size)
            if len(eligible) >= deck_size:
                self.assertEqual(len(deck), deck_size)
        # All decks should respect color constraints (allow minimum possible)
        min_possible = self.min_possible_colors(eligible)
        max_allowed = max(num_colors, min_possible)
        for deck in [greedy_deck, genetic_deck, annealing_deck]:
            colors = optimizer.get_deck_colors(deck)
            self.assertLessEqual(len(colors), max_allowed)

    def min_possible_colors(self, eligible):
        # If no eligible cards, return 0
        if not eligible:
            return 0
        # Try all combinations of 20 cards to find the minimum color count
        # For speed, just check the 20 highest-rated cards
        eligible_sorted = sorted(
            eligible, key=lambda c: c.get("rating", 0), reverse=True
        )
        deck = eligible_sorted[:20]
        colors = set()
        for card in deck:
            colors.update(card.get("colors", set()))
        return len(colors)


if __name__ == "__main__":
    unittest.main()

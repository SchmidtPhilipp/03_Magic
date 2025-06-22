"""
Test the new evaluation methods functionality
"""

import os
import sys
import unittest

import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from magic_optimizer.deck_builder import EnhancedDeckBuilder
from magic_optimizer.evaluator import DeckEvaluator
from magic_optimizer.optimizer import AdvancedDeckOptimizer


class TestEvaluationMethods(unittest.TestCase):
    """Test the new evaluation methods"""

    def setUp(self):
        """Set up test data"""
        # Create test ratings
        test_ratings = [
            {"Card Name": "Lightning Bolt", "Rating": "9/10"},
            {"Card Name": "Counterspell", "Rating": "8/10"},
            {"Card Name": "Dark Confidant", "Rating": "9/10"},
            {"Card Name": "Sol Ring", "Rating": "10/10"},
            {"Card Name": "Goblin Guide", "Rating": "7/10"},
            {"Card Name": "Path to Exile", "Rating": "8/10"},
            {"Card Name": "Lightning Greaves", "Rating": "8/10"},
            {"Card Name": "Skullclamp", "Rating": "9/10"},
        ]

        self.test_ratings_df = pd.DataFrame(test_ratings)
        self.test_ratings_file = "test_ratings.csv"
        self.test_ratings_df.to_csv(self.test_ratings_file, index=False)

        # Create test collection
        test_collection = [
            {"Card Name": "Lightning Bolt", "Quantity": 1},
            {"Card Name": "Counterspell", "Quantity": 1},
            {"Card Name": "Dark Confidant", "Quantity": 1},
            {"Card Name": "Sol Ring", "Quantity": 1},
            {"Card Name": "Goblin Guide", "Quantity": 1},
            {"Card Name": "Path to Exile", "Quantity": 1},
            {"Card Name": "Lightning Greaves", "Quantity": 1},
            {"Card Name": "Skullclamp", "Quantity": 1},
        ]

        self.test_collection_df = pd.DataFrame(test_collection)

    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.test_ratings_file):
            os.remove(self.test_ratings_file)

    def test_evaluator_initialization(self):
        """Test DeckEvaluator initialization"""
        evaluator = DeckEvaluator(self.test_ratings_file)

        self.assertIsNotNone(evaluator.ratings_df)
        self.assertEqual(len(evaluator.ratings_dict), 8)
        self.assertIn("Lightning Bolt", evaluator.ratings_dict)
        self.assertEqual(evaluator.ratings_dict["Lightning Bolt"], 9)

    def test_manual_evaluation(self):
        """Test manual evaluation method"""
        evaluator = DeckEvaluator(self.test_ratings_file)

        decklist = ["Lightning Bolt", "Counterspell", "Dark Confidant"]
        score = evaluator.evaluate_deck_manual(decklist)

        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)

        # Test with synergy cards
        synergy_decklist = ["Lightning Greaves", "Dark Confidant", "Skullclamp"]
        synergy_score = evaluator.evaluate_deck_manual(synergy_decklist)

        # Synergy deck should have higher score
        self.assertGreaterEqual(synergy_score, score)

    def test_17lands_evaluation(self):
        """Test 17Lands evaluation method"""
        evaluator = DeckEvaluator(self.test_ratings_file)

        decklist = ["Lightning Bolt", "Counterspell", "Dark Confidant"]
        score = evaluator.evaluate_deck_17lands(decklist)

        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_evaluation_interface(self):
        """Test the main evaluation interface"""
        evaluator = DeckEvaluator(self.test_ratings_file)

        decklist = ["Lightning Bolt", "Counterspell", "Dark Confidant"]

        # Test manual method
        manual_score = evaluator.evaluate_deck(decklist, "manual")
        self.assertGreater(manual_score, 0.0)

        # Test 17lands method
        lands_score = evaluator.evaluate_deck(decklist, "17lands")
        self.assertGreater(lands_score, 0.0)

        # Test unknown method (should default to manual)
        default_score = evaluator.evaluate_deck(decklist, "unknown")
        self.assertEqual(default_score, manual_score)

    def test_synergy_calculation(self):
        """Test synergy calculation"""
        evaluator = DeckEvaluator(self.test_ratings_file)

        # Test known synergy pair
        synergy = evaluator._calculate_card_synergy(
            "Lightning Greaves", "Dark Confidant"
        )
        self.assertGreater(synergy, 0.0)

        # Test non-synergy pair
        no_synergy = evaluator._calculate_card_synergy("Lightning Bolt", "Counterspell")
        self.assertEqual(no_synergy, 0.0)

    def test_deck_analysis(self):
        """Test deck analysis functionality"""
        evaluator = DeckEvaluator(self.test_ratings_file)

        decklist = ["Lightning Bolt", "Counterspell", "Dark Confidant", "Sol Ring"]
        analysis = evaluator.get_deck_analysis(decklist, "manual")

        self.assertIn("score", analysis)
        self.assertIn("method", analysis)
        self.assertIn("card_count", analysis)
        self.assertIn("avg_rating", analysis)
        self.assertIn("synergy_bonus", analysis)
        self.assertIn("analysis", analysis)

        self.assertEqual(analysis["card_count"], 4)
        self.assertEqual(analysis["method"], "manual")

    def test_evaluation_methods_list(self):
        """Test getting evaluation methods for UI"""
        evaluator = DeckEvaluator(self.test_ratings_file)
        methods = evaluator.get_evaluation_methods()

        self.assertEqual(len(methods), 2)

        # Check 17Lands method
        lands_method = next(m for m in methods if m["value"] == "17lands")
        self.assertEqual(lands_method["label"], "17Lands Data-Based")
        self.assertIn("GIH Winrate", lands_method["description"])

        # Check manual method
        manual_method = next(m for m in methods if m["value"] == "manual")
        self.assertEqual(manual_method["label"], "Manual + Synergy")
        self.assertIn("Synergiewerte", manual_method["description"])

    def test_optimizer_integration(self):
        """Test integration with AdvancedDeckOptimizer"""
        optimizer = AdvancedDeckOptimizer(self.test_ratings_file)

        # Test getting evaluation methods
        methods = optimizer.get_evaluation_methods()
        self.assertEqual(len(methods), 2)

        # Test deck analysis
        test_deck = [
            {"name": "Lightning Bolt", "colors": {"R"}, "rating": 9, "cmc": 1},
            {"name": "Counterspell", "colors": {"U"}, "rating": 8, "cmc": 2},
        ]

        analysis = optimizer.get_deck_analysis(test_deck, "manual")
        self.assertIn("score", analysis)

    def test_deck_builder_integration(self):
        """Test integration with EnhancedDeckBuilder"""
        builder = EnhancedDeckBuilder(self.test_ratings_file)

        # Test getting evaluation methods
        methods = builder.optimizer.get_evaluation_methods()
        self.assertEqual(len(methods), 2)

        # Test building deck with different evaluation methods
        result_manual = builder.build_optimal_deck_advanced(
            self.test_collection_df, 2, 6, "greedy", [], 0.5, None, None, "manual"
        )

        result_17lands = builder.build_optimal_deck_advanced(
            self.test_collection_df, 2, 6, "greedy", [], 0.5, None, None, "17lands"
        )

        self.assertIn("evaluation_method", result_manual)
        self.assertIn("evaluation_method", result_17lands)
        self.assertEqual(result_manual["evaluation_method"], "manual")
        self.assertEqual(result_17lands["evaluation_method"], "17lands")


if __name__ == "__main__":
    unittest.main()

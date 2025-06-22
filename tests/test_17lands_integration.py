"""
Test 17Lands API Integration

This module tests the 17Lands API integration, caching, and evaluation methods.
"""

import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from src.magic_optimizer.evaluator import DeckEvaluator, SeventeenLandsAPI


class TestSeventeenLandsAPI(unittest.TestCase):
    """Test 17Lands API client functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, "17lands_cache.json")
        self.api = SeventeenLandsAPI(self.cache_file)

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)

    def test_api_initialization(self):
        """Test API client initialization"""
        self.assertIsNotNone(self.api.cache)
        self.assertIsNotNone(self.api.cache_lock)
        self.assertEqual(self.api.cache_file, self.cache_file)

    def test_cache_operations(self):
        """Test cache operations"""
        # Test cache stats
        stats = self.api.get_cache_stats()
        self.assertIn("total_entries", stats)
        self.assertIn("cache_file", stats)
        self.assertEqual(stats["total_entries"], 0)

        # Test cache clearing
        self.api.clear_cache()
        stats_after = self.api.get_cache_stats()
        self.assertEqual(stats_after["total_entries"], 0)

    @patch("requests.get")
    def test_get_card_data_success(self, mock_get):
        """Test successful card data retrieval"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "name": "Lightning Bolt",
                "game_in_hand_win_rate": 0.65,
                "improvement_when_drawn": 0.05,
                "avg_seen": 2.5,
                "avg_pick": 1.8,
                "drawn_win_rate": 0.68,
                "ever_drawn_win_rate": 0.67,
            }
        ]
        mock_get.return_value = mock_response

        # Get card data
        result = self.api.get_card_data("Lightning Bolt")

        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Lightning Bolt")
        self.assertEqual(result["game_in_hand_win_rate"], 0.65)
        self.assertEqual(result["improvement_when_drawn"], 0.05)

        # Verify cache was updated
        stats = self.api.get_cache_stats()
        self.assertEqual(stats["total_entries"], 1)

    @patch("requests.get")
    def test_get_card_data_not_found(self, mock_get):
        """Test card data retrieval when card not found"""
        # Mock successful API response with empty data
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        # Get card data for non-existent card
        result = self.api.get_card_data("NonExistentCard")

        # Verify empty result
        self.assertEqual(result, {})

        # Verify cache was updated with empty entry
        stats = self.api.get_cache_stats()
        self.assertEqual(stats["total_entries"], 1)

    @patch("requests.get")
    def test_get_card_data_api_error(self, mock_get):
        """Test card data retrieval with API error"""
        # Mock API error
        mock_get.side_effect = Exception("API Error")

        # Get card data
        result = self.api.get_card_data("Lightning Bolt")

        # Verify empty result
        self.assertEqual(result, {})

    def test_cache_persistence(self):
        """Test that cache persists between API instances"""
        # Add some test data to cache
        test_data = {
            "Lightning Bolt_PremierDraft": {
                "name": "Lightning Bolt",
                "game_in_hand_win_rate": 0.65,
                "improvement_when_drawn": 0.05,
            }
        }

        with open(self.cache_file, "w") as f:
            json.dump(test_data, f)

        # Create new API instance
        new_api = SeventeenLandsAPI(self.cache_file)

        # Verify cache was loaded
        stats = new_api.get_cache_stats()
        self.assertEqual(stats["total_entries"], 1)

        # Verify data is accessible
        result = new_api.get_card_data("Lightning Bolt")
        self.assertEqual(result["name"], "Lightning Bolt")


class Test17LandsEvaluation(unittest.TestCase):
    """Test 17Lands evaluation integration"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

        # Create test ratings file
        self.ratings_file = os.path.join(self.temp_dir, "test_ratings.csv")
        ratings_data = {
            "Card Name": ["Lightning Bolt", "Counterspell", "Dark Confidant"],
            "Rating": ["8/10", "7/10", "7/10"],
        }
        pd.DataFrame(ratings_data).to_csv(self.ratings_file, index=False)

        # Create test collection
        self.collection_data = {
            "Card Name": [
                "Lightning Bolt",
                "Counterspell",
                "Dark Confidant",
                "Sol Ring",
            ],
            "Quantity": [4, 4, 4, 4],
            "Rating": ["8/10", "7/10", "7/10", "6/10"],
        }
        self.collection_df = pd.DataFrame(self.collection_data)

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)

    @patch("src.magic_optimizer.evaluator.SeventeenLandsAPI.get_card_data")
    def test_17lands_evaluation_with_mock_data(self, mock_get_data):
        """Test 17Lands evaluation with mocked API data"""
        # Mock 17Lands API responses
        mock_get_data.side_effect = [
            {
                "name": "Lightning Bolt",
                "game_in_hand_win_rate": 0.65,
                "improvement_when_drawn": 0.05,
            },
            {
                "name": "Counterspell",
                "game_in_hand_win_rate": 0.58,
                "improvement_when_drawn": 0.03,
            },
            {
                "name": "Dark Confidant",
                "game_in_hand_win_rate": 0.62,
                "improvement_when_drawn": 0.04,
            },
        ]

        # Create evaluator
        evaluator = DeckEvaluator(self.ratings_file)

        # Test 17Lands evaluation
        decklist = ["Lightning Bolt", "Counterspell", "Dark Confidant"]
        score = evaluator.evaluate_deck(decklist, "17lands")

        # Verify score is calculated correctly
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)

        # Verify API was called for each card
        self.assertEqual(mock_get_data.call_count, 3)

    @patch("src.magic_optimizer.evaluator.SeventeenLandsAPI.get_card_data")
    def test_17lands_evaluation_fallback(self, mock_get_data):
        """Test 17Lands evaluation with fallback to manual ratings"""
        # Mock empty API responses (cards not found in 17Lands)
        mock_get_data.return_value = {}

        # Create evaluator
        evaluator = DeckEvaluator(self.ratings_file)

        # Test 17Lands evaluation
        decklist = ["Lightning Bolt", "Counterspell", "Dark Confidant"]
        score = evaluator.evaluate_deck(decklist, "17lands")

        # Verify score is calculated using fallback ratings
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)

        # Verify API was called for each card
        self.assertEqual(mock_get_data.call_count, 3)

    def test_evaluation_method_comparison(self):
        """Test comparison between manual and 17Lands evaluation"""
        evaluator = DeckEvaluator(self.ratings_file)
        decklist = ["Lightning Bolt", "Counterspell", "Dark Confidant"]

        # Test both evaluation methods
        manual_score = evaluator.evaluate_deck(decklist, "manual")
        lands_score = evaluator.evaluate_deck(decklist, "17lands")

        # Both should return valid scores
        self.assertGreater(manual_score, 0.0)
        self.assertLessEqual(manual_score, 1.0)
        self.assertGreater(lands_score, 0.0)
        self.assertLessEqual(lands_score, 1.0)

    def test_cache_integration(self):
        """Test that evaluation results are cached"""
        evaluator = DeckEvaluator(self.ratings_file)
        decklist = ["Lightning Bolt", "Counterspell", "Dark Confidant"]

        # Get initial cache stats
        initial_stats = evaluator.get_cache_stats()

        # First evaluation
        score1 = evaluator.evaluate_deck(decklist, "manual")
        stats1 = evaluator.get_cache_stats()

        # Second evaluation (should use cache)
        score2 = evaluator.evaluate_deck(decklist, "manual")
        stats2 = evaluator.get_cache_stats()

        # Scores should be identical
        self.assertEqual(score1, score2)

        # Cache should have been used
        self.assertGreaterEqual(
            stats2["evaluation_cache_size"], stats1["evaluation_cache_size"]
        )

    def test_parallel_evaluation(self):
        """Test parallel evaluation for large decks"""
        evaluator = DeckEvaluator(self.ratings_file)

        # Create large deck
        large_deck = (
            ["Lightning Bolt"] * 20 + ["Counterspell"] * 20 + ["Dark Confidant"] * 20
        )

        # Test 17Lands evaluation with parallel processing
        score = evaluator.evaluate_deck_17lands(large_deck)

        # Verify score is valid
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_cache_clearing(self):
        """Test cache clearing functionality"""
        evaluator = DeckEvaluator(self.ratings_file)
        decklist = ["Lightning Bolt", "Counterspell", "Dark Confidant"]

        # Add some data to cache
        evaluator.evaluate_deck(decklist, "manual")
        initial_stats = evaluator.get_cache_stats()

        # Clear caches
        evaluator.clear_caches()
        final_stats = evaluator.get_cache_stats()

        # Verify caches were cleared
        self.assertEqual(final_stats["evaluation_cache_size"], 0)
        self.assertEqual(final_stats["synergy_cache_size"], 0)
        self.assertEqual(final_stats["total_entries"], 0)


if __name__ == "__main__":
    unittest.main()

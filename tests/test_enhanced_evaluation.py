"""
Tests for the enhanced evaluation system with performance optimizations and advanced synergy detection
"""

import os
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from magic_optimizer.evaluator import DeckEvaluator


class TestEnhancedEvaluationSystem(unittest.TestCase):
    """Test the enhanced evaluation system with performance optimizations"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary ratings file
        self.temp_dir = tempfile.mkdtemp()
        self.ratings_file = os.path.join(self.temp_dir, "test_ratings.csv")

        # Create test ratings data
        test_data = {
            "Card Name": [
                "Goblin Guide",
                "Lightning Bolt",
                "Dark Confidant",
                "Sol Ring",
                "Primeval Titan",
                "Counterspell",
                "Goblin Chieftain",
                "Elvish Archdruid",
                "Splinter Twin",
                "Deceiver Exarch",
                "Grapeshot",
                "Desperate Ritual",
                "Arcbound Ravager",
                "Cranial Plating",
                "Delver of Secrets",
                "Ponder",
            ],
            "Rating": [
                "8/10",
                "9/10",
                "8/10",
                "9/10",
                "8/10",
                "8/10",
                "7/10",
                "7/10",
                "8/10",
                "6/10",
                "7/10",
                "6/10",
                "8/10",
                "7/10",
                "7/10",
                "7/10",
            ],
        }

        df = pd.DataFrame(test_data)
        df.to_csv(self.ratings_file, index=False)

        # Initialize evaluator
        self.evaluator = DeckEvaluator(self.ratings_file)

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_performance_caching_initialization(self):
        """Test that performance optimizations are properly initialized"""
        self.assertIsNotNone(self.evaluator._synergy_cache)
        self.assertIsNotNone(self.evaluator.deck_evaluation_cache)

    def test_cache_operations(self):
        """Test cache operations"""
        # Test cache stats
        stats = self.evaluator.get_cache_stats()
        self.assertIn("synergy_cache", stats)
        self.assertIn("deck_evaluation_cache", stats)
        self.assertIn("17lands_cache", stats)

    def test_evaluation_caching(self):
        """Test that evaluation results are properly cached"""
        decklist = ["Goblin Guide", "Lightning Bolt", "Dark Confidant"]

        # First evaluation should cache the result
        score1 = self.evaluator.evaluate_deck(decklist, "manual")
        stats1 = self.evaluator.get_cache_stats()

        # Second evaluation should use cache
        score2 = self.evaluator.evaluate_deck(decklist, "manual")
        stats2 = self.evaluator.get_cache_stats()

        # Scores should be identical
        self.assertEqual(score1, score2)

        # Cache should have been used (size should remain the same)
        self.assertEqual(
            stats2["deck_evaluation_cache"]["size"],
            stats1["deck_evaluation_cache"]["size"],
        )

    def test_synergy_caching(self):
        """Test that synergy calculations are properly cached"""
        decklist = ["Goblin Guide", "Goblin Chieftain", "Lightning Bolt"]

        # First synergy calculation should cache the result
        bonus1 = self.evaluator._calculate_synergy_bonus(decklist)
        stats1 = self.evaluator.get_cache_stats()

        # Second calculation should use cache
        bonus2 = self.evaluator._calculate_synergy_bonus(decklist)
        stats2 = self.evaluator.get_cache_stats()

        # Bonuses should be identical
        self.assertEqual(bonus1, bonus2)

        # Cache should have been used
        self.assertEqual(
            stats2["synergy_cache"]["size"], stats1["synergy_cache"]["size"]
        )

    def test_enhanced_tribal_synergies(self):
        """Test enhanced tribal synergy detection"""
        # Goblin tribal synergy
        goblin_synergy = self.evaluator._calculate_card_synergy(
            "Goblin Guide", "Goblin Chieftain"
        )
        self.assertGreater(goblin_synergy, 0.0)

        # Elf tribal synergy
        elf_synergy = self.evaluator._calculate_card_synergy(
            "Elvish Archdruid", "Llanowar Elves"
        )
        self.assertGreater(elf_synergy, 0.0)

        # Non-tribal cards should have no synergy
        no_synergy = self.evaluator._calculate_card_synergy(
            "Lightning Bolt", "Counterspell"
        )
        self.assertEqual(no_synergy, 0.0)

    def test_enhanced_combo_synergies(self):
        """Test enhanced combo synergy detection"""
        # Splinter Twin combo
        twin_synergy = self.evaluator._calculate_card_synergy(
            "Splinter Twin", "Deceiver Exarch"
        )
        self.assertGreater(twin_synergy, 0.0)

        # Storm combo
        storm_synergy = self.evaluator._calculate_card_synergy(
            "Grapeshot", "Desperate Ritual"
        )
        self.assertGreater(storm_synergy, 0.0)

        # Non-combo cards should have no synergy (using cards that don't have any synergy patterns)
        no_synergy = self.evaluator._calculate_card_synergy("Counterspell", "Sol Ring")
        self.assertEqual(no_synergy, 0.0)

    def test_enhanced_equipment_synergies(self):
        """Test enhanced equipment synergy detection"""
        # Equipment + creature synergy
        equipment_synergy = self.evaluator._calculate_card_synergy(
            "Lightning Greaves", "Goblin Guide"
        )
        self.assertGreater(equipment_synergy, 0.0)

        # Artifact synergy
        artifact_synergy = self.evaluator._calculate_card_synergy(
            "Arcbound Ravager", "Cranial Plating"
        )
        self.assertGreater(artifact_synergy, 0.0)

    def test_dynamic_synergy_bonus(self):
        """Test dynamic synergy bonus calculation"""
        # Tribal deck
        tribal_deck = [
            "Goblin Guide",
            "Goblin Chieftain",
            "Goblin Warchief",
            "Goblin King",
            "Goblin Matron",
            "Goblin Lackey",
            "Lightning Bolt",
            "Lightning Bolt",
        ]
        tribal_bonus = self.evaluator._calculate_dynamic_synergy_bonus(tribal_deck)
        self.assertGreater(tribal_bonus, 0.0)

        # Combo deck
        combo_deck = [
            "Splinter Twin",
            "Deceiver Exarch",
            "Pestermite",
            "Kiki-Jiki, Mirror Breaker",
            "Grapeshot",
            "Desperate Ritual",
            "Pyretic Ritual",
            "Manamorphose",
        ]
        combo_bonus = self.evaluator._calculate_dynamic_synergy_bonus(combo_deck)
        self.assertGreater(combo_bonus, 0.0)

        # Control deck
        control_deck = [
            "Counterspell",
            "Mana Leak",
            "Remand",
            "Force of Will",
            "Daze",
            "Path to Exile",
            "Swords to Plowshares",
            "Terminate",
        ]
        control_bonus = self.evaluator._calculate_dynamic_synergy_bonus(control_deck)
        self.assertGreater(control_bonus, 0.0)

        # Random deck should have minimal bonus
        random_deck = ["Goblin Guide", "Lightning Bolt", "Counterspell", "Sol Ring"]
        random_bonus = self.evaluator._calculate_dynamic_synergy_bonus(random_deck)
        self.assertLessEqual(random_bonus, 0.1)

    def test_deck_composition_analysis(self):
        """Test deck composition analysis"""
        deck = [
            "Goblin Guide",
            "Goblin Chieftain",
            "Goblin Warchief",
            "Lightning Bolt",
            "Splinter Twin",
            "Deceiver Exarch",
            "Counterspell",
            "Sol Ring",
        ]

        analysis = self.evaluator._analyze_deck_composition(deck)

        self.assertIn("tribal_count", analysis)
        self.assertIn("combo_pieces", analysis)
        self.assertIn("control_elements", analysis)
        self.assertIn("aggro_elements", analysis)
        self.assertIn("ramp_elements", analysis)
        self.assertIn("synergy_pairs", analysis)

        # Should detect tribal elements
        self.assertGreater(analysis["tribal_count"], 0)

        # Should detect combo pieces
        self.assertGreater(analysis["combo_pieces"], 0)

        # Should detect control elements
        self.assertGreater(analysis["control_elements"], 0)

    def test_parallel_processing_large_decks(self):
        """Test parallel processing for large decks"""
        # Create a large deck
        large_deck = (
            ["Goblin Guide"] * 10
            + ["Lightning Bolt"] * 10
            + ["Counterspell"] * 10
            + ["Sol Ring"] * 10
        )

        # Test 17Lands evaluation with parallel processing
        score_17lands = self.evaluator.evaluate_deck_17lands(large_deck)
        self.assertGreaterEqual(score_17lands, 0.0)
        self.assertLessEqual(score_17lands, 1.0)

        # Test manual evaluation with parallel processing
        score_manual = self.evaluator.evaluate_deck_manual(large_deck)
        self.assertGreaterEqual(score_manual, 0.0)
        self.assertLessEqual(score_manual, 1.0)

    def test_enhanced_deck_analysis(self):
        """Test enhanced deck analysis with performance metrics"""
        deck = ["Goblin Guide", "Goblin Chieftain", "Lightning Bolt", "Counterspell"]

        analysis = self.evaluator.get_deck_analysis(deck, "manual")

        self.assertIn("score", analysis)
        self.assertIn("method", analysis)
        self.assertIn("card_count", analysis)
        self.assertIn("avg_rating", analysis)
        self.assertIn("synergy_bonus", analysis)
        self.assertIn("analysis", analysis)
        self.assertIn("performance", analysis)

        # Check performance metrics
        performance = analysis["performance"]
        self.assertIn("synergy_cache", performance)
        self.assertIn("deck_evaluation_cache", performance)

        # Check analysis details
        analysis_details = analysis["analysis"]
        self.assertIn("highest_rated", analysis_details)
        self.assertIn("lowest_rated", analysis_details)
        self.assertIn("rating_distribution", analysis_details)

    def test_rating_distribution(self):
        """Test rating distribution calculation"""
        ratings = [9, 8, 7, 6, 5, 4, 3, 2, 1]
        distribution = self.evaluator._get_rating_distribution(ratings)

        self.assertIn("excellent", distribution)
        self.assertIn("good", distribution)
        self.assertIn("average", distribution)
        self.assertIn("poor", distribution)
        self.assertIn("bad", distribution)

        # Check that distribution sums to total ratings
        total_cards = sum(distribution.values())
        self.assertEqual(total_cards, len(ratings))

    def test_thread_pool_cleanup(self):
        """Test thread pool cleanup on deletion"""
        # Create a new evaluator
        evaluator = DeckEvaluator(self.ratings_file)

        # Access thread pool to ensure it exists
        thread_pool = evaluator._thread_pool

        # Delete evaluator (should trigger cleanup)
        del evaluator

        # Thread pool should be shut down
        self.assertTrue(thread_pool._shutdown)

    def test_cache_thread_safety(self):
        """Test that cache operations are thread-safe"""
        # Create multiple threads that access the cache simultaneously
        results = []
        errors = []

        def worker(thread_id):
            try:
                deck = [f"Card_{thread_id}_{i}" for i in range(5)]
                score = self.evaluator.evaluate_deck(deck, "manual")
                results.append((thread_id, score))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check that no errors occurred
        self.assertEqual(len(errors), 0, f"Thread safety errors: {errors}")

        # Check that all threads completed successfully
        self.assertEqual(len(results), 5)

    def test_performance_optimization_effectiveness(self):
        """Test that performance optimizations actually improve performance"""
        # Create a large deck for testing
        large_deck = (
            ["Goblin Guide"] * 20 + ["Lightning Bolt"] * 20 + ["Counterspell"] * 20
        )

        # Measure time without cache (first run)
        start_time = time.time()
        score1 = self.evaluator.evaluate_deck(large_deck, "manual")
        time1 = time.time() - start_time

        # Measure time with cache (second run)
        start_time = time.time()
        score2 = self.evaluator.evaluate_deck(large_deck, "manual")
        time2 = time.time() - start_time

        # Scores should be identical
        self.assertEqual(score1, score2)

        # Second run should be faster (cache hit)
        self.assertLess(
            time2,
            time1,
            f"Cache did not improve performance: {time1:.4f}s vs {time2:.4f}s",
        )

    def test_enhanced_synergy_patterns_coverage(self):
        """Test that enhanced synergy patterns cover more card combinations"""
        # Test various synergy patterns
        test_cases = [
            ("Goblin Guide", "Goblin Chieftain", "tribal"),
            ("Splinter Twin", "Deceiver Exarch", "combo"),
            ("Lightning Greaves", "Goblin Guide", "equipment"),
            ("Arcbound Ravager", "Cranial Plating", "artifact"),
            ("Delver of Secrets", "Ponder", "delver"),
            ("Grapeshot", "Desperate Ritual", "storm"),
            ("Entomb", "Griselbrand", "reanimator"),
            ("Crop Rotation", "Gaea's Cradle", "land"),
        ]

        for card1, card2, synergy_type in test_cases:
            synergy = self.evaluator._calculate_card_synergy(card1, card2)
            self.assertGreater(
                synergy,
                0.0,
                f"No synergy detected for {synergy_type}: {card1} + {card2}",
            )

    def test_get_evaluation_methods(self):
        """Test that available evaluation methods are returned correctly"""
        # ... existing code ...


if __name__ == "__main__":
    unittest.main()

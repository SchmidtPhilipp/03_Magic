#!/usr/bin/env python3
"""
Simplified Performance Test

This script tests the simplified evaluator without unnecessary caching.
"""

import time
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from magic_optimizer.evaluator import DeckEvaluator


def test_simplified_evaluator():
    """Test simplified evaluator performance"""
    print("🧪 Testing Simplified Evaluator Performance")
    print("=" * 60)

    # Initialize evaluator
    evaluator = DeckEvaluator()

    # Test cards
    test_cards = [
        "Lightning Bolt",
        "Counterspell",
        "Dark Confidant",
        "Tarmogoyf",
        "Snapcaster Mage",
        "Jace, the Mind Sculptor",
        "Force of Will",
        "Brainstorm",
        "Ponder",
        "Preordain",
        "Goblin Guide",
        "Sol Ring",
        "Primeval Titan",
        "Path to Exile",
        "Swords to Plowshares",
    ]

    print(f"Testing with {len(test_cards)} cards...")

    # Test 1: Manual evaluation performance
    print("\n📊 Manual Evaluation Performance:")

    start_time = time.time()
    score_manual = evaluator.evaluate_deck(test_cards, "manual")
    manual_time = time.time() - start_time

    print(f"  Manual evaluation: {manual_time:.4f}s")
    print(f"  Manual score: {score_manual:.4f}")

    # Test 2: 17Lands evaluation performance
    print("\n🌐 17Lands Evaluation Performance:")

    start_time = time.time()
    score_17lands = evaluator.evaluate_deck(test_cards, "17lands")
    lands_time = time.time() - start_time

    print(f"  17Lands evaluation: {lands_time:.4f}s")
    print(f"  17Lands score: {score_17lands:.4f}")

    # Test 3: Method comparison
    print("\n📈 Method Comparison:")
    print(f"  Manual: {score_manual:.4f}")
    print(f"  17Lands: {score_17lands:.4f}")
    print(f"  Difference: {abs(score_manual - score_17lands):.4f}")

    # Test 4: Large deck performance
    print("\n🔄 Large Deck Performance:")
    large_deck = test_cards * 5  # 75 cards

    start_time = time.time()
    score_large = evaluator.evaluate_deck(large_deck, "manual")
    large_time = time.time() - start_time

    print(f"  Large deck evaluation: {large_time:.4f}s")
    print(f"  Large deck score: {score_large:.4f}")

    # Test 5: 17Lands cache stats
    print("\n📊 17Lands Cache Stats:")
    cache_stats = evaluator.seventeen_lands.get_cache_stats()
    for key, value in cache_stats.items():
        print(f"  {key}: {value}")

    print("\n✅ Simplified performance test completed successfully!")


if __name__ == "__main__":
    print("🚀 Starting Simplified Performance Test")
    print("=" * 50)

    try:
        test_simplified_evaluator()

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()

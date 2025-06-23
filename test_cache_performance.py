#!/usr/bin/env python3
"""
Cache Performance Test for 17Lands API

This script tests the caching functionality and performance of the 17Lands API integration.
"""

import time
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from magic_optimizer.evaluator import DeckEvaluator, SeventeenLandsAPI


def test_cache_performance():
    """Test cache performance and functionality"""
    print("🧪 Testing 17Lands Cache Performance")
    print("=" * 50)
    
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
        "Preordain"
    ]
    
    print(f"Testing with {len(test_cards)} cards...")
    
    # Test 1: Initial cache stats
    print("\n📊 Initial Cache Stats:")
    initial_stats = evaluator.get_cache_stats()
    for key, value in initial_stats.items():
        print(f"  {key}: {value}")
    
    # Test 2: First evaluation (should fetch from API)
    print("\n🔄 First Evaluation (API calls):")
    start_time = time.time()
    score1 = evaluator.evaluate_deck(test_cards, "17lands")
    api_time = time.time() - start_time
    
    print(f"  Score: {score1:.4f}")
    print(f"  Time: {api_time:.2f} seconds")
    
    # Test 3: Second evaluation (should use cache)
    print("\n⚡ Second Evaluation (cache):")
    start_time = time.time()
    score2 = evaluator.evaluate_deck(test_cards, "17lands")
    cache_time = time.time() - start_time
    
    print(f"  Score: {score2:.4f}")
    print(f"  Time: {cache_time:.2f} seconds")
    
    # Test 4: Performance comparison
    print("\n📈 Performance Comparison:")
    if api_time > 0:
        speedup = api_time / cache_time
        print(f"  Speedup: {speedup:.1f}x faster with cache")
    
    # Test 5: Cache stats after evaluation
    print("\n📊 Cache Stats After Evaluation:")
    final_stats = evaluator.get_cache_stats()
    for key, value in final_stats.items():
        print(f"  {key}: {value}")
    
    # Test 6: Verify scores are identical
    print("\n✅ Score Verification:")
    if abs(score1 - score2) < 0.0001:
        print("  ✓ Scores are identical (cache working correctly)")
    else:
        print("  ✗ Scores differ (cache issue detected)")
    
    # Test 7: Test cache persistence
    print("\n💾 Cache Persistence Test:")
    evaluator2 = DeckEvaluator()
    score3 = evaluator2.evaluate_deck(test_cards, "17lands")
    
    if abs(score2 - score3) < 0.0001:
        print("  ✓ Cache persistence working correctly")
    else:
        print("  ✗ Cache persistence issue detected")
    
    print("\n🎉 Cache Performance Test Complete!")


def test_evaluation_methods():
    """Test different evaluation methods"""
    print("\n🔬 Testing Evaluation Methods")
    print("=" * 50)
    
    evaluator = DeckEvaluator()
    test_cards = ["Lightning Bolt", "Counterspell", "Dark Confidant"]
    
    # Test manual evaluation
    print("\n📝 Manual Evaluation:")
    manual_score = evaluator.evaluate_deck(test_cards, "manual")
    print(f"  Score: {manual_score:.4f}")
    
    # Test 17Lands evaluation
    print("\n🌐 17Lands Evaluation:")
    lands_score = evaluator.evaluate_deck(test_cards, "17lands")
    print(f"  Score: {lands_score:.4f}")
    
    # Compare methods
    print("\n📊 Method Comparison:")
    print(f"  Manual: {manual_score:.4f}")
    print(f"  17Lands: {lands_score:.4f}")
    print(f"  Difference: {abs(manual_score - lands_score):.4f}")


def test_cache_optimization():
    """Test cache optimization features"""
    print("\n⚙️ Testing Cache Optimization")
    print("=" * 50)
    
    evaluator = DeckEvaluator()
    
    # Get initial stats
    initial_stats = evaluator.get_cache_stats()
    print(f"Initial cache entries: {initial_stats['total_entries']}")
    
    # Test cache clearing
    print("\n🗑️ Testing Cache Clearing:")
    evaluator.clear_caches()
    cleared_stats = evaluator.get_cache_stats()
    print(f"After clearing: {cleared_stats['total_entries']} entries")
    
    if cleared_stats['total_entries'] == 0:
        print("  ✓ Cache clearing working correctly")
    else:
        print("  ✗ Cache clearing issue detected")


if __name__ == "__main__":
    print("🚀 Starting 17Lands Cache Performance Tests")
    print("=" * 60)
    
    try:
        test_cache_performance()
        test_evaluation_methods()
        test_cache_optimization()
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc() 
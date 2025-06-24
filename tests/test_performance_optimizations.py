#!/usr/bin/env python3
"""
Performance Optimization Tests

This script tests the new performance optimizations including LRU cache,
parallel processing, and memory management.
"""

import time
import sys
import os
import threading
import gc

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from magic_optimizer.evaluator import DeckEvaluator, LRUCache


def test_lru_cache_performance():
    """Test LRU cache performance and functionality"""
    print("🧪 Testing LRU Cache Performance")
    print("=" * 50)
    
    # Initialize cache
    cache = LRUCache(max_size=100)
    
    # Test 1: Basic operations
    print("\n📊 Basic Cache Operations:")
    cache.put("key1", "value1")
    cache.put("key2", "value2")
    
    assert cache.get("key1") == "value1"
    assert cache.get("key2") == "value2"
    assert cache.get("key3") is None
    print("  ✓ Basic put/get operations working")
    
    # Test 2: LRU eviction
    print("\n🔄 LRU Eviction Test:")
    # Fill cache to capacity
    for i in range(100):
        cache.put(f"key{i}", f"value{i}")
    
    # Access some keys to make them recently used
    cache.get("key50")
    cache.get("key75")
    
    # Add more items to trigger eviction
    cache.put("new_key1", "new_value1")
    cache.put("new_key2", "new_value2")
    
    # Check that recently accessed keys are still there
    assert cache.get("key50") == "value50"
    assert cache.get("key75") == "value75"
    
    # Check that old keys are evicted
    assert cache.get("key0") is None
    print("  ✓ LRU eviction working correctly")
    
    # Test 3: Performance comparison
    print("\n⚡ Performance Comparison:")
    
    # Test with regular dict
    regular_dict = {}
    start_time = time.time()
    for i in range(1000):
        regular_dict[f"key{i}"] = f"value{i}"
        _ = regular_dict.get(f"key{i}")
    dict_time = time.time() - start_time
    
    # Test with LRU cache
    lru_cache = LRUCache(max_size=1000)
    start_time = time.time()
    for i in range(1000):
        lru_cache.put(f"key{i}", f"value{i}")
        _ = lru_cache.get(f"key{i}")
    lru_time = time.time() - start_time
    
    print(f"  Regular dict time: {dict_time:.4f}s")
    print(f"  LRU cache time: {lru_time:.4f}s")
    print(f"  Performance ratio: {dict_time/lru_time:.2f}x")
    
    # Test 4: Thread safety
    print("\n🔒 Thread Safety Test:")
    cache = LRUCache(max_size=100)
    
    def worker(thread_id):
        for i in range(100):
            cache.put(f"thread{thread_id}_key{i}", f"value{i}")
            _ = cache.get(f"thread{thread_id}_key{i}")
    
    threads = []
    for i in range(4):
        thread = threading.Thread(target=worker, args=(i,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    print("  ✓ Thread safety test passed")
    
    # Test 5: Memory management
    print("\n💾 Memory Management Test:")
    cache = LRUCache(max_size=50)
    
    # Add items and check size
    for i in range(100):
        cache.put(f"key{i}", f"value{i}")
    
    stats = cache.get_stats()
    assert stats["size"] <= 50
    print(f"  Cache size: {stats['size']}/{stats['max_size']}")
    print(f"  Utilization: {stats['utilization']}")
    print("  ✓ Memory management working correctly")


def test_evaluator_performance():
    """Test evaluator performance optimizations"""
    print("\n🔬 Testing Evaluator Performance Optimizations")
    print("=" * 60)
    
    # Initialize evaluator
    evaluator = DeckEvaluator()
    
    # Test cards
    test_cards = [
        "Lightning Bolt", "Counterspell", "Dark Confidant", "Tarmogoyf",
        "Snapcaster Mage", "Jace, the Mind Sculptor", "Force of Will",
        "Brainstorm", "Ponder", "Preordain", "Goblin Guide", "Sol Ring",
        "Primeval Titan", "Path to Exile", "Swords to Plowshares"
    ]
    
    print(f"Testing with {len(test_cards)} cards...")
    
    # Test 1: Cache performance
    print("\n📊 Cache Performance Test:")
    
    # First evaluation (should be slower)
    start_time = time.time()
    score1 = evaluator.evaluate_deck(test_cards, "manual")
    first_time = time.time() - start_time
    
    # Second evaluation (should use cache)
    start_time = time.time()
    score2 = evaluator.evaluate_deck(test_cards, "manual")
    second_time = time.time() - start_time
    
    print(f"  First evaluation: {first_time:.4f}s")
    print(f"  Second evaluation: {second_time:.4f}s")
    print(f"  Speedup: {first_time/second_time:.1f}x")
    print(f"  Scores identical: {abs(score1 - score2) < 0.0001}")
    
    # Test 2: Cache statistics
    print("\n📈 Cache Statistics:")
    stats = evaluator.get_cache_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Test 3: Parallel processing for large decks
    print("\n🔄 Parallel Processing Test:")
    large_deck = test_cards * 10  # 150 cards
    
    start_time = time.time()
    score_large = evaluator.evaluate_deck(large_deck, "manual")
    large_time = time.time() - start_time
    
    print(f"  Large deck evaluation: {large_time:.4f}s")
    print(f"  Large deck score: {score_large:.4f}")
    
    # Test 4: Memory usage
    print("\n💾 Memory Usage Test:")
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Perform many evaluations
    for i in range(50):
        evaluator.evaluate_deck(test_cards, "manual")
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    
    print(f"  Initial memory: {initial_memory:.1f} MB")
    print(f"  Final memory: {final_memory:.1f} MB")
    print(f"  Memory increase: {memory_increase:.1f} MB")
    
    # Test 5: Cache clearing
    print("\n🗑️ Cache Clearing Test:")
    evaluator.clear_caches()
    stats_after_clear = evaluator.get_cache_stats()
    
    print("  Cache sizes after clearing:")
    for key, value in stats_after_clear.items():
        if "size" in key:
            print(f"    {key}: {value}")


def test_17lands_integration_performance():
    """Test 17Lands integration performance"""
    print("\n🌐 Testing 17Lands Integration Performance")
    print("=" * 60)
    
    evaluator = DeckEvaluator()
    test_cards = ["Lightning Bolt", "Counterspell", "Dark Confidant"]
    
    # Test 1: 17Lands evaluation performance
    print("\n📊 17Lands Evaluation Performance:")
    
    start_time = time.time()
    score_17lands = evaluator.evaluate_deck(test_cards, "17lands")
    lands_time = time.time() - start_time
    
    start_time = time.time()
    score_manual = evaluator.evaluate_deck(test_cards, "manual")
    manual_time = time.time() - start_time
    
    print(f"  17Lands evaluation: {lands_time:.4f}s")
    print(f"  Manual evaluation: {manual_time:.4f}s")
    print(f"  17Lands score: {score_17lands:.4f}")
    print(f"  Manual score: {score_manual:.4f}")
    
    # Test 2: Cache hit rates
    print("\n🎯 Cache Hit Rate Test:")
    
    # Second evaluation should use cache
    start_time = time.time()
    score_17lands_cached = evaluator.evaluate_deck(test_cards, "17lands")
    lands_cached_time = time.time() - start_time
    
    print(f"  Cached 17Lands evaluation: {lands_cached_time:.4f}s")
    print(f"  Speedup: {lands_time/lands_cached_time:.1f}x")
    print(f"  Scores identical: {abs(score_17lands - score_17lands_cached) < 0.0001}")


def test_memory_optimization():
    """Test memory optimization features"""
    print("\n🧠 Testing Memory Optimization")
    print("=" * 50)
    
    evaluator = DeckEvaluator()
    
    # Test 1: Memory usage over time
    print("\n📊 Memory Usage Over Time:")
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    
    memory_readings = []
    for i in range(10):
        # Perform evaluation
        test_cards = [f"Card{i}_{j}" for j in range(10)]
        evaluator.evaluate_deck(test_cards, "manual")
        
        # Record memory usage
        memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_readings.append(memory)
        
        print(f"  Iteration {i+1}: {memory:.1f} MB")
    
    # Test 2: Garbage collection
    print("\n🗑️ Garbage Collection Test:")
    initial_memory = process.memory_info().rss / 1024 / 1024
    
    # Force garbage collection
    gc.collect()
    
    final_memory = process.memory_info().rss / 1024 / 1024
    memory_freed = initial_memory - final_memory
    
    print(f"  Memory before GC: {initial_memory:.1f} MB")
    print(f"  Memory after GC: {final_memory:.1f} MB")
    print(f"  Memory freed: {memory_freed:.1f} MB")


if __name__ == "__main__":
    print("🚀 Starting Performance Optimization Tests")
    print("=" * 70)
    
    try:
        test_lru_cache_performance()
        test_evaluator_performance()
        test_17lands_integration_performance()
        test_memory_optimization()
        
        print("\n✅ All performance tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Performance test failed with error: {e}")
        import traceback
        traceback.print_exc() 
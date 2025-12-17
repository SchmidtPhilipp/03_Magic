#!/usr/bin/env python3
"""
Test to isolate the genetic algorithm hanging issue
"""

import sys
import os
import pandas as pd
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from magic_optimizer.deck_builder import EnhancedDeckBuilder

def test_genetic_components():
    """Test each component of the genetic algorithm separately"""
    print("🧪 Testing Genetic Algorithm Components")
    print("=" * 50)
    
    # Load test collection
    collection_df = pd.read_csv("data/collections/FinalFantasy.csv")
    print(f"Loaded {len(collection_df)} cards from collection")
    
    # Create deck builder
    deck_builder = EnhancedDeckBuilder()
    
    print("\n🔍 Testing Component 1: Card Preparation")
    print("-" * 40)
    
    # Test card preparation
    start_time = time.time()
    try:
        # This should work quickly
        result = deck_builder.build_optimal_deck_advanced(
            collection_df=collection_df,
            num_colors=2,
            total_deck_size=25,
            num_lands=8,
            algorithm="greedy",  # Use greedy first to test card preparation
            optimization_criterion="manual",
            lambda_penalty=1.0,
            fixed_colors=None,
        )
        prep_time = time.time() - start_time
        print(f"✅ Card preparation completed in {prep_time:.2f} seconds")
        print(f"   Greedy algorithm score: {result['score']:.3f}")
        
    except Exception as e:
        print(f"❌ Card preparation failed: {e}")
        return
    
    print("\n🔍 Testing Component 2: Genetic Algorithm with Small Parameters")
    print("-" * 60)
    
    # Test genetic algorithm with very small parameters
    start_time = time.time()
    try:
        result = deck_builder.build_optimal_deck_advanced(
            collection_df=collection_df,
            num_colors=2,
            total_deck_size=20,  # Very small deck
            num_lands=6,
            algorithm="genetic",
            optimization_criterion="manual",
            lambda_penalty=1.0,
            fixed_colors=None,
        )
        genetic_time = time.time() - start_time
        print(f"✅ Genetic algorithm completed in {genetic_time:.2f} seconds")
        print(f"   Genetic algorithm score: {result['score']:.3f}")
        
    except Exception as e:
        print(f"❌ Genetic algorithm failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n🔍 Testing Component 3: Genetic Algorithm with Normal Parameters")
    print("-" * 60)
    
    # Test genetic algorithm with normal parameters
    start_time = time.time()
    try:
        result = deck_builder.build_optimal_deck_advanced(
            collection_df=collection_df,
            num_colors=2,
            total_deck_size=30,  # Normal deck size
            num_lands=10,
            algorithm="genetic",
            optimization_criterion="manual",
            lambda_penalty=1.0,
            fixed_colors=None,
        )
        genetic_time = time.time() - start_time
        print(f"✅ Genetic algorithm with normal parameters completed in {genetic_time:.2f} seconds")
        print(f"   Genetic algorithm score: {result['score']:.3f}")
        
    except Exception as e:
        print(f"❌ Genetic algorithm with normal parameters failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n✅ All tests completed successfully!")

if __name__ == "__main__":
    test_genetic_components() 
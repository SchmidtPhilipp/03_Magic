#!/usr/bin/env python3
"""
Test script to debug the greedy algorithm deck size issue
"""

import sys
import os
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from magic_optimizer.optimizers.greedy_optimizer import GreedyOptimizer
from magic_optimizer.evaluators import create_evaluator

def test_greedy_debug():
    """Test the greedy algorithm with debug output"""
    print("🧪 Testing Greedy Algorithm Debug")
    print("=" * 50)
    
    # Load test collection
    collection_df = pd.read_csv("uploads/FinalFantasy.csv")
    print(f"Loaded {len(collection_df)} cards from collection")
    
    # Create evaluator
    evaluator = create_evaluator("manual")
    
    # Create optimizer
    optimizer = GreedyOptimizer(evaluator)
    
    # Test parameters
    num_colors = 2
    deck_size = 23  # Non-land cards (40 - 17)
    lambda_penalty = 0.5
    
    print(f"\nTest Parameters:")
    print(f"  Num Colors: {num_colors}")
    print(f"  Deck Size (non-lands): {deck_size}")
    print(f"  Lambda Penalty: {lambda_penalty}")
    
    # Run optimization
    result = optimizer.optimize_deck(
        collection_df=collection_df,
        num_colors=num_colors,
        deck_size=deck_size,
        lambda_penalty=lambda_penalty,
        fixed_colors=[]
    )
    
    # Analyze result
    deck = result["deck"]
    print(f"\nResults:")
    print(f"  Target deck size: {deck_size}")
    print(f"  Actual deck size: {len(deck)}")
    print(f"  Target colors: {result['target_colors']}")
    print(f"  Score: {result['score']:.4f}")
    
    if len(deck) != deck_size:
        print(f"❌ BUG: Deck size mismatch! Expected {deck_size}, got {len(deck)}")
    else:
        print(f"✅ Deck size is correct")
    
    # Show first few cards
    print(f"\nFirst 5 cards:")
    for i, card in enumerate(deck[:5]):
        print(f"  {i+1}. {card.name} (Score: {card.optimization_score:.2f})")

if __name__ == "__main__":
    test_greedy_debug() 
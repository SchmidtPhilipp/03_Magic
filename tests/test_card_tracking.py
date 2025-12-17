#!/usr/bin/env python3
"""
Test script to track cards throughout the pipeline
"""

import sys
import os
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from magic_optimizer.optimizers.greedy_optimizer import GreedyOptimizer
from magic_optimizer.evaluators import create_evaluator

def test_card_tracking():
    """Test to track what happens to cards throughout the pipeline"""
    print("🧪 Testing Card Tracking")
    print("=" * 50)
    
    # Load test collection
    collection_df = pd.read_csv("uploads/FinalFantasy.csv")
    print(f"Loaded {len(collection_df)} cards from collection")
    
    # Check for duplicates
    duplicate_names = collection_df[collection_df.duplicated(subset=['Name'], keep=False)]['Name'].unique()
    if len(duplicate_names) > 0:
        print(f"Found {len(duplicate_names)} duplicate card names: {duplicate_names[:5]}")
    
    # Create evaluator and optimizer
    evaluator = create_evaluator("manual")
    optimizer = GreedyOptimizer(evaluator)
    
    # Test parameters
    num_colors = 2
    deck_size = 23  # Non-land cards
    lambda_penalty = 0.5
    
    print(f"\nTest Parameters:")
    print(f"  Num Colors: {num_colors}")
    print(f"  Deck Size (non-lands): {deck_size}")
    
    # Step 1: Prepare eligible cards
    print(f"\nStep 1: Preparing eligible cards...")
    eligible_cards = optimizer.prepare_eligible_cards(collection_df, num_colors)
    print(f"  Eligible cards: {len(eligible_cards)}")
    
    # Step 2: Select target colors
    print(f"\nStep 2: Selecting target colors...")
    target_colors = optimizer.select_target_colors(eligible_cards, num_colors, [])
    print(f"  Target colors: {target_colors}")
    
    # Step 3: Filter to target colors
    print(f"\nStep 3: Filtering to target colors...")
    target_colors_set = set(target_colors)
    filtered_cards = [
        card
        for card in eligible_cards
        if not card.colors or card.colors.issubset(target_colors_set)
    ]
    print(f"  Filtered cards: {len(filtered_cards)}")
    
    # Step 4: Run greedy algorithm
    print(f"\nStep 4: Running greedy algorithm...")
    selected_cards = optimizer.greedy_algorithm_optimization(
        filtered_cards,
        deck_size,
        lambda_penalty,
    )
    print(f"  Selected cards: {len(selected_cards)}")
    
    # Check for duplicates in selected cards
    selected_names = [card.name for card in selected_cards]
    unique_names = set(selected_names)
    print(f"  Unique card names: {len(unique_names)}")
    print(f"  Duplicate names: {len(selected_names) - len(unique_names)}")
    
    if len(selected_names) != len(unique_names):
        # Find duplicates
        from collections import Counter
        name_counts = Counter(selected_names)
        duplicates = {name: count for name, count in name_counts.items() if count > 1}
        print(f"  Duplicate details: {duplicates}")
    
    # Show first 10 selected cards
    print(f"\nFirst 10 selected cards:")
    for i, card in enumerate(selected_cards[:10]):
        print(f"  {i+1}. {card.name} (Score: {card.optimization_score:.2f})")

if __name__ == "__main__":
    test_card_tracking() 
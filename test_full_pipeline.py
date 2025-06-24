#!/usr/bin/env python3
"""
Test script to debug the full pipeline deck size issue
"""

import sys
import os
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from magic_optimizer.deck_builder import EnhancedDeckBuilder

def test_full_pipeline():
    """Test the full pipeline to see where deck size issue occurs"""
    print("🧪 Testing Full Pipeline Debug")
    print("=" * 50)
    
    # Load test collection
    collection_df = pd.read_csv("uploads/FinalFantasy.csv")
    print(f"Loaded {len(collection_df)} cards from collection")
    
    # Create deck builder
    builder = EnhancedDeckBuilder()
    
    # Test parameters (same as web app)
    num_colors = 2
    total_deck_size = 40
    num_lands = 17
    algorithm = "greedy"
    optimization_criterion = "17lands"  # Test with 17Lands evaluator
    lambda_penalty = 0.5
    
    print(f"\nTest Parameters:")
    print(f"  Num Colors: {num_colors}")
    print(f"  Total Deck Size: {total_deck_size}")
    print(f"  Num Lands: {num_lands}")
    print(f"  Expected Non-Lands: {total_deck_size - num_lands}")
    print(f"  Algorithm: {algorithm}")
    print(f"  Optimization Criterion: {optimization_criterion}")
    
    # Run full pipeline
    result = builder.build_optimal_deck_advanced(
        collection_df=collection_df,
        num_colors=num_colors,
        total_deck_size=total_deck_size,
        num_lands=num_lands,
        algorithm=algorithm,
        optimization_criterion=optimization_criterion,
        lambda_penalty=lambda_penalty,
        fixed_colors=[]
    )
    
    # Analyze result
    deck = result["deck"]
    print(f"\nResults:")
    print(f"  Target total deck size: {total_deck_size}")
    print(f"  Actual total deck size: {len(deck)}")
    print(f"  Target non-lands: {total_deck_size - num_lands}")
    print(f"  Target lands: {num_lands}")
    
    # Count card types
    non_land_cards = [card for card in deck if "Land" not in card.get("type", "")]
    land_cards = [card for card in deck if "Land" in card.get("type", "")]
    
    print(f"  Actual non-lands: {len(non_land_cards)}")
    print(f"  Actual lands: {len(land_cards)}")
    print(f"  Target colors: {result['target_colors']}")
    print(f"  Score: {result['score']:.4f}")
    
    # Check for issues
    issues = []
    if len(deck) != total_deck_size:
        issues.append(f"Total deck size mismatch: {len(deck)} != {total_deck_size}")
    if len(non_land_cards) != total_deck_size - num_lands:
        issues.append(f"Non-land count mismatch: {len(non_land_cards)} != {total_deck_size - num_lands}")
    if len(land_cards) != num_lands:
        issues.append(f"Land count mismatch: {len(land_cards)} != {num_lands}")
    
    if issues:
        print(f"\n❌ ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print(f"\n✅ All deck sizes are correct")
    
    # Show card type breakdown
    print(f"\nCard Type Breakdown:")
    card_types = {}
    for card in deck:
        card_type = card.get("type", "Unknown")
        card_types[card_type] = card_types.get(card_type, 0) + 1
    
    for card_type, count in sorted(card_types.items()):
        print(f"  {card_type}: {count}")

if __name__ == "__main__":
    test_full_pipeline() 
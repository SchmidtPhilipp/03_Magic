#!/usr/bin/env python3
"""
Test script to debug color constraint issues with dual-color cards
"""

import pandas as pd
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from magic_optimizer.deck_builder import EnhancedDeckBuilder
from magic_optimizer.optimizer import AdvancedDeckOptimizer


def test_color_constraints():
    """Test that color constraints work correctly with dual-color cards"""
    print("=== Testing Color Constraints with Dual-Color Cards ===")

    # Create a test collection with known dual-color cards
    test_data = {
        "Card Name": [
            "Lightning Bolt",  # Red
            "Counterspell",  # Blue
            "Ultimecia Time Sorceress",  # Blue/Black
            "Giant Growth",  # Green
            "Dark Ritual",  # Black
            "Healing Salve",  # White
            "Fireball",  # Red
            "Blue Elemental Blast",  # Blue
            "Red Blue Spell",  # Red/Blue
            "Black Red Spell",  # Black/Red
        ],
        "Rating": ["9/10", "8/10", "7/10", "6/10", "5/10", "4/10", "8/10", "7/10", "6/10", "5/10"],
        "Quantity": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    }
    collection_df = pd.DataFrame(test_data)

    # Initialize optimizer
    optimizer = AdvancedDeckOptimizer("data/ratings/card_ratings.csv")

    # Test 1: Fixed colors Blue and Red
    print("\n--- Test 1: Fixed colors Blue and Red ---")
    fixed_colors = ["U", "R"]
    
    # Prepare eligible cards
    eligible_cards = optimizer.prepare_eligible_cards(collection_df, 2)
    print(f"Total eligible cards: {len(eligible_cards)}")
    
    # Select target colors (should be Blue and Red)
    target_colors = optimizer.select_target_colors(eligible_cards, 2, fixed_colors)
    print(f"Target colors: {target_colors}")
    
    # Filter cards by colors
    filtered_cards = optimizer.filter_cards_by_colors(eligible_cards, target_colors)
    print(f"Filtered cards: {len(filtered_cards)}")
    
    print("\nCards that should be allowed:")
    for card in filtered_cards:
        colors = card.get("colors", set())
        print(f"  {card['name']} - Colors: {colors}")
    
    # Check for problematic cards
    problematic_cards = []
    for card in filtered_cards:
        colors = card.get("colors", set())
        if colors and not colors.issubset(set(target_colors)):
            problematic_cards.append((card["name"], colors, target_colors))
    
    if problematic_cards:
        print(f"\n❌ PROBLEM: Found {len(problematic_cards)} cards that shouldn't be allowed:")
        for name, colors, target in problematic_cards:
            print(f"  {name} - Colors: {colors}, Target: {target}")
    else:
        print(f"\n✅ All filtered cards respect color constraints")

    # Test 2: Run actual optimization
    print("\n--- Test 2: Running optimization with fixed colors ---")
    deck_builder = EnhancedDeckBuilder()
    
    try:
        result = deck_builder.build_optimal_deck_advanced(
            collection_df=collection_df,
            num_colors=2,
            total_deck_size=10,
            num_lands=0,  # No lands for testing
            algorithm="greedy",
            fixed_colors=fixed_colors,
        )

        deck = result["deck"]
        target_colors = result["target_colors"]
        
        print(f"Optimization result:")
        print(f"  Target colors: {target_colors}")
        print(f"  Deck size: {len(deck)}")
        
        print(f"\nDeck contents:")
        for i, card in enumerate(deck):
            colors = card.get("colors", set())
            print(f"  {i+1}. {card['name']} - Colors: {colors}")
        
        # Check for off-color cards
        off_color_cards = []
        for card in deck:
            colors = card.get("colors", set())
            if colors and not colors.issubset(set(target_colors)):
                off_color_cards.append((card["name"], colors, target_colors))
        
        if off_color_cards:
            print(f"\n❌ PROBLEM: Found {len(off_color_cards)} off-color cards in deck:")
            for name, colors, target in off_color_cards:
                print(f"  {name} - Colors: {colors}, Target: {target}")
        else:
            print(f"\n✅ All cards in deck respect color constraints")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_color_constraints()

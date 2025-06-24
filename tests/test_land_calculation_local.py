#!/usr/bin/env python3
"""
Test script to verify land calculation and deck size
"""

import pandas as pd
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from magic_optimizer.deck_builder import EnhancedDeckBuilder


def test_land_calculation():
    """Test that land calculation works correctly"""
    print("=== Testing Land Calculation ===")

    # Use the real FinalFantasy.csv collection
    collection_path = "data/collections/FinalFantasy.csv"
    if not os.path.exists(collection_path):
        print(f"ERROR: Collection file not found: {collection_path}")
        return
    collection_df = pd.read_csv(collection_path)
    print(f"Loaded {len(collection_df)} cards from FinalFantasy collection")

    # Initialize deck builder
    deck_builder = EnhancedDeckBuilder()

    # Test case: 40-card deck with 17 lands
    print("\n--- Testing 40-card deck with 17 lands ---")

    try:
        result = deck_builder.build_optimal_deck_advanced(
            collection_df=collection_df,
            num_colors=2,
            algorithm="greedy",
            total_deck_size=40,
            num_lands=17,  # Use absolute number instead of ratio
            evaluation_method="manual",
        )

        # Count non-land and land cards
        non_land_cards = [card for card in result["deck"] if card.get("type") != "Land"]
        land_cards = [card for card in result["deck"] if card.get("type") == "Land"]

        total_cards = len(result["deck"])
        actual_nonlands = len(non_land_cards)
        actual_lands = len(land_cards)

        print(f"Expected: 23 non-lands, 17 lands, 40 total")
        print(
            f"Actual: {actual_nonlands} non-lands, {actual_lands} lands, {total_cards} total"
        )

        # Check if the numbers are correct
        if actual_nonlands == 23 and actual_lands == 17 and total_cards == 40:
            print("✅ PASS: Land calculation is correct")
        else:
            print("❌ FAIL: Land calculation is incorrect")

        # Show detailed breakdown
        print(f"\nDetailed breakdown:")
        print(f"  Non-land cards: {actual_nonlands}")
        print(f"  Land cards: {actual_lands}")
        print(f"  Total: {total_cards}")
        print(
            f"  Land ratio: {actual_lands/total_cards:.3f} ({actual_lands/total_cards*100:.1f}%)"
        )

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_land_calculation()

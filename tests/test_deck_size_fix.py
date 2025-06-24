#!/usr/bin/env python3
"""
Test script to verify deck size calculations are working correctly
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.magic_optimizer.deck_builder import EnhancedDeckBuilder
import pandas as pd


def create_test_collection():
    """Create a test collection using real cards from ratings"""
    # Load the ratings file to get real card names
    ratings_file = "data/ratings/card_ratings.csv"
    if not os.path.exists(ratings_file):
        print(f"Error: Ratings file not found at {ratings_file}")
        return None

    ratings_df = pd.read_csv(ratings_file)
    print(f"Loaded {len(ratings_df)} cards from ratings file")

    # Create a test collection with the top rated cards
    test_cards = []
    for _, row in ratings_df.head(50).iterrows():  # Use top 50 cards
        test_cards.append(
            {
                "Card Name": row["Card Name"],
                "Quantity": 4,  # 4 copies of each card
            }
        )

    return pd.DataFrame(test_cards)


def test_deck_size_calculations():
    """Test that deck size calculations are correct"""
    print("=== Testing Deck Size Calculations ===")

    # Create test collection
    collection_df = create_test_collection()
    if collection_df is None:
        print("Failed to create test collection")
        return

    print(f"Created test collection with {len(collection_df)} cards")

    # Initialize deck builder
    deck_builder = EnhancedDeckBuilder()

    # Test cases with different deck sizes and absolute land counts
    test_cases = [
        {
            "total_deck_size": 40,
            "num_lands": 16,
            "expected_lands": 16,
            "expected_nonlands": 24,
        },
        {
            "total_deck_size": 60,
            "num_lands": 21,
            "expected_lands": 21,
            "expected_nonlands": 39,
        },
        {
            "total_deck_size": 40,
            "num_lands": 18,
            "expected_lands": 18,
            "expected_nonlands": 22,
        },
    ]

    for i, test_case in enumerate(test_cases):
        print(f"\n--- Test Case {i+1} ---")
        print(f"Total deck size: {test_case['total_deck_size']}")
        print(f"Number of lands: {test_case['num_lands']}")
        print(f"Expected lands: {test_case['expected_lands']}")
        print(f"Expected non-lands: {test_case['expected_nonlands']}")

        try:
            # Run optimization
            result = deck_builder.build_optimal_deck_advanced(
                collection_df=collection_df,
                num_colors=2,
                algorithm="greedy",  # Use greedy for faster testing
                total_deck_size=test_case["total_deck_size"],
                num_lands=test_case["num_lands"],
                evaluation_method="manual",
            )

            # Analyze the result
            deck = result["deck"]
            total_cards = len(deck)
            non_land_cards = len([card for card in deck if card.get("type") != "Land"])
            land_cards = len([card for card in deck if card.get("type") == "Land"])

            print(f"Result:")
            print(f"  Total cards: {total_cards}")
            print(f"  Non-land cards: {non_land_cards}")
            print(f"  Land cards: {land_cards}")

            # Verify the results
            assert (
                total_cards == test_case["total_deck_size"]
            ), f"Total deck size mismatch: {total_cards} != {test_case['total_deck_size']}"
            assert (
                non_land_cards == test_case["expected_nonlands"]
            ), f"Non-land count mismatch: {non_land_cards} != {test_case['expected_nonlands']}"
            assert (
                land_cards == test_case["expected_lands"]
            ), f"Land count mismatch: {land_cards} != {test_case['expected_lands']}"

            print("✓ Test case PASSED")

        except Exception as e:
            print(f"✗ Test case FAILED: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    test_deck_size_calculations()
    print("\n=== All tests completed ===")

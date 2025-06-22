#!/usr/bin/env python3
"""
Debug script to check Ultimecia Time Sorceress colors and greedy algorithm
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import pandas as pd

from magic_optimizer.deck_builder import EnhancedDeckBuilder
from magic_optimizer.optimizer import AdvancedDeckOptimizer


def test_ultimecia_colors():
    """Test what colors Ultimecia Time Sorceress actually has"""
    print("Testing Ultimecia Time Sorceress colors...")

    optimizer = AdvancedDeckOptimizer("data/ratings/card_ratings.csv")

    # Get card data for Ultimecia
    card_data = optimizer.get_card_data("Ultimecia Time Sorceress")
    print(f"Card data: {card_data}")

    if card_data:
        colors = card_data.get("colors", [])
        print(f"Ultimecia Time Sorceress colors: {colors}")
        return colors
    else:
        print("Could not find card data for Ultimecia Time Sorceress")
        return []


def test_greedy_algorithm_colors():
    """Test the greedy algorithm with a small collection"""
    print("\nTesting greedy algorithm color constraints...")

    # Create a test collection with known cards
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
        ],
        "Rating": ["9/10", "8/10", "7/10", "6/10", "5/10", "4/10", "8/10", "7/10"],
        "Quantity": [1, 1, 1, 1, 1, 1, 1, 1],
    }
    collection_df = pd.DataFrame(test_data)

    builder = EnhancedDeckBuilder()

    # Test with 2 colors (should be Red/Blue)
    result = builder.build_optimal_deck_advanced(
        collection_df=collection_df,
        num_colors=2,
        deck_size=6,  # Small deck for testing
        algorithm="greedy",
        export_formats=[],
        lambda_penalty=0.5,
        total_deck_size=6,
        land_ratio=0.0,  # No lands for testing
    )

    print(f"\nGreedy algorithm result:")
    print(f"Target colors: {result['target_colors']}")
    print(f"Score: {result['score']:.4f}")
    print(f"Deck size: {len(result['deck'])}")

    print("\nDeck contents:")
    for i, card in enumerate(result["deck"]):
        colors = card.get("colors", set())
        print(f"  {i+1}. {card['name']} - Colors: {colors} - Rating: {card['rating']}")

    # Check if any cards have colors outside the target colors
    target_colors = set(result["target_colors"])
    problematic_cards = []

    for card in result["deck"]:
        card_colors = card.get("colors", set())
        if card_colors and not card_colors.issubset(target_colors):
            problematic_cards.append((card["name"], card_colors, target_colors))

    if problematic_cards:
        print(f"\n❌ PROBLEM: Found cards with wrong colors:")
        for card_name, card_colors, target_colors in problematic_cards:
            print(f"  {card_name}: has {card_colors}, should only have {target_colors}")
    else:
        print(f"\n✅ All cards have correct colors!")


if __name__ == "__main__":
    ultimecia_colors = test_ultimecia_colors()
    test_greedy_algorithm_colors()

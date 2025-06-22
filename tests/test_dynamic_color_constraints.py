#!/usr/bin/env python3
"""
Test dynamic color constraints with lambda penalty
"""

import os
import sys

import numpy as np
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from magic_optimizer.deck_builder import EnhancedDeckBuilder
from magic_optimizer.optimizer import AdvancedDeckOptimizer


def create_test_collection():
    """Create a test collection with cards of different colors and ratings"""
    test_data = []

    # High-rated cards in different colors
    high_rated_cards = [
        ("Lightning Bolt", "R", 9.5),
        ("Counterspell", "U", 9.0),
        ("Dark Ritual", "B", 8.5),
        ("Giant Growth", "G", 8.0),
        ("Healing Salve", "W", 7.5),
        ("Fireball", "R", 8.8),
        ("Blue Elemental Blast", "U", 7.2),
        ("Demonic Tutor", "B", 9.2),
        ("Llanowar Elves", "G", 8.3),
        ("Swords to Plowshares", "W", 9.1),
    ]

    # Medium-rated cards in different colors
    medium_rated_cards = [
        ("Shock", "R", 6.5),
        ("Divination", "U", 6.0),
        ("Duress", "B", 6.8),
        ("Rampant Growth", "G", 6.2),
        ("Pacifism", "W", 6.4),
        ("Lava Axe", "R", 5.8),
        ("Cancel", "U", 5.5),
        ("Murder", "B", 6.1),
        ("Giant Spider", "G", 5.9),
        ("White Knight", "W", 6.3),
    ]

    # Low-rated cards in different colors
    low_rated_cards = [
        ("Stone Rain", "R", 3.5),
        ("Mind Rot", "U", 3.8),
        ("Bog Imp", "B", 2.5),
        ("Grizzly Bears", "G", 4.0),
        ("Holy Day", "W", 3.2),
        ("Mountain Goat", "R", 2.8),
        ("Merfolk of the Pearl Trident", "U", 3.0),
        ("Drudge Skeletons", "B", 3.1),
        ("Craw Wurm", "G", 3.6),
        ("Benalish Infantry", "W", 3.4),
    ]

    # Add all cards
    for name, color, rating in high_rated_cards + medium_rated_cards + low_rated_cards:
        test_data.append({"Card Name": name, "Rating": rating, "Color": color})

    return pd.DataFrame(test_data)


def test_dynamic_color_constraints():
    """Test that the optimizer respects color constraints with different lambda values"""
    print("Testing Dynamic Color Constraints with Lambda Penalty")
    print("=" * 60)

    # Create test collection
    collection_df = create_test_collection()
    print(f"Created test collection with {len(collection_df)} cards")

    # Initialize deck builder
    deck_builder = EnhancedDeckBuilder()

    # Test different lambda penalty values
    lambda_values = [0.1, 0.5, 1.0, 2.0]
    max_colors = 2
    deck_size = 20

    results = {}

    for lambda_penalty in lambda_values:
        print(f"\n--- Testing with lambda_penalty = {lambda_penalty} ---")

        try:
            result = deck_builder.build_optimal_deck_advanced(
                collection_df=collection_df,
                num_colors=max_colors,
                deck_size=deck_size,
                algorithm="genetic",
                export_formats=[],
                lambda_penalty=lambda_penalty,
            )

            # Analyze the result
            deck = result["deck"]
            actual_colors = result["target_colors"]
            score = result["score"]

            # Count cards by color
            color_counts = {}
            for card in deck:
                colors = card.get("colors", set())
                for color in colors:
                    color_counts[color] = color_counts.get(color, 0) + 1

            print(f"  Score: {score:.4f}")
            print(f"  Colors used: {actual_colors}")
            print(f"  Color distribution: {color_counts}")
            print(f"  Number of colors: {len(actual_colors)}")

            # Verify constraint
            if len(actual_colors) <= max_colors:
                print(
                    f"  ✅ Color constraint satisfied ({len(actual_colors)} <= {max_colors})"
                )
            else:
                print(
                    f"  ❌ Color constraint violated ({len(actual_colors)} > {max_colors})"
                )

            results[lambda_penalty] = {
                "score": score,
                "colors": actual_colors,
                "color_counts": color_counts,
                "num_colors": len(actual_colors),
            }

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results[lambda_penalty] = None

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    for lambda_penalty, result in results.items():
        if result:
            print(
                f"Lambda {lambda_penalty}: Score={result['score']:.4f}, Colors={result['colors']}, Count={result['num_colors']}"
            )
        else:
            print(f"Lambda {lambda_penalty}: Failed")

    # Verify that higher lambda values result in fewer colors
    successful_results = {k: v for k, v in results.items() if v is not None}
    if len(successful_results) > 1:
        lambda_scores = [(k, v["num_colors"]) for k, v in successful_results.items()]
        lambda_scores.sort(key=lambda x: x[0])  # Sort by lambda value

        print(f"\nColor count trend:")
        for lambda_val, color_count in lambda_scores:
            print(f"  Lambda {lambda_val}: {color_count} colors")

        # Check if higher lambda generally results in fewer colors
        if lambda_scores[0][1] >= lambda_scores[-1][1]:
            print("  ✅ Higher lambda values generally result in fewer colors")
        else:
            print("  ⚠️  Lambda penalty may not be working as expected")


def test_optimizer_scoring():
    """Test the scoring function with different color configurations"""
    print("\nTesting Optimizer Scoring Function")
    print("=" * 60)

    # Use the correct ratings file path
    ratings_file = "data/ratings/card_ratings.csv"
    optimizer = AdvancedDeckOptimizer(ratings_file)

    # Create test decks with different color counts
    test_cards = [
        {"name": "Lightning Bolt", "colors": {"R"}, "rating": 9.5, "cmc": 1},
        {"name": "Counterspell", "colors": {"U"}, "rating": 9.0, "cmc": 2},
        {"name": "Dark Ritual", "colors": {"B"}, "rating": 8.5, "cmc": 1},
        {"name": "Giant Growth", "colors": {"G"}, "rating": 8.0, "cmc": 1},
        {"name": "Healing Salve", "colors": {"W"}, "rating": 7.5, "cmc": 1},
    ]

    # Test different deck configurations
    configurations = [
        (test_cards[:2], "2-color deck"),  # 2 colors
        (test_cards[:3], "3-color deck"),  # 3 colors
        (test_cards[:4], "4-color deck"),  # 4 colors
        (test_cards[:5], "5-color deck"),  # 5 colors
    ]

    lambda_values = [0.1, 0.5, 1.0, 2.0, 5.0]  # Added stronger penalties

    for deck, description in configurations:
        print(f"\n{description}: {[card['name'] for card in deck]}")

        for lambda_penalty in lambda_values:
            score = optimizer.calculate_deck_score(
                deck, [], 40, max_colors=2, lambda_penalty=lambda_penalty
            )
            actual_colors = optimizer.get_deck_colors(deck)
            print(
                f"  Lambda {lambda_penalty}: Score={score:.4f}, Colors={actual_colors}"
            )


if __name__ == "__main__":
    test_dynamic_color_constraints()
    test_optimizer_scoring()
    print("\n✅ All tests completed!")

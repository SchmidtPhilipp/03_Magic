#!/usr/bin/env python3
"""
Test script for the improved color constraint system
Demonstrates how the Lagrange-style penalty function improves color focus
"""

import os
import sys

import pandas as pd

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from magic_optimizer import EnhancedDeckBuilder


def create_test_collection():
    """Create a test collection with cards from all colors"""
    test_cards = [
        # Red cards
        "Lightning Bolt",
        "Fireball",
        "Shock",
        "Lightning Strike",
        "Flame Slash",
        "Goblin Guide",
        "Monastery Swiftspear",
        "Young Pyromancer",
        "Grim Lavamancer",
        # Blue cards
        "Counterspell",
        "Mana Leak",
        "Remand",
        "Spell Pierce",
        "Dispel",
        "Delver of Secrets",
        "Snapcaster Mage",
        "Vendilion Clique",
        "Serum Visions",
        # Green cards
        "Giant Growth",
        "Rancor",
        "Vines of Vastwood",
        "Mutagenic Growth",
        "Groundswell",
        "Tarmogoyf",
        "Scavenging Ooze",
        "Noble Hierarch",
        "Birds of Paradise",
        # White cards
        "Path to Exile",
        "Swords to Plowshares",
        "Lightning Helix",
        "Boros Charm",
        "Savannah Lions",
        "Student of Warfare",
        "Steppe Lynx",
        "Kor Firewalker",
        # Black cards
        "Doom Blade",
        "Go for the Throat",
        "Dismember",
        "Victim of Night",
        "Dark Confidant",
        "Tasigur, the Golden Fang",
        "Gurmag Angler",
        "Death's Shadow",
        # Colorless cards
        "Sol Ring",
        "Lightning Greaves",
        "Swiftfoot Boots",
        "Skullclamp",
        "Sensei's Divining Top",
        "Engineered Explosives",
        "Pithing Needle",
    ]

    return pd.DataFrame({"Card Name": test_cards})


def analyze_deck_colors(deck, target_colors):
    """Analyze the colors in a deck and check for constraint violations"""
    print(f"\n=== DECK COLOR ANALYSIS ===")
    print(f"Target Colors: {target_colors}")
    print(f"Target Color Count: {len(target_colors)}")

    # Count cards by color
    color_counts = {}
    colorless_count = 0
    off_color_cards = []

    for card in deck:
        colors = card.get("colors", set())
        if not colors:
            colorless_count += 1
        else:
            for color in colors:
                color_counts[color] = color_counts.get(color, 0) + 1

            # Check for off-color cards
            card_colors = set(colors)
            off_colors = card_colors - set(target_colors)
            if off_colors:
                off_color_cards.append(
                    {
                        "name": card.get("name", "Unknown"),
                        "colors": list(card_colors),
                        "off_colors": list(off_colors),
                    }
                )

    print(f"\nColor Distribution:")
    for color, count in sorted(color_counts.items()):
        status = "✓" if color in target_colors else "✗ OFF-COLOR"
        print(f"  {color}: {count} cards {status}")

    if colorless_count > 0:
        print(f"  Colorless: {colorless_count} cards ✓")

    # Check for constraint violations
    used_colors = set(color_counts.keys())
    target_color_set = set(target_colors)

    print(f"\nConstraint Analysis:")
    print(f"Colors used: {len(used_colors)} ({list(used_colors)})")
    print(f"Target colors: {len(target_color_set)} ({list(target_color_set)})")

    # Check if we're using more colors than specified
    if len(used_colors) > len(target_colors):
        print(
            f"✗ VIOLATION: Using {len(used_colors)} colors but only {len(target_colors)} specified!"
        )
        excess_colors = used_colors - target_color_set
        print(f"  Excess colors: {list(excess_colors)}")
    else:
        print(f"✓ Colors constraint respected")

    # Check for off-color cards
    if off_color_cards:
        print(f"\n✗ VIOLATION: Found {len(off_color_cards)} cards with off-colors:")
        for card in off_color_cards[:5]:  # Show first 5
            print(f"  {card['name']}: {card['colors']} (off: {card['off_colors']})")
        if len(off_color_cards) > 5:
            print(f"  ... and {len(off_color_cards) - 5} more")
    else:
        print(f"✓ No off-color cards found")

    return {
        "used_colors": used_colors,
        "target_colors": target_color_set,
        "off_color_cards": off_color_cards,
        "violation": len(used_colors) > len(target_colors) or len(off_color_cards) > 0,
    }


def test_color_constraints():
    """Test all algorithms for color constraint compliance"""
    print("=== TESTING COLOR CONSTRAINTS ===")

    # Initialize deck builder
    builder = EnhancedDeckBuilder()

    # Create test collection
    collection_df = create_test_collection()
    print(f"Created test collection with {len(collection_df)} cards")

    # Test parameters
    num_colors = 2  # Test with 2 colors
    deck_size = 40

    algorithms = ["greedy", "genetic", "simulated_annealing"]

    results = {}

    for algorithm in algorithms:
        print(f"\n{'='*50}")
        print(f"TESTING {algorithm.upper()} ALGORITHM")
        print(f"{'='*50}")

        try:
            # Build deck
            result = builder.build_optimal_deck_advanced(
                collection_df, num_colors, deck_size, algorithm, []
            )

            # Analyze colors
            analysis = analyze_deck_colors(result["deck"], result["target_colors"])

            results[algorithm] = {
                "success": True,
                "score": result["score"],
                "target_colors": result["target_colors"],
                "analysis": analysis,
            }

        except Exception as e:
            print(f"Error with {algorithm}: {e}")
            results[algorithm] = {"success": False, "error": str(e)}

    # Summary
    print(f"\n{'='*50}")
    print(f"SUMMARY")
    print(f"{'='*50}")

    for algorithm, result in results.items():
        if result["success"]:
            status = "✓ PASS" if not result["analysis"]["violation"] else "✗ FAIL"
            print(f"{algorithm.upper()}: {status}")
            print(f"  Score: {result['score']:.4f}")
            print(f"  Target Colors: {result['target_colors']}")
            if result["analysis"]["violation"]:
                print(
                    f"  Issues: {len(result['analysis']['off_color_cards'])} off-color cards"
                )
        else:
            print(f"{algorithm.upper()}: ✗ ERROR - {result['error']}")


def test_penalty_function():
    """Test the penalty function directly"""
    print(f"\n=== TESTING PENALTY FUNCTION ===")

    from magic_optimizer.optimizer import AdvancedDeckOptimizer

    optimizer = AdvancedDeckOptimizer()

    # Test cases
    test_cases = [
        {
            "name": "Focused Mono-Red",
            "deck": [
                {"name": "Lightning Bolt", "colors": {"R"}, "rating": 9, "cmc": 1},
                {"name": "Fireball", "colors": {"R"}, "rating": 7, "cmc": 3},
                {"name": "Shock", "colors": {"R"}, "rating": 6, "cmc": 1},
            ],
            "target_colors": ["R"],
            "expected": "Low penalty",
        },
        {
            "name": "Spread Across Many Colors",
            "deck": [
                {"name": "Lightning Bolt", "colors": {"R"}, "rating": 9, "cmc": 1},
                {"name": "Counterspell", "colors": {"U"}, "rating": 9, "cmc": 2},
                {"name": "Giant Growth", "colors": {"G"}, "rating": 6, "cmc": 1},
                {"name": "Path to Exile", "colors": {"W"}, "rating": 8, "cmc": 1},
                {"name": "Doom Blade", "colors": {"B"}, "rating": 8, "cmc": 2},
            ],
            "target_colors": ["R", "U"],
            "expected": "High penalty",
        },
        {
            "name": "Off-Color Cards",
            "deck": [
                {"name": "Lightning Bolt", "colors": {"R"}, "rating": 9, "cmc": 1},
                {"name": "Counterspell", "colors": {"U"}, "rating": 9, "cmc": 2},
                {
                    "name": "Giant Growth",
                    "colors": {"G"},
                    "rating": 6,
                    "cmc": 1,
                },  # Off-color
            ],
            "target_colors": ["R", "U"],
            "expected": "High penalty for off-color",
        },
    ]

    for test_case in test_cases:
        penalty = optimizer.calculate_color_penalty(
            test_case["deck"], test_case["target_colors"]
        )

        print(f"\n{test_case['name']}:")
        print(f"  Expected: {test_case['expected']}")
        print(f"  Actual Penalty: {penalty:.4f}")

        if penalty < 0.5:
            print("  ✅ Low penalty (good)")
        elif penalty < 2.0:
            print("  ⚠️  Moderate penalty")
        else:
            print("  ❌ High penalty (bad)")


def main():
    """Main test function"""
    print("COLOR CONSTRAINT SYSTEM TEST")
    print("=" * 50)

    try:
        # Test color constraints
        test_color_constraints()

        # Test penalty function
        test_penalty_function()

        print(f"\n=== ALL TESTS COMPLETED ===")
        print("The color constraint system should now produce more focused decks!")

    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

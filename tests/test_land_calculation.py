#!/usr/bin/env python3
"""
Test for land calculation functionality
"""

import os
import sys

import pandas as pd

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from magic_optimizer import EnhancedDeckBuilder


def create_simple_test_collection():
    """Create a simple test collection for land testing"""
    test_cards = [
        # Red cards
        "Lightning Bolt",
        "Fireball",
        "Shock",
        "Lightning Strike",
        "Goblin Guide",
        "Monastery Swiftspear",
        "Young Pyromancer",
        # Blue cards
        "Counterspell",
        "Mana Leak",
        "Remand",
        "Spell Pierce",
        "Delver of Secrets",
        "Snapcaster Mage",
        "Serum Visions",
        # Green cards
        "Giant Growth",
        "Rancor",
        "Tarmogoyf",
        "Scavenging Ooze",
        "Noble Hierarch",
        "Birds of Paradise",
        "Llanowar Elves",
        # White cards
        "Path to Exile",
        "Swords to Plowshares",
        "Lightning Helix",
        "Savannah Lions",
        "Thalia, Guardian of Thraben",
        # Black cards
        "Doom Blade",
        "Dark Confidant",
        "Thoughtseize",
        "Liliana of the Veil",
        # Colorless cards
        "Sol Ring",
        "Lightning Greaves",
        "Skullclamp",
        "Sensei's Divining Top",
    ]

    return pd.DataFrame({"Card Name": test_cards})


def test_land_calculation():
    """Test land calculation for different deck sizes and formats"""
    print("=== LAND CALCULATION TEST ===")
    print("Testing optimal land calculation for different deck sizes")

    # Initialize deck builder
    builder = EnhancedDeckBuilder()

    # Create test collection
    collection_df = create_simple_test_collection()
    print(f"Created test collection with {len(collection_df)} cards")

    # Test configurations
    test_configs = [
        {
            "name": "Limited 40-card deck",
            "num_colors": 2,
            "deck_size": 40,
            "expected_lands_min": 15,
            "expected_lands_max": 18,
        },
        {
            "name": "Limited 30-card deck",
            "num_colors": 2,
            "deck_size": 30,
            "expected_lands_min": 12,
            "expected_lands_max": 15,
        },
        {
            "name": "Constructed 60-card deck",
            "num_colors": 2,
            "deck_size": 60,
            "expected_lands_min": 20,
            "expected_lands_max": 26,
        },
        {
            "name": "Mono-color deck",
            "num_colors": 1,
            "deck_size": 40,
            "expected_lands_min": 15,
            "expected_lands_max": 18,
        },
    ]

    results = {}

    for config in test_configs:
        print(f"\n{'='*50}")
        print(f"TESTING: {config['name']}")
        print(f"{'='*50}")
        print(f"Colors: {config['num_colors']}")
        print(f"Deck size: {config['deck_size']}")
        print(
            f"Expected lands: {config['expected_lands_min']}-{config['expected_lands_max']}"
        )

        try:
            # Build deck
            result = builder.build_optimal_deck_advanced(
                collection_df, config["num_colors"], config["deck_size"], "greedy", []
            )

            deck = result["deck"]
            target_colors = result["target_colors"]

            # Separate lands from non-land cards
            non_land_cards = [card for card in deck if card.get("type") != "Land"]
            land_cards = [card for card in deck if card.get("type") == "Land"]

            print(f"\nResults:")
            print(f"  Target Colors: {target_colors}")
            print(f"  Non-land cards: {len(non_land_cards)}")
            print(f"  Land cards: {len(land_cards)}")
            print(f"  Total deck size: {len(deck)}")

            # Analyze land distribution
            land_counts = {}
            for land in land_cards:
                land_name = land["name"]
                land_counts[land_name] = land_counts.get(land_name, 0) + 1

            print(f"\nLand Distribution:")
            for land_name, count in sorted(land_counts.items()):
                print(f"  {land_name}: {count}")

            # Test evaluation
            land_count = len(land_cards)
            expected_min = config["expected_lands_min"]
            expected_max = config["expected_lands_max"]

            # Success criteria
            success_criteria = []

            # 1. Land count should be within expected range
            if expected_min <= land_count <= expected_max:
                success_criteria.append(("✅ Land count in expected range", True))
            else:
                success_criteria.append(
                    (
                        f"❌ Land count {land_count} not in range {expected_min}-{expected_max}",
                        False,
                    )
                )

            # 2. Lands should match target colors
            land_colors = set()
            for land in land_cards:
                colors = land.get("colors", set())
                land_colors.update(colors)

            if land_colors.issubset(
                set(target_colors) | {None}
            ):  # None for colorless lands
                success_criteria.append(("✅ Land colors match target colors", True))
            else:
                success_criteria.append(
                    ("❌ Land colors don't match target colors", False)
                )

            # 3. Total deck size should be correct
            if len(deck) == config["deck_size"]:
                success_criteria.append(("✅ Total deck size correct", True))
            else:
                success_criteria.append(
                    (f"❌ Total deck size {len(deck)} != {config['deck_size']}", False)
                )

            # 4. Lands should be basic lands or appropriate utility lands
            valid_lands = ["Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"]
            invalid_lands = [
                land["name"] for land in land_cards if land["name"] not in valid_lands
            ]

            if not invalid_lands:
                success_criteria.append(
                    ("✅ All lands are valid basic/utility lands", True)
                )
            else:
                success_criteria.append(
                    (f"❌ Invalid lands found: {invalid_lands}", False)
                )

            # Display results
            for criterion, passed in success_criteria:
                print(f"  {criterion}")

            # Overall test result
            passed_tests = sum(1 for _, passed in success_criteria if passed)
            total_tests = len(success_criteria)

            print(f"\nTest Results: {passed_tests}/{total_tests} criteria passed")

            results[config["name"]] = {
                "success": passed_tests == total_tests,
                "land_count": land_count,
                "expected_range": (expected_min, expected_max),
                "land_distribution": land_counts,
                "total_deck_size": len(deck),
            }

            if passed_tests == total_tests:
                print("✅ LAND CALCULATION TEST PASSED!")
            else:
                print("⚠️  Some land calculation criteria failed.")

        except Exception as e:
            print(f"❌ Error during test: {e}")
            import traceback

            traceback.print_exc()
            results[config["name"]] = {"success": False, "error": str(e)}

    # Final summary
    print(f"\n{'='*60}")
    print(f"LAND CALCULATION TEST SUMMARY")
    print(f"{'='*60}")

    successful_tests = 0
    total_tests = len(test_configs)

    for test_name, result in results.items():
        if result["success"]:
            print(
                f"✅ {test_name}: {result['land_count']} lands (expected: {result['expected_range'][0]}-{result['expected_range'][1]})"
            )
            successful_tests += 1
        else:
            print(f"❌ {test_name}: {result.get('error', 'Unknown error')}")

    print(f"\nOverall Results: {successful_tests}/{total_tests} tests passed")

    if successful_tests == total_tests:
        print("🎉 ALL LAND CALCULATION TESTS PASSED!")
    else:
        print("⚠️  Some land calculation tests failed.")

    return results


def test_land_distribution():
    """Test land distribution across different color combinations"""
    print(f"\n{'='*60}")
    print(f"LAND DISTRIBUTION TEST")
    print(f"{'='*60}")

    builder = EnhancedDeckBuilder()
    collection_df = create_simple_test_collection()

    color_configs = [
        {"name": "Mono-Red", "colors": 1, "expected_lands": ["Mountain"]},
        {"name": "Red-Green", "colors": 2, "expected_lands": ["Mountain", "Forest"]},
        {
            "name": "Three-Color",
            "colors": 3,
            "expected_lands": ["Mountain", "Forest", "Island"],
        },
    ]

    for config in color_configs:
        print(f"\nTesting {config['name']}...")

        try:
            result = builder.build_optimal_deck_advanced(
                collection_df, config["colors"], 40, "greedy", []
            )

            land_cards = [card for card in result["deck"] if card.get("type") == "Land"]
            land_names = [land["name"] for land in land_cards]

            print(f"  Lands found: {land_names}")

            # Check if expected land types are present
            expected_lands = config["expected_lands"]
            found_expected = [land for land in expected_lands if land in land_names]

            if (
                len(found_expected) >= len(expected_lands) * 0.8
            ):  # At least 80% of expected lands
                print(f"  ✅ Expected land types found")
            else:
                print(f"  ❌ Missing expected land types")

        except Exception as e:
            print(f"  ❌ Error: {e}")


if __name__ == "__main__":
    test_land_calculation()
    test_land_distribution()

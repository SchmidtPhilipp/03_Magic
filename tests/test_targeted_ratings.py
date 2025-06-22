#!/usr/bin/env python3
"""
Targeted test with known card ratings to verify selection accuracy
"""

import os
import sys

import pandas as pd

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from magic_optimizer import EnhancedDeckBuilder


def create_targeted_test_collection():
    """
    Create a test collection with known high and low rated cards
    This allows us to verify that the system correctly selects high-rated cards
    """

    # High-rated cards (should be selected)
    high_rated_cards = [
        # Red cards with high ratings
        "Lightning Bolt",  # Rating: 9/10
        "Fireball",  # Rating: 8/10
        "Shock",  # Rating: 7/10
        "Lightning Strike",  # Rating: 7/10
        "Goblin Guide",  # Rating: 8/10
        "Monastery Swiftspear",  # Rating: 8/10
        # Blue cards with high ratings
        "Counterspell",  # Rating: 9/10
        "Mana Leak",  # Rating: 8/10
        "Remand",  # Rating: 8/10
        "Spell Pierce",  # Rating: 7/10
        "Delver of Secrets",  # Rating: 8/10
        "Snapcaster Mage",  # Rating: 9/10
        # Green cards with high ratings
        "Giant Growth",  # Rating: 7/10
        "Rancor",  # Rating: 8/10
        "Tarmogoyf",  # Rating: 9/10
        "Scavenging Ooze",  # Rating: 8/10
        "Noble Hierarch",  # Rating: 8/10
        "Birds of Paradise",  # Rating: 8/10
        # White cards with high ratings
        "Path to Exile",  # Rating: 9/10
        "Swords to Plowshares",  # Rating: 9/10
        "Lightning Helix",  # Rating: 8/10
        "Savannah Lions",  # Rating: 7/10
        "Thalia, Guardian of Thraben",  # Rating: 8/10
        # Black cards with high ratings
        "Doom Blade",  # Rating: 8/10
        "Dark Confidant",  # Rating: 9/10
        "Thoughtseize",  # Rating: 9/10
        "Liliana of the Veil",  # Rating: 9/10
        "Death's Shadow",  # Rating: 8/10
        # Colorless cards with high ratings
        "Sol Ring",  # Rating: 9/10
        "Lightning Greaves",  # Rating: 8/10
        "Skullclamp",  # Rating: 9/10
        "Sensei's Divining Top",  # Rating: 8/10
    ]

    # Low-rated cards (should NOT be selected)
    low_rated_cards = [
        # Red cards with low ratings
        "Flame Slash",  # Rating: 2/10
        "Grim Lavamancer",  # Rating: 3/10
        "Eidolon of the Great Revel",  # Rating: 2/10
        "Searing Blaze",  # Rating: 3/10
        "Skullcrack",  # Rating: 2/10
        "Young Pyromancer",  # Rating: 3/10
        # Blue cards with low ratings
        "Dispel",  # Rating: 2/10
        "Vendilion Clique",  # Rating: 3/10
        "Serum Visions",  # Rating: 2/10
        "Thought Scour",  # Rating: 2/10
        "Gitaxian Probe",  # Rating: 1/10
        "Ponder",  # Rating: 3/10
        # Green cards with low ratings
        "Vines of Vastwood",  # Rating: 2/10
        "Mutagenic Growth",  # Rating: 2/10
        "Groundswell",  # Rating: 2/10
        "Llanowar Elves",  # Rating: 3/10
        "Elvish Mystic",  # Rating: 3/10
        "Arbor Elf",  # Rating: 2/10
        # White cards with low ratings
        "Boros Charm",  # Rating: 2/10
        "Student of Warfare",  # Rating: 2/10
        "Steppe Lynx",  # Rating: 2/10
        "Kor Firewalker",  # Rating: 2/10
        "Aven Mindcensor",  # Rating: 2/10
        "Restoration Angel",  # Rating: 3/10
        # Black cards with low ratings
        "Go for the Throat",  # Rating: 2/10
        "Dismember",  # Rating: 2/10
        "Victim of Night",  # Rating: 2/10
        "Tasigur, the Golden Fang",  # Rating: 2/10
        "Gurmag Angler",  # Rating: 2/10
        "Inquisition of Kozilek",  # Rating: 3/10
        "Duress",  # Rating: 2/10
        # Colorless cards with low ratings
        "Swiftfoot Boots",  # Rating: 2/10
        "Engineered Explosives",  # Rating: 2/10
        "Pithing Needle",  # Rating: 2/10
    ]

    # Create DataFrame with all cards
    all_cards = high_rated_cards + low_rated_cards

    # Create ratings DataFrame
    ratings_data = []

    # Add high-rated cards
    for card in high_rated_cards:
        if "Lightning Bolt" in card:
            rating = 9
        elif (
            "Counterspell" in card
            or "Path to Exile" in card
            or "Swords to Plowshares" in card
            or "Dark Confidant" in card
            or "Thoughtseize" in card
            or "Liliana of the Veil" in card
            or "Sol Ring" in card
            or "Skullclamp" in card
        ):
            rating = 9
        elif "Snapcaster Mage" in card or "Tarmogoyf" in card:
            rating = 9
        elif (
            "Fireball" in card
            or "Goblin Guide" in card
            or "Monastery Swiftspear" in card
            or "Mana Leak" in card
            or "Remand" in card
            or "Delver of Secrets" in card
            or "Rancor" in card
            or "Scavenging Ooze" in card
            or "Noble Hierarch" in card
            or "Birds of Paradise" in card
            or "Lightning Helix" in card
            or "Thalia, Guardian of Thraben" in card
            or "Doom Blade" in card
            or "Death's Shadow" in card
            or "Lightning Greaves" in card
            or "Sensei's Divining Top" in card
        ):
            rating = 8
        else:
            rating = 7
        ratings_data.append({"Card Name": card, "Rating": f"{rating}/10"})

    # Add low-rated cards
    for card in low_rated_cards:
        if "Gitaxian Probe" in card:
            rating = 1
        else:
            rating = 2  # Most low-rated cards get 2/10
        ratings_data.append({"Card Name": card, "Rating": f"{rating}/10"})

    # Save ratings to file
    ratings_df = pd.DataFrame(ratings_data)
    ratings_file = "data/ratings/test_targeted_ratings.csv"
    os.makedirs(os.path.dirname(ratings_file), exist_ok=True)
    ratings_df.to_csv(ratings_file, index=False)

    print(f"Created targeted test collection:")
    print(f"  High-rated cards: {len(high_rated_cards)}")
    print(f"  Low-rated cards: {len(low_rated_cards)}")
    print(f"  Total cards: {len(all_cards)}")
    print(f"  Ratings saved to: {ratings_file}")

    return pd.DataFrame({"Card Name": all_cards}), high_rated_cards, low_rated_cards


def test_targeted_selection():
    """Test that the system correctly selects high-rated cards and avoids low-rated cards"""
    print("=== TARGETED RATING SELECTION TEST ===")
    print("Testing that high-rated cards are selected and low-rated cards are avoided")

    # Create test collection
    collection_df, high_rated_cards, low_rated_cards = create_targeted_test_collection()

    # Initialize deck builder with our test ratings
    builder = EnhancedDeckBuilder("data/ratings/test_targeted_ratings.csv")

    # Test parameters
    num_colors = 2
    deck_size = 25  # Non-land cards
    algorithm = "greedy"  # Use greedy for predictable results
    export_formats = ["copy_paste"]

    print(f"\nTest Configuration:")
    print(f"  Colors: {num_colors}")
    print(f"  Deck size (non-land): {deck_size}")
    print(f"  Algorithm: {algorithm}")

    try:
        # Build deck
        result = builder.build_optimal_deck_advanced(
            collection_df, num_colors, deck_size, algorithm, export_formats
        )

        deck = result["deck"]
        target_colors = result["target_colors"]

        print(f"\n=== RESULTS ===")
        print(f"Target Colors: {target_colors}")
        print(f"Final Deck Size: {len(deck)}")

        # Separate lands from non-land cards
        non_land_cards = [card for card in deck if card.get("type") != "Land"]
        land_cards = [card for card in deck if card.get("type") == "Land"]

        print(f"Non-land cards: {len(non_land_cards)}")
        print(f"Land cards: {len(land_cards)}")

        # Analyze card selection
        selected_high_rated = []
        selected_low_rated = []
        selected_other = []

        for card in non_land_cards:
            card_name = card["name"]
            rating = card.get("rating", 0)

            if card_name in high_rated_cards:
                selected_high_rated.append((card_name, rating))
            elif card_name in low_rated_cards:
                selected_low_rated.append((card_name, rating))
            else:
                selected_other.append((card_name, rating))

        # Calculate statistics - use available cards in target colors
        available_high_rated = []
        available_low_rated = []

        for card_name in high_rated_cards:
            card_data = builder.validator.search_card(card_name)
            if card_data:
                colors = card_data.get("colors", [])
                if not colors or any(color in target_colors for color in colors):
                    available_high_rated.append(card_name)

        for card_name in low_rated_cards:
            card_data = builder.validator.search_card(card_name)
            if card_data:
                colors = card_data.get("colors", [])
                if not colors or any(color in target_colors for color in colors):
                    available_low_rated.append(card_name)

        total_high_rated_available = len(available_high_rated)
        total_low_rated_available = len(available_low_rated)

        high_rated_selection_rate = (
            len(selected_high_rated) / total_high_rated_available
            if total_high_rated_available > 0
            else 0
        )
        low_rated_selection_rate = (
            len(selected_low_rated) / total_low_rated_available
            if total_low_rated_available > 0
            else 0
        )

        print(f"\n=== SELECTION ANALYSIS ===")
        print(
            f"High-rated cards selected: {len(selected_high_rated)}/{total_high_rated_available} ({high_rated_selection_rate:.1%})"
        )
        print(
            f"Low-rated cards selected: {len(selected_low_rated)}/{total_low_rated_available} ({low_rated_selection_rate:.1%})"
        )
        print(f"Other cards selected: {len(selected_other)}")

        # Display selected cards
        print(f"\nSelected High-Rated Cards:")
        for card_name, rating in selected_high_rated:
            print(f"  ✅ {card_name} (Rating: {rating}/10)")

        print(f"\nSelected Low-Rated Cards:")
        for card_name, rating in selected_low_rated:
            print(f"  ❌ {card_name} (Rating: {rating}/10)")

        if selected_other:
            print(f"\nSelected Other Cards:")
            for card_name, rating in selected_other:
                print(f"  ⚠️  {card_name} (Rating: {rating}/10)")

        # Display land distribution
        print(f"\n=== LAND DISTRIBUTION ===")
        land_counts = {}
        for land in land_cards:
            land_name = land["name"]
            land_counts[land_name] = land_counts.get(land_name, 0) + 1

        for land_name, count in sorted(land_counts.items()):
            print(f"  {land_name}: {count}")

        # Test evaluation
        print(f"\n=== TEST EVALUATION ===")

        # Success criteria
        success_criteria = []

        # 1. High-rated cards should be selected
        if high_rated_selection_rate >= 0.8:
            success_criteria.append(("✅ High-rated cards selected", True))
        else:
            success_criteria.append(("❌ High-rated cards not selected enough", False))

        # 2. Low-rated cards should be avoided
        if low_rated_selection_rate <= 0.2:
            success_criteria.append(("✅ Low-rated cards avoided", True))
        else:
            success_criteria.append(("❌ Too many low-rated cards selected", False))

        # 3. Lands should be added
        if len(land_cards) > 0:
            success_criteria.append(("✅ Lands added to deck", True))
        else:
            success_criteria.append(("❌ No lands added", False))

        # 4. Color constraints respected
        used_colors = set()
        for card in non_land_cards:
            colors = card.get("colors", set())
            used_colors.update(colors)

        if len(used_colors) <= len(target_colors):
            success_criteria.append(("✅ Color constraints respected", True))
        else:
            success_criteria.append(("❌ Color constraints violated", False))

        # 5. Land count should be reasonable (15-18 for 40-card deck)
        total_deck_size = len(deck)
        expected_lands_min = int(total_deck_size * 0.35)  # 35% minimum
        expected_lands_max = int(total_deck_size * 0.45)  # 45% maximum

        if expected_lands_min <= len(land_cards) <= expected_lands_max:
            success_criteria.append(("✅ Land count is reasonable", True))
        else:
            success_criteria.append(
                (
                    f"❌ Land count {len(land_cards)} not in reasonable range {expected_lands_min}-{expected_lands_max}",
                    False,
                )
            )

        # Display results
        for criterion, passed in success_criteria:
            print(f"  {criterion}")

        # Overall test result
        passed_tests = sum(1 for _, passed in success_criteria if passed)
        total_tests = len(success_criteria)

        print(f"\nTest Results: {passed_tests}/{total_tests} criteria passed")

        if passed_tests == total_tests:
            print(
                "🎉 ALL TESTS PASSED! System correctly selects high-rated cards and avoids low-rated cards."
            )
        else:
            print("⚠️  Some tests failed. Check the analysis above.")

        return {
            "success": passed_tests == total_tests,
            "high_rated_selection_rate": high_rated_selection_rate,
            "low_rated_selection_rate": low_rated_selection_rate,
            "lands_added": len(land_cards),
            "color_constraints_respected": len(used_colors) <= len(target_colors),
            "land_count_reasonable": expected_lands_min
            <= len(land_cards)
            <= expected_lands_max,
        }

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


def test_multiple_algorithms():
    """Test multiple algorithms with the targeted collection"""
    print(f"\n{'='*60}")
    print(f"MULTIPLE ALGORITHM TEST WITH TARGETED RATINGS")
    print(f"{'='*60}")

    # Create test collection
    collection_df, high_rated_cards, low_rated_cards = create_targeted_test_collection()

    algorithms = ["greedy", "genetic", "simulated_annealing"]
    results = {}

    for algorithm in algorithms:
        print(f"\nTesting {algorithm.upper()} algorithm...")

        try:
            builder = EnhancedDeckBuilder("data/ratings/test_targeted_ratings.csv")
            result = builder.build_optimal_deck_advanced(
                collection_df, 2, 20, algorithm, []
            )

            # Analyze results
            deck = result["deck"]
            non_land_cards = [card for card in deck if card.get("type") != "Land"]

            selected_high_rated = [
                card["name"]
                for card in non_land_cards
                if card["name"] in high_rated_cards
            ]
            selected_low_rated = [
                card["name"]
                for card in non_land_cards
                if card["name"] in low_rated_cards
            ]

            high_rated_rate = (
                len(selected_high_rated) / len(non_land_cards) if non_land_cards else 0
            )
            low_rated_rate = (
                len(selected_low_rated) / len(non_land_cards) if non_land_cards else 0
            )

            results[algorithm] = {
                "success": True,
                "score": result["score"],
                "high_rated_rate": high_rated_rate,
                "low_rated_rate": low_rated_rate,
                "lands_added": len(
                    [card for card in deck if card.get("type") == "Land"]
                ),
                "selected_high_rated": selected_high_rated,
                "selected_low_rated": selected_low_rated,
            }

            print(f"  Score: {result['score']:.4f}")
            print(
                f"  High-rated cards: {len(selected_high_rated)} ({high_rated_rate:.1%})"
            )
            print(
                f"  Low-rated cards: {len(selected_low_rated)} ({low_rated_rate:.1%})"
            )
            print(f"  Lands added: {results[algorithm]['lands_added']}")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results[algorithm] = {"success": False, "error": str(e)}

    # Summary
    print(f"\n{'='*60}")
    print(f"ALGORITHM COMPARISON SUMMARY")
    print(f"{'='*60}")

    for algorithm, result in results.items():
        if result["success"]:
            status = (
                "✅"
                if result["high_rated_rate"] >= 0.8 and result["low_rated_rate"] <= 0.2
                else "⚠️"
            )
            print(f"{status} {algorithm.upper()}:")
            print(f"  Score: {result['score']:.4f}")
            print(f"  High-rated selection: {result['high_rated_rate']:.1%}")
            print(f"  Low-rated selection: {result['low_rated_rate']:.1%}")
            print(f"  Lands: {result['lands_added']}")
        else:
            print(f"❌ {algorithm.upper()}: {result['error']}")


if __name__ == "__main__":
    test_targeted_selection()
    test_multiple_algorithms()

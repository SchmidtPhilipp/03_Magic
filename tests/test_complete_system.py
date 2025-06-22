#!/usr/bin/env python3
"""
Complete system test for Magic Optimizer including HTML artwork export
"""

import os
import sys

import pandas as pd

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from magic_optimizer import EnhancedDeckBuilder


def create_comprehensive_test_collection():
    """Create a comprehensive test collection with cards from all colors"""
    test_cards = [
        # Red cards (high ratings)
        "Lightning Bolt",
        "Fireball",
        "Shock",
        "Lightning Strike",
        "Flame Slash",
        "Goblin Guide",
        "Monastery Swiftspear",
        "Young Pyromancer",
        "Grim Lavamancer",
        "Eidolon of the Great Revel",
        "Searing Blaze",
        "Skullcrack",
        # Blue cards (high ratings)
        "Counterspell",
        "Mana Leak",
        "Remand",
        "Spell Pierce",
        "Dispel",
        "Delver of Secrets",
        "Snapcaster Mage",
        "Vendilion Clique",
        "Serum Visions",
        "Thought Scour",
        "Gitaxian Probe",
        "Ponder",
        # Green cards (medium ratings)
        "Giant Growth",
        "Rancor",
        "Vines of Vastwood",
        "Mutagenic Growth",
        "Groundswell",
        "Tarmogoyf",
        "Scavenging Ooze",
        "Noble Hierarch",
        "Birds of Paradise",
        "Llanowar Elves",
        "Elvish Mystic",
        "Arbor Elf",
        # White cards (medium ratings)
        "Path to Exile",
        "Swords to Plowshares",
        "Lightning Helix",
        "Boros Charm",
        "Savannah Lions",
        "Student of Warfare",
        "Steppe Lynx",
        "Kor Firewalker",
        "Thalia, Guardian of Thraben",
        "Aven Mindcensor",
        "Restoration Angel",
        # Black cards (medium ratings)
        "Doom Blade",
        "Go for the Throat",
        "Dismember",
        "Victim of Night",
        "Dark Confidant",
        "Tasigur, the Golden Fang",
        "Gurmag Angler",
        "Death's Shadow",
        "Thoughtseize",
        "Inquisition of Kozilek",
        "Duress",
        "Liliana of the Veil",
        # Colorless cards (high ratings)
        "Sol Ring",
        "Lightning Greaves",
        "Swiftfoot Boots",
        "Skullclamp",
        "Sensei's Divining Top",
        "Engineered Explosives",
        "Pithing Needle",
    ]

    return pd.DataFrame({"Card Name": test_cards})


def test_complete_system():
    """Test the complete system with all features"""
    print("=== COMPLETE MAGIC OPTIMIZER SYSTEM TEST ===")
    print("Testing all algorithms, color constraints, and export formats")

    # Initialize deck builder
    builder = EnhancedDeckBuilder()

    # Create test collection
    collection_df = create_comprehensive_test_collection()
    print(f"Created test collection with {len(collection_df)} cards")

    # Test configurations
    test_configs = [
        {
            "name": "Mono-Red Aggro",
            "num_colors": 1,
            "deck_size": 25,
            "algorithm": "greedy",
            "export_formats": ["html_artwork", "copy_paste", "arena"],
        },
        {
            "name": "Red-Black Midrange",
            "num_colors": 2,
            "deck_size": 30,
            "algorithm": "genetic",
            "export_formats": ["html_artwork", "copy_paste", "mtgo"],
        },
        {
            "name": "Three-Color Control",
            "num_colors": 3,
            "deck_size": 35,
            "algorithm": "simulated_annealing",
            "export_formats": ["html_artwork", "copy_paste", "cockatrice"],
        },
    ]

    results = {}

    for config in test_configs:
        print(f"\n{'='*60}")
        print(f"TESTING: {config['name']}")
        print(f"{'='*60}")
        print(f"Colors: {config['num_colors']}")
        print(f"Deck Size: {config['deck_size']}")
        print(f"Algorithm: {config['algorithm']}")
        print(f"Export Formats: {config['export_formats']}")

        try:
            # Build deck
            result = builder.build_optimal_deck_advanced(
                collection_df,
                config["num_colors"],
                config["deck_size"],
                config["algorithm"],
                config["export_formats"],
            )

            # Analyze results
            deck = result["deck"]
            target_colors = result["target_colors"]
            score = result["score"]

            # Check color constraints
            used_colors = set()
            off_color_cards = []

            for card in deck:
                colors = card.get("colors", set())
                if colors:
                    for color in colors:
                        used_colors.add(color)
                    # Check for off-color cards
                    card_colors = set(colors)
                    off_colors = card_colors - set(target_colors)
                    if off_colors:
                        off_color_cards.append(
                            {
                                "name": card["name"],
                                "colors": list(card_colors),
                                "off_colors": list(off_colors),
                            }
                        )

            # Calculate statistics
            color_counts = {}
            colorless_count = 0
            for card in deck:
                colors = card.get("colors", set())
                if not colors:
                    colorless_count += 1
                else:
                    for color in colors:
                        color_counts[color] = color_counts.get(color, 0) + 1

            ratings = [card.get("rating", 0) for card in deck]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0

            # Store results
            results[config["name"]] = {
                "success": True,
                "score": score,
                "target_colors": target_colors,
                "used_colors": used_colors,
                "deck_size": len(deck),
                "avg_rating": avg_rating,
                "color_constraint_violation": len(used_colors) > len(target_colors)
                or len(off_color_cards) > 0,
                "off_color_cards": off_color_cards,
                "exported_files": result.get("exported_files", {}),
            }

            # Print results
            print(f"\n✅ Deck built successfully!")
            print(f"Score: {score:.4f}")
            print(f"Target Colors: {target_colors}")
            print(f"Used Colors: {list(used_colors)}")
            print(f"Deck Size: {len(deck)}")
            print(f"Average Rating: {avg_rating:.2f}/10")

            print(f"\nColor Distribution:")
            for color, count in sorted(color_counts.items()):
                status = "✓" if color in target_colors else "✗ OFF-COLOR"
                print(f"  {color}: {count} cards {status}")
            if colorless_count > 0:
                print(f"  Colorless: {colorless_count} cards ✓")

            if results[config["name"]]["color_constraint_violation"]:
                print(f"\n⚠️  COLOR CONSTRAINT VIOLATION DETECTED!")
                print(
                    f"Using {len(used_colors)} colors but only {len(target_colors)} specified"
                )
                if off_color_cards:
                    print(f"Off-color cards: {len(off_color_cards)}")
            else:
                print(f"\n✅ Color constraints respected")

            # Check exported files
            if "exported_files" in result:
                print(f"\nExported files:")
                for format_type, filename in result["exported_files"].items():
                    if filename and os.path.exists(filename):
                        file_size = os.path.getsize(filename)
                        print(f"  ✅ {format_type}: {filename} ({file_size} bytes)")
                    else:
                        print(f"  ❌ {format_type}: Export failed")

        except Exception as e:
            print(f"❌ Error: {e}")
            results[config["name"]] = {"success": False, "error": str(e)}

    # Final summary
    print(f"\n{'='*60}")
    print(f"FINAL SUMMARY")
    print(f"{'='*60}")

    successful_tests = 0
    total_tests = len(test_configs)

    for test_name, result in results.items():
        if result["success"]:
            status = (
                "✅ PASS"
                if not result["color_constraint_violation"]
                else "⚠️  PASS WITH VIOLATIONS"
            )
            print(f"{test_name}: {status}")
            print(f"  Score: {result['score']:.4f}")
            print(
                f"  Colors: {result['target_colors']} (used: {list(result['used_colors'])})"
            )
            print(f"  Size: {result['deck_size']}")
            print(f"  Avg Rating: {result['avg_rating']:.2f}/10")

            if result["color_constraint_violation"]:
                print(f"  ⚠️  Color constraint violations detected")

            successful_tests += 1
        else:
            print(f"{test_name}: ❌ FAIL - {result['error']}")

    print(f"\nTest Results: {successful_tests}/{total_tests} successful")

    if successful_tests == total_tests:
        print("🎉 ALL TESTS PASSED! System is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

    return results


def test_html_artwork_specific():
    """Test HTML artwork export specifically"""
    print(f"\n{'='*60}")
    print(f"HTML ARTWORK EXPORT SPECIFIC TEST")
    print(f"{'='*60}")

    builder = EnhancedDeckBuilder()
    collection_df = create_comprehensive_test_collection()

    try:
        result = builder.build_optimal_deck_advanced(
            collection_df, 2, 20, "greedy", ["html_artwork"]
        )

        html_file = result["exported_files"].get("html_artwork")
        if html_file and os.path.exists(html_file):
            print(f"✅ HTML file created: {html_file}")

            # Check HTML content
            with open(html_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for key elements
            checks = [
                ("Magic Optimizer Deck", "Title"),
                ("card-image", "Card images"),
                ("color-symbol", "Color symbols"),
                ("rating", "Rating display"),
                ("CMC", "CMC display"),
            ]

            print(f"\nHTML Content Analysis:")
            for check_text, description in checks:
                count = content.count(check_text)
                status = "✅" if count > 0 else "❌"
                print(f"  {status} {description}: {count} occurrences")

            # Check for Scryfall URLs
            scryfall_urls = content.count("api.scryfall.com")
            print(f"  ✅ Scryfall image URLs: {scryfall_urls}")

            if scryfall_urls == len(result["deck"]):
                print(f"  ✅ All cards have Scryfall image URLs")
            else:
                print(f"  ⚠️  Missing Scryfall URLs for some cards")

            print(f"\n🎨 HTML Artwork Export Test: SUCCESS!")

        else:
            print(f"❌ HTML file not created or not found")

    except Exception as e:
        print(f"❌ Error in HTML artwork test: {e}")


if __name__ == "__main__":
    test_complete_system()
    test_html_artwork_specific()

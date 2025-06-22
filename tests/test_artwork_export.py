#!/usr/bin/env python3
"""
Test script for HTML artwork export functionality
"""

import os
import sys

import pandas as pd

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from magic_optimizer import EnhancedDeckBuilder


def create_test_collection():
    """Create a test collection with popular cards"""
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
        "Vines of Vastwood",
        "Tarmogoyf",
        "Scavenging Ooze",
        "Noble Hierarch",
        "Birds of Paradise",
        # White cards
        "Path to Exile",
        "Swords to Plowshares",
        "Lightning Helix",
        "Savannah Lions",
        "Student of Warfare",
        "Thalia, Guardian of Thraben",
        # Black cards
        "Doom Blade",
        "Go for the Throat",
        "Dismember",
        "Dark Confidant",
        "Tasigur, the Golden Fang",
        "Thoughtseize",
        # Colorless cards
        "Sol Ring",
        "Lightning Greaves",
        "Swiftfoot Boots",
        "Skullclamp",
    ]

    return pd.DataFrame({"Card Name": test_cards})


def test_artwork_export():
    """Test the HTML artwork export functionality"""
    print("=== TESTING HTML ARTWORK EXPORT ===")

    # Initialize deck builder
    builder = EnhancedDeckBuilder()

    # Create test collection
    collection_df = create_test_collection()
    print(f"Created test collection with {len(collection_df)} cards")

    # Test parameters
    num_colors = 2
    deck_size = 20  # Smaller deck for testing
    algorithm = "greedy"  # Fast algorithm for testing
    export_formats = ["html_artwork", "copy_paste"]

    try:
        print(f"\nBuilding deck with {algorithm} algorithm...")
        print(f"Target colors: {num_colors}")
        print(f"Deck size: {deck_size}")
        print(f"Export formats: {export_formats}")

        # Build deck
        result = builder.build_optimal_deck_advanced(
            collection_df, num_colors, deck_size, algorithm, export_formats
        )

        print(f"\nDeck building completed!")
        print(f"Algorithm: {algorithm.upper()}")
        print(f"Score: {result['score']:.4f}")
        print(f"Target Colors: {result['target_colors']}")
        print(f"Deck Size: {len(result['deck'])}")

        # Check exported files
        if "exported_files" in result:
            print(f"\nExported files:")
            for format_type, filename in result["exported_files"].items():
                if filename:
                    print(f"  {format_type}: {filename}")

                    # Check if HTML file exists and has content
                    if format_type == "html_artwork" and os.path.exists(filename):
                        file_size = os.path.getsize(filename)
                        print(f"    File size: {file_size} bytes")

                        # Check HTML content
                        with open(filename, "r", encoding="utf-8") as f:
                            content = f.read()
                            if "Magic Optimizer Deck" in content:
                                print(f"    ✅ HTML content looks good")
                            else:
                                print(f"    ⚠️  HTML content may be incomplete")

                        # Check for card images
                        card_count = content.count("card-image")
                        print(f"    Card images found: {card_count}")

                        if card_count == len(result["deck"]):
                            print(f"    ✅ All cards have image placeholders")
                        else:
                            print(f"    ⚠️  Missing image placeholders for some cards")
                    else:
                        print(f"    ❌ File not found or export failed")

        # Test deck analysis
        print(f"\n=== DECK ANALYSIS ===")
        color_counts = {}
        colorless_count = 0

        for card in result["deck"]:
            colors = card.get("colors", set())
            if not colors:
                colorless_count += 1
            else:
                for color in colors:
                    color_counts[color] = color_counts.get(color, 0) + 1

        print(f"Color Distribution:")
        for color, count in sorted(color_counts.items()):
            print(f"  {color}: {count} cards")
        if colorless_count > 0:
            print(f"  Colorless: {colorless_count} cards")

        # Rating analysis
        ratings = [card.get("rating", 0) for card in result["deck"]]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        print(f"Average Rating: {avg_rating:.2f}/10")

        print(f"\n✅ HTML Artwork Export Test Completed Successfully!")

    except Exception as e:
        print(f"❌ Error during artwork export test: {e}")
        import traceback

        traceback.print_exc()


def test_multiple_formats():
    """Test multiple export formats including artwork"""
    print(f"\n{'='*50}")
    print(f"TESTING MULTIPLE EXPORT FORMATS")
    print(f"{'='*50}")

    # Initialize deck builder
    builder = EnhancedDeckBuilder()

    # Create test collection
    collection_df = create_test_collection()

    # Test all export formats
    all_formats = [
        "copy_paste",
        "arena",
        "mtgo",
        "cockatrice",
        "tappedout",
        "archidekt",
        "moxfield",
        "html_artwork",
    ]

    try:
        result = builder.build_optimal_deck_advanced(
            collection_df, 2, 15, "greedy", all_formats
        )

        print(f"Export Results:")
        for format_type, filename in result["exported_files"].items():
            status = "✅" if filename and os.path.exists(filename) else "❌"
            print(f"  {status} {format_type}: {filename}")

            if filename and os.path.exists(filename):
                file_size = os.path.getsize(filename)
                print(f"    Size: {file_size} bytes")

        print(f"\n✅ Multiple Format Export Test Completed!")

    except Exception as e:
        print(f"❌ Error during multiple format test: {e}")


if __name__ == "__main__":
    test_artwork_export()
    test_multiple_formats()

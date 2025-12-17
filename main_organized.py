#!/usr/bin/env python3
"""
Enhanced Magic: The Gathering Deck Builder with Advanced Optimization
Now includes optimal land calculation and comprehensive testing
"""

import os
import sys
from typing import Dict, List

import pandas as pd

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from magic_optimizer import EnhancedDeckBuilder


def main():
    """Main application with enhanced features"""
    print("=" * 60)
    print("ENHANCED MAGIC: THE GATHERING DECK BUILDER")
    print("=" * 60)
    print("Features:")
    print("✅ Advanced optimization algorithms (Greedy, Genetic, Simulated Annealing)")
    print("✅ Color constraint enforcement")
    print("✅ Optimal land calculation and distribution")
    print("✅ Multiple export formats (MTG Arena, MTGO, Cockatrice, etc.)")
    print("✅ HTML export with card artworks")
    print("✅ Comprehensive testing with targeted ratings")
    print("=" * 60)

    # Initialize deck builder
    try:
        builder = EnhancedDeckBuilder()
        print("✅ Enhanced Deck Builder initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing deck builder: {e}")
        return

    # Load collection
    collection_file = "data/collections/FinalFantasy.csv"
    if not os.path.exists(collection_file):
        print(f"❌ Collection file not found: {collection_file}")
        print("Please ensure you have a valid collection file.")
        return

    try:
        collection_df = builder.load_collection(collection_file)
        print(f"✅ Loaded collection with {len(collection_df)} cards")
    except Exception as e:
        print(f"❌ Error loading collection: {e}")
        return

    # Configuration
    print("\n" + "=" * 40)
    print("DECK CONFIGURATION")
    print("=" * 40)

    # Get user input
    try:
        num_colors = int(input("Maximum number of colors (1-5): "))
        if num_colors < 1 or num_colors > 5:
            print("Invalid number of colors. Using 2 colors.")
            num_colors = 2
    except ValueError:
        print("Invalid input. Using 2 colors.")
        num_colors = 2

    try:
        deck_size = int(input("Deck size (non-land cards, e.g., 25 for Limited): "))
        if deck_size < 20 or deck_size > 40:
            print("Invalid deck size. Using 25 non-land cards.")
            deck_size = 25
    except ValueError:
        print("Invalid input. Using 25 non-land cards.")
        deck_size = 25

    try:
        lambda_penalty = float(
            input("Color penalty strength (0.1-2.0, default 0.5): ") or "0.5"
        )
        if lambda_penalty < 0.1 or lambda_penalty > 2.0:
            print("Invalid penalty strength. Using 0.5.")
            lambda_penalty = 0.5
    except ValueError:
        print("Invalid input. Using 0.5.")
        lambda_penalty = 0.5

    # Algorithm selection
    print("\nAvailable algorithms:")
    print("1. Greedy (fast, predictable)")
    print("2. Genetic (balanced, good results)")
    print("3. Simulated Annealing (best optimization)")

    try:
        algorithm_choice = input("Choose algorithm (1-3): ")
        if algorithm_choice == "1":
            algorithm = "greedy"
        elif algorithm_choice == "2":
            algorithm = "genetic"
        elif algorithm_choice == "3":
            algorithm = "simulated_annealing"
        else:
            print("Invalid choice. Using genetic algorithm.")
            algorithm = "genetic"
    except:
        print("Invalid input. Using genetic algorithm.")
        algorithm = "genetic"

    # Export formats
    print("\nAvailable export formats:")
    print("1. Copy-paste (simple text)")
    print("2. MTG Arena")
    print("3. MTGO")
    print("4. Cockatrice")
    print("5. TappedOut")
    print("6. Archidekt")
    print("7. Moxfield")
    print("8. HTML with artworks")
    print("9. All formats")

    try:
        export_choice = input("Choose export format (1-9): ")
        export_formats = []

        if export_choice == "1":
            export_formats = ["copy_paste"]
        elif export_choice == "2":
            export_formats = ["mtg_arena"]
        elif export_choice == "3":
            export_formats = ["mtgo"]
        elif export_choice == "4":
            export_formats = ["cockatrice"]
        elif export_choice == "5":
            export_formats = ["tappedout"]
        elif export_choice == "6":
            export_formats = ["archidekt"]
        elif export_choice == "7":
            export_formats = ["moxfield"]
        elif export_choice == "8":
            export_formats = ["html"]
        elif export_choice == "9":
            export_formats = [
                "copy_paste",
                "mtg_arena",
                "mtgo",
                "cockatrice",
                "tappedout",
                "archidekt",
                "moxfield",
                "html",
            ]
        else:
            print("Invalid choice. Using copy-paste format.")
            export_formats = ["copy_paste"]
    except:
        print("Invalid input. Using copy-paste format.")
        export_formats = ["copy_paste"]

    # Build optimal deck
    print(f"\nBuilding optimal {num_colors}-color deck with {algorithm} algorithm...")
    print(f"Color penalty strength: {lambda_penalty}")

    result = builder.build_optimal_deck_advanced(
        collection_df=collection_df,
        num_colors=num_colors,
        deck_size=deck_size,
        algorithm=algorithm,
        export_formats=export_formats,
        lambda_penalty=lambda_penalty,
    )

    print(f"\n{'='*60}")
    print(f"BUILD COMPLETED SUCCESSFULLY!")
    print(f"{'='*60}")
    print(f"Final Score: {result['score']:.4f}")
    print(f"Target Colors: {result['target_colors']}")
    print(f"Total Deck Size: {len(result['deck'])} cards")

    # Count lands and non-lands
    land_cards = [card for card in result["deck"] if card.get("type") == "Land"]
    non_land_cards = [card for card in result["deck"] if card.get("type") != "Land"]

    print(f"Non-land cards: {len(non_land_cards)}")
    print(f"Land cards: {len(land_cards)}")

    # Show land distribution
    land_counts = {}
    for land in land_cards:
        land_name = land["name"]
        land_counts[land_name] = land_counts.get(land_name, 0) + 1

    print(f"\nLand Distribution:")
    for land_name, count in sorted(land_counts.items()):
        print(f"  {land_name}: {count}")

    # Show exported files
    if "exported_files" in result and result["exported_files"]:
        print(f"\nExported files:")
        for format_name, file_path in result["exported_files"].items():
            print(f"  {format_name}: {file_path}")

    print(f"\n🎉 Deck building completed successfully!")
    print(f"The system has:")
    print(f"✅ Selected optimal cards based on ratings")
    print(f"✅ Enforced color constraints")
    print(f"✅ Added optimal number of lands ({len(land_cards)} lands)")
    print(f"✅ Distributed lands appropriately for {result['target_colors']} colors")
    print(f"✅ Exported deck in requested formats")


def run_tests():
    """Run comprehensive tests"""
    print("=" * 60)
    print("RUNNING COMPREHENSIVE TESTS")
    print("=" * 60)

    print("\n1. Testing targeted rating selection...")
    try:
        from tests.test_targeted_ratings import test_targeted_selection

        result = test_targeted_selection()
        if result["success"]:
            print("✅ Targeted rating test passed!")
        else:
            print("⚠️  Targeted rating test had issues")
    except Exception as e:
        print(f"❌ Error in targeted rating test: {e}")

    print("\n2. Testing land calculation...")
    try:
        from tests.test_land_calculation import test_land_calculation

        results = test_land_calculation()
        passed_tests = sum(
            1 for result in results.values() if result.get("success", False)
        )
        total_tests = len(results)
        print(f"✅ Land calculation tests: {passed_tests}/{total_tests} passed")
    except Exception as e:
        print(f"❌ Error in land calculation test: {e}")

    print("\n3. Testing complete system...")
    try:
        from tests.test_complete_system import test_complete_system

        result = test_complete_system()
        if result["success"]:
            print("✅ Complete system test passed!")
        else:
            print("⚠️  Complete system test had issues")
    except Exception as e:
        print(f"❌ Error in complete system test: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_tests()
    else:
        main()

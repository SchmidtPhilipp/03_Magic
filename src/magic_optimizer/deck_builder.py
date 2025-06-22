import json
import random
import time
from typing import Dict, List, Set, Tuple

import numpy as np
import pandas as pd

from .exporters.deck_exporter import DeckExporter
from .optimizer import AdvancedDeckOptimizer
from .validator import CardValidator


class EnhancedDeckBuilder:
    def __init__(self, ratings_file: str = "data/ratings/card_ratings.csv"):
        """Initialize enhanced deck builder with advanced optimization"""
        self.optimizer = AdvancedDeckOptimizer(ratings_file)
        self.validator = CardValidator()
        self.exporter = DeckExporter()

        print("Enhanced Deck Builder initialized with advanced optimization algorithms")

    def load_collection(self, collection_file: str) -> pd.DataFrame:
        """Load card collection from file"""
        try:
            if collection_file.endswith(".csv"):
                collection_df = pd.read_csv(collection_file)
            elif collection_file.endswith(".json"):
                collection_df = pd.read_json(collection_file)
            else:
                raise ValueError("Unsupported file format. Use CSV or JSON.")

            print(f"Loaded collection with {len(collection_df)} cards")
            return collection_df
        except Exception as e:
            print(f"Error loading collection: {e}")
            return pd.DataFrame()

    def build_optimal_deck_advanced(
        self,
        collection_df: pd.DataFrame,
        num_colors: int = 2,
        deck_size: int = 40,
        algorithm: str = "genetic",
        export_formats: List[str] = None,
        lambda_penalty: float = 0.5,
        total_deck_size: int = None,
        land_ratio: float = None,
    ) -> Dict:
        """
        Build optimal deck using advanced optimization algorithms

        Args:
            collection_df: DataFrame with card collection
            num_colors: Maximum number of colors to use in deck
            deck_size: Target non-land card count (if total_deck_size/land_ratio given, this is ignored)
            algorithm: 'genetic', 'simulated_annealing', or 'greedy'
            export_formats: List of formats to export ('arena', 'mtgo', 'cockatrice', etc.)
            lambda_penalty: Penalty multiplier for exceeding color limit
            total_deck_size: (optional) total deck size (lands + non-lands)
            land_ratio: (optional) ratio of lands in deck
        """

        # If total_deck_size and land_ratio are given, calculate non-land count
        if total_deck_size is not None and land_ratio is not None:
            num_lands = round(total_deck_size * land_ratio)
            deck_size = total_deck_size - num_lands
            print(
                f"[DeckBuilder] Using total deck size {total_deck_size}, land ratio {land_ratio}, lands {num_lands}, non-lands {deck_size}"
            )

        print(f"\n=== ENHANCED DECK OPTIMIZATION ===")
        print(f"Algorithm: {algorithm.upper()}")
        print(f"Max Colors: {num_colors}")
        print(f"Deck Size: {deck_size}")
        print(f"Lambda Penalty: {lambda_penalty}")

        start_time = time.time()

        # Run optimization
        if algorithm in ["genetic", "simulated_annealing"]:
            result = self.optimizer.optimize_deck(
                collection_df=collection_df,
                num_colors=num_colors,
                deck_size=deck_size,
                algorithm=algorithm,
                lambda_penalty=lambda_penalty,
            )
        elif algorithm == "greedy":
            result = self.build_greedy_deck(
                collection_df, num_colors, deck_size, lambda_penalty
            )
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        end_time = time.time()

        print(f"\nOptimization completed in {end_time - start_time:.2f} seconds")
        print(f"Final Score: {result['score']:.4f}")
        print(f"Actual Colors: {result['target_colors']}")

        # Add optimal lands to the deck
        print(f"\n=== ADDING OPTIMAL LANDS ===")
        if total_deck_size is not None and land_ratio is not None:
            complete_deck = self.add_lands_to_deck(
                result["deck"], result["target_colors"], total_deck_size, land_ratio
            )
        else:
            complete_deck = self.add_lands_to_deck(
                result["deck"], result["target_colors"], deck_size
            )
        result["deck"] = complete_deck

        # Analyze and display deck
        self.analyze_deck(result["deck"])

        # Export in requested formats
        if export_formats:
            exported_files = self.exporter.export_deck(
                deck=result["deck"],
                algorithm=algorithm,
                target_colors=result["target_colors"],
                score=result["score"],
                formats=export_formats,
            )
            result["exported_files"] = exported_files

        return result

    def build_greedy_deck(
        self,
        collection_df: pd.DataFrame,
        num_colors: int,
        deck_size: int,
        lambda_penalty: float = 0.5,
    ) -> Dict:
        """Build deck using greedy algorithm with dynamic color constraints"""
        print("Running Greedy Algorithm with Dynamic Color Constraints...")

        # Prepare eligible cards (no color filtering)
        eligible_cards = self.optimizer.prepare_eligible_cards(
            collection_df, num_colors
        )

        # If only one color is requested, filter eligible cards to strictly mono-color (or colorless)
        if num_colors == 1:
            # Find the most common color in the eligible pool
            color_counts = {}
            for card in eligible_cards:
                for color in card.get("colors", set()):
                    color_counts[color] = color_counts.get(color, 0) + 1
            if color_counts:
                main_color = max(color_counts, key=color_counts.get)
                eligible_cards = [
                    card
                    for card in eligible_cards
                    if (card.get("colors", set()) == {main_color})
                    or (not card.get("colors"))
                ]

        # Exclude all lands from eligible cards (basic and nonbasic)
        eligible_spells = [
            card for card in eligible_cards if card.get("type") != "Land"
        ]

        if len(eligible_spells) < deck_size:
            print(
                f"Warning: Only {len(eligible_spells)} eligible cards for {deck_size}-card deck"
            )
            deck_size = len(eligible_spells)

        print(f"Using {len(eligible_spells)} eligible cards for optimization")

        # Sort cards by rating
        eligible_spells.sort(key=lambda x: x["rating"], reverse=True)

        # Build deck with greedy approach
        deck = []
        color_counts = {}
        deck_colors = set()  # Track current deck colors

        # Phase 1: Add cards with highest ratings while monitoring color count
        for card in eligible_spells:
            if len(deck) >= deck_size:
                break

            card_colors = card.get("colors", set())

            # Check if adding this card would exceed color limit
            temp_deck = deck + [card]
            temp_colors = set()
            for temp_card in temp_deck:
                colors = temp_card.get("colors", set())
                temp_colors.update(colors)

            # If adding this card would exceed color limit, skip it
            if len(temp_colors) > num_colors:
                continue

            # FIXED: Allow cards that expand the color pool up to the limit
            # Only restrict if we're already at the color limit
            if len(deck_colors) >= num_colors and card_colors:
                # If we're at the limit, only allow cards that use existing colors
                if not (card_colors & deck_colors):
                    continue  # Skip cards that don't use existing colors

            deck.append(card)

            # Update color counts and deck colors
            for color in card_colors:
                color_counts[color] = color_counts.get(color, 0) + 1
            deck_colors.update(card_colors)

        # Phase 2: Fill remaining slots with best available cards
        remaining_slots = deck_size - len(deck)
        remaining_cards = [card for card in eligible_spells if card not in deck]

        # Sort remaining cards by rating
        remaining_cards.sort(key=lambda x: x["rating"], reverse=True)

        for card in remaining_cards[:remaining_slots]:
            card_colors = card.get("colors", set())

            # Apply same color compatibility check
            if len(deck_colors) >= num_colors and card_colors:
                # If we're at the limit, only allow cards that use existing colors
                if not (card_colors & deck_colors):
                    continue  # Skip cards that don't use existing colors

            deck.append(card)
            # Update color counts
            for color in card_colors:
                color_counts[color] = color_counts.get(color, 0) + 1
            deck_colors.update(card_colors)

        # Get actual colors used
        actual_colors = sorted(list(color_counts.keys()))

        # Calculate final score
        final_score = self.optimizer.calculate_deck_score(
            deck, [], deck_size, num_colors, lambda_penalty
        )

        return {
            "deck": deck,
            "score": final_score,
            "target_colors": actual_colors,
            "algorithm": "greedy",
        }

    def analyze_deck(self, deck: List[Dict]):
        """Analyze and display detailed deck statistics"""
        print(f"\n=== DECK ANALYSIS ===")
        print(f"Total Cards: {len(deck)}")

        # Color distribution
        color_counts = {}
        colorless_count = 0
        for card in deck:
            colors = card["colors"]
            if not colors:
                colorless_count += 1
            else:
                for color in colors:
                    color_counts[color] = color_counts.get(color, 0) + 1

        print(f"\nColor Distribution:")
        for color, count in sorted(color_counts.items()):
            print(f"  {color}: {count} cards")
        if colorless_count > 0:
            print(f"  Colorless: {colorless_count} cards")

        # Mana curve
        curve = self.optimizer.calculate_mana_curve(deck)
        print(f"\nMana Curve:")
        for cmc in range(8):
            if curve[cmc] > 0:
                print(f"  {cmc} CMC: {curve[cmc]} cards")

        # Card types
        type_counts = {}
        for card in deck:
            card_type = card.get("type", "Unknown")
            type_counts[card_type] = type_counts.get(card_type, 0) + 1

        print(f"\nCard Types:")
        for card_type, count in sorted(type_counts.items()):
            print(f"  {card_type}: {count} cards")

        # Rating statistics
        ratings = [card.get("rating", 0) for card in deck]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        print(f"\nRating Statistics:")
        print(f"  Average Rating: {avg_rating:.2f}/10")
        print(f"  Highest Rating: {max(ratings)}/10")
        print(f"  Lowest Rating: {min(ratings)}/10")

    def compare_algorithms(
        self, collection_df: pd.DataFrame, num_colors: int = 2, deck_size: int = 40
    ) -> Dict:
        """Compare different optimization algorithms"""
        print(f"\n=== ALGORITHM COMPARISON ===")

        algorithms = ["greedy", "genetic", "simulated_annealing"]
        results = {}

        for algorithm in algorithms:
            print(f"\nTesting {algorithm.upper()} algorithm...")
            try:
                result = self.build_optimal_deck_advanced(
                    collection_df, num_colors, deck_size, algorithm, [], 0.5
                )
                results[algorithm] = {
                    "score": result["score"],
                    "colors": result["target_colors"],
                    "deck": result["deck"],
                }
            except Exception as e:
                print(f"Error with {algorithm}: {e}")
                results[algorithm] = None

        # Display comparison
        print(f"\n=== COMPARISON RESULTS ===")
        for algorithm, result in results.items():
            if result:
                print(
                    f"{algorithm.upper()}: Score = {result['score']:.4f}, Colors = {result['colors']}"
                )
            else:
                print(f"{algorithm.upper()}: Failed")

        # Find best algorithm
        best_algorithm = max(
            results.keys(), key=lambda k: results[k]["score"] if results[k] else 0
        )

        print(f"\nBest Algorithm: {best_algorithm.upper()}")
        print(f"Best Score: {results[best_algorithm]['score']:.4f}")

        return results

    def calculate_optimal_lands(
        self,
        deck: List[Dict],
        target_colors: List[str],
        deck_size: int = 40,
        num_lands: int = None,
        collection_df: pd.DataFrame = None,
    ) -> List[Dict]:
        """
        Calculate optimal land count and add appropriate lands to the deck
        Args:
            deck: Current deck without lands
            target_colors: Target colors for the deck
            deck_size: Target deck size
            num_lands: Optional specific number of lands to add
            collection_df: The full collection DataFrame (for nonbasic lands)
        Returns:
            List of land cards to add
        """
        non_land_cards = len(deck)

        # Use provided num_lands or calculate optimal land count
        if num_lands is not None:
            optimal_lands = num_lands
        else:
            # Calculate optimal land count (typically 33-40% of deck)
            if deck_size <= 40:  # Limited format
                optimal_lands = max(16, min(18, int(deck_size * 0.42)))
            else:  # Constructed format
                optimal_lands = max(22, min(26, int(deck_size * 0.40)))

            # Adjust based on mana curve
            curve = self.optimizer.calculate_mana_curve(deck)
            avg_cmc = (
                sum(cmc * count for cmc, count in curve.items()) / non_land_cards
                if non_land_cards > 0
                else 0
            )

            if avg_cmc > 3.5:
                optimal_lands += 1
            elif avg_cmc < 2.5:
                optimal_lands -= 1

            optimal_lands = min(optimal_lands, deck_size - non_land_cards)
            if deck_size <= 40:
                optimal_lands = max(15, optimal_lands)
            else:
                optimal_lands = max(20, optimal_lands)

        print(f"Calculated optimal lands: {optimal_lands}")

        lands = []
        lands_needed = optimal_lands

        # 1. Add nonbasic lands from collection that match deck colors
        nonbasic_lands = []
        if collection_df is not None:
            for _, row in collection_df.iterrows():
                card_name = (
                    row["Card Name"]
                    if "Card Name" in collection_df.columns
                    else row.iloc[0]
                )
                # Get card data
                card_data = self.optimizer.get_card_data(card_name)
                if not card_data:
                    continue
                type_line = card_data.get("type_line", "")
                if "Land" in type_line and "Basic" not in type_line:
                    # Check if land produces at least one deck color
                    produces_colors = set()
                    if "colors" in card_data:
                        produces_colors.update(card_data["colors"])
                    if "card_faces" in card_data:
                        for face in card_data["card_faces"]:
                            produces_colors.update(face.get("colors", []))
                    if produces_colors & set(target_colors):
                        # Add as many as available in collection
                        qty = row["Quantity"] if "Quantity" in row else 1
                        for _ in range(int(qty)):
                            nonbasic_lands.append(
                                {
                                    "name": card_name,
                                    "colors": produces_colors,
                                    "rating": 6,  # Slightly above basic
                                    "cmc": 0,
                                    "type": "Land",
                                    "card_data": card_data,
                                }
                            )
        # Add nonbasic lands up to the number needed
        for land in nonbasic_lands:
            if lands_needed <= 0:
                break
            lands.append(land)
            lands_needed -= 1

        # 2. Fill remaining with basic lands as before
        if lands_needed > 0:
            if target_colors:
                # Calculate land distribution based on color requirements
                color_requirements = {color: 0 for color in target_colors}
                for card in deck:
                    colors = card.get("colors", set())
                    for color in colors:
                        if color in target_colors:
                            color_requirements[color] += 1

                total_colored_requirements = sum(color_requirements.values())
                if total_colored_requirements == 0:
                    # If no colored requirements, distribute evenly
                    color_shares = {
                        color: 1 / len(target_colors) for color in target_colors
                    }
                else:
                    color_shares = {
                        color: color_requirements[color] / total_colored_requirements
                        for color in target_colors
                    }

                # Calculate number of lands per color (initial assignment)
                lands_per_color = {
                    color: int(lands_needed * share)
                    for color, share in color_shares.items()
                }
                assigned = sum(lands_per_color.values())
                # Distribute any remaining lands to colors with highest share
                remaining = lands_needed - assigned
                if remaining > 0:
                    # Sort colors by share descending
                    sorted_colors = sorted(
                        target_colors, key=lambda c: color_shares[c], reverse=True
                    )
                    for i in range(remaining):
                        lands_per_color[sorted_colors[i % len(sorted_colors)]] += 1

                # Add basic lands for each color
                for color, count in lands_per_color.items():
                    land_name = None
                    if color == "W":
                        land_name = "Plains"
                    elif color == "U":
                        land_name = "Island"
                    elif color == "B":
                        land_name = "Swamp"
                    elif color == "R":
                        land_name = "Mountain"
                    elif color == "G":
                        land_name = "Forest"
                    if land_name:
                        for _ in range(count):
                            lands.append(self._create_land_card(land_name, color))
            else:
                # If no colors, default to Plains (never Wastes)
                for _ in range(lands_needed):
                    lands.append(self._create_land_card("Plains", "W"))

        return lands

    def _create_land_card(self, land_name: str, color: str) -> Dict:
        """Create a land card dictionary"""
        return {
            "name": land_name,
            "colors": set([color]) if color else set(),
            "rating": 5,  # Neutral rating for lands
            "cmc": 0,
            "type": "Land",
            "card_data": {
                "name": land_name,
                "type_line": "Basic Land",
                "colors": [color] if color else [],
                "cmc": 0,
            },
        }

    def add_lands_to_deck(
        self,
        deck: List[Dict],
        target_colors: List[str],
        deck_size: int = 40,
        land_ratio: float = None,
        collection_df: pd.DataFrame = None,
    ) -> List[Dict]:
        """Add optimal lands to the deck, using deck_size and land_ratio if given"""
        if land_ratio is not None:
            num_lands = round(deck_size * land_ratio)
            non_land_count = deck_size - num_lands
            print(
                f"[AddLands] Using deck size {deck_size}, land ratio {land_ratio}, lands {num_lands}, non-lands {non_land_count}"
            )
            # Truncate deck to non_land_count
            deck = deck[:non_land_count]
            # Add lands with specific count
            lands = self.calculate_optimal_lands(
                deck, target_colors, deck_size, num_lands, collection_df
            )
        else:
            # Add lands with automatic calculation
            lands = self.calculate_optimal_lands(
                deck, target_colors, deck_size, collection_df=collection_df
            )

        print(f"Added {len(lands)} lands to deck")
        return deck + lands

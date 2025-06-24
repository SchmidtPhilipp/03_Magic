import json
import random
import time
from typing import Dict, List, Set, Tuple, Optional

import numpy as np
import pandas as pd

from .card import Card
from .exporters.deck_exporter import DeckExporter
from .optimizers import create_optimizer
from .validator import CardValidator


class EnhancedDeckBuilder:
    def __init__(self, ratings_file: str = "data/ratings/card_ratings.csv"):
        """Initialize enhanced deck builder with advanced optimization"""
        self.ratings_file = ratings_file
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
        total_deck_size: int = 40,
        num_lands: int = 17,
        algorithm: str = "genetic",
        optimization_criterion: str = "manual",
        lambda_penalty: float = 0.5,
        fixed_colors: Optional[List[str]] = None,
        export_formats: Optional[List[str]] = None,
    ) -> Dict:
        """
        Build optimal deck using advanced optimization algorithms

        Args:
            collection_df: DataFrame with card collection
            num_colors: Maximum number of colors to use in deck
            total_deck_size: Total deck size (lands + non-lands)
            num_lands: Absolute number of lands in deck
            algorithm: 'genetic', 'simulated_annealing', or 'greedy'
            optimization_criterion: 'manual' or '17lands'
            lambda_penalty: Penalty for exceeding color limit in some algorithms
            fixed_colors: A list of colors to force into the deck (e.g., ['W', 'U'])
            export_formats: List of formats to export ('arena', 'mtgo', 'html_artwork')
        """
        if fixed_colors is None:
            fixed_colors = []

        # Ensure num_lands is not greater than total_deck_size
        if num_lands > total_deck_size:
            print(f"Warning: Number of lands ({num_lands}) exceeds total deck size ({total_deck_size}). Adjusting lands to {total_deck_size}.")
            num_lands = total_deck_size

        deck_size = total_deck_size - num_lands

        print(f"\n=== ENHANCED DECK OPTIMIZATION ===")
        print(f"Algorithm: {algorithm.upper()}")
        print(
            f"Max Colors: {num_colors}, Fixed Colors: {fixed_colors if fixed_colors else 'None'}"
        )
        print(
            f"Deck Size: {total_deck_size} (Non-Lands: {deck_size}, Lands: {num_lands})"
        )
        print(f"Optimization Criterion: {optimization_criterion}")

        start_time = time.time()

        # Create optimizer with the appropriate evaluation method
        optimizer = create_optimizer(
            algorithm=algorithm,
            evaluation_method=optimization_criterion,
            ratings_file=self.ratings_file
        )

        # Run optimization
        if algorithm in ["genetic", "simulated_annealing", "greedy"]:
            result = optimizer.optimize_deck(
                collection_df=collection_df,
                num_colors=num_colors,
                deck_size=deck_size,
                lambda_penalty=lambda_penalty,
                fixed_colors=fixed_colors,
            )
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        end_time = time.time()

        print(f"\nOptimization completed in {end_time - start_time:.2f} seconds")
        print(f"Final Score: {result['score']:.4f}")
        print(f"Actual Colors: {result['target_colors']}")

        # Add optimal lands to the deck
        print(f"\n=== ADDING OPTIMAL LANDS ===")
        complete_deck = self.add_lands_to_deck(
            result["deck"], result["target_colors"], total_deck_size, num_lands
        )
        result["deck"] = complete_deck

        # Analyze and display deck
        self.analyze_deck(result["deck"])

        # Export in requested formats
        if export_formats:
            exported_files = self.exporter.export_deck(
                deck=[card.to_dict() for card in result["deck"]],
                algorithm=algorithm,
                target_colors=result["target_colors"],
                score=result["score"],
                formats=export_formats,
            )
            result["exported_files"] = exported_files

        result["deck"] = [card.to_dict() for card in result["deck"]]
        return result

    def analyze_deck(self, deck: List[Card]):
        """Analyze and display detailed deck statistics"""
        print(f"\n=== DECK ANALYSIS ===")
        print(f"Total Cards: {len(deck)}")
        
        card_types = {}
        for card in deck:
            main_type = card.main_type
            card_types[main_type] = card_types.get(main_type, 0) + 1
        
        print("\nCard Types:")
        for type_name, count in sorted(card_types.items()):
            print(f"- {type_name}: {count}")

        non_land_cards = [c for c in deck if "Land" not in c.main_type]
        if non_land_cards:
            mana_curve = self._calculate_mana_curve(non_land_cards)
            print("\nMana Curve (Non-lands):")
            for cmc, count in sorted(mana_curve.items()):
                if count > 0:
                    print(f"- CMC {cmc}: {count}")

    def _calculate_mana_curve(self, deck: List[Card]) -> Dict[int, int]:
        """Calculate the mana curve distribution"""
        curve = {i: 0 for i in range(8)}  # 0-7+ CMC

        for card in deck:
            cmc = card.cmc
            if cmc >= 7:
                curve[7] += 1
            else:
                curve[int(cmc)] += 1

        return curve

    def _get_deck_colors(self, deck: List[Card]) -> List[str]:
        """Get the actual colors used in the deck"""
        colors_used = set()
        for card in deck:
            colors_used.update(card.colors)
        return sorted(list(colors_used))

    def compare_algorithms(
        self, collection_df: pd.DataFrame, num_colors: int = 2, deck_size: int = 40
    ) -> Dict:
        """Compare performance of different optimization algorithms"""
        print(f"\n=== COMPARING OPTIMIZATION ALGORITHMS ===")
        print(f"Deck Size: {deck_size}, Colors: {num_colors}")

        results = {}
        algorithms = ["greedy", "genetic", "simulated_annealing"]

        for algo in algorithms:
            print(f"\n--- Running {algo.upper()} ---")
            result = self.build_optimal_deck_advanced(
                collection_df=collection_df,
                num_colors=num_colors,
                total_deck_size=deck_size,
                num_lands=int(deck_size * 17 / 40),
                algorithm=str(algo),
            )
            results[algo] = result

        return results

    def calculate_optimal_lands(
        self,
        deck: List[Card],
        target_colors: List[str],
        deck_size: int = 40,
        num_lands: Optional[int] = None,
        collection_df: Optional[pd.DataFrame] = None,
    ) -> List[Card]:
        """
        Calculate the optimal number and type of basic lands for a deck.
        """
        if num_lands is None:
            num_lands = max(0, deck_size - len(deck))

        if num_lands == 0:
            return []

        # Calculate mana symbols required by the deck
        mana_symbols: Dict[str, int] = {}
        for card in deck:
            # This is a simplified version. A full implementation would parse mana costs.
            # For now, we rely on the card's colors.
            for color in card.colors:
                mana_symbols[color] = mana_symbols.get(color, 0) + 1

        total_symbols = sum(mana_symbols.values())
        if total_symbols == 0:
            # If no colored spells, add lands based on target colors, or just one type if no targets
            if not target_colors:
                deck_colors = self._get_deck_colors(deck)
                if "W" in deck_colors:
                    return [self._create_land_card("Plains", "W")] * num_lands
                else: # Default to plains
                    return [self._create_land_card("Plains", "W")] * num_lands
            
            num_per_color = num_lands // len(target_colors)
            lands: List[Card] = []
            for color in target_colors:
                land_name = self.get_land_name_for_color(color)
                lands.extend([self._create_land_card(land_name, color)] * num_per_color)
            
            # Add remainder
            if len(lands) < num_lands:
                land_name = self.get_land_name_for_color(target_colors[0])
                lands.extend([self._create_land_card(land_name, target_colors[0])] * (num_lands - len(lands)))
            return lands


        # Distribute lands based on mana symbol proportions
        lands = []
        # sort mana symbols to make land distribution deterministic
        sorted_mana_symbols = sorted(mana_symbols.items(), key=lambda item: item[1], reverse=True)

        for color, count in sorted_mana_symbols:
            proportion = count / total_symbols
            num_lands_for_color = round(proportion * num_lands)
            land_name = self.get_land_name_for_color(color)
            lands.extend([self._create_land_card(land_name, color)] * num_lands_for_color)

        # Adjust land count if rounding caused a mismatch
        while len(lands) < num_lands:
            # Add to the most represented color
            most_represented_color = sorted_mana_symbols[0][0]
            land_name = self.get_land_name_for_color(most_represented_color)
            lands.append(self._create_land_card(land_name, most_represented_color))

        if len(lands) > num_lands:
            lands = lands[:num_lands]
            
        return lands

    def get_land_name_for_color(self, color: str) -> str:
        """Get the basic land name for a given color initial."""
        return {"W": "Plains", "U": "Island", "B": "Swamp", "R": "Mountain", "G": "Forest"}.get(
            color, "Plains"
        )

    def _create_land_card(self, land_name: str, color: str) -> Card:
        """Create a dictionary representing a basic land card."""
        return Card({
            "name": land_name,
            "type_line": "Basic Land",
            "colors": [], # Basic lands are colorless
            "color_identity": [color],
            "cmc": 0,
        })

    def add_lands_to_deck(
        self,
        deck: List[Card],
        target_colors: List[str],
        deck_size: int = 40,
        num_lands: Optional[int] = None,
        collection_df: Optional[pd.DataFrame] = None,
    ) -> List[Card]:
        """
        Add the optimal number of lands to a deck to reach the desired size.
        """
        non_land_deck = [c for c in deck if "Land" not in c.main_type]
        
        if num_lands is None:
            num_lands = deck_size - len(non_land_deck)
            if num_lands < 0:
                print("Warning: Deck size exceeds target size before adding lands.")
                num_lands = 0

        print(f"Calculating and adding {num_lands} lands...")
        
        optimal_lands = self.calculate_optimal_lands(
            deck=non_land_deck,
            target_colors=target_colors,
            deck_size=deck_size,
            num_lands=num_lands,
            collection_df=collection_df,
        )

        complete_deck = non_land_deck + optimal_lands
        print(f"Final deck size with lands: {len(complete_deck)}")

        return complete_deck

"""
Greedy algorithm optimizer for deck optimization.
"""

import time
from typing import Dict, List, Optional

import pandas as pd

from .base_optimizer import BaseOptimizer


class GreedyOptimizer(BaseOptimizer):
    """Greedy algorithm implementation for deck optimization."""
    
    def optimize_deck(
        self,
        collection_df: pd.DataFrame,
        num_colors: int = 2,
        deck_size: int = 40,
        lambda_penalty: float = 0.5,
        fixed_colors: Optional[List[str]] = None,
    ) -> Dict:
        """Optimize deck using Greedy algorithm."""
        print(f"Starting Greedy optimization...")
        print(f"Max Colors: {num_colors}, Lambda Penalty: {lambda_penalty}")

        start_time = time.time()

        # Step 1: Prepare eligible cards
        eligible_cards = self.prepare_eligible_cards(collection_df, num_colors)

        # Filter out all lands from eligible cards
        eligible_cards = [card for card in eligible_cards if "Land" not in card.main_type]

        # Step 2: Determine target colors
        target_colors = self.select_target_colors(eligible_cards, num_colors, fixed_colors or [])
        print(f"Target colors selected: {target_colors}")

        # Step 3: Filter cards to target colors (strict filtering for greedy)
        target_colors_set = set(target_colors)
        filtered_cards = [
            card
            for card in eligible_cards
            if not card.colors or card.colors.issubset(target_colors_set)
        ]
        print(f"Filtered to {len(filtered_cards)} cards in target colors.")

        # Step 4: Run greedy algorithm
        best_deck = self.greedy_algorithm_optimization(
            filtered_cards,
            deck_size,
            lambda_penalty,
        )

        # Step 5: Final Evaluation
        final_score = self.calculate_deck_score(
            best_deck,
            target_colors,
            deck_size,
            num_colors,
            lambda_penalty=lambda_penalty,
        )

        end_time = time.time()
        print(f"Greedy optimization finished in {end_time - start_time:.2f} seconds.")

        return {
            "deck": best_deck,
            "score": final_score,
            "target_colors": target_colors,
            "algorithm": "greedy",
            "execution_time": end_time - start_time,
        }

    def greedy_algorithm_optimization(
        self,
        eligible_cards: List,
        deck_size: int = 40,
        lambda_penalty: float = 0.5,
    ) -> List:
        """Simple greedy algorithm that picks the best cards."""
        print(f"DEBUG: Greedy algorithm - Target deck size: {deck_size}")
        print(f"DEBUG: Greedy algorithm - Available cards: {len(eligible_cards)}")
        
        # Sort cards by their optimization score
        sorted_cards = sorted(eligible_cards, key=lambda x: x.optimization_score, reverse=True)
        
        # Take the top cards up to deck size
        selected_cards = sorted_cards[:deck_size]
        
        print(f"DEBUG: Greedy algorithm - Selected cards: {len(selected_cards)}")
        print(f"DEBUG: Greedy algorithm - First few cards: {[c.name for c in selected_cards[:5]]}")
        
        return selected_cards 
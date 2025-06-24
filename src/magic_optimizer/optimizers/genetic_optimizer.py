"""
Genetic Algorithm optimizer for deck optimization.
"""

import random
import time
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .base_optimizer import BaseOptimizer


class GeneticAlgorithmOptimizer(BaseOptimizer):
    """Genetic Algorithm implementation for deck optimization."""
    
    def optimize_deck(
        self,
        collection_df: pd.DataFrame,
        num_colors: int = 2,
        deck_size: int = 40,
        lambda_penalty: float = 0.5,
        fixed_colors: Optional[List[str]] = None,
        population_size: int = 50,
        generations: int = 100,
        mutation_rate: float = 0.1,
    ) -> Dict:
        """Optimize deck using Genetic Algorithm."""
        print(f"Starting Genetic Algorithm optimization...")
        print(f"Max Colors: {num_colors}, Lambda Penalty: {lambda_penalty}")

        start_time = time.time()

        # Step 1: Prepare eligible cards
        eligible_cards = self.prepare_eligible_cards(collection_df, num_colors)

        # Step 2: Determine target colors
        target_colors = self.select_target_colors(eligible_cards, num_colors, fixed_colors or [])
        print(f"Target colors selected: {target_colors}")
        print(f"Using all {len(eligible_cards)} eligible cards for optimization.")

        # Step 3: Run genetic algorithm
        best_deck = self.genetic_algorithm_optimization(
            eligible_cards,
            num_colors,
            deck_size,
            population_size,
            generations,
            mutation_rate,
            lambda_penalty,
        )

        # Step 4: Final Evaluation
        final_score = self.calculate_deck_score(
            best_deck,
            target_colors,
            deck_size,
            num_colors,
            lambda_penalty=lambda_penalty,
        )

        end_time = time.time()
        print(f"Genetic Algorithm finished in {end_time - start_time:.2f} seconds.")

        return {
            "deck": best_deck,
            "score": final_score,
            "target_colors": target_colors,
            "algorithm": "genetic",
            "execution_time": end_time - start_time,
        }

    def genetic_algorithm_optimization(
        self,
        eligible_cards: List,
        max_colors: int = 2,
        deck_size: int = 40,
        population_size: int = 50,
        generations: int = 100,
        mutation_rate: float = 0.1,
        lambda_penalty: float = 0.5,
    ) -> List:
        """Optimize deck using a Genetic Algorithm."""
        # Step 1: Initialize population
        population = [
            self.create_random_deck(eligible_cards, deck_size, max_colors)
            for _ in range(population_size)
        ]

        best_deck_overall: List = []
        best_score_overall = -1.0

        for gen in range(generations):
            # Step 2: Evaluate population
            deck_scores = [
                (
                    deck,
                    self.calculate_deck_score(
                        deck,
                        self.get_deck_colors(deck),
                        deck_size,
                        max_colors,
                        lambda_penalty,
                    ),
                )
                for deck in population
            ]

            # Sort by score
            deck_scores.sort(key=lambda x: x[1], reverse=True)

            # Update best overall
            if deck_scores[0][1] > best_score_overall:
                best_deck_overall = deck_scores[0][0]
                best_score_overall = deck_scores[0][1]

            # Step 3: Selection (Elitism and Tournament)
            new_population = [deck_scores[0][0]]  # Keep the best

            # Fill the rest of the new population
            while len(new_population) < population_size:
                # Select parents (e.g., tournament selection)
                parent1 = self.tournament_selection(deck_scores)
                parent2 = self.tournament_selection(deck_scores)

                # Step 4: Crossover
                child1, child2 = self.crossover_decks(parent1, parent2, deck_size, eligible_cards)

                # Step 5: Mutation
                if random.random() < mutation_rate:
                    child1 = self.mutate_deck(
                        child1, eligible_cards, deck_size, max_colors
                    )
                if random.random() < mutation_rate:
                    child2 = self.mutate_deck(
                        child2, eligible_cards, deck_size, max_colors
                    )

                new_population.extend([child1, child2])

            population = new_population[:population_size]

        return best_deck_overall

    def tournament_selection(self, scored_population, k: int = 5):
        """Select a parent using tournament selection"""
        tournament = random.sample(scored_population, k)
        tournament.sort(key=lambda x: x[1], reverse=True)
        return tournament[0][0]

    def create_random_deck(
        self, eligible_cards: List, deck_size: int, max_colors: int = 2
    ) -> List:
        """Create a random deck that respects color constraints more intelligently."""
        if not eligible_cards:
            return []

        # Try to find a valid set of cards
        for _ in range(10):  # Try 10 times to build a valid deck
            # Pick a random color combination
            all_colors = set()
            for c in eligible_cards:
                all_colors.update(c.colors)
            
            if len(all_colors) < max_colors:
                target_colors = list(all_colors)
            else:
                target_colors = random.sample(list(all_colors), max_colors)

            # Filter cards by these colors
            color_filtered_cards = [
                card
                for card in eligible_cards
                if not card.colors or card.colors.issubset(target_colors)
            ]

            if len(color_filtered_cards) >= deck_size:
                return random.sample(color_filtered_cards, deck_size)

        # Fallback to just picking any cards if a color-constrained deck can't be made
        if len(eligible_cards) < deck_size:
            if not eligible_cards:
                return []
            # If not enough unique cards, sample with replacement to reach deck_size
            return random.choices(eligible_cards, k=deck_size)
        return random.sample(eligible_cards, deck_size)

    def crossover_decks(
        self, deck1: List, deck2: List, deck_size: int, eligible_cards: List
    ) -> Tuple[List, List]:
        """Perform uniform crossover and repair to maintain deck size."""
        # Create copies to avoid modifying the original decks
        child1 = list(deck1)
        child2 = list(deck2)
        
        # Perform uniform crossover - each card has 50% chance to be swapped
        for i in range(min(len(child1), len(child2))):
            if random.random() < 0.5:
                child1[i], child2[i] = child2[i], child1[i]
        
        # Ensure both children have exactly deck_size cards and no duplicates
        child1 = self._repair_deck(child1, deck_size, eligible_cards)
        child2 = self._repair_deck(child2, deck_size, eligible_cards)
        
        return child1, child2
    
    def _repair_deck(self, deck: List, deck_size: int, eligible_cards: List) -> List:
        """Repair a deck to have exactly deck_size cards with no duplicates."""
        # Remove duplicates while preserving order
        seen = set()
        unique_deck = []
        for card in deck:
            if card not in seen:
                seen.add(card)
                unique_deck.append(card)
        
        # Fill up if too small
        while len(unique_deck) < deck_size:
            available_cards = [c for c in eligible_cards if c not in seen]
            if not available_cards:
                break  # No more cards available
            new_card = random.choice(available_cards)
            unique_deck.append(new_card)
            seen.add(new_card)
        
        # Truncate if too large
        return unique_deck[:deck_size]

    def mutate_deck(
        self,
        deck: List,
        eligible_cards: List,
        deck_size: int,
        max_colors: int = 2,
    ) -> List:
        """Mutate the deck by swapping one card."""
        if not eligible_cards or not deck:
            return deck

        # Create a copy to avoid modifying the original
        mutated_deck = list(deck)
        
        # Remove a random card from the deck
        removed_card_index = random.randint(0, len(mutated_deck) - 1)
        removed_card = mutated_deck.pop(removed_card_index)

        # Add a new random card from eligible cards
        potential_new_cards = [
            c for c in eligible_cards if c not in mutated_deck
        ]
        if potential_new_cards:
            new_card = random.choice(potential_new_cards)
            mutated_deck.append(new_card)
        else:
            mutated_deck.append(removed_card) # Add back if no replacement found

        # Ensure the deck has exactly deck_size cards
        return self._repair_deck(mutated_deck, deck_size, eligible_cards) 
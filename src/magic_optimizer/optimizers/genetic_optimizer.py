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
        max_runtime_seconds: Optional[int] = None,
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
            max_runtime_seconds,
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
        max_runtime_seconds: Optional[int] = None,
    ) -> List:
        """Optimize deck using a Genetic Algorithm."""
        print(f"🧬 Genetic Algorithm Configuration:")
        print(f"   Population Size: {population_size}")
        print(f"   Generations: {generations}")
        print(f"   Mutation Rate: {mutation_rate}")
        print(f"   Deck Size: {deck_size}")
        print(f"   Max Colors: {max_colors}")
        print(f"   Lambda Penalty: {lambda_penalty}")
        print(f"   Eligible Cards: {len(eligible_cards)}")
        
        # Step 1: Initialize population
        print(f"\n🎯 Initializing population of {population_size} decks...")
        population = [
            self.create_random_deck(eligible_cards, deck_size, max_colors)
            for _ in range(population_size)
        ]
        print(f"✅ Population initialized successfully")

        best_deck_overall: List = []
        best_score_overall = -1.0
        generation_stats = []

        print(f"\n🔄 Starting evolution over {generations} generations...")
        if max_runtime_seconds:
            print(f"⏱️  Runtime limit: {max_runtime_seconds} seconds")
        print(f"{'Gen':>3} {'Best':>8} {'Avg':>8} {'Worst':>8} {'Improvement':>12} {'Colors':>10}")
        print("-" * 60)

        start_time = time.time()
        for gen in range(generations):
            # Step 2: Evaluate population
            deck_scores = [
                (
                    deck,
                    self.calculate_normalized_deck_score(
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
            
            # Calculate statistics
            scores = [score for _, score in deck_scores]
            best_score = scores[0]
            avg_score = sum(scores) / len(scores)
            worst_score = scores[-1]
            
            # Send progress update after best_score is calculated
            progress_percent = int((gen + 1) / generations * 100)
            print(f"PROGRESS: Generation {gen + 1}/{generations} ({progress_percent}%) - Best Score: {best_score:.3f}")
            
            # Check runtime limit
            if max_runtime_seconds:
                elapsed_time = time.time() - start_time
                if elapsed_time >= max_runtime_seconds:
                    print(f"⏰ Runtime limit reached ({elapsed_time:.1f}s). Stopping optimization.")
                    break
            
            # Track improvement
            improvement = best_score - best_score_overall if best_score > best_score_overall else 0
            
            # Get colors of best deck
            best_colors = self.get_deck_colors(deck_scores[0][0])
            color_str = "".join(sorted(best_colors)) if best_colors else "None"

            # Update best overall
            if best_score > best_score_overall:
                best_deck_overall = deck_scores[0][0]
                best_score_overall = best_score
                print(f"{gen:>3} {best_score:>8.3f} {avg_score:>8.3f} {worst_score:>8.3f} {improvement:>12.3f} {color_str:>10} ⭐")
            else:
                print(f"{gen:>3} {best_score:>8.3f} {avg_score:>8.3f} {worst_score:>8.3f} {improvement:>12.3f} {color_str:>10}")

            # Store generation stats
            generation_stats.append({
                'generation': gen,
                'best_score': best_score,
                'avg_score': avg_score,
                'worst_score': worst_score,
                'improvement': improvement
            })

            # Step 3: Selection (Elitism and Tournament)
            new_population = [deck_scores[0][0]]  # Keep the best (elitism)
            elite_count = 1

            # Fill the rest of the new population
            crossover_count = 0
            mutation_count = 0
            
            while len(new_population) < population_size:
                # Select parents (e.g., tournament selection)
                parent1 = self.tournament_selection(deck_scores)
                parent2 = self.tournament_selection(deck_scores)

                # Step 4: Crossover
                child1, child2 = self.crossover_decks(parent1, parent2, deck_size, eligible_cards)
                crossover_count += 2

                # Step 5: Mutation
                if random.random() < mutation_rate:
                    child1 = self.mutate_deck(
                        child1, eligible_cards, deck_size, max_colors
                    )
                    mutation_count += 1
                if random.random() < mutation_rate:
                    child2 = self.mutate_deck(
                        child2, eligible_cards, deck_size, max_colors
                    )
                    mutation_count += 1

                new_population.extend([child1, child2])

            population = new_population[:population_size]
            
            # Log detailed stats every 10 generations
            if (gen + 1) % 10 == 0:
                print(f"\n📊 Generation {gen + 1} Statistics:")
                print(f"   Elite individuals: {elite_count}")
                print(f"   Crossover operations: {crossover_count}")
                print(f"   Mutation operations: {mutation_count}")
                print(f"   Population diversity: {len(set(tuple(deck) for deck in population))} unique decks")

        print(f"\n🏆 Evolution completed!")
        print(f"   Best score achieved: {best_score_overall:.3f}")
        print(f"   Best deck colors: {self.get_deck_colors(best_deck_overall)}")
        print(f"   Total generations: {generations}")
        
        # Final statistics
        if generation_stats:
            total_improvement = generation_stats[-1]['best_score'] - generation_stats[0]['best_score']
            print(f"   Total improvement: {total_improvement:.3f}")
            print(f"   Average score per generation: {sum(stat['avg_score'] for stat in generation_stats) / len(generation_stats):.3f}")

        return best_deck_overall

    def tournament_selection(self, scored_population, k: int = 5):
        """Select a parent using tournament selection"""
        tournament = random.sample(scored_population, k)
        tournament.sort(key=lambda x: x[1], reverse=True)
        return tournament[0][0]

    def create_random_deck(
        self, eligible_cards: List, deck_size: int, max_colors: int = 2
    ) -> List:
        """Create a random deck with better color diversity exploration."""
        if not eligible_cards:
            return []

        # Try to find a valid set of cards with varying color counts
        for _ in range(10):  # Try 10 times to build a valid deck
            # Pick a random number of colors (1 to max_colors)
            num_colors = random.randint(1, max_colors)
            
            # Get all available colors
            all_colors = set()
            for c in eligible_cards:
                all_colors.update(c.colors)
            
            if len(all_colors) < num_colors:
                target_colors = list(all_colors)
            else:
                target_colors = random.sample(list(all_colors), num_colors)

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
        """Perform intelligent crossover that preserves color diversity."""
        # Create copies to avoid modifying the original decks
        child1 = list(deck1)
        child2 = list(deck2)
        
        # Get colors from parents
        parent1_colors = set(self.get_deck_colors(deck1))
        parent2_colors = set(self.get_deck_colors(deck2))
        
        # Perform uniform crossover - each card has 50% chance to be swapped
        for i in range(min(len(child1), len(child2))):
            if random.random() < 0.5:
                child1[i], child2[i] = child2[i], child1[i]
        
        # Repair decks to maintain size and add diversity
        child1 = self._repair_deck_with_color_diversity(child1, deck_size, eligible_cards, parent1_colors, parent2_colors)
        child2 = self._repair_deck_with_color_diversity(child2, deck_size, eligible_cards, parent2_colors, parent1_colors)
        
        return child1, child2
    
    def _repair_deck_with_color_diversity(self, deck: List, deck_size: int, eligible_cards: List, 
                                        primary_colors: set, secondary_colors: set) -> List:
        """Repair a deck while maintaining color diversity from parents."""
        # Remove duplicates while preserving order
        seen = set()
        unique_deck = []
        for card in deck:
            if card not in seen:
                unique_deck.append(card)
                seen.add(card)
        
        # If we need more cards, add them with color diversity
        while len(unique_deck) < deck_size:
            # 70% chance to add from primary colors, 30% from secondary
            if random.random() < 0.7 and primary_colors:
                target_colors = primary_colors
            else:
                target_colors = secondary_colors
            
            # Filter cards by target colors
            available_cards = [
                card for card in eligible_cards 
                if card not in seen and (not card.colors or card.colors.issubset(target_colors))
            ]
            
            if available_cards:
                new_card = random.choice(available_cards)
                unique_deck.append(new_card)
                seen.add(new_card)
            else:
                # Fallback to any available card
                available_cards = [card for card in eligible_cards if card not in seen]
                if available_cards:
                    new_card = random.choice(available_cards)
                    unique_deck.append(new_card)
                    seen.add(new_card)
                else:
                    break
        
        return unique_deck[:deck_size]
    
    def _repair_deck(self, deck: List, deck_size: int, eligible_cards: List) -> List:
        """Repair a deck to have exactly deck_size cards with no duplicates."""
        # Remove duplicates while preserving order
        seen = set()
        unique_deck = []
        for card in deck:
            if card not in seen:
                unique_deck.append(card)
                seen.add(card)
        
        # If we need more cards, add them
        while len(unique_deck) < deck_size:
            available_cards = [card for card in eligible_cards if card not in seen]
            if available_cards:
                new_card = random.choice(available_cards)
                unique_deck.append(new_card)
                seen.add(new_card)
            else:
                break
        
        return unique_deck[:deck_size]

    def mutate_deck(
        self,
        deck: List,
        eligible_cards: List,
        deck_size: int,
        max_colors: int = 2,
    ) -> List:
        """Mutate a deck with better color diversity exploration."""
        if not deck:
            return self.create_random_deck(eligible_cards, deck_size, max_colors)
        
        mutated_deck = list(deck)
        current_colors = self.get_deck_colors(deck)
        
        # Different types of mutations
        mutation_type = random.random()
        
        if mutation_type < 0.3:
            # Color reduction mutation: remove cards from one color
            if len(current_colors) > 1:
                color_to_remove = random.choice(list(current_colors))
                cards_to_remove = [card for card in mutated_deck if color_to_remove in card.colors]
                if cards_to_remove:
                    card_to_remove = random.choice(cards_to_remove)
                    mutated_deck.remove(card_to_remove)
        elif mutation_type < 0.6:
            # Color addition mutation: add cards from a new color
            all_colors = set()
            for c in eligible_cards:
                all_colors.update(c.colors)
            new_colors = all_colors - set(current_colors)
            if new_colors and len(current_colors) < max_colors:
                new_color = random.choice(list(new_colors))
                new_color_cards = [card for card in eligible_cards 
                                 if new_color in card.colors and card not in mutated_deck]
                if new_color_cards:
                    # Replace a random card
                    replace_index = random.randint(0, len(mutated_deck) - 1)
                    mutated_deck[replace_index] = random.choice(new_color_cards)
        else:
            # Standard mutation: replace a random card
            if len(mutated_deck) > 0:
                replace_index = random.randint(0, len(mutated_deck) - 1)
                available_cards = [card for card in eligible_cards if card not in mutated_deck]
                if available_cards:
                    mutated_deck[replace_index] = random.choice(available_cards)
        
        # Ensure deck size is maintained
        if len(mutated_deck) != deck_size:
            mutated_deck = self._repair_deck(mutated_deck, deck_size, eligible_cards)
        
        return mutated_deck 
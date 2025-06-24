"""
Simulated Annealing optimizer for deck optimization.
"""

import random
import time
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .base_optimizer import BaseOptimizer


class SimulatedAnnealingOptimizer(BaseOptimizer):
    """Simulated Annealing implementation for deck optimization."""
    
    def optimize_deck(
        self,
        collection_df: pd.DataFrame,
        num_colors: int = 2,
        deck_size: int = 40,
        lambda_penalty: float = 0.5,
        fixed_colors: Optional[List[str]] = None,
        iterations: int = 1000,
        initial_temp: float = 100.0,
    ) -> Dict:
        """Optimize deck using Simulated Annealing."""
        print(f"Starting Simulated Annealing optimization...")
        print(f"Max Colors: {num_colors}, Lambda Penalty: {lambda_penalty}")

        start_time = time.time()

        # Step 1: Prepare eligible cards
        eligible_cards = self.prepare_eligible_cards(collection_df, num_colors)

        # Step 2: Determine target colors
        target_colors = self.select_target_colors(eligible_cards, num_colors, fixed_colors or [])
        print(f"Target colors selected: {target_colors}")
        print(f"Using all {len(eligible_cards)} eligible cards for optimization.")

        # Step 3: Run simulated annealing
        best_deck = self.simulated_annealing_optimization(
            eligible_cards,
            num_colors,
            deck_size,
            iterations,
            initial_temp,
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
        print(f"Simulated Annealing finished in {end_time - start_time:.2f} seconds.")

        return {
            "deck": best_deck,
            "score": final_score,
            "target_colors": target_colors,
            "algorithm": "simulated_annealing",
            "execution_time": end_time - start_time,
        }

    def simulated_annealing_optimization(
        self,
        eligible_cards: List,
        max_colors: int = 2,
        deck_size: int = 40,
        iterations: int = 1000,
        initial_temp: float = 100.0,
        lambda_penalty: float = 0.5,
    ) -> List:
        """Optimize deck using Simulated Annealing."""
        print(f"🌡️ Simulated Annealing Configuration:")
        print(f"   Iterations: {iterations}")
        print(f"   Initial Temperature: {initial_temp}")
        print(f"   Cooling Rate: 0.995 (geometric)")
        print(f"   Deck Size: {deck_size}")
        print(f"   Max Colors: {max_colors}")
        print(f"   Lambda Penalty: {lambda_penalty}")
        print(f"   Eligible Cards: {len(eligible_cards)}")
        
        # Initial solution
        print(f"\n🎯 Creating initial random deck...")
        current_deck = self.create_random_deck(eligible_cards, deck_size, max_colors)
        current_score = self.calculate_normalized_deck_score(
            current_deck,
            self.get_deck_colors(current_deck),
            deck_size,
            max_colors,
            lambda_penalty,
        )
        print(f"✅ Initial deck created with score: {current_score:.3f}")
        print(f"   Initial colors: {self.get_deck_colors(current_deck)}")

        best_deck: List = current_deck
        best_score = current_score
        temp = initial_temp
        
        # Statistics tracking
        accepted_better = 0
        accepted_worse = 0
        rejected = 0
        improvement_count = 0
        iteration_stats = []

        print(f"\n🔄 Starting simulated annealing optimization...")
        print(f"{'Iter':>4} {'Temp':>8} {'Current':>8} {'Best':>8} {'Accept':>6} {'Colors':>10}")
        print("-" * 55)

        for i in range(iterations):
            # Generate a neighbor solution
            neighbor_deck = self.generate_neighbor_deck(
                current_deck, eligible_cards, deck_size, max_colors
            )
            neighbor_score = self.calculate_normalized_deck_score(
                neighbor_deck,
                self.get_deck_colors(neighbor_deck),
                deck_size,
                max_colors,
                lambda_penalty,
            )

            # Decide whether to move to the neighbor
            score_diff = neighbor_score - current_score
            accepted = False
            
            if score_diff > 0:
                # Always accept better solutions
                current_deck = neighbor_deck
                current_score = neighbor_score
                accepted_better += 1
                accepted = True
            else:
                # Accept a worse solution with a certain probability
                probability = np.exp(score_diff / temp)
                if random.random() < probability:
                    current_deck = neighbor_deck
                    current_score = neighbor_score
                    accepted_worse += 1
                    accepted = True
                else:
                    rejected += 1

            # Update best solution found so far
            if current_score > best_score:
                best_deck = current_deck
                best_score = current_score
                improvement_count += 1
                print(f"{i:>4} {temp:>8.2f} {current_score:>8.3f} {best_score:>8.3f} {'YES':>6} {''.join(sorted(self.get_deck_colors(current_deck))):>10} ⭐")
            else:
                # Log every 50th iteration to avoid spam
                if i % 50 == 0:
                    accept_rate = (accepted_better + accepted_worse) / (i + 1) * 100
                    print(f"{i:>4} {temp:>8.2f} {current_score:>8.3f} {best_score:>8.3f} {'YES' if accepted else 'NO':>6} {''.join(sorted(self.get_deck_colors(current_deck))):>10}")

            # Store iteration stats
            iteration_stats.append({
                'iteration': i,
                'temperature': temp,
                'current_score': current_score,
                'best_score': best_score,
                'accepted': accepted,
                'score_diff': score_diff
            })

            # Cool down the temperature
            temp *= 0.995  # Geometric cooling

        print(f"\n🏆 Simulated Annealing completed!")
        print(f"   Best score achieved: {best_score:.3f}")
        print(f"   Best deck colors: {self.get_deck_colors(best_deck)}")
        print(f"   Total iterations: {iterations}")
        print(f"   Final temperature: {temp:.2f}")
        
        # Acceptance statistics
        total_attempts = accepted_better + accepted_worse + rejected
        print(f"\n📊 Acceptance Statistics:")
        print(f"   Better solutions accepted: {accepted_better} ({accepted_better/total_attempts*100:.1f}%)")
        print(f"   Worse solutions accepted: {accepted_worse} ({accepted_worse/total_attempts*100:.1f}%)")
        print(f"   Solutions rejected: {rejected} ({rejected/total_attempts*100:.1f}%)")
        print(f"   Total improvements: {improvement_count}")
        
        # Temperature analysis
        if iteration_stats:
            avg_temp = sum(stat['temperature'] for stat in iteration_stats) / len(iteration_stats)
            print(f"   Average temperature: {avg_temp:.2f}")
            print(f"   Temperature range: {initial_temp:.2f} → {temp:.2f}")

        return best_deck

    def create_random_deck(
        self, eligible_cards: List, deck_size: int, max_colors: int = 2
    ) -> List:
        """Create a random deck for simulated annealing."""
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

    def generate_neighbor_deck(
        self,
        deck: List,
        eligible_cards: List,
        deck_size: int,
        max_colors: int = 2,
    ) -> List:
        """Generate a neighbor solution by swapping one card."""
        if not deck or not eligible_cards:
            return deck

        neighbor = list(deck)
        index_to_replace = random.randint(0, len(neighbor) - 1)

        # Find a replacement card that is not already in the deck
        replacement_options = [
            c for c in eligible_cards if c not in neighbor
        ]

        if replacement_options:
            replacement = random.choice(replacement_options)
            neighbor[index_to_replace] = replacement

        return neighbor 
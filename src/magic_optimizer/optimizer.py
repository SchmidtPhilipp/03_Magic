import itertools
import json
import random
import time
from copy import deepcopy
from typing import Dict, List, Set, Tuple

import numpy as np
import pandas as pd

from .evaluator import DeckEvaluator
from .validator import CardValidator


class AdvancedDeckOptimizer:
    def __init__(self, ratings_file: str = "card_ratings.csv"):
        """Initialize advanced deck optimizer with card ratings"""
        self.ratings_df = pd.read_csv(ratings_file)
        self.validator = CardValidator()

        # Initialize the new deck evaluator
        self.evaluator = DeckEvaluator(ratings_file)

        # Convert ratings to numeric for easier comparison
        self.ratings_df["Rating_Value"] = (
            self.ratings_df["Rating"].str.split("/").str[0].astype(int)
        )

        # Create a dictionary for quick rating lookup
        self.ratings_dict = dict(
            zip(self.ratings_df["Card Name"], self.ratings_df["Rating_Value"])
        )

        # Cache for card data to avoid repeated API calls
        self.card_data_cache = {}

        print(f"Loaded {len(self.ratings_df)} rated cards")

    def get_card_data(self, card_name: str) -> Dict:
        """Get complete card data using Scryfall API with caching"""
        if card_name in self.card_data_cache:
            return self.card_data_cache[card_name]

        try:
            card_data = self.validator.search_card(card_name)
            if card_data:
                self.card_data_cache[card_name] = card_data
                return card_data
            else:
                self.card_data_cache[card_name] = {}
                return {}
        except Exception as e:
            self.card_data_cache[card_name] = {}
            return {}

    def calculate_deck_score(
        self,
        deck: List[Dict],
        target_colors: List[str],
        deck_size: int = 40,
        max_colors: int = 2,
        lambda_penalty: float = 0.5,
        evaluation_method: str = "manual",
    ) -> float:
        """
        Calculate comprehensive deck score based on multiple factors

        Scoring components:
        1. Rating Score (35% weight) - now uses new evaluator
        2. Mana Curve Score (20% weight)
        3. Color Balance Score (15% weight) - now uses actual colors in deck
        4. Synergy Score (10% weight)
        5. Card Type Balance Score (5% weight)
        6. Dynamic Color Constraint Penalty

        NEW: Dynamic Color Constraint: Penalizes decks with too many colors
        NEW: Evaluation Method Selection: Choose between 17Lands and manual evaluation
        """

        if not deck:
            return 0.0

        # Extract card names for the new evaluator
        card_names = [card.get("name", "") for card in deck]

        # 1. Rating Score (35% weight) - now uses new evaluator
        rating_score = (
            self.evaluator.evaluate_deck(card_names, evaluation_method) * 0.35
        )

        # 2. Mana Curve Score (20% weight)
        mana_curve = self.calculate_mana_curve(deck)
        curve_score = self.evaluate_mana_curve(mana_curve, deck_size) * 0.20

        # 3. Color Balance Score (15% weight) - now uses actual colors in deck
        actual_colors = self.get_deck_colors(deck)
        color_score = self.evaluate_color_balance_dynamic(deck, actual_colors) * 0.15

        # 4. Synergy Score (10% weight)
        synergy_score = self.calculate_synergy_score(deck) * 0.10

        # 5. Card Type Balance Score (5% weight)
        type_score = self.evaluate_card_type_balance(deck) * 0.05

        # NEW: 6. Dynamic Color Constraint Penalty
        color_penalty = (
            self.calculate_dynamic_color_penalty(deck, max_colors, lambda_penalty)
            * 0.30
        )

        total_score = (
            rating_score
            + curve_score
            + color_score
            + synergy_score
            + type_score
            - color_penalty
        )

        return max(0.0, total_score)  # Ensure non-negative score

    def calculate_mana_curve(self, deck: List[Dict]) -> Dict[int, int]:
        """Calculate the mana curve distribution"""
        curve = {i: 0 for i in range(8)}  # 0-7+ CMC

        for card in deck:
            cmc = card.get("cmc", 0)
            if cmc >= 7:
                curve[7] += 1
            else:
                curve[cmc] += 1

        return curve

    def evaluate_mana_curve(self, curve: Dict[int, int], deck_size: int) -> float:
        """
        Evaluate mana curve quality
        Ideal curve for Limited: 2-3-4-3-2-1 (for 15 non-land cards)
        """
        non_land_cards = deck_size - (deck_size // 3)  # 33% lands

        # Ideal curve distribution (percentages)
        ideal_curve = {
            0: 0.05,  # 5% 0-drops
            1: 0.15,  # 15% 1-drops
            2: 0.25,  # 25% 2-drops
            3: 0.25,  # 25% 3-drops
            4: 0.20,  # 20% 4-drops
            5: 0.08,  # 8% 5-drops
            6: 0.02,  # 2% 6-drops
            7: 0.00,  # 0% 7+ drops
        }

        score = 0.0
        for cmc in range(8):
            actual_ratio = curve[cmc] / non_land_cards if non_land_cards > 0 else 0
            ideal_ratio = ideal_curve[cmc]

            # Penalty for deviation from ideal
            deviation = abs(actual_ratio - ideal_ratio)
            score += (1.0 - deviation) * ideal_ratio

        return max(0.0, score)

    def get_deck_colors(self, deck: List[Dict]) -> List[str]:
        """Get the actual colors used in the deck"""
        colors_used = set()
        for card in deck:
            colors = card.get("colors", set())
            colors_used.update(colors)
        return sorted(list(colors_used))

    def evaluate_color_balance_dynamic(
        self, deck: List[Dict], actual_colors: List[str]
    ) -> float:
        """Evaluate color balance using the actual colors in the deck"""
        if not actual_colors:
            return 0.0

        color_counts = {color: 0 for color in actual_colors}
        colorless_count = 0

        for card in deck:
            colors = card.get("colors", set())
            if not colors:
                colorless_count += 1
            else:
                for color in colors:
                    if color in actual_colors:
                        color_counts[color] += 1

        # Calculate balance score
        total_colored = sum(color_counts.values())
        if total_colored == 0:
            return 0.0

        # Penalty for uneven distribution
        avg_per_color = total_colored / len(actual_colors)
        variance = sum((count - avg_per_color) ** 2 for count in color_counts.values())
        balance_score = 1.0 / (1.0 + variance)

        # Bonus for having cards in all colors
        color_coverage = sum(1 for count in color_counts.values() if count > 0) / len(
            actual_colors
        )

        return (balance_score + color_coverage) / 2.0

    def calculate_synergy_score(self, deck: List[Dict]) -> float:
        """Calculate synergy between cards"""
        synergy_score = 0.0
        synergy_pairs = 0

        # Look for common synergy patterns
        for i, card1 in enumerate(deck):
            for j, card2 in enumerate(deck[i + 1 :], i + 1):
                synergy = self.calculate_card_synergy(card1, card2)
                synergy_score += synergy
                synergy_pairs += 1

        return synergy_score / max(1, synergy_pairs)

    def calculate_card_synergy(self, card1: Dict, card2: Dict) -> float:
        """Calculate synergy between two specific cards"""
        synergy = 0.0

        # Tribal synergies
        if self.has_tribal_synergy(card1, card2):
            synergy += 0.3

        # Spell synergies
        if self.has_spell_synergy(card1, card2):
            synergy += 0.2

        # Color synergies
        if self.has_color_synergy(card1, card2):
            synergy += 0.1

        # Mana curve synergies
        if self.has_curve_synergy(card1, card2):
            synergy += 0.1

        return min(1.0, synergy)

    def has_tribal_synergy(self, card1: Dict, card2: Dict) -> bool:
        """Check if two cards have tribal synergy"""
        # This is a simplified check - in practice you'd have a tribal database
        creature_types = ["Human", "Elf", "Goblin", "Zombie", "Dragon", "Merfolk"]

        type1 = card1.get("type", "")
        type2 = card2.get("type", "")

        for creature_type in creature_types:
            if creature_type in type1 and creature_type in type2:
                return True

        return False

    def has_spell_synergy(self, card1: Dict, card2: Dict) -> bool:
        """Check if two cards have spell synergy"""
        # Simplified spell synergy check
        spell_types = ["Instant", "Sorcery"]
        type1 = card1.get("type", "")
        type2 = card2.get("type", "")

        return type1 in spell_types and type2 in spell_types

    def has_color_synergy(self, card1: Dict, card2: Dict) -> bool:
        """Check if two cards have color synergy"""
        colors1 = card1.get("colors", set())
        colors2 = card2.get("colors", set())

        return bool(colors1 & colors2)  # Intersection

    def has_curve_synergy(self, card1: Dict, card2: Dict) -> bool:
        """Check if two cards have good curve synergy"""
        cmc1 = card1.get("cmc", 0)
        cmc2 = card2.get("cmc", 0)

        # Good curve: 2-drop + 3-drop, 3-drop + 4-drop, etc.
        return abs(cmc1 - cmc2) == 1

    def evaluate_card_type_balance(self, deck: List[Dict]) -> float:
        """Evaluate balance of card types"""
        type_counts = {
            "Creature": 0,
            "Instant": 0,
            "Sorcery": 0,
            "Enchantment": 0,
            "Artifact": 0,
            "Planeswalker": 0,
        }

        for card in deck:
            card_type = card.get("type", "Unknown")
            if card_type in type_counts:
                type_counts[card_type] += 1

        total_cards = len(deck)
        if total_cards == 0:
            return 0.0

        # Ideal ratios for Limited
        ideal_ratios = {
            "Creature": 0.40,  # 40% creatures
            "Instant": 0.20,  # 20% instants
            "Sorcery": 0.15,  # 15% sorceries
            "Enchantment": 0.10,  # 10% enchantments
            "Artifact": 0.10,  # 10% artifacts
            "Planeswalker": 0.05,  # 5% planeswalkers
        }

        score = 0.0
        for card_type, ideal_ratio in ideal_ratios.items():
            actual_ratio = type_counts[card_type] / total_cards
            deviation = abs(actual_ratio - ideal_ratio)
            score += (1.0 - deviation) * ideal_ratio

        return max(0.0, score)

    def calculate_dynamic_color_penalty(
        self, deck: List[Dict], max_colors: int, lambda_penalty: float = 0.5
    ) -> float:
        """
        Calculate penalty for exceeding the maximum number of colors

        Args:
            deck: The deck to evaluate
            max_colors: Maximum allowed colors
            lambda_penalty: Penalty multiplier (hyperparameter)

        Returns:
            Penalty score (higher = worse)
        """
        actual_colors = self.get_deck_colors(deck)
        num_colors_used = len(actual_colors)

        if num_colors_used <= max_colors:
            return 0.0  # No penalty if within limit

        # EXTREMELY STRONG PENALTY: Make it much more severe
        excess_colors = num_colors_used - max_colors

        # Base penalty is much higher now
        penalty = lambda_penalty * excess_colors * 50.0  # 50x stronger base penalty

        # Exponential penalty for excess colors
        penalty += lambda_penalty * (3.0**excess_colors) * 10.0

        # Additional penalty for each excess color
        penalty += lambda_penalty * excess_colors * excess_colors * 20.0

        # Extra penalty for very restrictive limits (1-2 colors)
        if max_colors <= 2:
            penalty *= 5.0  # 5x multiplier for very restrictive limits

        return penalty

    def enforce_strict_color_constraints(
        self, deck, max_colors, deck_size, eligible_cards
    ):
        """
        Enforce that the deck contains only the N most common colors and is filled to deck_size.
        If not enough cards of allowed colors, fill with any eligible cards.
        """
        from collections import Counter

        color_counts = Counter()
        for card in deck:
            color_counts.update(card.get("colors", set()))
        most_common = [c for c, _ in color_counts.most_common(max_colors)]
        allowed_colors = set(most_common)
        filtered_deck = [
            card for card in deck if card.get("colors", set()) & allowed_colors
        ]
        already_in = set(card["name"] for card in filtered_deck)
        refill_pool = [
            card
            for card in eligible_cards
            if card.get("colors", set()) & allowed_colors
            and card["name"] not in already_in
        ]
        refill_pool.sort(key=lambda c: c.get("rating", 0), reverse=True)
        filtered_deck += refill_pool[: deck_size - len(filtered_deck)]
        # If still too small, fill with any eligible cards not already in deck
        if len(filtered_deck) < deck_size:
            already_in = set(card["name"] for card in filtered_deck)
            any_pool = [
                card for card in eligible_cards if card["name"] not in already_in
            ]
            any_pool.sort(key=lambda c: c.get("rating", 0), reverse=True)
            filtered_deck += any_pool[: deck_size - len(filtered_deck)]
        return filtered_deck[:deck_size]

    def genetic_algorithm_optimization(
        self,
        eligible_cards: List[Dict],
        max_colors: int = 2,
        deck_size: int = 40,
        population_size: int = 50,
        generations: int = 100,
        mutation_rate: float = 0.1,
        lambda_penalty: float = 0.5,
        evaluation_method: str = "manual",
    ) -> List[Dict]:
        """
        Use genetic algorithm to find optimal deck with dynamic color constraints
        """
        print(f"Running Genetic Algorithm Optimization...")
        print(f"Population: {population_size}, Generations: {generations}")
        print(f"Max Colors: {max_colors}, Lambda Penalty: {lambda_penalty}")
        print(f"Evaluation Method: {evaluation_method}")

        # Validate input
        if not eligible_cards or len(eligible_cards) < deck_size:
            print(
                f"Error: Not enough eligible cards ({len(eligible_cards)}) for deck size {deck_size}"
            )
            return []

        # Initialize population
        population = []
        for _ in range(population_size):
            deck = self.create_random_deck(eligible_cards, deck_size, max_colors)
            if deck and len(deck) > 0:  # Ensure deck is valid
                population.append(deck)
            else:
                # Create a fallback deck if random creation fails
                fallback_deck = (
                    eligible_cards[:deck_size]
                    if len(eligible_cards) >= deck_size
                    else eligible_cards
                )
                population.append(fallback_deck)

        if not population:
            print("Error: Failed to create initial population")
            return (
                eligible_cards[:deck_size]
                if len(eligible_cards) >= deck_size
                else eligible_cards
            )

        best_deck = None
        best_score = 0.0

        for generation in range(generations):
            # Evaluate fitness
            fitness_scores = []
            valid_population = []

            for deck in population:
                if deck and len(deck) > 0:  # Ensure deck is valid
                    try:
                        score = self.calculate_deck_score(
                            deck,
                            [],
                            deck_size,
                            max_colors,
                            lambda_penalty,
                            evaluation_method,
                        )
                        fitness_scores.append(score)
                        valid_population.append(deck)

                        if score > best_score:
                            best_score = score
                            best_deck = deepcopy(deck)
                    except Exception as e:
                        print(f"Error evaluating deck: {e}")
                        fitness_scores.append(0.0)
                        valid_population.append(deck)
                else:
                    fitness_scores.append(0.0)
                    valid_population.append(deck)

            if not valid_population or not fitness_scores:
                print("Error: No valid population members")
                return (
                    eligible_cards[:deck_size]
                    if len(eligible_cards) >= deck_size
                    else eligible_cards
                )

            # Selection (tournament selection)
            new_population = []
            for _ in range(population_size):
                # Tournament selection
                tournament_size = min(3, len(valid_population))
                if tournament_size > 0:
                    tournament = random.sample(
                        list(enumerate(valid_population)), tournament_size
                    )
                    winner_idx = max(tournament, key=lambda x: fitness_scores[x[0]])[0]
                    new_population.append(deepcopy(valid_population[winner_idx]))
                else:
                    # Fallback: create a new random deck
                    fallback_deck = (
                        eligible_cards[:deck_size]
                        if len(eligible_cards) >= deck_size
                        else eligible_cards
                    )
                    new_population.append(fallback_deck)

            # Crossover
            for i in range(0, population_size - 1, 2):
                if random.random() < 0.8 and i + 1 < len(
                    new_population
                ):  # 80% crossover rate
                    parent1 = new_population[i]
                    parent2 = new_population[i + 1]
                    if parent1 and parent2 and len(parent1) > 0 and len(parent2) > 0:
                        try:
                            child1, child2 = self.crossover_decks(
                                parent1, parent2, deck_size
                            )
                            new_population[i] = child1
                            new_population[i + 1] = child2
                        except Exception as e:
                            print(f"Error in crossover: {e}")

            # Mutation
            for i in range(population_size):
                if random.random() < mutation_rate and i < len(new_population):
                    deck = new_population[i]
                    if deck and len(deck) > 0:
                        try:
                            new_population[i] = self.mutate_deck(
                                deck, eligible_cards, deck_size, max_colors
                            )
                        except Exception as e:
                            print(f"Error in mutation: {e}")

            population = new_population

            if generation % 10 == 0:
                avg_fitness = (
                    sum(fitness_scores) / len(fitness_scores) if fitness_scores else 0.0
                )
                if best_deck:
                    actual_colors = self.get_deck_colors(best_deck)
                    print(
                        f"Generation {generation}: Best Score = {best_score:.4f}, Avg Score = {avg_fitness:.4f}, Colors = {actual_colors}"
                    )
                else:
                    print(f"Generation {generation}: No valid best deck found")

        print(f"Genetic Algorithm completed. Best score: {best_score:.4f}")

        if best_deck:
            actual_colors = self.get_deck_colors(best_deck)
            print(f"Final deck colors: {actual_colors}")

            # POST-PROCESSING: Enforce strict color constraints
            best_deck = self.enforce_strict_color_constraints(
                best_deck, max_colors, deck_size, eligible_cards
            )
            return best_deck
        else:
            print("Error: No valid deck found during optimization")
            return (
                eligible_cards[:deck_size]
                if len(eligible_cards) >= deck_size
                else eligible_cards
            )

    def simulated_annealing_optimization(
        self,
        eligible_cards: List[Dict],
        max_colors: int = 2,
        deck_size: int = 40,
        iterations: int = 1000,
        initial_temp: float = 100.0,
        lambda_penalty: float = 0.5,
        evaluation_method: str = "manual",
    ) -> List[Dict]:
        """
        Use simulated annealing to find optimal deck with dynamic color constraints
        """
        print(f"Running Simulated Annealing Optimization...")
        print(f"Iterations: {iterations}, Initial Temperature: {initial_temp}")
        print(f"Max Colors: {max_colors}, Lambda Penalty: {lambda_penalty}")
        print(f"Evaluation Method: {evaluation_method}")

        # Start with random deck
        current_deck = self.create_random_deck(eligible_cards, deck_size, max_colors)
        current_score = self.calculate_deck_score(
            current_deck, [], deck_size, max_colors, lambda_penalty, evaluation_method
        )

        best_deck = deepcopy(current_deck)
        best_score = current_score

        temperature = initial_temp

        for iteration in range(iterations):
            # Generate neighbor (small change to current deck)
            neighbor_deck = self.generate_neighbor_deck(
                current_deck, eligible_cards, deck_size, max_colors
            )
            neighbor_score = self.calculate_deck_score(
                neighbor_deck,
                [],
                deck_size,
                max_colors,
                lambda_penalty,
                evaluation_method,
            )

            # Calculate acceptance probability
            delta_score = neighbor_score - current_score
            if delta_score > 0 or random.random() < np.exp(delta_score / temperature):
                current_deck = neighbor_deck
                current_score = neighbor_score

                if current_score > best_score:
                    best_deck = deepcopy(current_deck)
                    best_score = current_score

            # Cool down
            temperature *= 0.995

            if iteration % 100 == 0:
                actual_colors = self.get_deck_colors(best_deck)
                print(
                    f"Iteration {iteration}: Best Score = {best_score:.4f}, Current Score = {current_score:.4f}, Temp = {temperature:.2f}, Colors = {actual_colors}"
                )

        print(f"Simulated Annealing completed. Best score: {best_score:.4f}")
        actual_colors = self.get_deck_colors(best_deck)
        print(f"Final deck colors: {actual_colors}")

        # POST-PROCESSING: Enforce strict color constraints
        best_deck = self.enforce_strict_color_constraints(
            best_deck, max_colors, deck_size, eligible_cards
        )
        return best_deck

    def create_random_deck(
        self, eligible_cards: List[Dict], deck_size: int, max_colors: int = None
    ) -> List[Dict]:
        """Create a random deck from eligible cards with optional color constraint"""
        # Validate input
        if not eligible_cards:
            return []

        if len(eligible_cards) < deck_size:
            return eligible_cards.copy()

        # If max_colors is specified, ensure the deck respects the color limit
        if max_colors is not None:
            # For very restrictive limits, use a more targeted approach
            if max_colors <= 2:
                # Try to find a dominant color first
                color_counts = {}
                for card in eligible_cards:
                    colors = card.get("colors", set())
                    for color in colors:
                        color_counts[color] = color_counts.get(color, 0) + 1

                # Find the color with the most cards
                if color_counts:
                    dominant_color = max(
                        color_counts.keys(), key=lambda c: color_counts[c]
                    )

                    # Create deck with dominant color + colorless + maybe one other color
                    dominant_cards = [
                        card
                        for card in eligible_cards
                        if card.get("colors", set()) == {dominant_color}
                    ]
                    colorless_cards = [
                        card for card in eligible_cards if not card.get("colors", set())
                    ]

                    deck = []
                    # Add dominant color cards first
                    if dominant_cards:
                        num_dominant = min(deck_size // 2, len(dominant_cards))
                        deck.extend(random.sample(dominant_cards, num_dominant))

                    # Add colorless cards
                    if colorless_cards and len(deck) < deck_size:
                        num_colorless = min(deck_size - len(deck), len(colorless_cards))
                        deck.extend(random.sample(colorless_cards, num_colorless))

                    # Fill remaining slots with any valid cards
                    remaining_cards = [
                        card for card in eligible_cards if card not in deck
                    ]
                    if remaining_cards and len(deck) < deck_size:
                        remaining_needed = deck_size - len(deck)
                        deck.extend(
                            random.sample(
                                remaining_cards,
                                min(remaining_needed, len(remaining_cards)),
                            )
                        )

                    return deck[:deck_size]

            # For less restrictive limits, use the original approach
            attempts = 0
            max_attempts = 200  # Increased attempts

            while attempts < max_attempts:
                deck = random.sample(eligible_cards, deck_size)
                actual_colors = self.get_deck_colors(deck)

                if len(actual_colors) <= max_colors:
                    return deck

                attempts += 1

            # If we can't find a valid deck, return the best attempt
            best_deck = random.sample(eligible_cards, deck_size)
            best_colors = len(self.get_deck_colors(best_deck))

            for _ in range(100):  # Try more times
                deck = random.sample(eligible_cards, deck_size)
                colors = len(self.get_deck_colors(deck))
                if colors < best_colors:
                    best_deck = deck
                    best_colors = colors
                    if best_colors <= max_colors:
                        break

            return best_deck

        # Default case: no color constraint
        return random.sample(eligible_cards, deck_size)

    def crossover_decks(
        self, deck1: List[Dict], deck2: List[Dict], deck_size: int
    ) -> Tuple[List[Dict], List[Dict]]:
        """Perform crossover between two decks"""
        # Single-point crossover
        crossover_point = random.randint(1, deck_size - 1)

        child1 = deck1[:crossover_point] + deck2[crossover_point:]
        child2 = deck2[:crossover_point] + deck1[crossover_point:]

        # Ensure no duplicates
        child1 = list({card["name"]: card for card in child1}.values())
        child2 = list({card["name"]: card for card in child2}.values())

        # Fill up to deck size if needed
        while len(child1) < deck_size and len(deck1) > len(child1):
            remaining = [card for card in deck1 if card not in child1]
            if remaining:
                child1.append(random.choice(remaining))

        while len(child2) < deck_size and len(deck2) > len(child2):
            remaining = [card for card in deck2 if card not in child2]
            if remaining:
                child2.append(random.choice(remaining))

        return child1[:deck_size], child2[:deck_size]

    def mutate_deck(
        self,
        deck: List[Dict],
        eligible_cards: List[Dict],
        deck_size: int,
        max_colors: int = None,
    ) -> List[Dict]:
        """Mutate a deck by replacing some cards with optional color constraint"""
        mutated_deck = deck.copy()

        # Replace 1-3 random cards
        num_mutations = random.randint(1, 3)
        for _ in range(num_mutations):
            if len(mutated_deck) > 0:
                # Remove random card
                removed_card = random.choice(mutated_deck)
                mutated_deck.remove(removed_card)

                # Add random card from eligible cards
                available_cards = [
                    card for card in eligible_cards if card not in mutated_deck
                ]

                if available_cards:
                    # If max_colors is specified, try to find a card that maintains the color limit
                    if max_colors is not None:
                        valid_cards = []
                        for card in available_cards:
                            temp_deck = mutated_deck + [card]
                            if len(self.get_deck_colors(temp_deck)) <= max_colors:
                                valid_cards.append(card)

                        if valid_cards:
                            mutated_deck.append(random.choice(valid_cards))
                        else:
                            # If no valid cards, add the best available one
                            mutated_deck.append(random.choice(available_cards))
                    else:
                        mutated_deck.append(random.choice(available_cards))

        return mutated_deck

    def generate_neighbor_deck(
        self,
        deck: List[Dict],
        eligible_cards: List[Dict],
        deck_size: int,
        max_colors: int = None,
    ) -> List[Dict]:
        """Generate a neighbor deck by making small changes with optional color constraint"""
        neighbor = deck.copy()

        # Make 1-2 small changes
        num_changes = random.randint(1, 2)
        for _ in range(num_changes):
            if len(neighbor) > 0:
                # Remove a random card
                removed_card = random.choice(neighbor)
                neighbor.remove(removed_card)

                # Add a random card from eligible cards
                available_cards = [
                    card for card in eligible_cards if card not in neighbor
                ]

                if available_cards:
                    # If max_colors is specified, try to find a card that maintains the color limit
                    if max_colors is not None:
                        valid_cards = []
                        for card in available_cards:
                            temp_deck = neighbor + [card]
                            if len(self.get_deck_colors(temp_deck)) <= max_colors:
                                valid_cards.append(card)

                        if valid_cards:
                            neighbor.append(random.choice(valid_cards))
                        else:
                            # If no valid cards, add the best available one
                            neighbor.append(random.choice(available_cards))
                    else:
                        neighbor.append(random.choice(available_cards))

        return neighbor

    def optimize_deck(
        self,
        collection_df: pd.DataFrame,
        num_colors: int = 2,
        deck_size: int = 40,
        algorithm: str = "genetic",
        lambda_penalty: float = 0.5,
        evaluation_method: str = "manual",
    ) -> Dict:
        """
        Main optimization function with dynamic color constraints
        """
        print(f"Starting deck optimization with {algorithm} algorithm...")
        print(f"Max Colors: {num_colors}, Lambda Penalty: {lambda_penalty}")
        print(f"Evaluation Method: {evaluation_method}")

        # Prepare eligible cards (no color filtering)
        eligible_cards = self.prepare_eligible_cards(collection_df, num_colors)

        if len(eligible_cards) < deck_size:
            print(
                f"Warning: Only {len(eligible_cards)} eligible cards for {deck_size}-card deck"
            )
            deck_size = len(eligible_cards)

        print(f"Using {len(eligible_cards)} eligible cards for optimization")

        # Run optimization with all eligible cards (no color filtering)
        if algorithm == "genetic":
            optimal_deck = self.genetic_algorithm_optimization(
                eligible_cards,
                num_colors,
                deck_size,
                lambda_penalty=lambda_penalty,
                evaluation_method=evaluation_method,
            )
        elif algorithm == "simulated_annealing":
            optimal_deck = self.simulated_annealing_optimization(
                eligible_cards,
                num_colors,
                deck_size,
                lambda_penalty=lambda_penalty,
                evaluation_method=evaluation_method,
            )
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        # Get the actual colors used in the optimal deck
        actual_colors = self.get_deck_colors(optimal_deck)

        # Calculate final score
        final_score = self.calculate_deck_score(
            optimal_deck, [], deck_size, num_colors, lambda_penalty, evaluation_method
        )

        return {
            "deck": optimal_deck,
            "score": final_score,
            "target_colors": actual_colors,  # Now contains the actual colors used
            "algorithm": algorithm,
            "evaluation_method": evaluation_method,
        }

    def prepare_eligible_cards(
        self, collection_df: pd.DataFrame, num_colors: int
    ) -> List[Dict]:
        """Prepare list of eligible cards with complete data (no color filtering)"""
        eligible_cards = []

        for _, row in collection_df.iterrows():
            card_name = (
                row["Card Name"]
                if "Card Name" in collection_df.columns
                else row.iloc[0]
            )

            # Get card data
            card_data = self.get_card_data(card_name)
            if card_data:
                colors = set(card_data.get("colors", []))
                # Fix: If colors is empty and card_faces exists, union all face colors
                if not colors and "card_faces" in card_data:
                    for face in card_data["card_faces"]:
                        colors.update(face.get("colors", []))
                rating = self.ratings_dict.get(card_name, 0)
                cmc = card_data.get("cmc", 0)
                card_type = self.get_card_type(card_name)

                # Include all cards (no color filtering)
                eligible_cards.append(
                    {
                        "name": card_name,
                        "colors": colors,
                        "rating": rating,
                        "cmc": cmc,
                        "type": card_type,
                        "card_data": card_data,
                    }
                )

        return eligible_cards

    def filter_cards_by_colors(
        self, eligible_cards: List[Dict], target_colors: List[str]
    ) -> List[Dict]:
        """Filter cards to only include those in target colors and colorless cards"""
        filtered_cards = []

        for card in eligible_cards:
            colors = card.get("colors", set())
            if not colors:  # Colorless cards are always allowed
                filtered_cards.append(card)
            else:
                # Only include cards that have at least one target color
                # AND don't have any off-target colors
                card_colors = set(colors)
                if card_colors.issubset(set(target_colors)):
                    filtered_cards.append(card)

        return filtered_cards

    def select_target_colors(
        self, eligible_cards: List[Dict], num_colors: int
    ) -> List[str]:
        """Select target colors based on card distribution with focus on concentration"""
        color_counts = {}
        color_ratings = {}  # Average rating per color

        # Count cards and calculate average ratings by color
        for card in eligible_cards:
            colors = card.get("colors", set())
            rating = card.get("rating", 0)

            for color in colors:
                if color not in color_counts:
                    color_counts[color] = 0
                    color_ratings[color] = []

                color_counts[color] += 1
                color_ratings[color].append(rating)

        # Calculate average rating for each color
        color_avg_ratings = {}
        for color, ratings in color_ratings.items():
            color_avg_ratings[color] = sum(ratings) / len(ratings)

        # Score each color combination based on:
        # 1. Number of cards available
        # 2. Average rating of cards
        # 3. Concentration (prefer colors with more cards)

        best_colors = []
        best_score = 0.0

        # Try different color combinations
        all_colors = list(color_counts.keys())

        if num_colors == 1:
            # For mono-color, pick the color with the most high-rated cards
            for color in all_colors:
                score = (
                    color_counts[color] * color_avg_ratings[color] * 0.01
                )  # Weight by count and rating
                if score > best_score:
                    best_score = score
                    best_colors = [color]

        elif num_colors == 2:
            # For dual-color, try all combinations and pick the best
            for i, color1 in enumerate(all_colors):
                for color2 in all_colors[i + 1 :]:
                    # Calculate score for this color pair
                    count1 = color_counts[color1]
                    count2 = color_counts[color2]
                    rating1 = color_avg_ratings[color1]
                    rating2 = color_avg_ratings[color2]

                    # Prefer balanced colors with good ratings
                    balance_factor = min(count1, count2) / max(
                        count1, count2
                    )  # 0-1, higher is better
                    total_cards = count1 + count2
                    avg_rating = (rating1 + rating2) / 2

                    score = (
                        total_cards * avg_rating * (0.5 + 0.5 * balance_factor) * 0.01
                    )

                    if score > best_score:
                        best_score = score
                        best_colors = [color1, color2]

        else:
            # For 3+ colors, be more selective
            # Sort colors by a combination of count and rating
            color_scores = []
            for color in all_colors:
                count = color_counts[color]
                rating = color_avg_ratings[color]
                # Weight count more heavily than rating for color selection
                score = count * 0.7 + rating * 0.3
                color_scores.append((color, score))

            # Sort by score and take top N
            color_scores.sort(key=lambda x: x[1], reverse=True)
            best_colors = [color for color, _ in color_scores[:num_colors]]

        # If we don't have enough colors, add the best remaining ones
        while len(best_colors) < num_colors and len(all_colors) > len(best_colors):
            remaining_colors = [c for c in all_colors if c not in best_colors]
            if remaining_colors:
                best_colors.append(remaining_colors[0])

        return best_colors

    def get_card_type(self, card_name: str) -> str:
        """Get the type of a card"""
        card_data = self.get_card_data(card_name)
        if card_data:
            type_line = card_data.get("type_line", "")
            if "Land" in type_line:
                return "Land"
            elif "Creature" in type_line:
                return "Creature"
            elif "Instant" in type_line:
                return "Instant"
            elif "Sorcery" in type_line:
                return "Sorcery"
            elif "Enchantment" in type_line:
                return "Enchantment"
            elif "Artifact" in type_line:
                return "Artifact"
            elif "Planeswalker" in type_line:
                return "Planeswalker"
        return "Unknown"

    def enforce_color_constraints(
        self,
        deck: List[Dict],
        max_colors: int,
        deck_size: int,
        eligible_cards: List[Dict],
    ) -> List[Dict]:
        """Enforce color constraints by filtering the deck"""
        filtered_deck = []
        actual_colors = self.get_deck_colors(deck)

        for card in deck:
            colors = card.get("colors", set())
            if not colors:  # Colorless cards are always allowed
                filtered_deck.append(card)
            else:
                # Only include cards that have at least one target color
                # AND don't have any off-target colors
                card_colors = set(colors)
                if card_colors.issubset(set(actual_colors)):
                    filtered_deck.append(card)

        # Ensure the deck size is maintained
        while len(filtered_deck) < deck_size:
            remaining_cards = [
                card for card in eligible_cards if card not in filtered_deck
            ]
            if remaining_cards:
                filtered_deck.append(remaining_cards[0])

        return filtered_deck

    def get_evaluation_methods(self) -> List[Dict[str, str]]:
        """Get available evaluation methods for UI"""
        return self.evaluator.get_evaluation_methods()

    def get_deck_analysis(self, deck: List[Dict], method: str = "manual") -> Dict:
        """Get detailed deck analysis using new evaluator"""
        card_names = [card.get("name", "") for card in deck]
        return self.evaluator.get_deck_analysis(card_names, method)

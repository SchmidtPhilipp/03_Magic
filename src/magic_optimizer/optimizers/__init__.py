"""
Optimization algorithms for Magic: The Gathering deck building.
"""

from .base_optimizer import BaseOptimizer
from .genetic_optimizer import GeneticAlgorithmOptimizer
from .simulated_annealing_optimizer import SimulatedAnnealingOptimizer
from .greedy_optimizer import GreedyOptimizer

__all__ = [
    "BaseOptimizer",
    "GeneticAlgorithmOptimizer",
    "SimulatedAnnealingOptimizer", 
    "GreedyOptimizer",
    "create_optimizer"
]


def create_optimizer(algorithm: str, evaluation_method: str = "manual", ratings_file: str = "card_ratings.csv") -> BaseOptimizer:
    """Factory function to create the appropriate optimizer."""
    from ..evaluators import create_evaluator
    
    evaluator = create_evaluator(evaluation_method, ratings_file)
    
    if algorithm == "genetic":
        return GeneticAlgorithmOptimizer(evaluator)
    elif algorithm == "simulated_annealing":
        return SimulatedAnnealingOptimizer(evaluator)
    elif algorithm == "greedy":
        return GreedyOptimizer(evaluator)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}") 
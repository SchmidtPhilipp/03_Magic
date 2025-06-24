"""
Evaluation system for Magic: The Gathering deck optimization.
"""

from .base_evaluator import BaseCardEvaluator
from .manual_evaluator import ManualCardEvaluator
from .empirical_models_evaluator import EmpiricalModelsEvaluator
from .model_specific_evaluator import ModelSpecificEvaluator

__all__ = [
    "BaseCardEvaluator",
    "ManualCardEvaluator", 
    "EmpiricalModelsEvaluator",
    "ModelSpecificEvaluator",
    "create_evaluator"
]


def create_evaluator(method: str, ratings_file: str = "card_ratings.csv") -> BaseCardEvaluator:
    """Factory function to create the appropriate evaluator."""
    if method == "manual":
        return ManualCardEvaluator(ratings_file)
    elif method in ["empirical_vanilla", "empirical_mit", "empirical_cube", "empirical_average"]:
        return ModelSpecificEvaluator(method)
    else:
        raise ValueError(f"Unknown evaluation method: {method}") 
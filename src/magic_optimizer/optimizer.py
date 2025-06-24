"""
Main optimizer module with legacy compatibility.
"""

from typing import Dict, List, Optional

import pandas as pd

from .evaluators import create_evaluator
from .optimizers import create_optimizer


# Legacy compatibility class
class AdvancedDeckOptimizer:
    """Legacy compatibility class that delegates to specific optimizers."""
    
    def __init__(self, evaluation_method: str = "manual", ratings_file: str = "card_ratings.csv"):
        self.evaluation_method = evaluation_method
        self.ratings_file = ratings_file
    
    def optimize_deck(
        self,
        collection_df: pd.DataFrame,
        num_colors: int = 2,
        deck_size: int = 40,
        algorithm: str = "genetic",
        lambda_penalty: float = 0.5,
        evaluation_method: str = "manual",
        fixed_colors: Optional[List[str]] = None,
    ) -> Dict:
        """Delegate to the appropriate optimizer."""
        optimizer = create_optimizer(algorithm, evaluation_method, self.ratings_file)
        return optimizer.optimize_deck(
            collection_df,
            num_colors,
            deck_size,
            lambda_penalty,
            fixed_colors,
        )

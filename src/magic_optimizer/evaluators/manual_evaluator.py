"""
Manual card evaluator that uses CSV file for ratings.
"""

import pandas as pd
from typing import Dict, List

from .base_evaluator import BaseCardEvaluator


class ManualCardEvaluator(BaseCardEvaluator):
    """Evaluator that uses manual ratings from CSV file."""
    
    def __init__(self, ratings_file: str = "card_ratings.csv"):
        try:
            self.ratings_df = pd.read_csv(ratings_file)
            # Convert ratings to numeric for easier comparison
            self.ratings_df["Rating_Value"] = (
                self.ratings_df["Rating"].str.split("/").str[0].astype(int)
            )
            
            # Create a dictionary for quick rating lookup
            self.ratings_dict = dict(
                zip(self.ratings_df["Card Name"], self.ratings_df["Rating_Value"])
            )
            
            print(f"Loaded {len(self.ratings_df)} rated cards")
        except FileNotFoundError:
            print(f"Warning: Ratings file '{ratings_file}' not found.")
            self.ratings_df = pd.DataFrame()
            self.ratings_dict = {}
    
    def get_card_rating(self, card_name: str) -> float:
        """Get the rating for a specific card from the CSV."""
        return self.ratings_dict.get(card_name, 0.0)
    
    def get_deck_rating(self, card_names: List[str]) -> float:
        """Get the overall rating for a deck by summing individual card ratings."""
        return sum(self.get_card_rating(name) for name in card_names)
    
    def get_available_methods(self) -> List[Dict[str, str]]:
        """Get available evaluation methods."""
        return [{"value": "manual", "label": "Manual Ratings"}]
    
    def evaluate_card(self, card) -> float:
        """Evaluate a card object using manual ratings."""
        if not card or not hasattr(card, 'name') or not card.name:
            return 0.0
        
        # Use the card name to get manual rating
        return self.get_card_rating(card.name) 
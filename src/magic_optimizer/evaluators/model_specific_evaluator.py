"""
Model-specific evaluator that routes to the correct empirical model.
"""

from typing import Dict, List
from .base_evaluator import BaseCardEvaluator
from .empirical_models_evaluator import EmpiricalModelsEvaluator
from ..card import Card


class ModelSpecificEvaluator(BaseCardEvaluator):
    """Evaluator that routes to specific empirical models based on the evaluation method."""
    
    def __init__(self, model_type: str):
        """Initialize with a specific model type."""
        self.model_type = model_type
        self.empirical_evaluator = EmpiricalModelsEvaluator()
        
    def get_card_rating(self, card_name: str) -> float:
        """Get the rating for a specific card using the selected model."""
        try:
            # Try to get card data from the validator (which uses Scryfall API)
            from ..validator import CardValidator
            validator = CardValidator()
            card_data = validator.search_card(card_name)
            
            if card_data:
                # Create a Card object and evaluate it with the specific model
                card = Card(card_data)
                return self.evaluate_card(card)
            else:
                # If we can't find the card, return a default rating
                print(f"Warning: Could not find card data for '{card_name}', using default rating")
                return 3.0  # Default middle rating
                
        except Exception as e:
            print(f"Error evaluating card '{card_name}': {e}")
            return 3.0  # Default middle rating
    
    def get_deck_rating(self, card_names: List[str]) -> float:
        """Get the overall rating for a deck by averaging individual card ratings."""
        if not card_names:
            return 0.0
            
        total_rating = 0.0
        valid_cards = 0
        
        for card_name in card_names:
            rating = self.get_card_rating(card_name)
            total_rating += rating
            valid_cards += 1
        
        # Return average rating if we have valid cards, otherwise 0
        return total_rating / valid_cards if valid_cards > 0 else 0.0
    
    def get_available_methods(self) -> List[Dict[str, str]]:
        """Get available evaluation methods."""
        return self.empirical_evaluator.get_available_methods()
    
    def evaluate_card(self, card: Card) -> float:
        """Evaluate a card using the configured empirical model."""
        return self.empirical_evaluator.evaluate_card_with_model(card, self.model_type) 
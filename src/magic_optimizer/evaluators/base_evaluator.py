"""
Base evaluator class for card evaluation systems.
"""

from abc import ABC, abstractmethod
from typing import Dict, List


class BaseCardEvaluator(ABC):
    """Base class for card evaluation systems."""
    
    @abstractmethod
    def get_card_rating(self, card_name: str) -> float:
        """Get the rating for a specific card."""
        pass
    
    @abstractmethod
    def get_deck_rating(self, card_names: List[str]) -> float:
        """Get the overall rating for a deck."""
        pass
    
    @abstractmethod
    def get_available_methods(self) -> List[Dict[str, str]]:
        """Get available evaluation methods."""
        pass

    def evaluate_card(self, card):
        """Optional: Evaluate a card object based on its mechanics. Override in advanced evaluators."""
        raise NotImplementedError("This evaluator does not support card object evaluation.") 
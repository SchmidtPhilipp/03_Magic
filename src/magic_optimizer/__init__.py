"""
Magic Optimizer - Advanced Magic: The Gathering Deck Building Tool

A comprehensive tool for optimizing Magic: The Gathering decks using
advanced algorithms including genetic algorithms, simulated annealing,
and greedy optimization with comprehensive scoring systems.
"""

__version__ = "1.1.0"
__author__ = "Magic Optimizer Team"

from .deck_builder import EnhancedDeckBuilder
from .optimizer import AdvancedDeckOptimizer
from .validator import CardValidator

__all__ = ["EnhancedDeckBuilder", "AdvancedDeckOptimizer", "CardValidator"]

#!/usr/bin/env python3
"""
Simple test to verify deck size functionality
"""

import sys
import os
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from magic_optimizer.evaluators import create_evaluator

def test_deck_size():
    """Test deck size functionality."""
    print("=== DECK SIZE TEST ===\n")
    
    # Test evaluator creation
    evaluator = create_evaluator("empirical_average")
    
    # Test with different numbers of cards
    test_cards_40 = ["Lightning Bolt"] * 40
    test_cards_60 = ["Lightning Bolt"] * 60
    test_cards_100 = ["Lightning Bolt"] * 100
    
    print("Testing deck ratings with different sizes:")
    
    rating_40 = evaluator.get_deck_rating(test_cards_40)
    rating_60 = evaluator.get_deck_rating(test_cards_60)
    rating_100 = evaluator.get_deck_rating(test_cards_100)
    
    print(f"40 cards: {rating_40:.2f}")
    print(f"60 cards: {rating_60:.2f}")
    print(f"100 cards: {rating_100:.2f}")
    
    # Test that ratings scale appropriately
    print(f"\nRating per card:")
    print(f"40 cards: {rating_40/40:.2f}")
    print(f"60 cards: {rating_60/60:.2f}")
    print(f"100 cards: {rating_100/100:.2f}")
    
    # Test with mixed cards
    print(f"\nTesting with mixed cards:")
    mixed_cards = ["Lightning Bolt", "Counterspell", "Phyrexian Rager"] * 20  # 60 cards total
    mixed_rating = evaluator.get_deck_rating(mixed_cards)
    print(f"60 mixed cards: {mixed_rating:.2f}")
    print(f"Average per card: {mixed_rating/60:.2f}")
    
    print(f"\n=== DECK SIZE TEST COMPLETED ===")

if __name__ == "__main__":
    test_deck_size() 
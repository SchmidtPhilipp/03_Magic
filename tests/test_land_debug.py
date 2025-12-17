#!/usr/bin/env python3
"""
Test script to debug land card creation and filtering
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from magic_optimizer.deck_builder import EnhancedDeckBuilder
from magic_optimizer.card import Card

def test_land_debug():
    """Test land card creation and filtering"""
    print("🧪 Testing Land Card Debug")
    print("=" * 50)
    
    # Create deck builder
    builder = EnhancedDeckBuilder()
    
    # Test land card creation
    print("Testing land card creation:")
    land_card = builder._create_land_card("Plains", "W")
    print(f"  Land card name: {land_card.name}")
    print(f"  Land card type_line: {land_card.type_line}")
    print(f"  Land card main_type: {land_card.main_type}")
    print(f"  Land card colors: {land_card.colors}")
    
    # Test filtering
    print(f"\nTesting filtering:")
    test_cards = [
        land_card,
        Card({"name": "Lightning Bolt", "type_line": "Instant", "colors": ["R"], "cmc": 1}),
        Card({"name": "Grizzly Bears", "type_line": "Creature — Bear", "colors": ["G"], "cmc": 2})
    ]
    
    for i, card in enumerate(test_cards):
        is_land = "Land" in card.main_type
        print(f"  Card {i+1}: {card.name}")
        print(f"    Type: {card.main_type}")
        print(f"    Is land: {is_land}")
    
    # Test the actual filter used in add_lands_to_deck
    print(f"\nTesting actual filter:")
    non_land_cards = [c for c in test_cards if "Land" not in c.main_type]
    print(f"  Total cards: {len(test_cards)}")
    print(f"  Non-land cards: {len(non_land_cards)}")
    print(f"  Non-land card names: {[c.name for c in non_land_cards]}")

if __name__ == "__main__":
    test_land_debug() 
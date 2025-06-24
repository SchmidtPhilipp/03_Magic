import pandas as pd
import pytest
from src.magic_optimizer.deck_builder import EnhancedDeckBuilder
from src.magic_optimizer.optimizer import AdvancedDeckOptimizer
from src.magic_optimizer.card import Card
from src.magic_optimizer.evaluator import DeckEvaluator

# Mock Optimizer that bypasses file loading and API calls
class MockOptimizer(AdvancedDeckOptimizer):
    def __init__(self, ratings_file):
        # Bypasses the original __init__ to avoid file I/O
        # but we need to initialize the attributes that are used.
        class MockEvaluator(DeckEvaluator):
            def __init__(self, ratings_file):
                pass
            def evaluate_deck(self, card_names, method):
                return 5.0 # Return a dummy score

        self.evaluator = MockEvaluator(ratings_file)

    def prepare_eligible_cards(self, collection_df, num_colors, optimization_criterion="manual"):
        card_db = {
            "Ultimecia": {"name": "Ultimecia", "colors": ["U", "B"], "cmc": 4, "type_line": "Creature"},
            "Counterspell": {"name": "Counterspell", "colors": ["U"], "cmc": 2, "type_line": "Instant"},
            "Lightning Bolt": {"name": "Lightning Bolt", "colors": ["R"], "cmc": 1, "type_line": "Instant"},
            "Thought Monitor": {"name": "Thought Monitor", "colors": ["U"], "cmc": 7, "type_line": "Creature"},
            "Shock": {"name": "Shock", "colors": ["R"], "cmc": 1, "type_line": "Instant"},
            "Sol Ring": {"name": "Sol Ring", "colors": [], "cmc": 1, "type_line": "Artifact"},
            "Ornithopter": {"name": "Ornithopter", "colors": [], "cmc": 0, "type_line": "Creature"},
            "Faithless Looting": {"name": "Faithless Looting", "colors": ["R"], "cmc": 1, "type_line": "Sorcery"},
            "Ponder": {"name": "Ponder", "colors": ["U"], "cmc": 1, "type_line": "Sorcery"},
            "Dragon's Rage Channeler": {"name": "Dragon's Rage Channeler", "colors": ["R"], "cmc": 1, "type_line": "Creature"},
            "Delver of Secrets": {"name": "Delver of Secrets", "colors": ["U"], "cmc": 1, "type_line": "Creature"},
            "Mishra's Bauble": {"name": "Mishra's Bauble", "colors": [], "cmc": 0, "type_line": "Artifact"},
        }
        
        scores = {
            "Counterspell": 20,
            "Ponder": 19,
            "Delver of Secrets": 18,
            "Thought Monitor": 17,
            "Lightning Bolt": 15,
            "Dragon's Rage Channeler": 14,
            "Shock": 13,
            "Faithless Looting": 12,
            "Sol Ring": 10,
            "Ornithopter": 9,
            "Mishra's Bauble": 8,
            "Ultimecia": 5
        }

        card_list = []
        for name in collection_df["Name"]:
            if name in card_db:
                card_obj = Card(card_db[name])
                card_obj.optimization_score = scores.get(name, 0)
                card_list.append(card_obj)
        return card_list

def test_multicolor_card_exclusion(monkeypatch):
    """
    Tests that a multicolor card with a non-matching color is excluded.
    Specifically, ensures a U/B card is not put in a U/R deck.
    """
    # Use monkeypatch to replace the real AdvancedDeckOptimizer with our mock
    monkeypatch.setattr("src.magic_optimizer.deck_builder.AdvancedDeckOptimizer", MockOptimizer)

    # 1. Create a mock collection
    mock_collection_data = {
        "Name": [
            "Ultimecia", "Counterspell", "Lightning Bolt", "Thought Monitor", "Shock",
            "Sol Ring", "Ornithopter", "Faithless Looting", "Ponder",
            "Dragon's Rage Channeler", "Delver of Secrets", "Mishra's Bauble",
        ],
        "Quantity": [1] * 12,
    }
    collection_df = pd.DataFrame(mock_collection_data)

    # 2. Initialize the Deck Builder
    # Now it will use the MockOptimizer instead of the real one.
    builder = EnhancedDeckBuilder(ratings_file="dummy_path.csv")

    # 3. Build the deck
    result = builder.build_optimal_deck_advanced(
        collection_df=collection_df,
        num_colors=2,
        total_deck_size=10,
        num_lands=4,
        algorithm="greedy",
    )

    # 4. Assert the results
    deck_card_names = [card['name'] for card in result['deck']]

    assert "Ultimecia" not in deck_card_names
    target_colors = result["target_colors"]
    assert "U" in target_colors
    assert "R" in target_colors
    assert "B" not in target_colors

    print("\nTest passed: U/B card was correctly excluded from the U/R deck.")

if __name__ == "__main__":
    pytest.main([__file__]) 
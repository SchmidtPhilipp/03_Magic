"""
Game mechanics-based card evaluator that rates cards based on their actual characteristics.
"""

import re
from typing import Dict, List, Set

from .base_evaluator import BaseCardEvaluator
from ..card import Card


class GameMechanicsEvaluator(BaseCardEvaluator):
    """Evaluator that rates cards based on their game mechanics and characteristics."""
    
    def __init__(self):
        # Define creature types that are generally considered good
        self.good_creature_types = {
            "Human", "Elf", "Goblin", "Zombie", "Dragon", "Merfolk", "Vampire", 
            "Angel", "Demon", "Spirit", "Elemental", "Beast", "Bird", "Cat", 
            "Dog", "Knight", "Wizard", "Warrior", "Rogue", "Cleric", "Druid"
        }
        
        # Define keywords that add value
        self.valuable_keywords = {
            "Flying", "Haste", "First Strike", "Double Strike", "Vigilance", 
            "Deathtouch", "Lifelink", "Trample", "Reach", "Flash", "Hexproof",
            "Indestructible", "Menace", "Skulk", "Prowess", "Scry", "Draw"
        }
        
        # Define removal keywords
        self.removal_keywords = {
            "Destroy", "Exile", "Return to hand", "Tap", "Counter", "Damage"
        }
        
        # Define card draw keywords
        self.draw_keywords = {
            "Draw", "Scry", "Look at", "Reveal", "Search"
        }
        
        # Define mana acceleration keywords
        self.ramp_keywords = {
            "Add", "Search for land", "Put land", "Mana", "Ramp"
        }
        
        print("Game Mechanics Evaluator initialized with comprehensive rating criteria")
    
    def get_card_rating(self, card_name: str) -> float:
        """Get the rating for a specific card based on game mechanics."""
        # This would need to be implemented to get card data
        # For now, we'll use a placeholder that would work with the card object
        return 5.0  # Default rating
    
    def get_deck_rating(self, card_names: List[str]) -> float:
        """Get the overall rating for a deck by summing individual card ratings."""
        return sum(self.get_card_rating(name) for name in card_names)
    
    def get_available_methods(self) -> List[Dict[str, str]]:
        """Get available evaluation methods."""
        return [{"value": "game_mechanics", "label": "Game Mechanics Analysis"}]
    
    def evaluate_card(self, card: Card) -> float:
        """Evaluate a card based on its game mechanics and characteristics."""
        if not card or not card.name:
            return 0.0
        
        # Get the main card type
        card_type = card.main_type.lower()
        
        # Route to appropriate evaluation method
        if "creature" in card_type:
            return self._evaluate_creature(card)
        elif "instant" in card_type:
            return self._evaluate_instant(card)
        elif "sorcery" in card_type:
            return self._evaluate_sorcery(card)
        elif "enchantment" in card_type:
            return self._evaluate_enchantment(card)
        elif "artifact" in card_type:
            return self._evaluate_artifact(card)
        elif "planeswalker" in card_type:
            return self._evaluate_planeswalker(card)
        elif "land" in card_type:
            return self._evaluate_land(card)
        else:
            return self._evaluate_generic(card)
    
    def _evaluate_creature(self, card: Card) -> float:
        """Evaluate creature cards based on power, toughness, and abilities."""
        base_score = 0.0
        
        # Base stats evaluation (Power + Toughness - Mana Cost)
        power = getattr(card, 'power', 0)
        toughness = getattr(card, 'toughness', 0)
        cmc = getattr(card, 'cmc', 0)
        
        if isinstance(power, str):
            try:
                power = int(power) if power != '*' else 3  # Assume 3 for variable power
            except ValueError:
                power = 0
        
        if isinstance(toughness, str):
            try:
                toughness = int(toughness) if toughness != '*' else 3  # Assume 3 for variable toughness
            except ValueError:
                toughness = 0
        
        # Stat efficiency: (Power + Toughness) - CMC
        stat_efficiency = (power + toughness) - cmc
        base_score += stat_efficiency * 2.0  # Weight stat efficiency heavily
        
        # Creature type bonus
        creature_types = self._extract_creature_types(card)
        good_type_count = sum(1 for t in creature_types if t in self.good_creature_types)
        base_score += good_type_count * 0.5
        
        # Keyword abilities
        keywords = self._extract_keywords(card)
        for keyword in keywords:
            if keyword in self.valuable_keywords:
                base_score += 1.0  # Each valuable keyword adds 1 point
        
        # Special abilities evaluation
        abilities_score = self._evaluate_abilities(card)
        base_score += abilities_score
        
        # Mana curve considerations
        if cmc <= 2:
            base_score += 1.0  # Bonus for low-cost creatures
        elif cmc >= 6:
            base_score -= 1.0  # Penalty for high-cost creatures
        
        return max(0.0, base_score)
    
    def _evaluate_instant(self, card: Card) -> float:
        """Evaluate instant spells based on their effects."""
        base_score = 5.0  # Base score for instants
        
        # Check for removal effects
        if self._has_removal_effect(card):
            base_score += 3.0
        
        # Check for card draw
        if self._has_draw_effect(card):
            base_score += 2.0
        
        # Check for protection/counter effects
        if self._has_protection_effect(card):
            base_score += 2.0
        
        # Check for combat tricks
        if self._has_combat_trick_effect(card):
            base_score += 1.5
        
        # Mana efficiency
        cmc = getattr(card, 'cmc', 0)
        if cmc <= 1:
            base_score += 2.0
        elif cmc <= 2:
            base_score += 1.0
        elif cmc >= 4:
            base_score -= 1.0
        
        return max(0.0, base_score)
    
    def _evaluate_sorcery(self, card: Card) -> float:
        """Evaluate sorcery spells based on their effects."""
        base_score = 4.0  # Base score for sorceries
        
        # Check for removal effects
        if self._has_removal_effect(card):
            base_score += 2.5
        
        # Check for card draw
        if self._has_draw_effect(card):
            base_score += 2.0
        
        # Check for ramp effects
        if self._has_ramp_effect(card):
            base_score += 2.0
        
        # Check for board wipes
        if self._has_board_wipe_effect(card):
            base_score += 3.0
        
        # Mana efficiency
        cmc = getattr(card, 'cmc', 0)
        if cmc <= 2:
            base_score += 1.5
        elif cmc >= 5:
            base_score -= 1.0
        
        return max(0.0, base_score)
    
    def _evaluate_enchantment(self, card: Card) -> float:
        """Evaluate enchantments based on their effects."""
        base_score = 3.0  # Base score for enchantments
        
        # Check for card draw effects
        if self._has_draw_effect(card):
            base_score += 2.0
        
        # Check for removal effects
        if self._has_removal_effect(card):
            base_score += 2.0
        
        # Check for protection effects
        if self._has_protection_effect(card):
            base_score += 1.5
        
        # Check for anthem effects (buffs to creatures)
        if self._has_anthem_effect(card):
            base_score += 2.0
        
        # Mana efficiency
        cmc = getattr(card, 'cmc', 0)
        if cmc <= 3:
            base_score += 1.0
        elif cmc >= 5:
            base_score -= 1.0
        
        return max(0.0, base_score)
    
    def _evaluate_artifact(self, card: Card) -> float:
        """Evaluate artifacts based on their effects."""
        base_score = 3.0  # Base score for artifacts
        
        # Check for mana acceleration
        if self._has_ramp_effect(card):
            base_score += 2.5
        
        # Check for card draw
        if self._has_draw_effect(card):
            base_score += 2.0
        
        # Check for equipment effects
        if self._has_equipment_effect(card):
            base_score += 1.5
        
        # Check for removal effects
        if self._has_removal_effect(card):
            base_score += 2.0
        
        # Mana efficiency
        cmc = getattr(card, 'cmc', 0)
        if cmc <= 2:
            base_score += 1.5
        elif cmc >= 5:
            base_score -= 1.0
        
        return max(0.0, base_score)
    
    def _evaluate_planeswalker(self, card: Card) -> float:
        """Evaluate planeswalkers based on their abilities."""
        base_score = 6.0  # Base score for planeswalkers (they're generally powerful)
        
        # Check for card draw abilities
        if self._has_draw_effect(card):
            base_score += 2.0
        
        # Check for removal abilities
        if self._has_removal_effect(card):
            base_score += 2.0
        
        # Check for protection abilities
        if self._has_protection_effect(card):
            base_score += 1.5
        
        # Mana efficiency
        cmc = getattr(card, 'cmc', 0)
        if cmc <= 3:
            base_score += 2.0
        elif cmc >= 6:
            base_score -= 1.0
        
        return max(0.0, base_score)
    
    def _evaluate_land(self, card: Card) -> float:
        """Evaluate lands based on their utility."""
        base_score = 2.0  # Base score for lands
        
        # Check if it's a dual land or has multiple colors
        colors = getattr(card, 'colors', [])
        if len(colors) > 1:
            base_score += 1.0
        
        # Check for utility effects
        if self._has_utility_effect(card):
            base_score += 1.5
        
        # Check for mana acceleration
        if self._has_ramp_effect(card):
            base_score += 1.0
        
        return max(0.0, base_score)
    
    def _evaluate_generic(self, card: Card) -> float:
        """Evaluate generic cards that don't fit other categories."""
        base_score = 3.0
        
        # Check for any valuable effects
        if self._has_draw_effect(card):
            base_score += 1.5
        if self._has_removal_effect(card):
            base_score += 1.5
        if self._has_protection_effect(card):
            base_score += 1.0
        
        return max(0.0, base_score)
    
    def _extract_creature_types(self, card: Card) -> Set[str]:
        """Extract creature types from card type line."""
        type_line = getattr(card, 'main_type', '')
        if not type_line:
            return set()
        
        # Look for creature types in the type line
        creature_types = set()
        type_parts = type_line.split('—')
        if len(type_parts) > 1:
            subtypes = type_parts[1].strip().split()
            creature_types.update(subtypes)
        
        return creature_types
    
    def _extract_keywords(self, card: Card) -> Set[str]:
        """Extract keywords from card text."""
        text = getattr(card, 'text', '')
        if not text:
            return set()
        
        keywords = set()
        for keyword in self.valuable_keywords:
            if keyword.lower() in text.lower():
                keywords.add(keyword)
        
        return keywords
    
    def _evaluate_abilities(self, card: Card) -> float:
        """Evaluate special abilities on the card."""
        text = getattr(card, 'text', '')
        if not text:
            return 0.0
        
        score = 0.0
        text_lower = text.lower()
        
        # Card draw abilities
        if any(phrase in text_lower for phrase in ['draw a card', 'draw cards', 'draw two']):
            score += 2.0
        
        # Removal abilities
        if any(phrase in text_lower for phrase in ['destroy', 'exile', 'return to hand', 'tap']):
            score += 2.0
        
        # Protection abilities
        if any(phrase in text_lower for phrase in ['hexproof', 'indestructible', 'can\'t be blocked']):
            score += 1.5
        
        # Mana acceleration
        if any(phrase in text_lower for phrase in ['add', 'mana', 'search for a land']):
            score += 1.5
        
        # Combat abilities
        if any(phrase in text_lower for phrase in ['first strike', 'double strike', 'trample']):
            score += 1.0
        
        return score
    
    def _has_removal_effect(self, card: Card) -> bool:
        """Check if card has removal effects."""
        text = getattr(card, 'text', '').lower()
        removal_phrases = ['destroy', 'exile', 'return to hand', 'tap', 'counter', 'damage']
        return any(phrase in text for phrase in removal_phrases)
    
    def _has_draw_effect(self, card: Card) -> bool:
        """Check if card has card draw effects."""
        text = getattr(card, 'text', '').lower()
        draw_phrases = ['draw a card', 'draw cards', 'draw two', 'scry']
        return any(phrase in text for phrase in draw_phrases)
    
    def _has_ramp_effect(self, card: Card) -> bool:
        """Check if card has mana acceleration effects."""
        text = getattr(card, 'text', '').lower()
        ramp_phrases = ['add', 'mana', 'search for a land', 'put a land']
        return any(phrase in text for phrase in ramp_phrases)
    
    def _has_protection_effect(self, card: Card) -> bool:
        """Check if card has protection effects."""
        text = getattr(card, 'text', '').lower()
        protection_phrases = ['hexproof', 'indestructible', 'can\'t be blocked', 'protection']
        return any(phrase in text for phrase in protection_phrases)
    
    def _has_combat_trick_effect(self, card: Card) -> bool:
        """Check if card has combat trick effects."""
        text = getattr(card, 'text', '').lower()
        combat_phrases = ['+1/+1', '+2/+2', 'first strike', 'double strike', 'trample']
        return any(phrase in text for phrase in combat_phrases)
    
    def _has_board_wipe_effect(self, card: Card) -> bool:
        """Check if card has board wipe effects."""
        text = getattr(card, 'text', '').lower()
        wipe_phrases = ['destroy all', 'exile all', 'damage to all']
        return any(phrase in text for phrase in wipe_phrases)
    
    def _has_anthem_effect(self, card: Card) -> bool:
        """Check if card has anthem effects (buffs to all creatures)."""
        text = getattr(card, 'text', '').lower()
        anthem_phrases = ['all creatures get', 'creatures you control get', '+1/+1 to all']
        return any(phrase in text for phrase in anthem_phrases)
    
    def _has_equipment_effect(self, card: Card) -> bool:
        """Check if card has equipment effects."""
        text = getattr(card, 'text', '').lower()
        equipment_phrases = ['equip', 'attach', 'equipped creature']
        return any(phrase in text for phrase in equipment_phrases)
    
    def _has_utility_effect(self, card: Card) -> bool:
        """Check if card has utility effects."""
        text = getattr(card, 'text', '').lower()
        utility_phrases = ['scry', 'investigate', 'explore', 'cycling']
        return any(phrase in text for phrase in utility_phrases) 
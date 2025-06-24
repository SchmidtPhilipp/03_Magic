"""
Empirical models-based card evaluator using three established methodologies.
"""

import re
from typing import Dict, List, Set
from .base_evaluator import BaseCardEvaluator
from ..card import Card


class EmpiricalModelsEvaluator(BaseCardEvaluator):
    """Evaluator implementing three empirical models for card evaluation."""
    
    def __init__(self):
        # Model A: Vanilla-Test + Keywords (LSV-Style) Constants
        self.model_a_weights = {
            'power': 0.8,
            'toughness': 0.6,
            'cmc_penalty': -1.0,
            'flying': 1.5,
            'deathtouch': 1.0,
            'lifelink': 1.2,
            'haste': 0.5,
            'first_strike': 0.8,
            'double_strike': 2.0,
            'trample': 0.8,
            'vigilance': 0.5,
            'reach': 0.3,
            'hexproof': 1.0,
            'menace': 0.7,
            'card_draw_etb': 2.0,
            'card_advantage': 3.0,
            'spell_effect_strength': 1.0,
            'instant_bonus': 0.5
        }
        
        # Model B: MIT DraftBot (Regression) Constants
        self.model_b_weights = {
            'intercept': 2.5,
            'power': 1.2,
            'toughness': 0.9,
            'cmc_penalty': -1.0,
            'flying': 1.8,
            'deathtouch': 1.1,
            'lifelink': 0.9,
            'haste': 0.6,
            'first_strike': 0.7,
            'trample': 0.8,
            'card_draw': 2.2,
            'removal': 2.0,
            'ramp': 1.5
        }
        
        # Model C: CubeTutor Value System Constants
        self.model_c_weights = {
            'base_power_multiplier': 1.0,
            'archetype_fit_multiplier': 1.0,
            'synergy_bonus_multiplier': 1.0
        }
        
        # Define keywords for identification
        self.keywords = {
            'flying', 'first strike', 'double strike', 'deathtouch', 'haste',
            'hexproof', 'indestructible', 'lifelink', 'menace', 'reach',
            'trample', 'vigilance', 'flash', 'prowess', 'scry'
        }
        
        # Define card draw patterns
        self.card_draw_patterns = [
            r'draw.*card', r'scry', r'look at.*card', r'reveal.*card',
            r'search.*library'
        ]
        
        # Define removal patterns
        self.removal_patterns = [
            r'destroy', r'exile', r'return.*to.*hand', r'counter',
            r'deal.*damage', r'tap.*creature'
        ]
        
        # Define ramp patterns
        self.ramp_patterns = [
            r'add.*mana', r'search.*basic land', r'put.*land.*battlefield',
            r'untap.*land'
        ]
        
        print("Empirical Models Evaluator initialized with three evaluation methods")
    
    def get_card_rating(self, card_name: str) -> float:
        """Get the rating for a specific card by fetching card data and evaluating it."""
        try:
            # Try to get card data from the validator (which uses Scryfall API)
            from ..validator import CardValidator
            validator = CardValidator()
            card_data = validator.search_card(card_name)
            
            if card_data:
                # Create a Card object and evaluate it
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
        """Get the overall rating for a deck by summing individual card ratings."""
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
        return [
            {"value": "empirical_mit", "label": "Empirical: MIT DraftBot Regression"},
            {"value": "empirical_vanilla", "label": "Empirical: Vanilla-Test + Keywords (LSV-Style)"},
            {"value": "empirical_cube", "label": "Empirical: CubeTutor Value System"},
            {"value": "empirical_average", "label": "Empirical: Average of All Models"}
        ]
    
    def evaluate_card(self, card: Card) -> float:
        """Evaluate a card using the default empirical model (average of all)."""
        return self.evaluate_card_with_model(card, "empirical_average")
        
    def evaluate_card_with_model(self, card: Card, model: str = "empirical_average") -> float:
        """Evaluate a card using the specified empirical model."""
        if not card or not card.name:
            return 0.0
        
        if model == "empirical_vanilla":
            return self._evaluate_vanilla_test(card)
        elif model == "empirical_mit":
            return self._evaluate_mit_draftbot(card)
        elif model == "empirical_cube":
            return self._evaluate_cubetutor(card)
        elif model == "empirical_average":
            vanilla_score = self._evaluate_vanilla_test(card)
            mit_score = self._evaluate_mit_draftbot(card)
            cube_score = self._evaluate_cubetutor(card)
            return (vanilla_score + mit_score + cube_score) / 3.0
        else:
            return self._evaluate_vanilla_test(card)  # Default to vanilla test
    
    def _evaluate_vanilla_test(self, card: Card) -> float:
        """
        Model A: Vanilla-Test + Keywords (LSV-Style)
        
        For creatures: Value = 0.8*P + 0.6*T - 1.0*CMC + Σ(γk*1k) + δETB + δCardAdv
        For spells: Value = α*EffectStrength - β*CMC + γ*1Instant
        """
        card_type = card.main_type.lower()
        
        if "creature" in card_type:
            return self._vanilla_evaluate_creature(card)
        elif "instant" in card_type:
            return self._vanilla_evaluate_spell(card, is_instant=True)
        elif "sorcery" in card_type:
            return self._vanilla_evaluate_spell(card, is_instant=False)
        else:
            return self._vanilla_evaluate_generic(card)
    
    def _vanilla_evaluate_creature(self, card: Card) -> float:
        """Evaluate creature using Vanilla-Test model."""
        power = self._get_numeric_value(card.power)
        toughness = self._get_numeric_value(card.toughness)
        cmc = getattr(card, 'cmc', 0)
        
        # Base formula: 0.8*P + 0.6*T - 1.0*CMC
        value = (self.model_a_weights['power'] * power + 
                self.model_a_weights['toughness'] * toughness + 
                self.model_a_weights['cmc_penalty'] * cmc)
        
        # Add keyword bonuses
        keywords = self._extract_keywords_from_card(card)
        for keyword in keywords:
            if keyword in self.model_a_weights:
                value += self.model_a_weights[keyword]
        
        # Check for ETB card draw
        if self._has_etb_draw_effect(card):
            value += self.model_a_weights['card_draw_etb']
        
        # Check for card advantage effects
        if self._has_card_advantage_effect(card):
            value += self.model_a_weights['card_advantage']
        
        # Check for ramp effects (mana dorks)
        if self._has_ramp_effect(card):
            value += 2.0  # Ramp is very valuable in Limited
        
        return max(0.0, value)
    
    def _vanilla_evaluate_spell(self, card: Card, is_instant: bool = False) -> float:
        """Evaluate instant/sorcery using Vanilla-Test model."""
        cmc = getattr(card, 'cmc', 0)
        
        # Base effect strength estimation
        effect_strength = self._estimate_spell_effect_strength(card)
        
        # Formula: α*EffectStrength - β*CMC + γ*1Instant
        value = (self.model_a_weights['spell_effect_strength'] * effect_strength +
                self.model_a_weights['cmc_penalty'] * cmc)
        
        if is_instant:
            value += self.model_a_weights['instant_bonus']
        
        return max(0.0, value)
    
    def _vanilla_evaluate_generic(self, card: Card) -> float:
        """Evaluate other card types using simplified Vanilla-Test model."""
        cmc = getattr(card, 'cmc', 0)
        base_value = 3.0 - (cmc * 0.5)  # Simple CMC penalty
        
        # Add bonuses for useful effects
        if self._has_card_advantage_effect(card):
            base_value += 2.0
        
        return max(0.0, base_value)
    
    def _evaluate_mit_draftbot(self, card: Card) -> float:
        """
        Model B: MIT DraftBot (Regression)
        
        DraftScore = β0 + β1*Power + β2*Toughness + β3*CMC + β4*1Flying + β5*1DrawCard + ...
        """
        # Start with intercept
        value = self.model_b_weights['intercept']
        
        card_type = card.main_type.lower()
        
        if "creature" in card_type:
            power = self._get_numeric_value(card.power)
            toughness = self._get_numeric_value(card.toughness)
            
            value += (self.model_b_weights['power'] * power +
                     self.model_b_weights['toughness'] * toughness)
        
        # CMC penalty
        cmc = getattr(card, 'cmc', 0)
        value += self.model_b_weights['cmc_penalty'] * cmc
        
        # Keyword bonuses
        keywords = self._extract_keywords_from_card(card)
        for keyword in keywords:
            if keyword in self.model_b_weights:
                value += self.model_b_weights[keyword]
        
        # Effect bonuses
        if self._has_card_draw_effect(card):
            value += self.model_b_weights['card_draw']
        
        if self._has_removal_effect(card):
            value += self.model_b_weights['removal']
        
        if self._has_ramp_effect(card):
            value += self.model_b_weights['ramp']
        
        return max(0.0, value)
    
    def _evaluate_cubetutor(self, card: Card) -> float:
        """
        Model C: CubeTutor Value System
        
        Value = θ1*BasePower + θ2*ArchetypeFit + θ3*SynergyBonus
        """
        base_power = self._calculate_base_power(card)
        archetype_fit = self._calculate_archetype_fit(card)
        synergy_bonus = self._calculate_synergy_bonus(card)
        
        value = (self.model_c_weights['base_power_multiplier'] * base_power +
                self.model_c_weights['archetype_fit_multiplier'] * archetype_fit +
                self.model_c_weights['synergy_bonus_multiplier'] * synergy_bonus)
        
        return max(0.0, value)
    
    def _calculate_base_power(self, card: Card) -> float:
        """Calculate base power rating (0-5 scale) for CubeTutor model."""
        card_type = card.main_type.lower()
        cmc = getattr(card, 'cmc', 0)
        
        if "creature" in card_type:
            power = self._get_numeric_value(card.power)
            toughness = self._get_numeric_value(card.toughness)
            
            # Simple stat efficiency rating
            stat_total = power + toughness
            efficiency = stat_total - cmc
            
            if efficiency >= 4:
                return 5.0
            elif efficiency >= 2:
                return 4.0
            elif efficiency >= 0:
                return 3.0
            elif efficiency >= -2:
                return 2.0
            else:
                return 1.0
        else:
            # Non-creatures based on CMC and effects
            if cmc <= 1 and (self._has_removal_effect(card) or self._has_card_draw_effect(card)):
                return 4.0  # Reduced from 5.0 for better balance
            elif cmc <= 2 and self._has_powerful_effect(card):
                return 3.5  # Reduced from 4.0
            elif cmc <= 3:
                return 3.0
            elif cmc <= 4:
                return 2.0
            else:
                return 1.0
    
    def _calculate_archetype_fit(self, card: Card) -> float:
        """Calculate archetype fit rating (0-3 scale) for CubeTutor model."""
        # Simplified archetype fitting based on colors and effects
        colors = len(card.colors)
        
        if colors == 1:
            return 3.0  # Mono-colored cards fit well in their archetype
        elif colors == 2:
            return 2.5  # Two-color cards are slightly more restrictive
        elif colors >= 3:
            return 1.0  # Multi-color cards are harder to fit
        else:  # Colorless
            return 2.0  # Artifacts fit in most decks
    
    def _calculate_synergy_bonus(self, card: Card) -> float:
        """Calculate synergy bonus rating (0-2 scale) for CubeTutor model."""
        # Simplified synergy calculation
        bonus = 0.0
        
        # Cards with tribal types get synergy bonus
        if "creature" in card.main_type.lower():
            if any(tribe in card.type_line.lower() for tribe in 
                   ['human', 'elf', 'goblin', 'zombie', 'merfolk']):
                bonus += 0.5
        
        # Spell-matters cards
        if any(pattern in card._data.get('oracle_text', '').lower() for pattern in
               ['instant', 'sorcery', 'spell']):
            bonus += 0.5
        
        # Token generators
        if 'token' in card._data.get('oracle_text', '').lower():
            bonus += 0.5
        
        # Graveyard synergies
        if 'graveyard' in card._data.get('oracle_text', '').lower():
            bonus += 0.5
        
        return min(2.0, bonus)
    
    def _get_numeric_value(self, value) -> float:
        """Convert power/toughness values to numeric (handle * and X)."""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            if value in ['*', 'X']:
                return 2.0  # Assume reasonable value for variable stats
            try:
                return float(value)
            except ValueError:
                return 0.0
        else:
            return 0.0
    
    def _extract_keywords_from_card(self, card: Card) -> Set[str]:
        """Extract keywords from card text."""
        oracle_text = card._data.get('oracle_text', '').lower()
        keywords_found = set()
        
        for keyword in self.keywords:
            if keyword in oracle_text:
                keywords_found.add(keyword.replace(' ', '_'))
        
        return keywords_found
    
    def _has_etb_draw_effect(self, card: Card) -> bool:
        """Check if card has enter-the-battlefield card draw effect."""
        oracle_text = card._data.get('oracle_text', '').lower()
        return ('enters the battlefield' in oracle_text or 'etb' in oracle_text) and \
               any(pattern in oracle_text for pattern in ['draw', 'scry'])
    
    def _has_card_advantage_effect(self, card: Card) -> bool:
        """Check if card provides card advantage."""
        oracle_text = card._data.get('oracle_text', '').lower()
        return any(re.search(pattern, oracle_text) for pattern in self.card_draw_patterns)
    
    def _has_card_draw_effect(self, card: Card) -> bool:
        """Check if card has card draw effect."""
        return self._has_card_advantage_effect(card)
    
    def _has_removal_effect(self, card: Card) -> bool:
        """Check if card has removal effect."""
        oracle_text = card._data.get('oracle_text', '').lower()
        return any(re.search(pattern, oracle_text) for pattern in self.removal_patterns)
    
    def _has_ramp_effect(self, card: Card) -> bool:
        """Check if card has mana ramp effect."""
        oracle_text = card._data.get('oracle_text', '').lower()
        return any(re.search(pattern, oracle_text) for pattern in self.ramp_patterns)
    
    def _has_powerful_effect(self, card: Card) -> bool:
        """Check if card has a generally powerful effect."""
        return (self._has_removal_effect(card) or 
                self._has_card_draw_effect(card) or 
                self._has_ramp_effect(card))
    
    def _estimate_spell_effect_strength(self, card: Card) -> float:
        """Estimate the strength of a spell's effect."""
        strength = 2.0  # Base strength
        
        if self._has_removal_effect(card):
            strength += 2.0
        
        if self._has_card_draw_effect(card):
            strength += 1.5
        
        if self._has_ramp_effect(card):
            strength += 1.0
        
        # Check for damage spells
        oracle_text = card._data.get('oracle_text', '').lower()
        damage_match = re.search(r'deal (\d+) damage', oracle_text)
        if damage_match:
            damage = int(damage_match.group(1))
            strength += damage * 0.5
        
        return strength 
import requests
import time
import json
from typing import Dict, List, Optional

class CardValidator:
    """Validates and corrects Magic: The Gathering card names using Scryfall API"""
    
    def __init__(self):
        self.base_url = "https://api.scryfall.com"
        self.cache = {}
    
    def search_card(self, card_name: str) -> Optional[Dict]:
        """Search for a card using Scryfall API"""
        if card_name in self.cache:
            return self.cache[card_name]
        
        try:
            # Search for exact card name
            url = f"{self.base_url}/cards/named"
            params = {"exact": card_name}
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                card_data = response.json()
                self.cache[card_name] = card_data
                return card_data
            else:
                # Try fuzzy search
                url = f"{self.base_url}/cards/search"
                params = {"q": card_name}
                
                response = requests.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('data') and len(data['data']) > 0:
                        card_data = data['data'][0]
                        self.cache[card_name] = card_data
                        return card_data
            
            # If not found, cache empty result
            self.cache[card_name] = None
            return None
            
        except Exception as e:
            print(f"Error searching for card '{card_name}': {e}")
            return None
    
    def validate_card_name(self, card_name: str) -> Dict:
        """Validate and correct a card name"""
        result = {
            'original_name': card_name,
            'corrected_name': card_name,
            'is_valid': False,
            'card_data': None
        }
        
        card_data = self.search_card(card_name)
        
        if card_data:
            result['corrected_name'] = card_data.get('name', card_name)
            result['is_valid'] = True
            result['card_data'] = card_data
        
        return result
    
    def validate_cards(self, card_names: List[str], sample_size: Optional[int] = None) -> Dict:
        """Validate a list of card names"""
        if sample_size:
            card_names = card_names[:sample_size]
        
        results = []
        valid_count = 0
        
        print(f"Validating {len(card_names)} cards...")
        
        for i, card_name in enumerate(card_names, 1):
            if i % 10 == 0:
                print(f"Progress: {i}/{len(card_names)}")
            
            result = self.validate_card_name(card_name)
            results.append(result)
            
            if result['is_valid']:
                valid_count += 1
            
            # Rate limiting
            time.sleep(0.1)
        
        return {
            'total_cards': len(card_names),
            'valid_cards': valid_count,
            'invalid_cards': len(card_names) - valid_count,
            'validation_rate': valid_count / len(card_names) if card_names else 0,
            'results': results
        } 
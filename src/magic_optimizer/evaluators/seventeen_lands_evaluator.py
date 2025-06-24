"""
17Lands card evaluator that uses API for ratings with CSV caching.
"""

import logging
import os
import pandas as pd
from typing import Dict, List

from .base_evaluator import BaseCardEvaluator
from ..evaluator import SeventeenLandsAPI


class SeventeenLandsCardEvaluator(BaseCardEvaluator):
    """Evaluator that uses 17lands API for ratings with CSV caching."""
    
    def __init__(self, cache_file: str = "data/ratings/17lands_cache.json", csv_cache_file: str = "data/ratings/17lands_ratings.csv"):
        """Initialize the 17Lands evaluator with API client and CSV caching."""
        self.seventeen_lands = SeventeenLandsAPI(cache_file=cache_file)
        self.csv_cache_file = csv_cache_file
        self.logger = logging.getLogger(__name__)
        
        # Load CSV cache
        self.ratings_cache = {}
        self._load_csv_cache()
        
        # Load manual ratings as fallback
        self._load_manual_ratings()
        
        # Track API data availability
        self.api_data_found = 0
        self.fallback_data_used = 0
        self.cards_processed = 0
        
        print("17Lands Card Evaluator initialized with API integration and CSV caching")
    
    def _load_csv_cache(self):
        """Load ratings from CSV cache file."""
        try:
            if os.path.exists(self.csv_cache_file):
                self.ratings_df = pd.read_csv(self.csv_cache_file)
                # Create a dictionary for quick lookup
                self.ratings_cache = dict(
                    zip(self.ratings_df["card_name"], self.ratings_df["rating"])
                )
                self.logger.info(f"Loaded {len(self.ratings_cache)} ratings from CSV cache")
                print(f"Loaded {len(self.ratings_cache)} ratings from CSV cache")
            else:
                self.ratings_df = pd.DataFrame(columns=["card_name", "rating", "gih_winrate", "iwd"])
                self.ratings_cache = {}
                self.logger.info("No CSV cache found - will create new cache")
                print("No CSV cache found - will create new cache")
        except Exception as e:
            self.logger.error(f"Error loading CSV cache: {e}")
            self.ratings_df = pd.DataFrame(columns=["card_name", "rating", "gih_winrate", "iwd"])
            self.ratings_cache = {}
    
    def _save_csv_cache(self):
        """Save ratings to CSV cache file."""
        try:
            os.makedirs(os.path.dirname(self.csv_cache_file), exist_ok=True)
            self.ratings_df.to_csv(self.csv_cache_file, index=False)
            self.logger.debug(f"Saved {len(self.ratings_cache)} ratings to CSV cache")
        except Exception as e:
            self.logger.error(f"Error saving CSV cache: {e}")
    
    def _load_manual_ratings(self):
        """Load manual ratings as fallback."""
        self.manual_ratings = {}
        try:
            manual_ratings_file = "data/ratings/card_ratings.csv"
            if os.path.exists(manual_ratings_file):
                manual_df = pd.read_csv(manual_ratings_file)
                # Convert ratings to numeric values (assuming format like "7/10")
                for _, row in manual_df.iterrows():
                    card_name = row["Card Name"]
                    rating_str = row["Rating"]
                    try:
                        # Extract numeric value from rating (e.g., "7/10" -> 7.0)
                        if "/" in str(rating_str):
                            rating_value = float(str(rating_str).split("/")[0])
                        else:
                            rating_value = float(rating_str)
                        self.manual_ratings[card_name] = rating_value
                    except (ValueError, AttributeError):
                        pass
                self.logger.info(f"Loaded {len(self.manual_ratings)} manual ratings for fallback")
            else:
                self.logger.info("No manual ratings file found for fallback")
        except Exception as e:
            self.logger.error(f"Error loading manual ratings: {e}")
            self.manual_ratings = {}
    
    def _get_cached_rating(self, card_name: str) -> float:
        """Get rating from CSV cache if available."""
        return self.ratings_cache.get(card_name, None)
    
    def _cache_rating(self, card_name: str, rating: float, gih_winrate: float = 0.0, iwd: float = 0.0):
        """Cache a rating in the CSV cache."""
        if card_name not in self.ratings_cache:
            # Add to DataFrame
            new_row = pd.DataFrame([{
                "card_name": card_name,
                "rating": rating,
                "gih_winrate": gih_winrate,
                "iwd": iwd
            }])
            
            # Handle empty DataFrame case
            if self.ratings_df.empty:
                self.ratings_df = new_row
            else:
                self.ratings_df = pd.concat([self.ratings_df, new_row], ignore_index=True)
            
            # Add to dictionary cache
            self.ratings_cache[card_name] = rating
            
            # Save periodically (every 10 new entries)
            if len(self.ratings_cache) % 10 == 0:
                self._save_csv_cache()
    
    def get_card_rating(self, card_name: str) -> float:
        """Get the rating for a specific card from 17lands with caching."""
        if not card_name:
            return 0.0
        
        # Check CSV cache first
        cached_rating = self._get_cached_rating(card_name)
        if cached_rating is not None:
            return cached_rating
        
        # If not in cache, get from API
        self.logger.debug(f"Fetching 17Lands data for {card_name}")
        card_data = self.seventeen_lands.get_card_data(card_name)
        
        if not card_data:
            self.logger.debug(f"No 17Lands data found for {card_name}")
            # Fall back to manual ratings if available
            manual_rating = self.manual_ratings.get(card_name, 5.0)  # Default to 5.0 if no manual rating
            self.logger.debug(f"Using manual rating for {card_name}: {manual_rating}")
            self._cache_rating(card_name, manual_rating)
            self.fallback_data_used += 1
            self.cards_processed += 1
            return manual_rating
        
        # Calculate combined score from GIH Winrate and IWD
        gih_winrate = card_data.get("game_in_hand_win_rate", 0.0)
        iwd = card_data.get("improvement_when_drawn", 0.0)
        
        # Combine metrics: 70% GIH Winrate + 30% IWD
        combined_score = (gih_winrate * 0.7) + (iwd * 0.3)
        
        # Convert to 0-10 scale for consistency with other evaluators
        rating = combined_score * 10.0
        
        # Cache the result
        self._cache_rating(card_name, rating, gih_winrate, iwd)
        self.api_data_found += 1
        self.cards_processed += 1
        
        return rating
    
    def get_deck_rating(self, card_names: List[str]) -> float:
        """Get the overall rating for a deck from 17lands with caching."""
        if not card_names:
            return 0.0
        
        # Reset counters for this deck evaluation
        initial_api_count = self.api_data_found
        initial_fallback_count = self.fallback_data_used
        
        # Get ratings for all cards (will use cache when available)
        card_ratings = []
        for card_name in card_names:
            rating = self.get_card_rating(card_name)
            card_ratings.append(rating)
        
        if not card_ratings:
            return 0.0
        
        # Calculate statistics for this deck
        deck_api_count = self.api_data_found - initial_api_count
        deck_fallback_count = self.fallback_data_used - initial_fallback_count
        
        # Provide warnings about data sources
        if deck_api_count == 0:
            self.logger.warning(f"⚠️  NO 17Lands API data found for any cards in this deck!")
            print(f"⚠️  WARNING: No 17Lands API data found for any cards in this deck - using manual ratings as fallback")
        elif deck_fallback_count > 0:
            self.logger.warning(f"⚠️  Mixed data sources: {deck_api_count} from API, {deck_fallback_count} from manual ratings")
            print(f"⚠️  WARNING: Mixed data sources - {deck_api_count} cards from 17Lands API, {deck_fallback_count} from manual ratings")
        else:
            self.logger.info(f"✅ All {deck_api_count} cards found in 17Lands API")
            print(f"✅ All {deck_api_count} cards found in 17Lands API data")
        
        # Calculate average rating (scale 0-10)
        average_rating = sum(card_ratings) / len(card_ratings)
        
        # Convert to 0-1 scale for consistency
        return average_rating / 10.0

    def get_api_data_stats(self) -> Dict[str, int]:
        """Get statistics about API data availability."""
        total_cards = self.api_data_found + self.fallback_data_used
        api_percentage = (self.api_data_found / total_cards * 100) if total_cards > 0 else 0
        
        return {
            "total_cards_processed": total_cards,
            "api_data_found": self.api_data_found,
            "fallback_data_used": self.fallback_data_used,
            "api_data_percentage": round(api_percentage, 1)
        }

    def print_api_data_summary(self):
        """Print a summary of API data availability."""
        stats = self.get_api_data_stats()
        print(f"\n=== 17Lands API Data Summary ===")
        print(f"Total cards processed: {stats['total_cards_processed']}")
        print(f"Cards found in 17Lands API: {stats['api_data_found']}")
        print(f"Cards using manual fallback: {stats['fallback_data_used']}")
        print(f"API data coverage: {stats['api_data_percentage']}%")
        
        if stats['api_data_percentage'] < 50:
            print(f"⚠️  WARNING: Low API data coverage ({stats['api_data_percentage']}%) - most ratings are from manual fallback")
        elif stats['api_data_percentage'] < 100:
            print(f"ℹ️  INFO: Partial API data coverage ({stats['api_data_percentage']}%) - some ratings are from manual fallback")
        else:
            print(f"✅ Excellent: 100% API data coverage - all ratings from 17Lands")
    
    def get_available_methods(self) -> List[Dict[str, str]]:
        """Get available evaluation methods."""
        return [{"value": "17lands", "label": "17Lands Data"}]
    
    def evaluate_card(self, card) -> float:
        """Evaluate a card object using 17Lands data with caching."""
        if not card or not hasattr(card, 'name') or not card.name:
            return 0.0
        
        # Use the card name to get 17Lands rating (with caching)
        return self.get_card_rating(card.name)
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics for monitoring."""
        api_stats = self.seventeen_lands.get_cache_stats()
        csv_stats = {
            "csv_cache_entries": len(self.ratings_cache),
            "csv_cache_file": self.csv_cache_file,
        }
        return {**api_stats, **csv_stats}
    
    def clear_cache(self):
        """Clear both API and CSV caches."""
        self.seventeen_lands.clear_cache()
        self.ratings_cache.clear()
        self.ratings_df = pd.DataFrame(columns=["card_name", "rating", "gih_winrate", "iwd"])
        if os.path.exists(self.csv_cache_file):
            os.remove(self.csv_cache_file)
        self.logger.info("Cleared both API and CSV caches")
    
    def optimize_cache(self):
        """Optimize the 17Lands cache."""
        self.seventeen_lands.optimize_cache()
        # Save CSV cache
        self._save_csv_cache()
    
    def get_csv_cache_info(self) -> Dict:
        """Get information about the CSV cache."""
        return {
            "total_entries": len(self.ratings_cache),
            "cache_file": self.csv_cache_file,
            "file_exists": os.path.exists(self.csv_cache_file),
            "file_size": os.path.getsize(self.csv_cache_file) if os.path.exists(self.csv_cache_file) else 0
        } 
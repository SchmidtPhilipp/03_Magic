"""
Deck Evaluation Module

This module provides different methods for evaluating deck quality:
1. 17Lands data-based evaluation (game_in_hand_win_rate + improvement_when_drawn)
2. Manual evaluation with synergy bonuses
3. Interface for selecting evaluation methods
4. Performance optimizations with caching and parallel processing
5. Comprehensive logging system with user and developer modes
"""

import functools
import json
import logging
import logging.handlers
import os
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

# Global logging configuration
_logger_initialized = False
_user_mode = True  # Default to user mode


def setup_logging(user_mode: bool = True, log_dir: str = "logs"):
    """
    Setup comprehensive logging system

    Args:
        user_mode: If True, only user-relevant messages are shown in console
        log_dir: Directory to store log files
    """
    global _logger_initialized, _user_mode
    _user_mode = user_mode

    if _logger_initialized:
        return

    # Create log directory
    os.makedirs(log_dir, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler (user mode: INFO, developer mode: DEBUG)
    console_level = logging.INFO if user_mode else logging.DEBUG
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)

    # User-friendly formatter for console
    if user_mode:
        console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    else:
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler for all logs (DEBUG level)
    all_log_file = os.path.join(log_dir, "all.log")
    file_handler = logging.handlers.RotatingFileHandler(
        all_log_file, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Separate handler for user-relevant logs
    user_log_file = os.path.join(log_dir, "user.log")
    user_handler = logging.handlers.RotatingFileHandler(
        user_log_file, maxBytes=5 * 1024 * 1024, backupCount=3
    )
    user_handler.setLevel(logging.INFO)
    user_handler.setFormatter(file_formatter)

    # Create user logger
    user_logger = logging.getLogger("user")
    user_logger.addHandler(user_handler)
    user_logger.setLevel(logging.INFO)
    user_logger.propagate = False

    # Separate handler for optimization logs
    optimization_log_file = os.path.join(log_dir, "optimization.log")
    optimization_handler = logging.handlers.RotatingFileHandler(
        optimization_log_file, maxBytes=5 * 1024 * 1024, backupCount=3
    )
    optimization_handler.setLevel(logging.DEBUG)
    optimization_handler.setFormatter(file_formatter)

    # Create optimization logger
    optimization_logger = logging.getLogger("optimization")
    optimization_logger.addHandler(optimization_handler)
    optimization_logger.setLevel(logging.DEBUG)
    optimization_logger.propagate = False

    # Separate handler for 17Lands API logs
    api_log_file = os.path.join(log_dir, "17lands_api.log")
    api_handler = logging.handlers.RotatingFileHandler(
        api_log_file, maxBytes=2 * 1024 * 1024, backupCount=2
    )
    api_handler.setLevel(logging.DEBUG)
    api_handler.setFormatter(file_formatter)

    # Create 17Lands API logger
    api_logger = logging.getLogger("17lands_api")
    api_logger.addHandler(api_handler)
    api_logger.setLevel(logging.DEBUG)
    api_logger.propagate = False

    _logger_initialized = True

    # Log initialization
    logger = logging.getLogger(__name__)
    logger.info(f"Logging system initialized (user_mode: {user_mode})")
    logger.info(f"Log files: {log_dir}/")


def get_user_logger():
    """Get logger for user-relevant messages"""
    return logging.getLogger("user")


def get_optimization_logger():
    """Get logger for optimization-specific messages"""
    return logging.getLogger("optimization")


def get_api_logger():
    """Get logger for 17Lands API messages"""
    return logging.getLogger("17lands_api")


# Initialize logging
setup_logging()

logger = logging.getLogger(__name__)
user_logger = get_user_logger()
optimization_logger = get_optimization_logger()
api_logger = get_api_logger()


class SeventeenLandsAPI:
    """17Lands API client with caching and performance optimizations"""

    def __init__(
        self,
        cache_file: str = "data/ratings/17lands_cache.json",
        max_cache_size: int = 10000,
    ):
        self.cache_file = cache_file
        self.cache = {}
        self.cache_lock = threading.Lock()
        self.max_cache_size = max_cache_size

        # Use appropriate loggers FIRST
        self.logger = api_logger
        self.user_logger = user_logger

        self._load_cache()

        # Performance optimization: Batch processing
        self.batch_size = 50
        self.request_delay = 0.1  # Delay between requests to avoid rate limiting

    def _load_cache(self):
        """Load cached 17Lands data with memory management"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r") as f:
                    self.cache = json.load(f)

                # Memory management: Limit cache size
                if len(self.cache) > self.max_cache_size:
                    # Remove oldest entries (simple FIFO)
                    keys_to_remove = list(self.cache.keys())[
                        : len(self.cache) - self.max_cache_size
                    ]
                    for key in keys_to_remove:
                        del self.cache[key]

                self.logger.info(
                    f"Loaded {len(self.cache)} cached 17Lands entries (max: {self.max_cache_size})"
                )
                self.user_logger.info(
                    f"17Lands cache loaded: {len(self.cache)} cards available"
                )
            else:
                self.cache = {}
                self.user_logger.info(
                    "No 17Lands cache found - will fetch data from API"
                )
        except Exception as e:
            self.logger.error(f"Error loading 17Lands cache: {e}")
            self.cache = {}

    def _save_cache(self):
        """Save cached 17Lands data with error handling"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)

            # Create backup of existing cache
            if os.path.exists(self.cache_file):
                backup_file = f"{self.cache_file}.backup"
                shutil.copy2(self.cache_file, backup_file)

            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2)

            self.logger.debug(f"Saved {len(self.cache)} 17Lands entries to cache")
        except Exception as e:
            self.logger.error(f"Error saving 17Lands cache: {e}")

    def get_card_data_batch(
        self, card_names: List[str], format_name: str = "PremierDraft"
    ) -> Dict[str, Dict]:
        """
        Get 17Lands data for multiple cards with batch processing

        Args:
            card_names: List of card names
            format_name: Format name (e.g., "PremierDraft", "QuickDraft")

        Returns:
            Dict mapping card names to their 17Lands data
        """
        if not card_names:
            return {}

        # Check cache first for all cards
        cached_data = {}
        uncached_cards = []

        with self.cache_lock:
            for card_name in card_names:
                cache_key = f"{card_name}_{format_name}"
                if cache_key in self.cache:
                    cached_data[card_name] = self.cache[cache_key]
                else:
                    uncached_cards.append(card_name)

        # Log cache hit rate
        cache_hit_rate = len(cached_data) / len(card_names) * 100
        self.logger.debug(
            f"17Lands cache hit rate: {cache_hit_rate:.1f}% ({len(cached_data)}/{len(card_names)})"
        )

        # Fetch uncached cards in batches
        if uncached_cards:
            self.user_logger.info(
                f"Fetching {len(uncached_cards)} cards from 17Lands API..."
            )
            batch_results = self._fetch_cards_batch(uncached_cards, format_name)
            cached_data.update(batch_results)
            self.user_logger.info(
                f"Successfully fetched {len(batch_results)} cards from 17Lands"
            )

        return cached_data

    def _fetch_cards_batch(
        self, card_names: List[str], format_name: str
    ) -> Dict[str, Dict]:
        """Fetch multiple cards from 17Lands API in batches"""
        results = {}

        # Process cards in batches
        for i in range(0, len(card_names), self.batch_size):
            batch = card_names[i : i + self.batch_size]
            self.logger.debug(
                f"Fetching batch {i//self.batch_size + 1}: {len(batch)} cards"
            )
            batch_results = self._fetch_single_batch(batch, format_name)
            results.update(batch_results)

            # Add delay between batches to avoid rate limiting
            if i + self.batch_size < len(card_names):
                time.sleep(self.request_delay)

        return results

    def _fetch_single_batch(
        self, card_names: List[str], format_name: str
    ) -> Dict[str, Dict]:
        """Fetch a single batch of cards from 17Lands API"""
        try:
            # 17Lands API endpoint for card data
            url = f"https://www.17lands.com/card_ratings/data"
            params = {
                "expansion": "LTR",  # Lord of the Rings set
                "format": format_name,
                "start_date": "2023-06-20",  # Set release date
                "end_date": "2024-12-31",  # Future date to get all data
            }

            self.logger.debug(
                f"Making API request to 17Lands for {len(card_names)} cards"
            )
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                self.logger.debug(f"Received {len(data)} cards from 17Lands API")

                # Create lookup dictionary for faster searching
                data_lookup = {
                    card_data.get("name", "").lower(): card_data for card_data in data
                }

                batch_results = {}
                found_cards = 0
                for card_name in card_names:
                    card_data = data_lookup.get(card_name.lower())
                    if card_data:
                        # Extract relevant metrics
                        result = {
                            "name": card_data.get("name", card_name),
                            "game_in_hand_win_rate": card_data.get(
                                "game_in_hand_win_rate", 0.0
                            ),
                            "improvement_when_drawn": card_data.get(
                                "improvement_when_drawn", 0.0
                            ),
                            "avg_seen": card_data.get("avg_seen", 0.0),
                            "avg_pick": card_data.get("avg_pick", 0.0),
                            "drawn_win_rate": card_data.get("drawn_win_rate", 0.0),
                            "ever_drawn_win_rate": card_data.get(
                                "ever_drawn_win_rate", 0.0
                            ),
                        }
                        batch_results[card_name] = result
                        found_cards += 1
                    else:
                        batch_results[card_name] = {}

                self.logger.debug(
                    f"Found {found_cards}/{len(card_names)} cards in 17Lands data"
                )

                # Cache all results
                with self.cache_lock:
                    for card_name, result in batch_results.items():
                        cache_key = f"{card_name}_{format_name}"
                        self.cache[cache_key] = result

                    # Save cache periodically
                    if len(self.cache) % 100 == 0:  # Save every 100 new entries
                        self._save_cache()

                return batch_results

            else:
                self.logger.warning(
                    f"17Lands API returned status {response.status_code}"
                )
                return {card_name: {} for card_name in card_names}

        except Exception as e:
            self.logger.error(f"Error fetching 17Lands data for batch: {e}")
            return {card_name: {} for card_name in card_names}

    def get_card_data(self, card_name: str, format_name: str = "PremierDraft") -> Dict:
        """
        Get 17Lands data for a single card with caching

        Args:
            card_name: Name of the card
            format_name: Format name (e.g., "PremierDraft", "QuickDraft")

        Returns:
            Dict with 17Lands metrics or empty dict if not found
        """
        # Use batch processing for single card
        batch_results = self.get_card_data_batch([card_name], format_name)
        return batch_results.get(card_name, {})

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        with self.cache_lock:
            return {
                "total_entries": len(self.cache),
                "cache_file": self.cache_file,
                "max_cache_size": self.max_cache_size,
                "cache_utilization": f"{len(self.cache) / self.max_cache_size * 100:.1f}%",
            }

    def clear_cache(self):
        """Clear the cache"""
        with self.cache_lock:
            self.cache.clear()
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
        self.logger.info("17Lands cache cleared")
        self.user_logger.info("17Lands cache cleared")

    def optimize_cache(self):
        """Optimize cache by removing least used entries"""
        with self.cache_lock:
            if len(self.cache) > self.max_cache_size * 0.8:  # If cache is 80% full
                # Simple optimization: remove oldest entries
                keys_to_remove = list(self.cache.keys())[
                    : len(self.cache) // 4
                ]  # Remove 25%
                for key in keys_to_remove:
                    del self.cache[key]
                self.logger.info(
                    f"Cache optimized: removed {len(keys_to_remove)} entries"
                )
                self.user_logger.info(
                    f"17Lands cache optimized: removed {len(keys_to_remove)} entries"
                )
                self._save_cache()


class DeckEvaluator:
    """Main deck evaluator class with multiple evaluation methods and performance optimizations"""

    def __init__(self, ratings_file: str = "data/ratings/card_ratings.csv"):
        """Initialize evaluator with card ratings"""
        # Use appropriate loggers FIRST
        self.logger = logger
        self.user_logger = user_logger
        self.optimization_logger = optimization_logger

        self.ratings_file = ratings_file
        self.ratings_df = None
        self.ratings_dict = {}
        self._load_ratings()

        # Initialize 17Lands API client
        self.seventeen_lands = SeventeenLandsAPI()

        # Performance optimization: Caching
        self._synergy_cache = {}
        self._evaluation_cache = {}
        self._cache_lock = threading.Lock()

        # Performance optimization: Thread pool for parallel processing
        self._thread_pool = ThreadPoolExecutor(max_workers=4)

        self.logger.info(
            "DeckEvaluator initialized with 17Lands API and performance optimizations"
        )
        self.user_logger.info(
            "Deck evaluator ready - supports manual and 17Lands evaluation methods"
        )

    def _load_ratings(self):
        """Load card ratings from file"""
        try:
            self.ratings_df = pd.read_csv(self.ratings_file)

            # Convert ratings to numeric for easier comparison
            self.ratings_df["Rating_Value"] = (
                self.ratings_df["Rating"].str.split("/").str[0].astype(int)
            )

            # Create a dictionary for quick rating lookup
            self.ratings_dict = dict(
                zip(self.ratings_df["Card Name"], self.ratings_df["Rating_Value"])
            )

            self.logger.info(f"Loaded {len(self.ratings_df)} rated cards")
            self.user_logger.info(
                f"Loaded {len(self.ratings_df)} cards with manual ratings"
            )

        except Exception as e:
            self.logger.error(f"Error loading ratings file: {e}")
            self.user_logger.error(f"Failed to load card ratings: {e}")
            self.ratings_df = pd.DataFrame()
            self.ratings_dict = {}

    def clear_caches(self):
        """Clear all caches to free memory"""
        with self._cache_lock:
            self._synergy_cache.clear()
            self._evaluation_cache.clear()
        self.seventeen_lands.clear_cache()
        self.logger.info("All caches cleared")
        self.user_logger.info("All evaluation caches cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for monitoring"""
        with self._cache_lock:
            stats = {
                "synergy_cache_size": len(self._synergy_cache),
                "evaluation_cache_size": len(self._evaluation_cache),
            }
        # Add 17Lands cache stats
        stats.update(self.seventeen_lands.get_cache_stats())
        return stats

    def evaluate_deck(self, decklist: List[str], method: str = "manual") -> float:
        """
        Main evaluation interface with caching

        Args:
            decklist: List of card names in the deck
            method: Evaluation method ("17lands" or "manual")

        Returns:
            float: Deck score (0.0 to 1.0)
        """
        # Create cache key
        cache_key = (tuple(sorted(decklist)), method)

        # Check cache first
        with self._cache_lock:
            if cache_key in self._evaluation_cache:
                self.logger.debug(
                    f"Cache hit for deck evaluation: {len(decklist)} cards"
                )
                return self._evaluation_cache[cache_key]

        # Log evaluation start
        self.user_logger.info(
            f"Evaluating deck with {len(decklist)} cards using {method} method"
        )
        self.optimization_logger.debug(
            f"Starting deck evaluation: {method} method, {len(decklist)} cards"
        )

        # Calculate evaluation
        if method == "17lands":
            result = self.evaluate_deck_17lands(decklist)
        elif method == "manual":
            result = self.evaluate_deck_manual(decklist)
        else:
            self.logger.warning(f"Unknown evaluation method: {method}. Using manual.")
            self.user_logger.warning(
                f"Unknown evaluation method '{method}', using manual evaluation"
            )
            result = self.evaluate_deck_manual(decklist)

        # Cache result
        with self._cache_lock:
            self._evaluation_cache[cache_key] = result

        # Log evaluation result
        score_percentage = result * 100
        self.user_logger.info(
            f"Deck evaluation complete: {score_percentage:.1f}% score"
        )
        self.optimization_logger.debug(
            f"Evaluation result: {result:.4f} ({method} method)"
        )

        return result

    def evaluate_deck_17lands(self, decklist: List[str]) -> float:
        """
        Evaluate deck using real 17Lands data with performance optimizations

        Uses game_in_hand_win_rate and improvement_when_drawn from 17Lands API.

        Args:
            decklist: List of card names in the deck

        Returns:
            float: Deck score (0.0 to 1.0)
        """
        if not decklist:
            return 0.0

        # Use parallel processing for large decks
        if len(decklist) > 20:
            return self._evaluate_deck_17lands_parallel(decklist)

        # Get 17Lands data for all cards in batch
        card_metrics = self._get_17lands_metrics_batch(decklist)

        if not card_metrics:
            return 0.0

        # Calculate average score
        avg_score = sum(card_metrics) / len(card_metrics)

        # Normalize to 0-1 scale
        return max(0.0, min(1.0, avg_score))

    def _get_17lands_metrics_batch(self, decklist: List[str]) -> List[float]:
        """Get 17Lands metrics for multiple cards using batch processing"""
        # Get all card data in one batch request
        all_card_data = self.seventeen_lands.get_card_data_batch(decklist)

        card_metrics = []
        for card_name in decklist:
            metrics = all_card_data.get(card_name, {})
            if metrics:
                # Calculate combined score from GIH Winrate and IWD
                gih_winrate = metrics.get("game_in_hand_win_rate", 0.0)
                iwd = metrics.get("improvement_when_drawn", 0.0)

                # Combine metrics: 70% GIH Winrate + 30% IWD
                combined_score = (gih_winrate * 0.7) + (iwd * 0.3)
                card_metrics.append(combined_score)
            else:
                # Fallback to manual rating if no 17Lands data
                manual_rating = self.ratings_dict.get(card_name, 5)
                card_metrics.append(manual_rating / 10.0)

        return card_metrics

    def _evaluate_deck_17lands_parallel(self, decklist: List[str]) -> float:
        """Parallel version of 17Lands evaluation for large decks"""
        # Split deck into chunks for parallel processing
        chunk_size = max(1, len(decklist) // 4)
        chunks = [
            decklist[i : i + chunk_size] for i in range(0, len(decklist), chunk_size)
        ]

        # Process chunks in parallel
        futures = []
        for chunk in chunks:
            future = self._thread_pool.submit(self._evaluate_chunk_17lands, chunk)
            futures.append(future)

        # Collect results
        chunk_scores = []
        for future in as_completed(futures):
            try:
                chunk_scores.append(future.result())
            except Exception as e:
                logger.error(f"Error in parallel evaluation: {e}")
                chunk_scores.append(0.0)

        # Combine chunk scores
        if chunk_scores:
            return sum(chunk_scores) / len(chunk_scores)
        return 0.0

    def _evaluate_chunk_17lands(self, chunk: List[str]) -> float:
        """Evaluate a chunk of cards for parallel processing"""
        if not chunk:
            return 0.0

        # Get metrics for this chunk
        card_metrics = self._get_17lands_metrics_batch(chunk)

        if not card_metrics:
            return 0.0

        avg_score = sum(card_metrics) / len(card_metrics)
        return max(0.0, min(1.0, avg_score))

    def evaluate_deck_manual(self, decklist: List[str]) -> float:
        """
        Evaluate deck using manual ratings and synergy bonuses with performance optimizations

        Args:
            decklist: List of card names in the deck

        Returns:
            float: Deck score (0.0 to 1.0)
        """
        if not decklist:
            return 0.0

        # Use parallel processing for large decks
        if len(decklist) > 30:
            return self._evaluate_deck_manual_parallel(decklist)

        # Get base ratings
        ratings = []
        for card_name in decklist:
            rating = self.ratings_dict.get(card_name, 0)
            ratings.append(rating)

        if not ratings:
            return 0.0

        # Calculate base score from ratings
        avg_rating = sum(ratings) / len(ratings)
        base_score = avg_rating / 10.0

        # Calculate synergy bonus with caching
        synergy_bonus = self._calculate_synergy_bonus(decklist)

        # Calculate dynamic synergy bonus based on deck composition
        dynamic_bonus = self._calculate_dynamic_synergy_bonus(decklist)

        # Combine base score with synergy bonuses
        total_score = base_score + synergy_bonus + dynamic_bonus

        return max(0.0, min(1.0, total_score))

    def _evaluate_deck_manual_parallel(self, decklist: List[str]) -> float:
        """Parallel version of manual evaluation for large decks"""
        # Split deck into chunks
        chunk_size = max(1, len(decklist) // 4)
        chunks = [
            decklist[i : i + chunk_size] for i in range(0, len(decklist), chunk_size)
        ]

        # Process chunks in parallel
        futures = []
        for chunk in chunks:
            future = self._thread_pool.submit(self._evaluate_chunk_manual, chunk)
            futures.append(future)

        # Collect results
        chunk_scores = []
        for future in as_completed(futures):
            try:
                chunk_scores.append(future.result())
            except Exception as e:
                logger.error(f"Error in parallel manual evaluation: {e}")
                chunk_scores.append(0.0)

        # Combine chunk scores
        if chunk_scores:
            return sum(chunk_scores) / len(chunk_scores)
        return 0.0

    def _evaluate_chunk_manual(self, chunk: List[str]) -> float:
        """Evaluate a chunk of cards for parallel processing"""
        if not chunk:
            return 0.0

        ratings = [self.ratings_dict.get(card_name, 0) for card_name in chunk]
        if not ratings:
            return 0.0

        avg_rating = sum(ratings) / len(ratings)
        base_score = avg_rating / 10.0

        # Calculate synergy bonus for this chunk
        synergy_bonus = self._calculate_synergy_bonus(chunk)

        # Calculate dynamic synergy bonus for this chunk
        dynamic_bonus = self._calculate_dynamic_synergy_bonus(chunk)

        return max(0.0, min(1.0, base_score + synergy_bonus + dynamic_bonus))

    def _calculate_synergy_bonus(self, decklist: List[str]) -> float:
        """
        Calculate synergy bonus for the entire deck with enhanced caching

        Args:
            decklist: List of card names in the deck

        Returns:
            float: Synergy bonus score (0.0 to 1.0)
        """
        if len(decklist) < 2:
            return 0.0

        # Create cache key for the entire deck
        cache_key = tuple(sorted(decklist))

        # Check cache first
        with self._cache_lock:
            if cache_key in self._synergy_cache:
                logger.debug(
                    f"Cache hit for synergy calculation: {len(decklist)} cards"
                )
                return self._synergy_cache[cache_key]

        # Calculate synergy using parallel processing for large decks
        if len(decklist) > 15:
            synergy_score = self._calculate_synergy_parallel(decklist)
        else:
            synergy_score = self._calculate_synergy_sequential(decklist)

        # Cache result
        with self._cache_lock:
            self._synergy_cache[cache_key] = synergy_score

        return synergy_score

    def _calculate_synergy_parallel(self, decklist: List[str]) -> float:
        """Calculate synergy using parallel processing for large decks"""
        # Split deck into chunks for parallel processing
        chunk_size = max(1, len(decklist) // 4)
        chunks = [
            decklist[i : i + chunk_size] for i in range(0, len(decklist), chunk_size)
        ]

        # Process chunks in parallel
        futures = []
        for chunk in chunks:
            future = self._thread_pool.submit(
                self._calculate_chunk_synergy, chunk, decklist
            )
            futures.append(future)

        # Collect results
        chunk_scores = []
        for future in as_completed(futures):
            try:
                chunk_scores.append(future.result())
            except Exception as e:
                logger.error(f"Error in parallel synergy calculation: {e}")
                chunk_scores.append(0.0)

        # Combine chunk scores
        if chunk_scores:
            return sum(chunk_scores) / len(chunk_scores)
        return 0.0

    def _calculate_chunk_synergy(
        self, chunk: List[str], full_decklist: List[str]
    ) -> float:
        """Calculate synergy for a chunk of cards against the full deck"""
        if not chunk:
            return 0.0

        total_synergy = 0.0
        pair_count = 0

        for card1 in chunk:
            for card2 in full_decklist:
                if card1 != card2:
                    synergy = self._calculate_card_synergy(card1, card2)
                    total_synergy += synergy
                    pair_count += 1

        return total_synergy / pair_count if pair_count > 0 else 0.0

    def _calculate_synergy_sequential(self, decklist: List[str]) -> float:
        """Calculate synergy using sequential processing for smaller decks"""
        total_synergy = 0.0
        pair_count = 0

        for i, card1 in enumerate(decklist):
            for j, card2 in enumerate(decklist[i + 1 :], i + 1):
                synergy = self._calculate_card_synergy(card1, card2)
                total_synergy += synergy
                pair_count += 1

        return total_synergy / pair_count if pair_count > 0 else 0.0

    def _calculate_card_synergy(self, card1: str, card2: str) -> float:
        """
        Calculate synergy between two specific cards with caching and enhanced patterns

        Args:
            card1: First card name
            card2: Second card name

        Returns:
            float: Synergy score (0.0 to 1.0)
        """
        # Create cache key for card pair
        cache_key = tuple(sorted([card1, card2]))

        # Check cache first
        with self._cache_lock:
            if cache_key in self._synergy_cache:
                return self._synergy_cache[cache_key]

        # Enhanced synergy patterns with more comprehensive coverage
        synergy_patterns = {
            # Equipment + Creatures
            ("Lightning Greaves", "Sol Ring"): 0.8,
            ("Lightning Greaves", "Dark Confidant"): 0.7,
            ("Skullclamp", "Dark Confidant"): 0.9,
            ("Umezawa's Jitte", "Goblin Guide"): 0.8,
            ("Sword of Fire and Ice", "Dark Confidant"): 0.8,
            ("Batterskull", "Primeval Titan"): 0.7,
            # Counterspell + Card draw
            ("Counterspell", "Dark Confidant"): 0.6,
            ("Mana Leak", "Dark Confidant"): 0.6,
            ("Remand", "Dark Confidant"): 0.5,
            ("Force of Will", "Brainstorm"): 0.7,
            ("Daze", "Ponder"): 0.5,
            # Removal + Aggro
            ("Lightning Bolt", "Goblin Guide"): 0.5,
            ("Path to Exile", "Goblin Guide"): 0.5,
            ("Swords to Plowshares", "Goblin Guide"): 0.5,
            ("Terminate", "Goblin Guide"): 0.5,
            ("Fatal Push", "Dark Confidant"): 0.4,
            # Ramp + Big spells
            ("Sol Ring", "Primeval Titan"): 0.7,
            ("Farseek", "Primeval Titan"): 0.6,
            ("Rampant Growth", "Primeval Titan"): 0.6,
            ("Cultivate", "Primeval Titan"): 0.6,
            ("Kodama's Reach", "Primeval Titan"): 0.6,
            # Tribal synergies
            ("Goblin Chieftain", "Goblin Guide"): 0.8,
            ("Goblin Warchief", "Goblin Guide"): 0.7,
            ("Goblin King", "Goblin Guide"): 0.6,
            ("Goblin Matron", "Goblin Guide"): 0.5,
            ("Goblin Lackey", "Goblin Guide"): 0.6,
            # Elf tribal
            ("Elvish Archdruid", "Llanowar Elves"): 0.8,
            ("Elvish Champion", "Llanowar Elves"): 0.7,
            ("Ezuri, Renegade Leader", "Llanowar Elves"): 0.8,
            ("Imperious Perfect", "Llanowar Elves"): 0.7,
            # Merfolk tribal
            ("Lord of Atlantis", "Silvergill Adept"): 0.8,
            ("Master of the Pearl Trident", "Silvergill Adept"): 0.8,
            ("Merrow Reejerey", "Silvergill Adept"): 0.7,
            # Zombie tribal
            ("Zombie Master", "Gravecrawler"): 0.8,
            ("Undead Warchief", "Gravecrawler"): 0.7,
            ("Lord of the Undead", "Gravecrawler"): 0.7,
            # Artifact synergies
            ("Arcbound Ravager", "Cranial Plating"): 0.9,
            ("Arcbound Worker", "Cranial Plating"): 0.7,
            ("Arcbound Stinger", "Cranial Plating"): 0.7,
            ("Steel Overseer", "Arcbound Ravager"): 0.8,
            # Enchantment synergies
            ("Enchantress's Presence", "Utopia Sprawl"): 0.6,
            ("Argothian Enchantress", "Utopia Sprawl"): 0.7,
            ("Sterling Grove", "Utopia Sprawl"): 0.5,
            # Land synergies
            ("Crop Rotation", "Gaea's Cradle"): 0.8,
            ("Crop Rotation", "Dark Depths"): 0.7,
            ("Knight of the Reliquary", "Gaea's Cradle"): 0.7,
            ("Knight of the Reliquary", "Dark Depths"): 0.6,
            # Combo pieces
            ("Splinter Twin", "Deceiver Exarch"): 0.9,
            ("Splinter Twin", "Pestermite"): 0.9,
            ("Kiki-Jiki, Mirror Breaker", "Deceiver Exarch"): 0.9,
            ("Kiki-Jiki, Mirror Breaker", "Pestermite"): 0.9,
            # Storm synergies
            ("Grapeshot", "Desperate Ritual"): 0.8,
            ("Grapeshot", "Pyretic Ritual"): 0.8,
            ("Grapeshot", "Manamorphose"): 0.7,
            ("Tendrils of Agony", "Desperate Ritual"): 0.8,
            # Reanimator synergies
            ("Entomb", "Griselbrand"): 0.9,
            ("Entomb", "Iona, Shield of Emeria"): 0.8,
            ("Reanimate", "Griselbrand"): 0.9,
            ("Reanimate", "Iona, Shield of Emeria"): 0.8,
            # Delver synergies
            ("Delver of Secrets", "Ponder"): 0.7,
            ("Delver of Secrets", "Brainstorm"): 0.7,
            ("Delver of Secrets", "Preordain"): 0.6,
            # Burn synergies
            ("Goblin Guide", "Lightning Bolt"): 0.5,
            ("Goblin Guide", "Lava Spike"): 0.5,
            ("Eidolon of the Great Revel", "Lightning Bolt"): 0.6,
            ("Eidolon of the Great Revel", "Lava Spike"): 0.6,
        }

        # Check for exact matches
        pair = (card1, card2)
        reverse_pair = (card2, card1)

        if pair in synergy_patterns:
            result = synergy_patterns[pair]
        elif reverse_pair in synergy_patterns:
            result = synergy_patterns[reverse_pair]
        else:
            # Enhanced partial matching with more patterns
            card1_lower = card1.lower()
            card2_lower = card2.lower()

            # Equipment synergy patterns
            if any(
                word in card1_lower
                for word in [
                    "greaves",
                    "boots",
                    "clamp",
                    "jitte",
                    "sword",
                    "batterskull",
                ]
            ) and any(
                word in card2_lower
                for word in ["creature", "goblin", "confidant", "titan", "guide"]
            ):
                result = 0.4
            elif any(
                word in card2_lower
                for word in [
                    "greaves",
                    "boots",
                    "clamp",
                    "jitte",
                    "sword",
                    "batterskull",
                ]
            ) and any(
                word in card1_lower
                for word in ["creature", "goblin", "confidant", "titan", "guide"]
            ):
                result = 0.4

            # Counterspell synergy patterns
            elif any(
                word in card1_lower
                for word in ["counterspell", "leak", "remand", "force", "daze"]
            ) and any(
                word in card2_lower
                for word in ["confidant", "draw", "card", "brainstorm", "ponder"]
            ):
                result = 0.3
            elif any(
                word in card2_lower
                for word in ["counterspell", "leak", "remand", "force", "daze"]
            ) and any(
                word in card1_lower
                for word in ["confidant", "draw", "card", "brainstorm", "ponder"]
            ):
                result = 0.3

            # Removal synergy patterns
            elif any(
                word in card1_lower
                for word in ["bolt", "path", "swords", "terminate", "push"]
            ) and any(
                word in card2_lower
                for word in ["goblin", "guide", "creature", "confidant"]
            ):
                result = 0.3
            elif any(
                word in card2_lower
                for word in ["bolt", "path", "swords", "terminate", "push"]
            ) and any(
                word in card1_lower
                for word in ["goblin", "guide", "creature", "confidant"]
            ):
                result = 0.3

            # Ramp synergy patterns
            elif any(
                word in card1_lower
                for word in ["sol ring", "farseek", "rampant", "cultivate", "kodama"]
            ) and any(
                word in card2_lower for word in ["titan", "big", "expensive", "cost"]
            ):
                result = 0.4
            elif any(
                word in card2_lower
                for word in ["sol ring", "farseek", "rampant", "cultivate", "kodama"]
            ) and any(
                word in card1_lower for word in ["titan", "big", "expensive", "cost"]
            ):
                result = 0.4

            # Tribal synergy patterns
            elif any(
                word in card1_lower
                for word in ["goblin", "chieftain", "warchief", "king", "matron"]
            ) and any(word in card2_lower for word in ["goblin", "guide", "lackey"]):
                result = 0.5
            elif any(
                word in card2_lower
                for word in ["goblin", "chieftain", "warchief", "king", "matron"]
            ) and any(word in card1_lower for word in ["goblin", "guide", "lackey"]):
                result = 0.5

            # Elf tribal patterns
            elif any(
                word in card1_lower
                for word in ["elf", "archdruid", "champion", "ezuri", "perfect"]
            ) and any(word in card2_lower for word in ["elf", "llanowar", "elvish"]):
                result = 0.5
            elif any(
                word in card2_lower
                for word in ["elf", "archdruid", "champion", "ezuri", "perfect"]
            ) and any(word in card1_lower for word in ["elf", "llanowar", "elvish"]):
                result = 0.5

            # Merfolk tribal patterns
            elif any(
                word in card1_lower
                for word in ["merfolk", "lord", "master", "reejerey"]
            ) and any(
                word in card2_lower for word in ["merfolk", "silvergill", "adept"]
            ):
                result = 0.5
            elif any(
                word in card2_lower
                for word in ["merfolk", "lord", "master", "reejerey"]
            ) and any(
                word in card1_lower for word in ["merfolk", "silvergill", "adept"]
            ):
                result = 0.5

            # Zombie tribal patterns
            elif any(
                word in card1_lower
                for word in ["zombie", "master", "warchief", "undead"]
            ) and any(
                word in card2_lower for word in ["zombie", "gravecrawler", "undead"]
            ):
                result = 0.5
            elif any(
                word in card2_lower
                for word in ["zombie", "master", "warchief", "undead"]
            ) and any(
                word in card1_lower for word in ["zombie", "gravecrawler", "undead"]
            ):
                result = 0.5

            # Artifact synergy patterns
            elif any(
                word in card1_lower
                for word in ["arcbound", "ravager", "worker", "stinger"]
            ) and any(
                word in card2_lower for word in ["cranial", "plating", "artifact"]
            ):
                result = 0.5
            elif any(
                word in card2_lower
                for word in ["arcbound", "ravager", "worker", "stinger"]
            ) and any(
                word in card1_lower for word in ["cranial", "plating", "artifact"]
            ):
                result = 0.5

            # Enchantment synergy patterns
            elif any(
                word in card1_lower for word in ["enchantress", "presence", "argothian"]
            ) and any(
                word in card2_lower for word in ["enchantment", "utopia", "sprawl"]
            ):
                result = 0.4
            elif any(
                word in card2_lower for word in ["enchantress", "presence", "argothian"]
            ) and any(
                word in card1_lower for word in ["enchantment", "utopia", "sprawl"]
            ):
                result = 0.4

            # Land synergy patterns
            elif any(
                word in card1_lower
                for word in ["crop", "rotation", "knight", "reliquary"]
            ) and any(
                word in card2_lower for word in ["gaea", "cradle", "dark", "depths"]
            ):
                result = 0.4
            elif any(
                word in card2_lower
                for word in ["crop", "rotation", "knight", "reliquary"]
            ) and any(
                word in card1_lower for word in ["gaea", "cradle", "dark", "depths"]
            ):
                result = 0.4

            # Combo synergy patterns
            elif any(
                word in card1_lower for word in ["splinter", "twin", "kiki", "mirror"]
            ) and any(
                word in card2_lower for word in ["deceiver", "exarch", "pestermite"]
            ):
                result = 0.6
            elif any(
                word in card2_lower for word in ["splinter", "twin", "kiki", "mirror"]
            ) and any(
                word in card1_lower for word in ["deceiver", "exarch", "pestermite"]
            ):
                result = 0.6

            # Storm synergy patterns
            elif any(
                word in card1_lower for word in ["grapeshot", "tendrils", "agony"]
            ) and any(
                word in card2_lower
                for word in ["desperate", "ritual", "pyretic", "manamorphose"]
            ):
                result = 0.5
            elif any(
                word in card2_lower for word in ["grapeshot", "tendrils", "agony"]
            ) and any(
                word in card1_lower
                for word in ["desperate", "ritual", "pyretic", "manamorphose"]
            ):
                result = 0.5

            # Reanimator synergy patterns
            elif any(word in card1_lower for word in ["entomb", "reanimate"]) and any(
                word in card2_lower
                for word in ["griselbrand", "iona", "shield", "emeria"]
            ):
                result = 0.6
            elif any(word in card2_lower for word in ["entomb", "reanimate"]) and any(
                word in card1_lower
                for word in ["griselbrand", "iona", "shield", "emeria"]
            ):
                result = 0.6

            # Delver synergy patterns
            elif any(word in card1_lower for word in ["delver", "secrets"]) and any(
                word in card2_lower for word in ["ponder", "brainstorm", "preordain"]
            ):
                result = 0.4
            elif any(word in card2_lower for word in ["delver", "secrets"]) and any(
                word in card1_lower for word in ["ponder", "brainstorm", "preordain"]
            ):
                result = 0.4

            # Burn synergy patterns
            elif any(
                word in card1_lower for word in ["goblin", "guide", "eidolon", "revel"]
            ) and any(
                word in card2_lower for word in ["lightning", "bolt", "lava", "spike"]
            ):
                result = 0.3
            elif any(
                word in card2_lower for word in ["goblin", "guide", "eidolon", "revel"]
            ) and any(
                word in card1_lower for word in ["lightning", "bolt", "lava", "spike"]
            ):
                result = 0.3

            else:
                result = 0.0

        # Cache result
        with self._cache_lock:
            self._synergy_cache[cache_key] = result

        return result

    def _calculate_dynamic_synergy_bonus(self, decklist: List[str]) -> float:
        """
        Calculate dynamic synergy bonus based on deck context and composition

        Args:
            decklist: List of card names in the deck

        Returns:
            float: Dynamic synergy bonus (0.0 to 0.3)
        """
        if len(decklist) < 3:
            return 0.0

        # Analyze deck composition
        deck_analysis = self._analyze_deck_composition(decklist)

        # Calculate bonuses based on deck archetype
        bonuses = []

        # Tribal deck bonus
        if deck_analysis["tribal_count"] >= 8:
            tribal_bonus = min(0.2, deck_analysis["tribal_count"] * 0.02)
            bonuses.append(tribal_bonus)

        # Combo deck bonus
        if deck_analysis["combo_pieces"] >= 4:
            combo_bonus = min(0.15, deck_analysis["combo_pieces"] * 0.03)
            bonuses.append(combo_bonus)

        # Control deck bonus
        if deck_analysis["control_elements"] >= 6:
            control_bonus = min(0.1, deck_analysis["control_elements"] * 0.015)
            bonuses.append(control_bonus)

        # Aggro deck bonus
        if deck_analysis["aggro_elements"] >= 8:
            aggro_bonus = min(0.1, deck_analysis["aggro_elements"] * 0.012)
            bonuses.append(aggro_bonus)

        # Ramp deck bonus
        if deck_analysis["ramp_elements"] >= 4:
            ramp_bonus = min(0.1, deck_analysis["ramp_elements"] * 0.02)
            bonuses.append(ramp_bonus)

        # Synergy density bonus
        synergy_density = deck_analysis["synergy_pairs"] / max(1, len(decklist))
        if synergy_density > 0.3:
            density_bonus = min(0.1, synergy_density * 0.2)
            bonuses.append(density_bonus)

        return min(0.3, sum(bonuses))

    def _analyze_deck_composition(self, decklist: List[str]) -> Dict[str, int]:
        """
        Analyze deck composition for dynamic synergy calculation

        Args:
            decklist: List of card names in the deck

        Returns:
            Dictionary with composition analysis
        """
        analysis = {
            "tribal_count": 0,
            "combo_pieces": 0,
            "control_elements": 0,
            "aggro_elements": 0,
            "ramp_elements": 0,
            "synergy_pairs": 0,
        }

        # Count tribal cards
        tribal_keywords = [
            "goblin",
            "elf",
            "merfolk",
            "zombie",
            "human",
            "dragon",
            "angel",
            "demon",
        ]
        for card in decklist:
            card_lower = card.lower()
            if any(tribe in card_lower for tribe in tribal_keywords):
                analysis["tribal_count"] += 1

        # Count combo pieces
        combo_keywords = [
            "splinter",
            "twin",
            "kiki",
            "grapeshot",
            "tendrils",
            "entomb",
            "reanimate",
        ]
        for card in decklist:
            card_lower = card.lower()
            if any(combo in card_lower for combo in combo_keywords):
                analysis["combo_pieces"] += 1

        # Count control elements
        control_keywords = [
            "counterspell",
            "leak",
            "remand",
            "force",
            "daze",
            "path",
            "swords",
            "terminate",
        ]
        for card in decklist:
            card_lower = card.lower()
            if any(control in card_lower for control in control_keywords):
                analysis["control_elements"] += 1

        # Count aggro elements
        aggro_keywords = ["goblin", "guide", "lackey", "creature", "hasty", "haste"]
        for card in decklist:
            card_lower = card.lower()
            if any(aggro in card_lower for aggro in aggro_keywords):
                analysis["aggro_elements"] += 1

        # Count ramp elements
        ramp_keywords = [
            "sol ring",
            "farseek",
            "rampant",
            "cultivate",
            "kodama",
            "mana",
            "ramp",
        ]
        for card in decklist:
            card_lower = card.lower()
            if any(ramp in card_lower for ramp in ramp_keywords):
                analysis["ramp_elements"] += 1

        # Count synergy pairs
        for i, card1 in enumerate(decklist):
            for j, card2 in enumerate(decklist[i + 1 :], i + 1):
                if self._calculate_card_synergy(card1, card2) > 0.0:
                    analysis["synergy_pairs"] += 1

        return analysis

    def get_evaluation_methods(self) -> List[Dict[str, str]]:
        """
        Get available evaluation methods for UI dropdown

        Returns:
            List of dictionaries with method info
        """
        return [
            {
                "value": "17lands",
                "label": "17Lands Data-Based",
                "description": "Data-based evaluation from 17Lands – combines GIH Winrate and IWD.",
            },
            {
                "value": "manual",
                "label": "Manual + Synergy",
                "description": "Manual evaluation + synergy values from local dictionary.",
            },
        ]

    def get_deck_analysis(self, decklist: List[str], method: str = "manual") -> Dict:
        """
        Get detailed deck analysis with performance optimizations

        Args:
            decklist: List of card names in the deck
            method: Evaluation method

        Returns:
            Dictionary with analysis results
        """
        if not decklist:
            return {
                "score": 0.0,
                "method": method,
                "card_count": 0,
                "avg_rating": 0.0,
                "synergy_bonus": 0.0,
                "analysis": {},
                "performance": self.get_cache_stats(),
            }

        # Get ratings for cards
        ratings = []
        for card_name in decklist:
            rating = self.ratings_dict.get(card_name, 0)
            ratings.append(rating)

        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

        # Calculate synergy bonus
        synergy_bonus = self._calculate_synergy_bonus(decklist)

        # Get overall score
        score = self.evaluate_deck(decklist, method)

        return {
            "score": score,
            "method": method,
            "card_count": len(decklist),
            "avg_rating": avg_rating,
            "synergy_bonus": synergy_bonus,
            "analysis": {
                "highest_rated": max(ratings) if ratings else 0,
                "lowest_rated": min(ratings) if ratings else 0,
                "rating_distribution": self._get_rating_distribution(ratings),
            },
            "performance": self.get_cache_stats(),
        }

    def _get_rating_distribution(self, ratings: List[int]) -> Dict[str, int]:
        """Get distribution of ratings"""
        distribution = {
            "excellent": 0,  # 9-10
            "good": 0,  # 7-8
            "average": 0,  # 5-6
            "poor": 0,  # 3-4
            "bad": 0,  # 1-2
        }

        for rating in ratings:
            if rating >= 9:
                distribution["excellent"] += 1
            elif rating >= 7:
                distribution["good"] += 1
            elif rating >= 5:
                distribution["average"] += 1
            elif rating >= 3:
                distribution["poor"] += 1
            else:
                distribution["bad"] += 1

        return distribution

    def __del__(self):
        """Cleanup thread pool on deletion"""
        if hasattr(self, "_thread_pool"):
            self._thread_pool.shutdown(wait=True)

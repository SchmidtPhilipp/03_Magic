#!/usr/bin/env python3
"""
Text file parser for Magic: The Gathering deck lists
Supports formats like: "1 Knight Luminary (EOE) 23"
"""

import re
import pandas as pd
from typing import List, Dict, Tuple


class TextFileParser:
    """Parser for text-based deck lists and collections"""
    
    def __init__(self):
        # Regex pattern to match: "1 Knight Luminary (EOE) 23"
        # Captures: quantity, card name, set code, collector number
        self.pattern = re.compile(r'^(\d+)\s+(.+?)\s+\(([A-Z]+)\)\s+(\d+)$')
    
    def parse_line(self, line: str) -> Tuple[int, str, str, int]:
        """
        Parse a single line of text format
        
        Args:
            line: Text line like "1 Knight Luminary (EOE) 23"
            
        Returns:
            Tuple of (quantity, card_name, set_code, collector_number)
        """
        line = line.strip()
        if not line or line.startswith('#'):
            return None
            
        match = self.pattern.match(line)
        if match:
            quantity = int(match.group(1))
            card_name = match.group(2).strip()
            set_code = match.group(3)
            collector_number = int(match.group(4))
            return (quantity, card_name, set_code, collector_number)
        
        return None
    
    def parse_text_file(self, filepath: str) -> pd.DataFrame:
        """
        Parse a text file and convert to DataFrame format
        
        Args:
            filepath: Path to the text file
            
        Returns:
            DataFrame with columns: name, quantity, set_code, collector_number
        """
        cards = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    parsed = self.parse_line(line)
                    if parsed:
                        quantity, card_name, set_code, collector_number = parsed
                        cards.append({
                            'Name': card_name,
                            'quantity': quantity,
                            'set_code': set_code,
                            'collector_number': collector_number
                        })
                    else:
                        # Skip empty lines and comments
                        if line.strip() and not line.strip().startswith('#'):
                            print(f"Warning: Could not parse line {line_num}: {line.strip()}")
        
        except Exception as e:
            print(f"Error reading text file {filepath}: {e}")
            return pd.DataFrame()
        
        if not cards:
            print(f"No valid cards found in {filepath}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(cards)
        
        # For compatibility with existing system, we need to expand quantities
        # and add default values for missing columns
        expanded_cards = []
        for _, row in df.iterrows():
            for _ in range(row['quantity']):
                expanded_cards.append({
                    'Name': row['Name'],
                    'rating': 5.0,  # Default rating
                    'colors': '',   # Will be filled by card validation
                    'cmc': 0,       # Will be filled by card validation
                    'type': '',     # Will be filled by card validation
                    'set_code': row['set_code'],
                    'collector_number': row['collector_number']
                })
        
        result_df = pd.DataFrame(expanded_cards)
        print(f"Parsed {len(result_df)} cards from text file")
        return result_df
    
    def validate_text_format(self, filepath: str) -> bool:
        """
        Check if a text file is in the expected format
        
        Args:
            filepath: Path to the text file
            
        Returns:
            True if file appears to be in correct format
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                # Check first few non-empty lines
                for line in file:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if self.pattern.match(line):
                            return True
                        else:
                            # If first non-empty line doesn't match, it's probably not our format
                            return False
            return False
        except Exception:
            return False 
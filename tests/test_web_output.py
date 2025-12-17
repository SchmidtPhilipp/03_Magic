#!/usr/bin/env python3
"""
Test to verify web output capture is working
"""

import sys
import os
import pandas as pd
import threading
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from magic_optimizer.deck_builder import EnhancedDeckBuilder

def test_web_output_capture():
    """Test that the deck builder output is captured properly"""
    print("🧪 Testing Web Output Capture")
    print("=" * 50)
    
    # Load test collection
    collection_df = pd.read_csv("data/collections/FinalFantasy.csv")
    print(f"Loaded {len(collection_df)} cards from collection")
    
    # Create deck builder
    deck_builder = EnhancedDeckBuilder()
    
    print("\n🔄 Testing Genetic Algorithm Output...")
    print("This should show detailed generation-by-generation output:")
    print("-" * 60)
    
    # Run genetic algorithm with small parameters for quick testing
    result = deck_builder.build_optimal_deck_advanced(
        collection_df=collection_df,
        num_colors=2,
        total_deck_size=30,  # Smaller deck for faster testing
        num_lands=10,
        algorithm="genetic",
        optimization_criterion="manual",
        lambda_penalty=1.0,
        fixed_colors=None,
    )
    
    print(f"\n✅ Test completed!")
    print(f"   Final score: {result['score']:.3f}")
    print(f"   Target colors: {result['target_colors']}")
    
    print("\n📋 Summary:")
    print("   - If you saw detailed generation output above, the issue is in the web interface")
    print("   - If you only saw basic messages, the issue is in the genetic algorithm itself")

if __name__ == "__main__":
    test_web_output_capture() 
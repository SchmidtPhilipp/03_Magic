#!/usr/bin/env python3
"""
Test to verify web interface output capture is working
"""

import sys
import os
import pandas as pd
import threading
import time
import queue

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from magic_optimizer.deck_builder import EnhancedDeckBuilder

# Simulate the web app's output capture system
class TestOutputCapture:
    def __init__(self):
        self.buffer = []
        self.output_queue = queue.Queue()
        self.captured_count = 0

    def write(self, text):
        timestamp = time.strftime("%H:%M:%S")
        self.buffer.append(f"[{timestamp}] {text}")
        if len(self.buffer) > 1000:  # Keep last 1000 lines
            self.buffer.pop(0)
        
        # Send output immediately
        self.output_queue.put({
            "type": "output",
            "timestamp": timestamp,
            "text": text,
            "full_buffer": self.buffer[-50:],  # Send last 50 lines
        })
        self.captured_count += 1

    def flush(self):
        pass

def test_web_interface_output():
    """Test that the web interface output capture works properly"""
    print("🧪 Testing Web Interface Output Capture")
    print("=" * 60)
    
    # Create output capture
    output_capture = TestOutputCapture()
    
    # Store original stdout
    original_stdout = sys.stdout
    
    try:
        # Redirect stdout to our capture
        sys.stdout = output_capture
        
        # Load test collection
        collection_df = pd.read_csv("data/collections/FinalFantasy.csv")
        print(f"Loaded {len(collection_df)} cards from collection")
        
        # Create deck builder
        deck_builder = EnhancedDeckBuilder()
        
        print("\n🔄 Testing Genetic Algorithm with Web Interface Output Capture...")
        print("This should show detailed generation-by-generation output:")
        print("-" * 70)
        
        # Run genetic algorithm with small parameters for quick testing
        result = deck_builder.build_optimal_deck_advanced(
            collection_df=collection_df,
            num_colors=2,
            total_deck_size=25,  # Even smaller deck for faster testing
            num_lands=8,
            algorithm="genetic",
            optimization_criterion="manual",
            lambda_penalty=1.0,
            fixed_colors=None,
        )
        
        print(f"\n✅ Test completed!")
        print(f"   Final score: {result['score']:.3f}")
        print(f"   Target colors: {result['target_colors']}")
        
        # Check what was captured
        print(f"\n📊 Output Capture Summary:")
        print(f"   Total captured lines: {len(output_capture.buffer)}")
        print(f"   Queue size: {output_capture.output_queue.qsize()}")
        
        # Show some captured output
        print(f"\n📋 Sample Captured Output:")
        for i, line in enumerate(output_capture.buffer[-10:]):  # Last 10 lines
            print(f"   {i+1}: {line.strip()}")
        
        print(f"\n📋 Summary:")
        print(f"   - If you saw 'CAPTURED:' messages above, the output capture is working")
        print(f"   - If you saw detailed generation output, the genetic algorithm is working")
        print(f"   - If both worked, the issue is in the web interface JavaScript")
        
    finally:
        # Restore original stdout
        sys.stdout = original_stdout

if __name__ == "__main__":
    test_web_interface_output() 
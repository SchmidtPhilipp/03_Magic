#!/usr/bin/env python3
"""
Simple test to verify web interface output capture
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

# Simulate the web app's output capture system exactly
class SimpleOutputCapture:
    def __init__(self):
        self.buffer = []
        self.output_queue = queue.Queue()

    def write(self, text):
        timestamp = time.strftime("%H:%M:%S")
        self.buffer.append(f"[{timestamp}] {text}")
        if len(self.buffer) > 1000:
            self.buffer.pop(0)
        
        # Send output immediately (like the web app does)
        self.output_queue.put({
            "type": "output",
            "timestamp": timestamp,
            "text": text,
            "full_buffer": self.buffer[-50:],
        })

    def flush(self):
        pass

def test_web_output_simple():
    """Test the web interface output capture with a simple genetic algorithm run"""
    print("🧪 Testing Web Interface Output Capture (Simple)")
    print("=" * 60)
    
    # Create output capture
    output_capture = SimpleOutputCapture()
    
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
        
        print("\n🔄 Testing Genetic Algorithm with Web Output Capture...")
        print("This should show detailed generation-by-generation output:")
        print("-" * 70)
        
        # Run genetic algorithm with small parameters
        result = deck_builder.build_optimal_deck_advanced(
            collection_df=collection_df,
            num_colors=2,
            total_deck_size=25,
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
        print(f"\n📋 Sample Captured Output (last 10 lines):")
        for i, line in enumerate(output_capture.buffer[-10:]):
            print(f"   {i+1}: {line.strip()}")
        
        # Simulate the web interface polling
        print(f"\n🔄 Simulating Web Interface Polling:")
        poll_count = 0
        while not output_capture.output_queue.empty() and poll_count < 5:
            try:
                msg = output_capture.output_queue.get_nowait()
                print(f"   Poll {poll_count + 1}: Received {msg['type']} message with text: '{msg['text'].strip()}'")
                poll_count += 1
            except queue.Empty:
                break
        
        print(f"\n📋 Summary:")
        print(f"   - If you saw detailed generation output above, the genetic algorithm is working")
        print(f"   - If you saw captured lines and queue messages, the output capture is working")
        print(f"   - If both worked, the issue is in the web interface JavaScript or Flask routing")
        
    finally:
        # Restore original stdout
        sys.stdout = original_stdout

if __name__ == "__main__":
    test_web_output_simple() 
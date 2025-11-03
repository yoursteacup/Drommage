#!/usr/bin/env python3
"""
Test script to verify LLM status callbacks work properly
"""

from pathlib import Path
from core.llm_analyzer import LLMAnalyzer, AnalysisLevel
import time

def test_status_callbacks():
    print("Testing LLM status callbacks...")
    
    # Initialize analyzer
    llm = LLMAnalyzer(model="mistral:latest")
    
    if not llm.ollama_available:
        print("⚠️  Ollama not available, testing with fallback mode")
    
    # Sample texts for testing
    old_text = """
    # API Documentation
    
    This is the original API documentation.
    It describes the basic endpoints.
    """
    
    new_text = """
    # API Documentation v2
    
    This is the updated API documentation.
    It describes the enhanced endpoints with new features.
    Added authentication requirements.
    Added rate limiting information.
    """
    
    # Status callback that prints updates
    def print_status(msg):
        print(f"  STATUS: {msg}")
    
    # Test 1: Brief analysis with status
    print("\n1. Testing BRIEF analysis with status updates:")
    analysis = llm.analyze_diff(
        old_text, 
        new_text, 
        "Testing status updates",
        AnalysisLevel.BRIEF,
        status_callback=print_status
    )
    print(f"  Result: {analysis.summary}")
    
    # Test 2: Detailed analysis with status
    print("\n2. Testing DETAILED analysis with status updates:")
    analysis = llm.analyze_diff(
        old_text, 
        new_text, 
        "Testing detailed status",
        AnalysisLevel.DETAILED,
        status_callback=print_status
    )
    print(f"  Result: {analysis.change_type.value} - {analysis.summary}")
    if analysis.details:
        print(f"  Details: {analysis.details[:100]}...")
    
    # Test 3: Cached analysis (should be fast)
    print("\n3. Testing cached analysis (should use cache):")
    analysis = llm.analyze_diff(
        old_text, 
        new_text, 
        "Testing status updates",  # Same context as test 1
        AnalysisLevel.BRIEF,
        status_callback=print_status
    )
    print(f"  Result: {analysis.summary}")
    
    print("\n✅ Status callback testing complete!")

if __name__ == "__main__":
    test_status_callbacks()
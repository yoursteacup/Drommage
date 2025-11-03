#!/usr/bin/env python3
"""
Debug script to see what LLM actually returns
"""

from pathlib import Path
from core.git_engine import GitDiffEngine
from core.llm_analyzer import LLMAnalyzer, AnalysisLevel
import json

PROJECT_ROOT = Path(__file__).parent
DOCS_DIR = PROJECT_ROOT / "docs"

HISTORY = [
    {"version": "v0.1", "date": "2024-04-12", "title": "Initial draft"},
    {"version": "v0.3", "date": "2024-05-02", "title": "Added API examples"},
]

def debug_llm_response():
    print("🔍 Debugging LLM Analysis Response")
    print("=" * 60)
    
    # Initialize components
    versions = [h["version"] for h in HISTORY]
    engine = GitDiffEngine(docs_dir=DOCS_DIR, versions=versions)
    engine.build_index()
    
    # Initialize LLM
    llm = LLMAnalyzer(model="mistral:latest")
    
    if not llm.ollama_available:
        print("❌ Ollama not available - can't debug")
        return
    
    # Get content for testing
    prev_lines = engine.get_document_lines("v0.1")
    curr_lines = engine.get_document_lines("v0.3")
    
    if not prev_lines or not curr_lines:
        print("❌ No document content available")
        return
    
    prev_text = "\n".join(prev_lines[:50])
    curr_text = "\n".join(curr_lines[:50])
    
    # Test DETAILED level analysis
    print("\n📝 Testing DETAILED level analysis...")
    print("-" * 40)
    
    def debug_callback(msg):
        print(f"  STATUS: {msg}")
    
    # Get raw response first
    prompt = llm._generate_prompt(prev_text, curr_text, "Debug test", AnalysisLevel.DETAILED)
    print(f"\n🔹 Prompt ({len(prompt)} chars):")
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    
    print(f"\n🔹 Calling Ollama...")
    raw_response = llm._call_ollama(prompt, debug_callback)
    
    print(f"\n🔹 Raw Response ({len(raw_response) if raw_response else 0} chars):")
    if raw_response:
        print("-" * 40)
        print(raw_response[:1000])
        if len(raw_response) > 1000:
            print("... [truncated]")
        print("-" * 40)
        
        # Try to parse as JSON
        print("\n🔹 Attempting JSON parse...")
        try:
            parsed = json.loads(raw_response)
            print("✅ Valid JSON!")
            print(json.dumps(parsed, indent=2)[:500])
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse failed: {e}")
            print("Will use fallback text parsing")
    else:
        print("❌ No response received")
    
    # Now test full analysis
    print("\n🔹 Testing full analysis pipeline...")
    analysis = llm.analyze_diff(prev_text, curr_text, "Debug", AnalysisLevel.DETAILED, debug_callback)
    
    print("\n🔹 Final Analysis Object:")
    print(f"  Summary: {analysis.summary}")
    print(f"  Type: {analysis.change_type.value} {analysis.change_type.name}")
    print(f"  Impact: {analysis.impact_level}")
    print(f"  Details: {analysis.details[:100] if analysis.details else 'None'}...")
    print(f"  Risks: {analysis.risks}")
    print(f"  Recommendations: {analysis.recommendations}")
    print(f"  Confidence: {analysis.confidence}")
    
    print("\n" + "=" * 60)
    print("✅ Debug complete")

if __name__ == "__main__":
    debug_llm_response()
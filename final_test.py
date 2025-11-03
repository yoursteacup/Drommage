#!/usr/bin/env python3
"""
Final test of Deep Analysis display
"""

from pathlib import Path
from core.git_engine import GitDiffEngine
from core.llm_analyzer import LLMAnalyzer, AnalysisLevel

PROJECT_ROOT = Path(__file__).parent
DOCS_DIR = PROJECT_ROOT / "docs"

HISTORY = [
    {"version": "v0.1", "date": "2024-04-12", "title": "Initial draft"},
    {"version": "v0.3", "date": "2024-05-02", "title": "Added API examples"},
]

def test_deep_analysis():
    print("\n🚀 Testing Deep Analysis Display")
    print("=" * 60)
    
    # Initialize
    versions = [h["version"] for h in HISTORY]
    engine = GitDiffEngine(docs_dir=DOCS_DIR, versions=versions)
    engine.build_index()
    
    llm = LLMAnalyzer(model="mistral:latest")
    
    if not llm.ollama_available:
        print("❌ Ollama not available")
        return
    
    # Get content
    prev_lines = engine.get_document_lines("v0.1")
    curr_lines = engine.get_document_lines("v0.3")
    
    if not prev_lines or not curr_lines:
        print("❌ No content")
        return
    
    prev_text = "\n".join(prev_lines[:100])
    curr_text = "\n".join(curr_lines[:100])
    
    # Status callback
    def status(msg):
        print(f"  📍 {msg}")
    
    print("\n🔍 Running DETAILED analysis...")
    print("-" * 40)
    
    analysis = llm.analyze_diff(
        prev_text, curr_text, 
        "v0.1 to v0.3",
        AnalysisLevel.DETAILED,
        status_callback=status
    )
    
    print("\n✅ Analysis Results:")
    print("-" * 40)
    print(f"\n{analysis.change_type.value} Type: {analysis.change_type.name}")
    print(f"Impact: {'▃▃▃' if analysis.impact_level == 'medium' else '▁▁▁'} {analysis.impact_level}")
    print(f"\n📋 Summary:")
    print(f"  {analysis.summary}")
    
    if analysis.details:
        print(f"\n📝 Details:")
        # Word wrap
        words = analysis.details.split()
        line = ""
        for word in words:
            if len(line) + len(word) > 55:
                print(f"  {line}")
                line = word
            else:
                line = f"{line} {word}" if line else word
        if line:
            print(f"  {line}")
    
    if analysis.risks:
        print(f"\n⚠️  Risks:")
        for risk in analysis.risks:
            print(f"  • {risk}")
    
    if analysis.recommendations:
        print(f"\n💡 Recommendations:")
        for rec in analysis.recommendations:
            print(f"  • {rec}")
    
    print("\n" + "=" * 60)
    print("✅ This should now appear in the Deep Analysis panel!")
    print("=" * 60)

if __name__ == "__main__":
    test_deep_analysis()
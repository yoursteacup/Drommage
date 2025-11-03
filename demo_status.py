#!/usr/bin/env python3
"""
Demo script showing LLM analysis status updates in action
Simulates what users would see in the TUI
"""

from pathlib import Path
from core.git_engine import GitDiffEngine
from core.region_index import RegionIndex
from core.llm_analyzer import LLMAnalyzer, AnalysisLevel
import time

PROJECT_ROOT = Path(__file__).parent
DOCS_DIR = PROJECT_ROOT / "docs"

HISTORY = [
    {"version": "v0.1", "date": "2024-04-12", "title": "Initial draft"},
    {"version": "v0.3", "date": "2024-05-02", "title": "Added API examples"},
    {"version": "v0.6", "date": "2024-06-10", "title": "Refactoring and cleanup"},
    {"version": "v1.0", "date": "2024-08-01", "title": "Stable release"},
    {"version": "v1.2", "date": "2024-09-14", "title": "Minor revisions"},
]

def print_separator():
    print("─" * 60)

def demo_analysis():
    print("🚀 DRommage v8 - Status Update Demo")
    print_separator()
    
    # Initialize components
    print("📊 Loading document versions...")
    versions = [h["version"] for h in HISTORY]
    engine = GitDiffEngine(docs_dir=DOCS_DIR, versions=versions)
    engine.build_index()
    
    print("🧩 Building region index...")
    region_index = RegionIndex(engine)
    region_index.build_regions()
    
    print("🤖 Initializing LLM analyzer...")
    llm = LLMAnalyzer(model="mistral:latest")
    
    print_separator()
    
    # Simulate analyzing different versions
    print("\n📍 Simulating version navigation and analysis:\n")
    
    for i in range(1, min(3, len(versions))):
        prev_ver = versions[i-1]
        curr_ver = versions[i]
        
        print(f"📄 Analyzing: {prev_ver} → {curr_ver}")
        print(f"   {HISTORY[i]['title']}")
        
        # Get document content
        prev_lines = engine.get_document_lines(prev_ver)
        curr_lines = engine.get_document_lines(curr_ver)
        
        if not prev_lines or not curr_lines:
            print("   ⚠️  No content available for comparison")
            continue
        
        prev_text = "\n".join(prev_lines[:100])  # Limit for demo
        curr_text = "\n".join(curr_lines[:100])
        
        # Status callback that shows updates
        status_updates = []
        def track_status(msg):
            status_updates.append(msg)
            print(f"   │ {msg}")
        
        # Analyze with status updates
        context = f"Version {prev_ver} to {curr_ver}"
        analysis = llm.analyze_diff(
            prev_text, 
            curr_text, 
            context, 
            AnalysisLevel.BRIEF,
            status_callback=track_status
        )
        
        # Show results
        print(f"   ╰→ {analysis.change_type.value} {analysis.summary[:60]}...")
        print()
    
    print_separator()
    
    # Demo region analysis
    print("\n🔍 Analyzing region evolution:\n")
    
    regions = region_index.get_most_volatile_regions(1)
    if regions:
        region = regions[0]
        print(f"📌 Most changed region (modified {region.versions_modified}x)")
        print(f"   Preview: {region.canonical_text[:50]}...")
        
        # Analyze region with status
        def region_status(msg):
            print(f"   │ {msg}")
        
        history = region_index.get_region_history(region.id)
        if history:
            summary = llm.analyze_region(history, AnalysisLevel.BRIEF, region_status)
            print(f"   ╰→ {summary}")
    
    print()
    print_separator()
    print("✅ Demo complete! The status updates show:")
    print("   • 📦 Cache hits for repeated analysis")
    print("   • 📊 Metrics about the diff being analyzed")
    print("   • 📝 Prompt size and analysis level")
    print("   • 🤖 LLM inference progress")
    print("   • ✅ Completion time")
    print("\n💡 In the TUI, these appear in the status bar and analysis panel")

if __name__ == "__main__":
    demo_analysis()
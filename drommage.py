#!/usr/bin/env python3
"""
DRommage v8 - LLM-Powered Documentation Analysis
Now with intelligent diff interpretation and enhanced UI
"""

from pathlib import Path
from drommage.core.diff_tracker import GitDiffEngine
from drommage.core.region_analyzer import RegionIndex
from drommage.core.interface import DocTUIView

PROJECT_ROOT = Path(__file__).parent
DOCS_DIR = PROJECT_ROOT / "test_docs" / "docs"

# История версий документа
HISTORY = [
    {"version": "v0.1", "date": "2024-04-12", "title": "Initial draft"},
    {"version": "v0.3", "date": "2024-05-02", "title": "Added API examples"},
    {"version": "v0.6", "date": "2024-06-10", "title": "Refactoring and cleanup"},
    {"version": "v1.0", "date": "2024-08-01", "title": "Stable release"},
    {"version": "v1.2", "date": "2024-09-14", "title": "Minor revisions"},
]

def main():
    print("🚀 Starting DRommage v8...")
    print("📊 Loading document versions...")
    
    # Создаем движок диффов
    versions = [h["version"] for h in HISTORY]
    engine = GitDiffEngine(docs_dir=DOCS_DIR, versions=versions)
    engine.build_index()
    
    # Создаем индекс регионов
    print("🧩 Building region index...")
    region_index = RegionIndex(engine)
    region_index.build_regions()
    
    # Check for Ollama
    print("🤖 Checking for LLM support...")
    try:
        import subprocess
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            print("✅ Ollama detected - LLM analysis available")
        else:
            print("⚠️  Ollama not found - install from https://ollama.ai for AI features")
    except:
        print("⚠️  Ollama not available - using fallback analysis")
    
    # Запускаем TUI
    print("\n📺 Launching interface...\n")
    tui = DocTUIView(engine=engine, region_index=region_index, history=HISTORY)
    tui.run()
    
    print("\n👋 Thanks for using DRommage!")

if __name__ == "__main__":
    main()
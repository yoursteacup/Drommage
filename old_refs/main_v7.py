#!/usr/bin/env python3
"""
DRommage v7 - Git-based documentation versioning with region tracking
"""

from pathlib import Path
from core.git_engine import GitDiffEngine
from core.region_index import RegionIndex
from core.tui import DocTUIView

PROJECT_ROOT = Path(__file__).parent
DOCS_DIR = PROJECT_ROOT / "docs"

# История версий документа
HISTORY = [
    {"version": "v0.1", "date": "2024-04-12", "title": "Initial draft"},
    {"version": "v0.3", "date": "2024-05-02", "title": "Added API examples"},
    {"version": "v0.6", "date": "2024-06-10", "title": "Refactoring and cleanup"},
    {"version": "v1.0", "date": "2024-08-01", "title": "Stable release"},
    {"version": "v1.2", "date": "2024-09-14", "title": "Minor revisions"},
]

def main():
    # Создаем движок диффов
    versions = [h["version"] for h in HISTORY]
    engine = GitDiffEngine(docs_dir=DOCS_DIR, versions=versions)
    engine.build_index()
    
    # Создаем индекс регионов
    region_index = RegionIndex(engine)
    region_index.build_regions()
    
    # Запускаем TUI
    tui = DocTUIView(engine=engine, region_index=region_index, history=HISTORY)
    tui.run()

if __name__ == "__main__":
    main()
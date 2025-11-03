#!/usr/bin/env python3
from pathlib import Path
from core.diff_engine import DocDiffEngine
from core.tui import DocTUIView

PROJECT_ROOT = Path(__file__).parent
DOCS_DIR = PROJECT_ROOT / "docs"

HISTORY = [
    {"version": "v0.1", "date": "2024-04-12", "title": "Initial draft"},
    {"version": "v0.3", "date": "2024-05-02", "title": "Added API examples"},
    {"version": "v0.6", "date": "2024-06-10", "title": "Refactoring and cleanup"},
    {"version": "v1.0", "date": "2024-08-01", "title": "Stable release"},
    {"version": "v1.2", "date": "2024-09-14", "title": "Minor revisions"},
]

def main():
    versions = [h["version"] for h in HISTORY]
    engine = DocDiffEngine(docs_dir=DOCS_DIR, versions=versions)
    engine.build_index()
    tui = DocTUIView(engine, HISTORY)
    tui.run()

if __name__ == "__main__":
    main()

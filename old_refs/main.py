#!/usr/bin/env python3
# main.py — entrypoint for the docdiff TUI demo

import os
import sys
from core.mock_data import get_docs_folder, get_doc_versions
from core.diff_engine import DocDiffEngine
from core.tui_viewer import TUIViewer

def main():
    base = os.path.dirname(__file__)
    docs_folder = os.path.join(base, "docs")

    # Load mock versions (v1..v5)
    versions = get_doc_versions(docs_folder)
    if not versions:
        print("No docs found in", docs_folder)
        sys.exit(1)

    engine = DocDiffEngine(versions)
    engine.build_index()  # builds region index from diffs

    viewer = TUIViewer(engine)
    try:
        viewer.run()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()


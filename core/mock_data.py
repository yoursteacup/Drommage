# mock_data.py
# Provides the mocked docs (reads docs/v1.txt .. v5.txt)

import os
from typing import List, Tuple

def get_docs_folder(base_folder: str = None) -> str:
    if base_folder:
        return base_folder
    return os.path.join(os.path.dirname(__file__), "..", "docs")

def discover_versions(docs_folder: str):
    # Return sorted list of fname paths that start with v1, v2, ...
    files = []
    for name in sorted(os.listdir(docs_folder)):
        if name.startswith("v") and name.endswith(".txt"):
            files.append(os.path.join(docs_folder, name))
    return files

def get_doc_versions(docs_folder: str) -> List[Tuple[str, str]]:
    """
    Returns list of tuples: (version_name, content)
    order: oldest -> newest
    """
    files = discover_versions(docs_folder)
    res = []
    for p in files:
        name = os.path.splitext(os.path.basename(p))[0]
        with open(p, "r", encoding="utf-8") as f:
            txt = f.read()
        res.append((name, txt))
    return res


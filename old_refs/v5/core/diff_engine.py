# core/diff_engine.py
import difflib
from pathlib import Path
from typing import List, Dict

class DocDiffEngine:
    def __init__(self, docs_dir: Path, versions: List[str]):
        self.docs_dir = Path(docs_dir)
        self.versions = versions
        self.documents: Dict[str, List[str]] = {}
        self.diffs: Dict[tuple, List[str]] = {}

    def build_index(self):
        # load docs
        for v in self.versions:
            p = self.docs_dir / f"{v}.txt"
            if p.exists():
                self.documents[v] = p.read_text(encoding="utf-8").splitlines()
            else:
                self.documents[v] = [f"[Missing file {p.name}]"]
        # compute unified diffs between successive pairs
        for i in range(1, len(self.versions)):
            a = self.versions[i-1]
            b = self.versions[i]
            ud = list(difflib.unified_diff(self.documents[a], self.documents[b],
                                           fromfile=a, tofile=b, lineterm=""))
            self.diffs[(a,b)] = ud

    def get_document_lines(self, version: str):
        return self.documents.get(version, [f"[No content for {version}]"])

    def get_unified_diff(self, prev: str, cur: str):
        return self.diffs.get((prev, cur), [])

    def get_diff_summary(self, prev: str, cur: str):
        ud = self.get_unified_diff(prev, cur)
        added = sum(1 for l in ud if l.startswith('+') and not l.startswith('+++'))
        removed = sum(1 for l in ud if l.startswith('-') and not l.startswith('---'))
        return f"+{added} / -{removed}"

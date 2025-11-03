import difflib
from pathlib import Path

class DocDiffEngine:
    def __init__(self, docs_dir: Path, versions: list[str]):
        self.docs_dir = docs_dir
        self.versions = versions
        self.documents = {}
        self.diffs = {}

    def build_index(self):
        for version in self.versions:
            path = self.docs_dir / f"{version}.txt"
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    self.documents[version] = f.read().splitlines()
            else:
                self.documents[version] = [f"[File {path.name} missing]"]

        for i in range(1, len(self.versions)):
            old_v = self.versions[i - 1]
            new_v = self.versions[i]
            diff = list(difflib.unified_diff(
                self.documents[old_v], self.documents[new_v],
                fromfile=old_v, tofile=new_v, lineterm=""
            ))
            self.diffs[(old_v, new_v)] = diff

    def get_diff_summary(self, old_v, new_v):
        diff = self.diffs.get((old_v, new_v), [])
        added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
        return f"+{added} / -{removed} lines"

    def get_document(self, version):
        return self.documents.get(version, ["[Missing]"])

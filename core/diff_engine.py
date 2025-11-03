# diff_engine.py
# Simplified engine: builds regions from diffs between successive versions.

import difflib
import hashlib
from dataclasses import dataclass
from typing import List, Dict, Tuple

@dataclass
class RegionHistoryEntry:
    from_tag: str
    to_tag: str
    added: List[str]
    removed: List[str]

@dataclass
class Region:
    id: str
    canonical: str  # canonical snippet or heading
    first_seen: str
    history: List[RegionHistoryEntry]

class DocDiffEngine:
    def __init__(self, versions: List[Tuple[str, str]]):
        """
        versions: list of (tag, text) ordered oldest -> newest
        """
        self.versions = versions
        self.regions: Dict[str, Region] = {}
        # convenience
        self.tags = [t for t, _ in versions]

    @staticmethod
    def _hunk_id(file_context: str, snippet_lines: List[str]) -> str:
        m = hashlib.sha1()
        m.update(file_context.encode("utf-8"))
        m.update(b"\x00")
        m.update("\n".join(snippet_lines).encode("utf-8"))
        return m.hexdigest()

    def _extract_hunks_from_unified(self, a_lines: List[str], b_lines: List[str]) -> List[Tuple[List[str], List[str]]]:
        """
        Use difflib.unified_diff to find hunks as (removed_lines, added_lines).
        Returns list of tuples for each hunk.
        """
        ud = list(difflib.unified_diff(a_lines, b_lines, lineterm=""))
        hunks = []
        cur_removed = []
        cur_added = []
        in_hunk = False
        for line in ud:
            if line.startswith('@@'):
                # start new hunk: flush previous
                if in_hunk:
                    hunks.append((cur_removed, cur_added))
                cur_removed = []
                cur_added = []
                in_hunk = True
                continue
            if not in_hunk:
                continue
            if line.startswith('-') and not line.startswith('---'):
                cur_removed.append(line[1:])
            elif line.startswith('+') and not line.startswith('+++'):
                cur_added.append(line[1:])
            else:
                # context line (space) - include in canonical snippet to identify region
                pass
        if in_hunk:
            hunks.append((cur_removed, cur_added))
        return hunks

    def build_index(self):
        """
        Iterate successive pairs of versions, build region entries keyed by a stable id.
        """
        for i in range(len(self.versions) - 1):
            tag_a, text_a = self.versions[i]
            tag_b, text_b = self.versions[i+1]
            a_lines = text_a.splitlines()
            b_lines = text_b.splitlines()
            hunks = self._extract_hunks_from_unified(a_lines, b_lines)
            for removed, added in hunks:
                # canonical snippet: first non-empty of added or removed or top context
                canonical_lines = added or removed
                if not canonical_lines:
                    # fallback: use a short signature from both
                    snippet = (a_lines[:2] + b_lines[:2])[:3]
                else:
                    snippet = canonical_lines[:3]
                rid = self._hunk_id(tag_a + "->" + tag_b, snippet)
                entry = RegionHistoryEntry(from_tag=tag_a, to_tag=tag_b, added=added, removed=removed)
                if rid in self.regions:
                    self.regions[rid].history.append(entry)
                else:
                    reg = Region(id=rid, canonical="\n".join(snippet), first_seen=tag_a, history=[entry])
                    self.regions[rid] = reg

    def regions_for_latest(self) -> List[Region]:
        # Return regions sorted by first_seen (stable order)
        return sorted(self.regions.values(), key=lambda r: r.first_seen)

    def find_regions_covering_line(self, line_text: str) -> List[Region]:
        """
        Very naive: find regions whose canonical snippet appears in given line_text or vice versa.
        Purpose: highlight lines in viewer that match known regions.
        """
        found = []
        for r in self.regions.values():
            if not r.canonical:
                continue
            # check if any small snippet substring appears
            if r.canonical.strip() and (r.canonical.strip() in line_text or line_text.strip() in r.canonical):
                found.append(r)
        return found

    def get_history_for_region(self, region_id: str):
        return self.regions.get(region_id)


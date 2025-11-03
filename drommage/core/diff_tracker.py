"""
Git-based diff engine that tracks document changes as regions
Each region = semantic chunk of text that evolved through versions
"""

import difflib
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class DiffChunk:
    """Represents a single change between versions"""
    start_line: int
    end_line: int
    action: str  # 'add', 'remove', 'modify'
    content: List[str]
    context: str  # surrounding text for identification

@dataclass
class Region:
    """A semantic region of the document with its history"""
    id: str  # hash-based unique ID
    first_seen: str  # version where first appeared
    last_modified: str  # version where last changed
    canonical_text: str  # current or most representative version
    history: List[Dict]  # list of changes through versions
    line_range: Tuple[int, int]  # current position in document

class GitDiffEngine:
    def __init__(self, docs_dir: Optional[Path] = None, versions: List[str] = None):
        self.docs_dir = Path(docs_dir) if docs_dir else None
        self.versions = versions or []
        self.documents: Dict[str, List[str]] = {}
        self.diffs: Dict[Tuple[str, str], List[DiffChunk]] = {}
        self.regions: Dict[str, Region] = {}
        
    def build_index(self):
        """Load all versions and compute structured diffs between them"""
        if not self.docs_dir or not self.versions:
            return  # Skip if no docs directory or versions
            
        # Load all document versions
        for v in self.versions:
            path = self.docs_dir / f"{v}.txt"
            if path.exists():
                self.documents[v] = path.read_text(encoding="utf-8").splitlines()
            else:
                self.documents[v] = [f"[Missing {v}.txt]"]
        
        # Build diffs between consecutive versions
        for i in range(len(self.versions)):
            if i == 0:
                # First version - all lines are "new regions"
                self._initialize_regions(self.versions[0])
            else:
                prev, cur = self.versions[i-1], self.versions[i]
                self._compute_diff(prev, cur)
    
    def _initialize_regions(self, version: str):
        """Create initial regions from first version"""
        lines = self.documents[version]
        chunks = self._split_into_semantic_chunks(lines)
        
        for chunk_lines, start, end in chunks:
            region_id = self._hash_region(chunk_lines)
            self.regions[region_id] = Region(
                id=region_id,
                first_seen=version,
                last_modified=version,
                canonical_text="\n".join(chunk_lines),
                history=[{
                    "version": version,
                    "action": "created",
                    "lines": chunk_lines
                }],
                line_range=(start, end)
            )
    
    def _compute_diff(self, prev_ver: str, cur_ver: str):
        """Compute semantic diff and update regions"""
        prev_lines = self.documents[prev_ver]
        cur_lines = self.documents[cur_ver]
        
        # Use difflib to find changes
        matcher = difflib.SequenceMatcher(None, prev_lines, cur_lines)
        chunks = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                # Region was modified
                old_chunk = prev_lines[i1:i2]
                new_chunk = cur_lines[j1:j2]
                chunks.append(DiffChunk(
                    start_line=j1,
                    end_line=j2,
                    action='modify',
                    content=new_chunk,
                    context=self._get_context(cur_lines, j1, j2)
                ))
                self._update_region(old_chunk, new_chunk, cur_ver, 'modify')
                
            elif tag == 'delete':
                # Region was removed
                old_chunk = prev_lines[i1:i2]
                chunks.append(DiffChunk(
                    start_line=i1,
                    end_line=i2,
                    action='remove',
                    content=old_chunk,
                    context=self._get_context(prev_lines, i1, i2)
                ))
                self._update_region(old_chunk, [], cur_ver, 'remove')
                
            elif tag == 'insert':
                # New region added
                new_chunk = cur_lines[j1:j2]
                chunks.append(DiffChunk(
                    start_line=j1,
                    end_line=j2,
                    action='add',
                    content=new_chunk,
                    context=self._get_context(cur_lines, j1, j2)
                ))
                self._create_new_region(new_chunk, cur_ver, j1, j2)
        
        self.diffs[(prev_ver, cur_ver)] = chunks
    
    def _split_into_semantic_chunks(self, lines: List[str]) -> List[Tuple[List[str], int, int]]:
        """Split document into semantic chunks (paragraphs, sections, etc)"""
        chunks = []
        current_chunk = []
        start_idx = 0
        
        for i, line in enumerate(lines):
            # Simple heuristic: split on empty lines or headers
            if line.strip() == "" or line.startswith("#"):
                if current_chunk:
                    chunks.append((current_chunk, start_idx, i))
                    current_chunk = []
                    start_idx = i
                if line.startswith("#"):
                    chunks.append(([line], i, i+1))
                    start_idx = i + 1
            else:
                current_chunk.append(line)
        
        if current_chunk:
            chunks.append((current_chunk, start_idx, len(lines)))
        
        return chunks
    
    def _hash_region(self, lines: List[str]) -> str:
        """Create stable hash for region identification"""
        content = "\n".join(lines).strip()
        # Use first few words as additional context for hash
        words = content.split()[:5]
        context = " ".join(words)
        return hashlib.sha1(context.encode()).hexdigest()[:12]
    
    def _get_context(self, lines: List[str], start: int, end: int) -> str:
        """Get surrounding context for a chunk"""
        context_before = lines[max(0, start-2):start]
        context_after = lines[end:min(len(lines), end+2)]
        return " [...] ".join(context_before[-1:] + context_after[:1])
    
    def _update_region(self, old_chunk: List[str], new_chunk: List[str], version: str, action: str):
        """Update existing region with changes"""
        if not old_chunk:
            return
            
        old_id = self._hash_region(old_chunk)
        if old_id in self.regions:
            region = self.regions[old_id]
            region.last_modified = version
            region.history.append({
                "version": version,
                "action": action,
                "old_lines": old_chunk,
                "new_lines": new_chunk
            })
            
            if new_chunk:
                # Update canonical text if modified
                region.canonical_text = "\n".join(new_chunk)
    
    def _create_new_region(self, chunk: List[str], version: str, start: int, end: int):
        """Create new region"""
        if not chunk:
            return
            
        region_id = self._hash_region(chunk)
        self.regions[region_id] = Region(
            id=region_id,
            first_seen=version,
            last_modified=version,
            canonical_text="\n".join(chunk),
            history=[{
                "version": version,
                "action": "created",
                "lines": chunk
            }],
            line_range=(start, end)
        )
    
    def get_document_lines(self, version: str) -> List[str]:
        """Get document content for a specific version"""
        return self.documents.get(version, [])
    
    def get_regions_for_version(self, version: str) -> List[Region]:
        """Get all regions active in a specific version"""
        active_regions = []
        for region in self.regions.values():
            # Check if region exists in this version
            for hist in region.history:
                if hist["version"] == version:
                    if hist["action"] != "remove":
                        active_regions.append(region)
                    break
        return active_regions
    
    def get_region_at_line(self, version: str, line_num: int) -> Optional[Region]:
        """Find which region contains a specific line"""
        for region in self.get_regions_for_version(version):
            if region.line_range[0] <= line_num < region.line_range[1]:
                return region
        return None
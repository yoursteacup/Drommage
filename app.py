"""
DocDiff — прототип инструмента для разметки регионов документации на основе git-diff.

Как это работает (упрощённо):
- Берёт список тегов/коммитов (например: v1 v2 v3 v4 v5).
- Для каждой пары соседних тегов делает `git diff tag_i tag_{i+1} -- <file>`.
- Парсит unified-diff, извлекает хунки (hunks) — они и будут нашими регионами.
- Для каждого региона собирает историю изменений (какие строки были добавлены/удалены между версиями).
- Сохраняет индекс в SQLite (таблица regions).

Команды:
  python docdiff_prototype.py index --file path/to/doc.md --tags v1 v2 v3 v4 v5
  python docdiff_prototype.py show --file path/to/doc.md
  python docdiff_prototype.py diff --from v1 --to v3 --file path/to/doc.md

Ограничения прототипа:
- Не делает глубокого семантического анализа, использует хунки unified-diff как регионы.
- Требует, чтобы текущая директория была git-репозиторием с упомянутыми тегами.

"""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple

UNIFIED_HUNK_RE = re.compile(r"@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?P<heading>.*)\n")

@dataclass
class Hunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    heading: str
    lines: List[str]  # includes leading '-', '+', or ' ' markers

@dataclass
class RegionHistoryEntry:
    from_tag: str
    to_tag: str
    added: List[str]
    removed: List[str]

@dataclass
class Region:
    id: str
    file: str
    canonical_heading: str
    first_seen: str
    history: List[RegionHistoryEntry]

DB_SCHEMA = '''
CREATE TABLE IF NOT EXISTS regions (
    id TEXT PRIMARY KEY,
    file TEXT NOT NULL,
    canonical_heading TEXT,
    first_seen TEXT,
    history_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_file ON regions(file);
'''


# ---------------------- Git helpers ----------------------
def run_git(args: List[str], cwd: Optional[str] = None) -> str:
    cmd = ["git"] + args
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, cwd=cwd)
        return output.decode('utf-8', errors='replace')
    except subprocess.CalledProcessError as e:
        print(f"git failed: {' '.join(cmd)}\n{e.output.decode('utf-8', errors='replace')}")
        raise


def list_tags_sorted() -> List[str]:
    # Sort by taggerdate if available, otherwise by name
    out = run_git(["tag", "--sort=creatordate"])  # may be empty
    tags = [t.strip() for t in out.splitlines() if t.strip()]
    return tags


def git_diff_between(a: str, b: str, path: str) -> str:
    # unified diff for a single file between two refs
    # Use --unified=0 to make hunks tight (optional)
    out = run_git(["diff", f"{a}", f"{b}", "--", path])
    return out


# ---------------------- Diff parsing ----------------------
def parse_unified_diff(diff_text: str) -> List[Hunk]:
    """Parses a unified diff text for a single file and returns list of hunks.
    This is a relatively small parser tailored for our use.
    """
    if not diff_text:
        return []
    lines = diff_text.splitlines(keepends=False)
    hunks: List[Hunk] = []
    i = 0
    # Find the first hunk marker @@ ... @@
    while i < len(lines):
        m = UNIFIED_HUNK_RE.match('\n'.join(lines[i:i+1]) + '\n')
        # The regex expects a newline; simpler: search for line starting with @@
        if lines[i].startswith('@@'):
            header = lines[i]
            mm = re.match(r"@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?P<heading>.*)", header)
            if not mm:
                i += 1
                continue
            old_start = int(mm.group('old_start'))
            old_count = int(mm.group('old_count') or 1)
            new_start = int(mm.group('new_start'))
            new_count = int(mm.group('new_count') or 1)
            heading = mm.group('heading').strip()
            i += 1
            hunk_lines: List[str] = []
            # collect lines until next @@ or end
            while i < len(lines) and not lines[i].startswith('@@'):
                hunk_lines.append(lines[i])
                i += 1
            hunks.append(Hunk(old_start=old_start, old_count=old_count,
                              new_start=new_start, new_count=new_count,
                              heading=heading, lines=hunk_lines))
        else:
            i += 1
    return hunks


def hunk_to_region_id(file: str, hunk: Hunk) -> str:
    # canonicalize heading and content to produce stable id for region
    m = hashlib.sha1()
    m.update(file.encode('utf-8'))
    m.update(b"\x00")
    # Use heading and the context lines (without leading +/-/ ) as signature
    context_lines = [ln[1:] if ln and ln[0] in '+- ' else ln for ln in hunk.lines]
    sig = '\n'.join(context_lines)
    m.update(sig.encode('utf-8'))
    return m.hexdigest()


# ---------------------- Storage ----------------------
class RegionStore:
    def __init__(self, path: str = 'docdiff_index.sqlite'):
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self._init_db()

    def _init_db(self):
        cur = self.conn.cursor()
        cur.executescript(DB_SCHEMA)
        self.conn.commit()

    def upsert_region(self, region: Region):
        cur = self.conn.cursor()
        cur.execute('SELECT history_json, first_seen FROM regions WHERE id = ?', (region.id,))
        row = cur.fetchone()
        history_json = json.dumps([asdict(h) for h in region.history], ensure_ascii=False)
        if row:
            # merge: keep existing first_seen if earlier
            existing_first = row[1]
            first_seen = existing_first or region.first_seen
            cur.execute('UPDATE regions SET file = ?, canonical_heading = ?, first_seen = ?, history_json = ? WHERE id = ?',
                        (region.file, region.canonical_heading, first_seen, history_json, region.id))
        else:
            cur.execute('INSERT INTO regions(id, file, canonical_heading, first_seen, history_json) VALUES(?,?,?,?,?)',
                        (region.id, region.file, region.canonical_heading, region.first_seen, history_json))
        self.conn.commit()

    def load_regions_for_file(self, file: str) -> List[Region]:
        cur = self.conn.cursor()
        cur.execute('SELECT id, canonical_heading, first_seen, history_json FROM regions WHERE file = ? ORDER BY first_seen', (file,))
        rows = cur.fetchall()
        res: List[Region] = []
        for id_, heading, first_seen, hist_json in rows:
            hist_list = json.loads(hist_json)
            history = [RegionHistoryEntry(**h) for h in hist_list]
            res.append(Region(id=id_, file=file, canonical_heading=heading, first_seen=first_seen or '', history=history))
        return res


# ---------------------- High-level indexing ----------------------

def index_file_across_tags(store: RegionStore, file: str, tags: List[str]):
    # tags ordered from oldest -> newest
    if len(tags) < 2:
        print('Need at least two tags to index diffs between them')
        return
    for a, b in zip(tags[:-1], tags[1:]):
        print(f"Indexing diff {a} → {b} for {file}")
        diff_text = git_diff_between(a, b, file)
        hunks = parse_unified_diff(diff_text)
        for h in hunks:
            rid = hunk_to_region_id(file, h)
            added = [ln[1:] for ln in h.lines if ln.startswith('+')]
            removed = [ln[1:] for ln in h.lines if ln.startswith('-')]
            entry = RegionHistoryEntry(from_tag=a, to_tag=b, added=added, removed=removed)
            # try to read existing region
            existing = None
            cur = store.conn.cursor()
            cur.execute('SELECT history_json, canonical_heading, first_seen FROM regions WHERE id = ?', (rid,))
            row = cur.fetchone()
            if row:
                hist = json.loads(row[0])
                hist.append(asdict(entry))
                canonical = row[1]
                first_seen = row[2] or a
                region = Region(id=rid, file=file, canonical_heading=canonical or h.heading, first_seen=first_seen, history=[RegionHistoryEntry(**x) for x in hist])
            else:
                region = Region(id=rid, file=file, canonical_heading=h.heading or '', first_seen=a, history=[entry])
            store.upsert_region(region)


# ---------------------- CLI show ----------------------

def show_file(store: RegionStore, file: str):
    regions = store.load_regions_for_file(file)
    if not regions:
        print('No regions indexed for', file)
        return
    for r in regions:
        print('REGION', r.id)
        if r.canonical_heading:
            print('  heading:', r.canonical_heading)
        print('  first_seen:', r.first_seen)
        print('  history:')
        for e in r.history:
            print(f"    {e.from_tag} → {e.to_tag}")
            if e.removed:
                print('      - removed:')
                for l in e.removed:
                    print('         ', l)
            if e.added:
                print('      + added:')
                for l in e.added:
                    print('         ', l)
        print('-' * 40)


# ---------------------- Utility: diff view ----------------------

def show_diff_between(a: str, b: str, file: str):
    txt = git_diff_between(a, b, file)
    if not txt:
        print('No diff')
        return
    print(txt)


# ---------------------- CLI ----------------------

def main(argv=None):
    p = argparse.ArgumentParser(prog='docdiff')
    sub = p.add_subparsers(dest='cmd')

    idx = sub.add_parser('index')
    idx.add_argument('--file', required=True, help='path to markdown file in repo')
    idx.add_argument('--tags', nargs='+', required=False, help='list of tags or commits oldest->newest')
    idx.add_argument('--db', default='docdiff_index.sqlite')

    sh = sub.add_parser('show')
    sh.add_argument('--file', required=True)
    sh.add_argument('--db', default='docdiff_index.sqlite')

    df = sub.add_parser('diff')
    df.add_argument('--from', dest='from_tag', required=True)
    df.add_argument('--to', dest='to_tag', required=True)
    df.add_argument('--file', required=True)

    args = p.parse_args(argv)
    if args.cmd == 'index':
        tags = args.tags
        if not tags:
            tags = list_tags_sorted()
            print('Detected tags:', tags)
        if len(tags) < 2:
            print('Need at least two tags to form diffs. Either create tags or pass --tags list manually.')
            return
        store = RegionStore(args.db)
        index_file_across_tags(store, args.file, tags)
        print('Indexing done.')

    elif args.cmd == 'show':
        store = RegionStore(args.db)
        show_file(store, args.file)

    elif args.cmd == 'diff':
        show_diff_between(args.from_tag, args.to_tag, args.file)

    else:
        p.print_help()


if __name__ == '__main__':
    main()


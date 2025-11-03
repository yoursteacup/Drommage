# tui_viewer.py
# curses based viewer for the docdiff demo

import curses
import textwrap
from typing import List
from .diff_engine import DocDiffEngine

PALETTE = {
    "bg": 0,
    "highlight": 1,
    "added": 2,
    "removed": 3,
    "title": 4
}

class TUIViewer:
    def __init__(self, engine: DocDiffEngine):
        self.engine = engine
        self.versions = engine.versions  # list of (tag, text)
        self.current_idx = len(self.versions) - 1  # show latest by default
        self.cursor_line = 0
        self.max_lines = 0
        self.screen = None
        self.selected_region = None
        self.lines_cache = [txt.splitlines() for _, txt in self.versions]

    def run(self):
        curses.wrapper(self._curses_main)

    def _curses_main(self, scr):
        self.screen = scr
        curses.curs_set(0)

        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            try:
                curses.init_pair(PALETTE["highlight"], curses.COLOR_BLACK, curses.COLOR_YELLOW)
                curses.init_pair(PALETTE["added"], curses.COLOR_GREEN, -1)
                curses.init_pair(PALETTE["removed"], curses.COLOR_RED, -1)
                curses.init_pair(PALETTE["title"], curses.COLOR_CYAN, -1)
            except curses.error:
                pass  # macOS иногда не даёт инициализировать цветовые пары

        while True:
            self.screen.clear()
            h, w = self.screen.getmaxyx()
            left_w = int(w * 0.62)
            right_w = w - left_w - 1

            # Draw borders
            self.screen.vline(0, left_w, ord("|"), h)

            # Titles
            title = " docdiff — TUI demo "
            ver_label = f" version: {self.versions[self.current_idx][0]} ({self.current_idx+1}/{len(self.versions)}) "
            self.screen.addstr(0, 1, title, curses.color_pair(PALETTE["title"]))
            self.screen.addstr(0, left_w + 2, ver_label, curses.color_pair(PALETTE["title"]))

            # Left pane: document
            left_win_h = h - 3
            doc_lines = self.lines_cache[self.current_idx]
            self.max_lines = max(1, len(doc_lines))
            # compute visible window offset
            top_line = max(0, min(self.cursor_line - left_win_h//2, max(0, self.max_lines - left_win_h)))
            for idx in range(left_win_h):
                ln = top_line + idx
                if ln >= len(doc_lines):
                    break
                txt = doc_lines[ln]
                # naive region highlight: if any region canonical appears in line -> highlight
                regions = self.engine.find_regions_covering_line(txt)
                if regions:
                    try:
                        self.screen.addnstr(1 + idx, 1, txt, left_w - 2, curses.color_pair(PALETTE["highlight"]))
                    except curses.error:
                        pass
                else:
                    try:
                        self.screen.addnstr(1 + idx, 1, txt, left_w - 2)
                    except curses.error:
                        pass
                # cursor indicator
                if ln == self.cursor_line:
                    try:
                        self.screen.addch(1 + idx, 0, ord(">"))
                    except curses.error:
                        pass

            # Right pane: region/history for the currently selected line
            right_x = left_w + 2
            sel_text = doc_lines[self.cursor_line] if self.cursor_line < len(doc_lines) else ""
            regions = self.engine.find_regions_covering_line(sel_text)
            if not regions:
                self.screen.addstr(2, right_x, "(no regions found for this line)")
            else:
                y = 1
                for r in regions[:8]:
                    heading = (r.canonical.replace("\n", " "))[:right_w-4]
                    self.screen.addnstr(y, right_x, f"[region] {heading}", right_w - 2, curses.A_BOLD)
                    y += 1
                    for e in r.history[-6:]:
                        # show small history snippet
                        prefix = f" {e.from_tag}→{e.to_tag} "
                        self.screen.addnstr(y, right_x, prefix + ("+%d -%d" % (len(e.added), len(e.removed))), right_w - 2)
                        y += 1
                        for a in (e.added[:2]):
                            self.screen.addnstr(y, right_x+2, "+ " + a[:right_w-6], right_w - 4, curses.color_pair(PALETTE["added"]))
                            y += 1
                        for rem in (e.removed[:2]):
                            self.screen.addnstr(y, right_x+2, "- " + rem[:right_w-6], right_w - 4, curses.color_pair(PALETTE["removed"]))
                            y += 1
                        if y > h - 2:
                            break
                    if y > h - 2:
                        break

            # Footer / help
            help_text = "←/→ switch version  ↑/↓ move  Enter show diff  q quit"
            try:
                self.screen.addnstr(h-1, 1, help_text, w-2, curses.A_REVERSE)
            except curses.error:
                pass

            self.screen.refresh()
            ch = self.screen.getch()
            if ch in (ord('q'), ord('Q')):
                break
            elif ch == curses.KEY_RIGHT:
                self.current_idx = min(len(self.versions)-1, self.current_idx + 1)
                self.cursor_line = min(self.cursor_line, len(self.lines_cache[self.current_idx]) - 1)
            elif ch == curses.KEY_LEFT:
                self.current_idx = max(0, self.current_idx - 1)
                self.cursor_line = min(self.cursor_line, len(self.lines_cache[self.current_idx]) - 1)
            elif ch == curses.KEY_UP:
                self.cursor_line = max(0, self.cursor_line - 1)
            elif ch == curses.KEY_DOWN:
                self.cursor_line = min(self.max_lines - 1, self.cursor_line + 1)
            elif ch in (curses.KEY_ENTER, 10, 13):
                self._show_diff_popup()
            # else: ignore other keys

    def _show_diff_popup(self):
        # Show unified diff between previous version and current for the selected line's region(s)
        if self.current_idx == 0:
            return  # no previous
        prev = self.current_idx - 1
        a_lines = self.lines_cache[prev]
        b_lines = self.lines_cache[self.current_idx]
        s = "\n".join(self._unified_samples(a_lines, b_lines, context=3))
        # popup simple pager
        self._pager(s)

    def _unified_samples(self, a_lines: List[str], b_lines: List[str], context: int = 3):
        import difflib
        name_a = self.versions[self.current_idx - 1][0]
        name_b = self.versions[self.current_idx][0]
        ud = difflib.unified_diff(a_lines, b_lines, fromfile=name_a, tofile=name_b, lineterm="")
        return list(ud)

    def _pager(self, text: str):
        h, w = self.screen.getmaxyx()
        lines = text.splitlines()
        pos = 0
        while True:
            self.screen.clear()
            # draw a box-like header
            header = " diff (press q or ESC to close) "
            try:
                self.screen.addnstr(0, 1, header, w-2, curses.A_BOLD)
            except curses.error:
                pass
            for i in range(1, h-2):
                ln = pos + i - 1
                if ln >= len(lines):
                    break
                try:
                    # naive color for + / -
                    line = lines[ln]
                    if line.startswith("+"):
                        self.screen.addnstr(i, 1, line[:w-2], w-2, curses.color_pair(PALETTE["added"]))
                    elif line.startswith("-"):
                        self.screen.addnstr(i, 1, line[:w-2], w-2, curses.color_pair(PALETTE["removed"]))
                    else:
                        self.screen.addnstr(i, 1, line[:w-2], w-2)
                except curses.error:
                    pass
            footer = f"lines {pos+1}..{min(pos+h-2, len(lines))} / {len(lines)}"
            try:
                self.screen.addnstr(h-1, 1, footer, w-2, curses.A_REVERSE)
            except curses.error:
                pass
            self.screen.refresh()
            ch = self.screen.getch()
            if ch in (ord('q'), ord('Q'), 27):  # ESC
                break
            elif ch == curses.KEY_DOWN:
                if pos + (h-2) < len(lines):
                    pos += 1
            elif ch == curses.KEY_UP:
                if pos > 0:
                    pos -= 1
            elif ch == curses.KEY_NPAGE:
                pos = min(len(lines) - (h-2), pos + (h-2))
            elif ch == curses.KEY_PPAGE:
                pos = max(0, pos - (h-2))
            # else ignore


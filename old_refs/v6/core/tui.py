# core/tui.py — integrates viewer + editor (editor operates inside right panel)
import curses
import difflib
from typing import List
from pathlib import Path
from core.editor import SimpleEditor
from core.diff_engine import DocDiffEngine

PALETTE = {
    "added": 1,
    "removed": 2,
    "title": 3,
    "hint": 4,
    "shadow": 5,
    "selected": 6
}

class DocTUIView:
    def __init__(self, engine: DocDiffEngine, history: List[dict]):
        self.engine = engine
        self.history = history
        self.version_list = [h["version"] for h in history]
        self.sel_index = len(self.version_list) - 1
        self.right_scroll = 0
        self.mode = "view"  # or "edit"
        self.status = ""  # Saved / No changes / Not saved messages

    def run(self):
        curses.wrapper(self._curses_main)

    def _init_colors(self):
        if curses.has_colors():
            curses.start_color()
            try:
                curses.use_default_colors()
            except Exception:
                pass
            curses.init_pair(PALETTE["added"], curses.COLOR_GREEN, -1)
            curses.init_pair(PALETTE["removed"], curses.COLOR_RED, -1)
            curses.init_pair(PALETTE["title"], curses.COLOR_CYAN, -1)
            curses.init_pair(PALETTE["hint"], curses.COLOR_YELLOW, -1)
            curses.init_pair(PALETTE["shadow"], curses.COLOR_BLACK, curses.COLOR_BLACK)
            curses.init_pair(PALETTE["selected"], curses.COLOR_BLACK, curses.COLOR_WHITE)

    def _curses_main(self, scr):
        curses.curs_set(0)
        scr.keypad(True)
        self._init_colors()
        while True:
            scr.erase()
            h, w = scr.getmaxyx()
            left_w = max(30, int(w*0.38))
            right_w = w - left_w - 3
            mid_y = h // 2

            # header
            title = " DRommage — docdiff v6 (editor integrated) "
            scr.addnstr(0, max(1, (w - len(title))//2), title, len(title),
                        curses.color_pair(PALETTE["title"]) | curses.A_BOLD)
            # separators
            for ry in range(1, h-1):
                try:
                    scr.addch(ry, left_w, curses.ACS_VLINE)
                except curses.error:
                    scr.addch(ry, left_w, ord('|'))
            try:
                scr.hline(mid_y, 1, curses.ACS_HLINE, left_w-1)
            except curses.error:
                for cx in range(1, left_w):
                    scr.addch(mid_y, cx, ord('-'))

            hint = "↑/↓ select version  PgUp/PgDn scroll doc  e edit  Enter diff  q quit"
            scr.addnstr(h-1, 1, hint[:w-2], w-2, curses.color_pair(PALETTE["hint"]))

            # draw panels
            self._draw_history(scr, 1, 1, left_w-1, mid_y-1)
            self._draw_changes(scr, mid_y+1, 1, left_w-1, h-mid_y-2)
            # right: document or editor
            if self.mode == "view":
                self._draw_document_view(scr, 1, left_w+2, right_w, h-2)
            else:
                # editor mode integrated
                self._run_editor_in_place(scr, 1, left_w+2, right_w, h-2)

            scr.refresh()
            ch = scr.getch()
            if ch in (ord('q'), ord('Q')):
                return
            if self.mode == "view":
                if ch in (curses.KEY_UP, ord('k')):
                    self.sel_index = max(0, self.sel_index - 1)
                    self.right_scroll = 0
                elif ch in (curses.KEY_DOWN, ord('j')):
                    self.sel_index = min(len(self.version_list)-1, self.sel_index + 1)
                    self.right_scroll = 0
                elif ch == curses.KEY_NPAGE:
                    self.right_scroll += (h - 6)
                elif ch == curses.KEY_PPAGE:
                    self.right_scroll = max(0, self.right_scroll - (h - 6))
                elif ch in (10,13):
                    self._show_diff_popup(scr)
                elif ch in (ord('e'), ord('E')):
                    choice = self._confirm_modal(scr)
                    if choice == 'y':
                        self.mode = "edit"
                        self._editor_target = self.version_list[self.sel_index]
                    elif choice == 'f':
                        self.mode = "edit"
                        self._editor_target = self.version_list[-1]
                    # else cancel
            # bound check scroll
            seq = self.engine.get_document_lines(self.version_list[self.sel_index])
            max_scroll = max(0, len(seq) - (h - 3))
            if self.right_scroll > max_scroll:
                self.right_scroll = max_scroll

    def _draw_history(self, scr, y, x, w, h):
        scr.addnstr(y, x, "History:", w, curses.A_BOLD)
        y += 1
        for i, hitem in enumerate(self.history[:h-2]):
            line = f"{'→' if i==self.sel_index else ' '} {hitem['version']} [{hitem['date']}] {hitem['title']}"
            attr = curses.color_pair(PALETTE["selected"]) if i==self.sel_index else 0
            scr.addnstr(y+i, x, line[:w], w, attr)

    def _draw_changes(self, scr, y, x, w, h):
        scr.addnstr(y, x, f"Changes ({self.version_list[self.sel_index]}):", w, curses.A_BOLD)
        y += 1
        prev = self.version_list[self.sel_index-1] if self.sel_index>0 else None
        if prev:
            ud = self.engine.get_unified_diff(prev, self.version_list[self.sel_index])
            i = 0
            for line in ud:
                if i >= h-2: break
                if line.startswith('+') and not line.startswith('+++'):
                    scr.addnstr(y+i, x+2, line[:w-4], w-4, curses.color_pair(PALETTE["added"]))
                elif line.startswith('-') and not line.startswith('---'):
                    scr.addnstr(y+i, x+2, line[:w-4], w-4, curses.color_pair(PALETTE["removed"]))
                else:
                    scr.addnstr(y+i, x+2, line[:w-4], w-4)
                i += 1

    def _draw_document_view(self, scr, y, x, w, h):
        ver = self.version_list[self.sel_index]
        seq = self.engine.get_document_lines(ver)
        visible = seq[self.right_scroll:self.right_scroll + h]
        for i, line in enumerate(visible):
            scr.addnstr(y+i, x, line[:w], w)

    def _confirm_modal(self, scr):
        h,w = scr.getmaxyx()
        mh, mw = 7, 64
        y0 = (h-mh)//2
        x0 = (w-mw)//2
        # shadow
        for yy in range(y0+1, y0+mh+1):
            try:
                scr.addstr(yy, x0+2, " "*mw, curses.color_pair(PALETTE["shadow"]))
            except curses.error:
                pass
        # window
        win = scr.subwin(mh, mw, y0, x0)
        win.box()
        win.addnstr(1,2,"А вы точно хотите править эту версию, а не последнюю?", mw-4)
        win.addnstr(3,4,"[Y] — Да, эту", mw-8)
        win.addnstr(4,4,"[F] — Править последнюю", mw-8)
        win.addnstr(5,4,"[N / Esc] — Нет", mw-8)
        win.refresh()
        while True:
            c = scr.getch()
            if c in (ord('y'), ord('Y')): return 'y'
            if c in (ord('f'), ord('F')): return 'f'
            if c in (ord('n'), ord('N'), 27): return 'n'

    def _run_editor_in_place(self, scr, y, x, w, h):
        # compose initial lines for editor from engine, but editor will run *inside* this same scr
        ver = self._editor_target
        lines = self.engine.get_document_lines(ver)
        editor = SimpleEditor(lines, filename_hint=ver)
        saved, status = editor.run(scr)
        # after editor returns, integrate status
        self.status = status
        if saved:
            # load saved into engine under new key (stem)
            newname = Path(saved).stem
            newver = newname
            self.engine.documents[newver] = open(saved, encoding="utf-8").read().splitlines()
            # append to lists (naive)
            if newver not in self.version_list:
                self.version_list.append(newver)
                self.history.append({"version":newver,"date":"edited","title":f"{ver} (edited)"})
        # return to view mode
        self.mode = "view"

    def _show_diff_popup(self, scr):
        ver = self.version_list[self.sel_index]
        if self.sel_index == 0:
            return
        prev = self.version_list[self.sel_index-1]
        ud = self.engine.get_unified_diff(prev, ver)
        self._pager(scr, ud, title=f"diff {prev} → {ver}")

    def _pager(self, scr, lines, title=""):
        h,w = scr.getmaxyx()
        page_h = h - 4
        pos = 0
        while True:
            scr.erase()
            scr.addnstr(0,2,title[:w-4],w-4,curses.color_pair(PALETTE["title"])|curses.A_BOLD)
            try:
                scr.hline(1,0,curses.ACS_HLINE,w)
            except curses.error:
                scr.addnstr(1,0,"-"*w,w)
            for i in range(page_h):
                if pos+i >= len(lines): break
                line = lines[pos+i]
                color = 0
                if line.startswith("+") and not line.startswith("+++"):
                    color = curses.color_pair(PALETTE["added"])
                elif line.startswith("-") and not line.startswith("---"):
                    color = curses.color_pair(PALETTE["removed"])
                scr.addnstr(2+i,2,line[:w-4],w-4,color)
            footer = f"{pos+1}/{max(1,len(lines))}  (PgDn/PgUp scroll, q/ESC to close)"
            scr.addnstr(h-1,2,footer[:w-4],w-4,curses.color_pair(PALETTE["hint"]))
            scr.refresh()
            c = scr.getch()
            if c in (ord('q'),27): break
            elif c == curses.KEY_NPAGE:
                pos = min(max(0,len(lines)-page_h), pos+page_h)
            elif c == curses.KEY_PPAGE:
                pos = max(0, pos-page_h)
            elif c == curses.KEY_DOWN:
                pos = min(max(0,len(lines)-page_h), pos+1)
            elif c == curses.KEY_UP:
                pos = max(0,pos-1)

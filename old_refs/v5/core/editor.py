# core/editor.py
# Simple terminal text editor component for curses.
# - arrow keys for movement
# - v  -> toggle selection mode (start/stop)
# - Ctrl-C -> copy selection
# - Ctrl-X -> cut selection
# - Ctrl-V -> paste
# - Ctrl-S -> save (writes to <version>_edited.txt) and exit (returns saved path)
# - ESC  -> cancel editing (returns None)

import curses
from typing import List, Optional

CTRL_C = 3
CTRL_X = 24
CTRL_V = 22
CTRL_S = 19
ESC = 27

class SimpleEditor:
    def __init__(self, lines: List[str], filename_hint: str):
        self.lines = lines[:]  # copy
        self.filename_hint = filename_hint
        self.cx = 0
        self.cy = 0
        self.scroll = 0
        self.clipboard = []
        self.select_mode = False
        self.sel_anchor = None  # (y,x) or None

    def run(self, scr) -> Optional[str]:
        curses.curs_set(1)
        scr.keypad(True)
        h, w = scr.getmaxyx()
        while True:
            scr.erase()
            self._render(scr, h, w)
            scr.move(self.cy - self.scroll + 1, self.cx + 1 + w//6)  # keep cursor in right area
            scr.refresh()
            ch = scr.getch()
            if ch in (ESC,):
                return None
            elif ch == CTRL_S:
                # save to file
                new_name = f"{self.filename_hint}_edited.txt"
                with open(new_name, "w", encoding="utf-8") as f:
                    f.write("\n".join(self.lines))
                return new_name
            elif ch == CTRL_C:
                self._copy_selection()
            elif ch == CTRL_X:
                self._cut_selection()
            elif ch == CTRL_V:
                self._paste_clipboard()
            elif ch == ord('v'):
                # toggle selection anchor
                if not self.select_mode:
                    self.select_mode = True
                    self.sel_anchor = (self.cy, self.cx)
                else:
                    self.select_mode = False
                    # leave anchor for next time
            elif ch in (curses.KEY_LEFT,):
                if self.cx > 0:
                    self.cx -= 1
                else:
                    if self.cy > 0:
                        self.cy -= 1
                        self.cx = len(self.lines[self.cy])
                self._ensure_scroll(h)
            elif ch in (curses.KEY_RIGHT,):
                if self.cx < len(self.lines[self.cy]):
                    self.cx += 1
                else:
                    if self.cy + 1 < len(self.lines):
                        self.cy += 1
                        self.cx = 0
                self._ensure_scroll(h)
            elif ch in (curses.KEY_UP,):
                if self.cy > 0:
                    self.cy -= 1
                    self.cx = min(self.cx, len(self.lines[self.cy]))
                self._ensure_scroll(h)
            elif ch in (curses.KEY_DOWN,):
                if self.cy + 1 < len(self.lines):
                    self.cy += 1
                    self.cx = min(self.cx, len(self.lines[self.cy]))
                self._ensure_scroll(h)
            elif ch in (curses.KEY_BACKSPACE, 127):
                if self.cx > 0:
                    line = self.lines[self.cy]
                    self.lines[self.cy] = line[:self.cx-1] + line[self.cx:]
                    self.cx -= 1
                else:
                    if self.cy > 0:
                        prev = self.lines[self.cy-1]
                        cur = self.lines.pop(self.cy)
                        self.cy -= 1
                        self.cx = len(prev)
                        self.lines[self.cy] = prev + cur
                self._ensure_scroll(h)
            elif ch in (10, 13):  # enter
                line = self.lines[self.cy]
                left = line[:self.cx]
                right = line[self.cx:]
                self.lines[self.cy] = left
                self.lines.insert(self.cy+1, right)
                self.cy += 1
                self.cx = 0
                self._ensure_scroll(h)
            elif 32 <= ch <= 126:  # printable
                line = self.lines[self.cy]
                self.lines[self.cy] = line[:self.cx] + chr(ch) + line[self.cx:]
                self.cx += 1
                self._ensure_scroll(h)
            # ignore other keys, continue loop

    def _ensure_scroll(self, h):
        visible = h - 3
        if self.cy < self.scroll:
            self.scroll = self.cy
        elif self.cy >= self.scroll + visible:
            self.scroll = self.cy - visible + 1

    def _render(self, scr, h, w):
        # left small gutter for line numbers; right is editor area
        gutter = w//6
        visible = h - 3
        for i in range(visible):
            ln = self.scroll + i
            if ln >= len(self.lines):
                break
            num = str(ln+1).rjust(4) + " "
            try:
                scr.addstr(1+i, 1, num[:gutter-1], curses.A_DIM)
                scr.addnstr(1+i, gutter+1, self.lines[ln][:w-gutter-2], w-gutter-2)
            except curses.error:
                pass
        # status
        status = f"EDIT {self.filename_hint}  |  Pos: {self.cy+1}:{self.cx}  |  v toggle selection  Ctrl-S save  Ctrl-C copy  Ctrl-X cut  Ctrl-V paste  Esc cancel"
        try:
            scr.addnstr(h-1, 1, status[:w-2], w-2, curses.A_REVERSE)
        except curses.error:
            pass
        # highlight selection if active
        if self.select_mode and self.sel_anchor:
            ay, ax = self.sel_anchor
            by, bx = self.cy, self.cx
            (sy, sx), (ey, ex) = ((ay, ax), (by, bx)) if (ay,ax) <= (by,bx) else ((by,bx),(ay,ax))
            for row in range(sy, ey+1):
                line = self.lines[row]
                a = sx if row == sy else 0
                b = ex if row == ey else len(line)
                if a < b:
                    scr.chgat(1 + row - self.scroll, w//6 + 1 + a, max(0, b-a), curses.A_STANDOUT)

    def _get_selection_range(self):
        if not self.sel_anchor:
            return None
        ay, ax = self.sel_anchor
        by, bx = self.cy, self.cx
        if (ay,ax) <= (by,bx):
            return (ay,ax,by,bx)
        return (by,bx,ay,ax)

    def _copy_selection(self):
        r = self._get_selection_range()
        if not r:
            return
        ay, ax, by, bx = r
        out = []
        for row in range(ay, by+1):
            line = self.lines[row]
            if row == ay and row == by:
                out.append(line[ax:bx])
            elif row == ay:
                out.append(line[ax:])
            elif row == by:
                out.append(line[:bx])
            else:
                out.append(line)
        self.clipboard = out

    def _cut_selection(self):
        r = self._get_selection_range()
        if not r:
            return
        ay, ax, by, bx = r
        new_lines = []
        for i, line in enumerate(self.lines):
            if i < ay or i > by:
                new_lines.append(line)
            else:
                if ay == by:
                    new_lines.append(line[:ax] + line[bx:])
                else:
                    if i == ay:
                        new_lines.append(line[:ax] + (self.lines[by][bx:] if by < len(self.lines) else ""))
                    elif i == by:
                        # already handled via ay
                        pass
                    else:
                        # middle lines removed
                        pass
        self.lines = new_lines
        self.cy, self.cx = ay, ax
        self.select_mode = False
        self.sel_anchor = None

    def _paste_clipboard(self):
        if not self.clipboard:
            return
        line = self.lines[self.cy]
        left = line[:self.cx]
        right = line[self.cx:]
        if len(self.clipboard) == 1:
            self.lines[self.cy] = left + self.clipboard[0] + right
            self.cx += len(self.clipboard[0])
        else:
            first = left + self.clipboard[0]
            last = self.clipboard[-1] + right
            mid = self.clipboard[1:-1]
            self.lines[self.cy] = first
            for idx, l in enumerate(mid):
                self.lines.insert(self.cy+1+idx, l)
            self.lines.insert(self.cy+1+len(mid), last)
            self.cy += len(self.clipboard)-1
            self.cx = len(self.clipboard[-1])

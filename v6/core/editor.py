# core/editor.py
# Editor component used inside right panel (integrated, not separate window).
# Features:
#  - arrow keys for movement
#  - Ctrl+Left / Ctrl+Right (common escape sequences) to jump words
#  - Home / End
#  - v (toggle selection) OR Shift-arrows when supported
#  - Ctrl-C / Ctrl-X / Ctrl-V copy/cut/paste
#  - Ctrl-S save and exit (returns (saved_path, status)), ESC exit without save (returns (None, status))
#  - Ctrl-Z / Ctrl-Y undo / redo
#  - status messages "Saved", "No changes", "Not saved" handled by caller

import curses
import re
from typing import List, Optional, Tuple

CTRL_C = 3
CTRL_X = 24
CTRL_V = 22
CTRL_S = 19
CTRL_Z = 26
CTRL_Y = 25
ESC = 27

# Helper: detect typical ctrl-arrow escape sequences: ESC [ 1 ; 5 C  (ctrl-right)
# We'll parse an escape sequence (starting with 27) if present.

def _read_escape_sequence(scr, first=27, timeout_ms=50):
    """Try to read the rest of an escape sequence; non-blocking short wait."""
    scr.nodelay(True)
    seq = [first]
    try:
        import time
        t0 = time.time()
        while True:
            ch = scr.getch()
            if ch == -1:
                # small sleep loop until timeout reached
                if (time.time() - t0) * 1000 > timeout_ms:
                    break
                continue
            seq.append(ch)
            # if char is letter (A-Z,a-z) or ~ likely end
            if (65 <= ch <= 90) or (97 <= ch <= 122) or ch == ord('~'):
                break
    finally:
        scr.nodelay(False)
    return bytes(seq)

class SimpleEditor:
    def __init__(self, lines: List[str], filename_hint: str):
        self.lines = lines[:] if lines else [""]
        self.filename_hint = filename_hint
        self.cx = 0
        self.cy = 0
        self.scroll = 0
        self.clipboard: List[str] = []
        self.select_mode = False
        self.sel_anchor = None  # (y,x)
        # undo/redo stacks store copies of lines
        self.undo_stack: List[List[str]] = []
        self.redo_stack: List[List[str]] = []
        self._push_undo()  # initial state
        self.modified = False

    def _push_undo(self):
        # shallow copy of list-of-lines
        self.undo_stack.append(self.lines.copy())
        if len(self.undo_stack) > 200:
            self.undo_stack.pop(0)
        # clear redo on new edit
        self.redo_stack.clear()

    def _undo(self):
        if len(self.undo_stack) <= 1:
            return
        cur = self.undo_stack.pop()
        self.redo_stack.append(cur)
        prev = self.undo_stack[-1]
        self.lines = prev.copy()
        self.cx = 0; self.cy = 0; self.scroll = 0
        self.modified = True

    def _redo(self):
        if not self.redo_stack:
            return
        nxt = self.redo_stack.pop()
        self.lines = nxt.copy()
        self.undo_stack.append(nxt.copy())
        self.modified = True

    def run(self, scr) -> Tuple[Optional[str], str]:
        """Return (saved_filename or None, status_message)"""
        curses.curs_set(1)
        scr.keypad(True)
        h, w = scr.getmaxyx()
        gutter = max(6, w//8)
        edit_x = gutter + 1
        while True:
            scr.erase()
            h, w = scr.getmaxyx()
            gutter = max(6, w//8)
            edit_x = gutter + 1
            self._ensure_scroll(h-3)
            self._render(scr, h, w, gutter, edit_x)
            # move cursor
            try:
                scr.move(1 + (self.cy - self.scroll), edit_x + self.cx)
            except curses.error:
                pass
            scr.refresh()
            ch = scr.getch()

            # handle escape sequences for Ctrl-arrow etc.
            if ch == ESC:
                # try to read sequence
                seq = _read_escape_sequence(scr, 27)
                # decode some known sequences
                s = seq.decode('latin1', errors='ignore')
                # ctrl-right often: ESC [ 1 ; 5 C  or ESC [ 5 C
                if seq.startswith(b'\x1b[') and seq.endswith(b'C') and b';5' in seq:
                    self._jump_word_right()
                    continue
                if seq.startswith(b'\x1b[') and seq.endswith(b'D') and b';5' in seq:
                    self._jump_word_left()
                    continue
                # if sequence empty -> treat as ESC (exit)
                if len(seq) == 1:
                    # ESC pressed alone -> exit without save (Not saved if modified)
                    if self.modified:
                        return (None, "Not saved")
                    else:
                        return (None, "No changes")
                # otherwise ignore unknown seq and continue

            # Ctrl keys
            if ch == CTRL_S:
                # save
                fname = f"{self.filename_hint}_edited.txt"
                with open(fname, "w", encoding="utf-8") as f:
                    f.write("\n".join(self.lines))
                self.modified = False
                return (fname, "Saved")
            if ch == CTRL_Z:
                self._undo()
                continue
            if ch == CTRL_Y:
                self._redo()
                continue
            if ch == CTRL_C:
                self._copy_selection()
                self._clear_selection()
                continue
            if ch == CTRL_X:
                self._cut_selection()
                self._clear_selection()
                self._push_undo()
                self.modified = True
                continue
            if ch == CTRL_V:
                self._paste_clipboard()
                self._push_undo()
                self.modified = True
                self._clear_selection()
                continue

            # navigation keys & editing
            if ch in (curses.KEY_LEFT,):
                self._move_left()
                continue
            if ch in (curses.KEY_RIGHT,):
                self._move_right()
                continue
            if ch in (curses.KEY_UP,):
                self._move_up()
                continue
            if ch in (curses.KEY_DOWN,):
                self._move_down()
                continue
            if ch in (curses.KEY_HOME,):
                self.cx = 0
                continue
            if ch in (curses.KEY_END,):
                self.cx = len(self.lines[self.cy])
                continue
            if ch in (curses.KEY_BACKSPACE, 127):
                self._backspace()
                self._push_undo()
                self.modified = True
                continue
            if ch in (10,13):
                self._enter()
                self._push_undo()
                self.modified = True
                continue
            # printable
            if 32 <= ch <= 126:
                self._insert_char(chr(ch))
                self._push_undo()
                self.modified = True
                continue
            # toggle selection (fallback) : 'V' (capital V) or 'v' if you prefer
            if ch in (ord('V'),):
                if not self.select_mode:
                    self.select_mode = True
                    self.sel_anchor = (self.cy, self.cx)
                else:
                    self.select_mode = False
                    # leave anchor for copy/cut if user wants; but we clear after actions
                continue
            # ignore unknown keys

    # low-level operations
    def _ensure_scroll(self, h):
        visible = h
        if self.cy < self.scroll:
            self.scroll = self.cy
        elif self.cy >= self.scroll + visible:
            self.scroll = self.cy - visible + 1

    def _render(self, scr, h, w, gutter, edit_x):
        visible = h - 3
        for i in range(visible):
            ln = self.scroll + i
            if ln >= len(self.lines):
                break
            try:
                scr.addstr(1+i, 1, str(ln+1).rjust(gutter-1)+" ", curses.A_DIM)
                scr.addnstr(1+i, edit_x, self.lines[ln][:w-edit_x-1], w-edit_x-1)
            except curses.error:
                pass
        # status
        undo_len = len(self.undo_stack)-1
        redo_len = len(self.redo_stack)
        status = f"EDIT {self.filename_hint}  |  Pos: {self.cy+1}:{self.cx}  |  Undo {undo_len} / Redo {redo_len}  |  Ctrl-S save  Esc cancel"
        try:
            scr.addnstr(h-1, 1, status[:w-2], w-2, curses.A_REVERSE)
        except curses.error:
            pass
        # highlight selection visually
        if self.select_mode and self.sel_anchor:
            ay, ax = self.sel_anchor
            by, bx = self.cy, self.cx
            (sy, sx), (ey, ex) = ((ay,ax),(by,bx)) if (ay,ax) <= (by,bx) else ((by,bx),(ay,ax))
            for row in range(sy, ey+1):
                if row < self.scroll or row >= self.scroll + visible:
                    continue
                line = self.lines[row]
                a = sx if row == sy else 0
                b = ex if row == ey else len(line)
                if a < b:
                    try:
                        scr.chgat(1 + (row - self.scroll), edit_x + a, max(0,b-a), curses.A_STANDOUT)
                    except curses.error:
                        pass

    def _move_left(self):
        if self.cx > 0:
            self.cx -= 1
        elif self.cy > 0:
            self.cy -= 1
            self.cx = len(self.lines[self.cy])
        # if select mode, keep anchor; otherwise clear selection
        if not self.select_mode:
            self.sel_anchor = None

    def _move_right(self):
        if self.cx < len(self.lines[self.cy]):
            self.cx += 1
        elif self.cy + 1 < len(self.lines):
            self.cy += 1
            self.cx = 0
        if not self.select_mode:
            self.sel_anchor = None

    def _move_up(self):
        if self.cy > 0:
            self.cy -= 1
            self.cx = min(self.cx, len(self.lines[self.cy]))
        if not self.select_mode:
            self.sel_anchor = None

    def _move_down(self):
        if self.cy + 1 < len(self.lines):
            self.cy += 1
            self.cx = min(self.cx, len(self.lines[self.cy]))
        if not self.select_mode:
            self.sel_anchor = None

    def _jump_word_right(self):
        line = self.lines[self.cy]
        # find word boundary after cx
        m = re.search(r'\w+\W*', line[self.cx:])
        if m:
            self.cx += m.end()
        else:
            # go to next line start if exists
            if self.cy + 1 < len(self.lines):
                self.cy += 1
                self.cx = 0
        if not self.select_mode:
            self.sel_anchor = None

    def _jump_word_left(self):
        line = self.lines[self.cy]
        left = line[:self.cx]
        # find last word start in left
        m = list(re.finditer(r'\w+', left))
        if m:
            self.cx = m[-1].start()
        else:
            if self.cy > 0:
                self.cy -= 1
                self.cx = len(self.lines[self.cy])
        if not self.select_mode:
            self.sel_anchor = None

    def _backspace(self):
        if self.select_mode and self.sel_anchor:
            # delete selection
            self._cut_selection()
            return
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

    def _enter(self):
        line = self.lines[self.cy]
        left = line[:self.cx]
        right = line[self.cx:]
        self.lines[self.cy] = left
        self.lines.insert(self.cy+1, right)
        self.cy += 1
        self.cx = 0

    def _insert_char(self, ch):
        if self.select_mode and self.sel_anchor:
            # replace selection with char
            self._cut_selection()
        line = self.lines[self.cy]
        self.lines[self.cy] = line[:self.cx] + ch + line[self.cx:]
        self.cx += 1

    def _get_selection_range(self):
        if not self.sel_anchor:
            return None
        ay, ax = self.sel_anchor
        by, bx = self.cy, self.cx
        if (ay,ax) <= (by,bx):
            return (ay,ax,by,bx)
        else:
            return (by,bx,ay,ax)

    def _copy_selection(self):
        r = self._get_selection_range()
        if not r:
            return
        ay, ax, by, bx = r
        out = []
        for row in range(ay, by+1):
            line = self.lines[row]
            if ay == by:
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
                        prefix = line[:ax]
                        if by < len(self.lines):
                            suffix = self.lines[by][bx:]
                        else:
                            suffix = ""
                        new_lines.append(prefix + suffix)
                    # middle lines are removed
        self.lines = new_lines
        self.cy, self.cx = ay, ax
        self.sel_anchor = None
        self.select_mode = False

    def _paste_clipboard(self):
        if not self.clipboard:
            return
        if len(self.clipboard) == 1:
            line = self.lines[self.cy]
            self.lines[self.cy] = line[:self.cx] + self.clipboard[0] + line[self.cx:]
            self.cx += len(self.clipboard[0])
        else:
            left = self.lines[self.cy][:self.cx]
            right = self.lines[self.cy][self.cx:]
            first = left + self.clipboard[0]
            last = self.clipboard[-1] + right
            mid = self.clipboard[1:-1]
            self.lines[self.cy] = first
            for idx, l in enumerate(mid):
                self.lines.insert(self.cy+1+idx, l)
            self.lines.insert(self.cy+1+len(mid), last)
            self.cy += len(self.clipboard)-1

    def _clear_selection(self):
        self.select_mode = False
        self.sel_anchor = None

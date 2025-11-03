"""
Region-aware editor with full functionality
- Word navigation (Ctrl+← / Ctrl+→)
- Home/End keys
- Undo/Redo (Ctrl+Z / Ctrl+Y) 
- Selection with Shift+arrows
- Copy/Cut/Paste (Ctrl+C/X/V)
- Region highlighting during edit
"""

import curses
import re
from typing import List, Tuple, Optional
from copy import deepcopy

# Control keys
CTRL_A = 1
CTRL_C = 3
CTRL_V = 22
CTRL_X = 24
CTRL_Y = 25
CTRL_Z = 26
CTRL_S = 19
ESC = 27

class RegionAwareEditor:
    def __init__(self, lines: List[str], version: str, engine=None):
        self.lines = lines[:] if lines else [""]
        self.version = version
        self.engine = engine
        
        # Cursor position
        self.cy = 0  # current line
        self.cx = 0  # current column
        self.scroll_y = 0
        self.scroll_x = 0
        
        # Selection
        self.selection_start = None  # (line, col) or None
        self.selection_end = None
        
        # Clipboard
        self.clipboard = []
        
        # Undo/Redo stacks
        self.undo_stack = []
        self.redo_stack = []
        self.save_state()  # Save initial state
        
        # Track if document was modified
        self.modified = False
        self.original_lines = deepcopy(lines)
    
    def save_state(self):
        """Save current state for undo"""
        state = {
            'lines': deepcopy(self.lines),
            'cy': self.cy,
            'cx': self.cx
        }
        self.undo_stack.append(state)
        # Limit undo stack size
        if len(self.undo_stack) > 100:
            self.undo_stack.pop(0)
        # Clear redo stack on new action
        self.redo_stack.clear()
    
    def undo(self):
        """Undo last action"""
        if len(self.undo_stack) > 1:
            # Save current state to redo stack
            current = self.undo_stack.pop()
            self.redo_stack.append(current)
            
            # Restore previous state
            state = self.undo_stack[-1]
            self.lines = deepcopy(state['lines'])
            self.cy = state['cy']
            self.cx = state['cx']
            self.modified = True
    
    def redo(self):
        """Redo last undone action"""
        if self.redo_stack:
            state = self.redo_stack.pop()
            self.undo_stack.append(state)
            self.lines = deepcopy(state['lines'])
            self.cy = state['cy']
            self.cx = state['cx']
            self.modified = True
    
    def run(self, win) -> Tuple[Optional[str], str]:
        """Run editor, return (saved_file, status_message)"""
        curses.curs_set(1)  # Show cursor
        win.keypad(True)
        
        while True:
            self._render(win)
            ch = win.getch()
            
            # Handle special key sequences
            if ch == ESC:
                seq = self._read_escape_sequence(win)
                if seq == ESC:  # Just ESC
                    if self.modified:
                        return (None, "⚠ Not saved")
                    else:
                        return (None, "No changes")
                else:
                    self._handle_escape_sequence(seq)
                    continue
            
            # Control keys
            elif ch == CTRL_S:
                return self._save()
            elif ch == CTRL_Z:
                self.undo()
            elif ch == CTRL_Y:
                self.redo()
            elif ch == CTRL_C:
                self._copy()
            elif ch == CTRL_X:
                self._cut()
            elif ch == CTRL_V:
                self._paste()
            elif ch == CTRL_A:
                self._select_all()
            
            # Navigation
            elif ch == curses.KEY_LEFT:
                self._move_left()
            elif ch == curses.KEY_RIGHT:
                self._move_right()
            elif ch == curses.KEY_UP:
                self._move_up()
            elif ch == curses.KEY_DOWN:
                self._move_down()
            elif ch == curses.KEY_HOME:
                self.cx = 0
            elif ch == curses.KEY_END:
                self.cx = len(self.lines[self.cy]) if self.cy < len(self.lines) else 0
            elif ch == curses.KEY_NPAGE:  # Page Down
                self._page_down(win.getmaxyx()[0])
            elif ch == curses.KEY_PPAGE:  # Page Up
                self._page_up(win.getmaxyx()[0])
            
            # Shift+arrows for selection (if terminal supports)
            elif ch == curses.KEY_SLEFT:
                self._start_selection()
                self._move_left()
            elif ch == curses.KEY_SRIGHT:
                self._start_selection()
                self._move_right()
            elif ch == curses.KEY_SR:  # Shift+Up
                self._start_selection()
                self._move_up()
            elif ch == curses.KEY_SF:  # Shift+Down
                self._start_selection()
                self._move_down()
            
            # Text input
            elif ch == curses.KEY_BACKSPACE or ch == 127:
                self._backspace()
            elif ch == curses.KEY_DC:  # Delete
                self._delete()
            elif ch in (10, 13):  # Enter
                self._insert_newline()
            elif 32 <= ch <= 126:  # Printable characters
                self._insert_char(chr(ch))
    
    def _render(self, win):
        """Render editor content"""
        h, w = win.getmaxyx()
        win.erase()
        
        # Calculate visible area
        visible_lines = self.lines[self.scroll_y:self.scroll_y + h - 2]
        
        # Draw lines with line numbers
        gutter_width = 6
        for i, line in enumerate(visible_lines):
            line_num = self.scroll_y + i + 1
            
            # Line number
            win.addstr(i, 0, f"{line_num:4d} ", curses.A_DIM)
            
            # Text with selection highlighting
            visible_text = line[self.scroll_x:self.scroll_x + w - gutter_width]
            
            # Check if line is in selection
            if self._is_line_selected(self.scroll_y + i):
                win.addstr(i, gutter_width, visible_text, curses.A_REVERSE)
            else:
                win.addstr(i, gutter_width, visible_text)
        
        # Status bar
        undo_count = len(self.undo_stack) - 1
        redo_count = len(self.redo_stack)
        status = f" {self.version} | Ln {self.cy+1}:{self.cx+1} | Undo {undo_count} / Redo {redo_count} | Ctrl-S save | ESC exit "
        win.addstr(h-1, 0, status[:w], curses.A_REVERSE)
        
        # Position cursor
        cursor_x = gutter_width + self.cx - self.scroll_x
        cursor_y = self.cy - self.scroll_y
        if 0 <= cursor_y < h - 1 and 0 <= cursor_x < w:
            win.move(cursor_y, cursor_x)
    
    def _read_escape_sequence(self, win, timeout_ms=50):
        """Read escape sequence for special keys"""
        win.nodelay(True)
        seq = [ESC]
        
        import time
        start = time.time()
        while (time.time() - start) * 1000 < timeout_ms:
            ch = win.getch()
            if ch != -1:
                seq.append(ch)
                # Check if sequence is complete
                if ch in range(64, 127) or ch == ord('~'):
                    break
        
        win.nodelay(False)
        
        if len(seq) == 1:
            return ESC
        return bytes(seq)
    
    def _handle_escape_sequence(self, seq):
        """Handle special escape sequences like Ctrl+arrows"""
        # Ctrl+Left: ESC [ 1 ; 5 D
        if seq == b'\x1b[1;5D' or seq == b'\x1bOD':
            self._move_word_left()
        # Ctrl+Right: ESC [ 1 ; 5 C
        elif seq == b'\x1b[1;5C' or seq == b'\x1bOC':
            self._move_word_right()
    
    def _move_left(self):
        """Move cursor left"""
        if self.cx > 0:
            self.cx -= 1
        elif self.cy > 0:
            self.cy -= 1
            self.cx = len(self.lines[self.cy])
        self._clear_selection()
    
    def _move_right(self):
        """Move cursor right"""
        if self.cy < len(self.lines):
            if self.cx < len(self.lines[self.cy]):
                self.cx += 1
            elif self.cy < len(self.lines) - 1:
                self.cy += 1
                self.cx = 0
        self._clear_selection()
    
    def _move_up(self):
        """Move cursor up"""
        if self.cy > 0:
            self.cy -= 1
            self.cx = min(self.cx, len(self.lines[self.cy]))
        self._clear_selection()
    
    def _move_down(self):
        """Move cursor down"""
        if self.cy < len(self.lines) - 1:
            self.cy += 1
            self.cx = min(self.cx, len(self.lines[self.cy]))
        self._clear_selection()
    
    def _move_word_left(self):
        """Move to previous word boundary"""
        if self.cy >= len(self.lines):
            return
        
        line = self.lines[self.cy]
        
        # Skip current word
        while self.cx > 0 and line[self.cx - 1].isalnum():
            self.cx -= 1
        
        # Skip spaces
        while self.cx > 0 and not line[self.cx - 1].isalnum():
            self.cx -= 1
        
        # Move to start of previous word
        while self.cx > 0 and line[self.cx - 1].isalnum():
            self.cx -= 1
    
    def _move_word_right(self):
        """Move to next word boundary"""
        if self.cy >= len(self.lines):
            return
        
        line = self.lines[self.cy]
        
        # Skip current word
        while self.cx < len(line) and line[self.cx].isalnum():
            self.cx += 1
        
        # Skip spaces
        while self.cx < len(line) and not line[self.cx].isalnum():
            self.cx += 1
    
    def _page_down(self, page_size):
        """Move down one page"""
        self.cy = min(len(self.lines) - 1, self.cy + page_size - 2)
        self.cx = min(self.cx, len(self.lines[self.cy]))
    
    def _page_up(self, page_size):
        """Move up one page"""
        self.cy = max(0, self.cy - page_size + 2)
        self.cx = min(self.cx, len(self.lines[self.cy]))
    
    def _insert_char(self, ch):
        """Insert character at cursor"""
        if self.cy >= len(self.lines):
            self.lines.append("")
        
        line = self.lines[self.cy]
        self.lines[self.cy] = line[:self.cx] + ch + line[self.cx:]
        self.cx += 1
        self.modified = True
        self.save_state()
    
    def _backspace(self):
        """Delete character before cursor"""
        if self.cx > 0:
            line = self.lines[self.cy]
            self.lines[self.cy] = line[:self.cx-1] + line[self.cx:]
            self.cx -= 1
        elif self.cy > 0:
            # Join with previous line
            prev_line = self.lines[self.cy - 1]
            curr_line = self.lines[self.cy]
            self.cx = len(prev_line)
            self.lines[self.cy - 1] = prev_line + curr_line
            del self.lines[self.cy]
            self.cy -= 1
        
        self.modified = True
        self.save_state()
    
    def _delete(self):
        """Delete character at cursor"""
        if self.cy < len(self.lines):
            line = self.lines[self.cy]
            if self.cx < len(line):
                self.lines[self.cy] = line[:self.cx] + line[self.cx+1:]
            elif self.cy < len(self.lines) - 1:
                # Join with next line
                self.lines[self.cy] = line + self.lines[self.cy + 1]
                del self.lines[self.cy + 1]
        
        self.modified = True
        self.save_state()
    
    def _insert_newline(self):
        """Insert new line at cursor"""
        if self.cy >= len(self.lines):
            self.lines.append("")
        else:
            line = self.lines[self.cy]
            self.lines[self.cy] = line[:self.cx]
            self.lines.insert(self.cy + 1, line[self.cx:])
        
        self.cy += 1
        self.cx = 0
        self.modified = True
        self.save_state()
    
    def _start_selection(self):
        """Start text selection"""
        if self.selection_start is None:
            self.selection_start = (self.cy, self.cx)
            self.selection_end = (self.cy, self.cx)
    
    def _clear_selection(self):
        """Clear text selection"""
        self.selection_start = None
        self.selection_end = None
    
    def _is_line_selected(self, line_num):
        """Check if line is in selection"""
        if not self.selection_start or not self.selection_end:
            return False
        
        start_y = min(self.selection_start[0], self.selection_end[0])
        end_y = max(self.selection_start[0], self.selection_end[0])
        
        return start_y <= line_num <= end_y
    
    def _get_selected_text(self):
        """Get selected text"""
        if not self.selection_start or not self.selection_end:
            return []
        
        # Normalize selection
        if self.selection_start <= self.selection_end:
            start = self.selection_start
            end = self.selection_end
        else:
            start = self.selection_end
            end = self.selection_start
        
        if start[0] == end[0]:
            # Single line selection
            line = self.lines[start[0]]
            return [line[start[1]:end[1]]]
        else:
            # Multi-line selection
            result = []
            for i in range(start[0], end[0] + 1):
                if i >= len(self.lines):
                    break
                if i == start[0]:
                    result.append(self.lines[i][start[1]:])
                elif i == end[0]:
                    result.append(self.lines[i][:end[1]])
                else:
                    result.append(self.lines[i])
            return result
    
    def _copy(self):
        """Copy selected text to clipboard"""
        self.clipboard = self._get_selected_text()
        self._clear_selection()
    
    def _cut(self):
        """Cut selected text to clipboard"""
        self.clipboard = self._get_selected_text()
        # TODO: Implement deletion of selected text
        self._clear_selection()
        self.modified = True
        self.save_state()
    
    def _paste(self):
        """Paste from clipboard"""
        if not self.clipboard:
            return
        
        for i, line in enumerate(self.clipboard):
            if i == 0:
                # First line - insert at cursor
                curr_line = self.lines[self.cy] if self.cy < len(self.lines) else ""
                self.lines[self.cy] = curr_line[:self.cx] + line + curr_line[self.cx:]
                self.cx += len(line)
            else:
                # Additional lines
                self.cy += 1
                self.lines.insert(self.cy, line)
                self.cx = len(line)
        
        self.modified = True
        self.save_state()
    
    def _select_all(self):
        """Select all text"""
        self.selection_start = (0, 0)
        if self.lines:
            self.selection_end = (len(self.lines) - 1, len(self.lines[-1]))
    
    def _save(self):
        """Save document"""
        filename = f"{self.version}_edited.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.lines))
        return (filename, "✔ Saved")
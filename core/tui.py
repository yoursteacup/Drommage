"""
TUI v7 - Three-panel interface with region tracking
Left top: Version history
Left bottom: Region analysis (volatility, changes)  
Right: Document with highlighted regions + integrated editor
"""

import curses
from typing import List, Optional
from pathlib import Path
from core.git_engine import GitDiffEngine
from core.region_index import RegionIndex
# from core.editor import RegionAwareEditor  # Временно отключен

PALETTE = {
    "added": 1,
    "removed": 2,
    "modified": 3,
    "stable": 4,
    "volatile": 5,
    "title": 6,
    "selected": 7,
    "region_highlight": 8,
    "hint": 9
}

class DocTUIView:
    def __init__(self, engine: GitDiffEngine, region_index: RegionIndex, history: List[dict]):
        self.engine = engine
        self.region_index = region_index
        self.history = history
        self.versions = [h["version"] for h in history]
        
        # UI state
        self.selected_version_idx = len(self.versions) - 1
        self.selected_region = None
        self.mode = "view"  # view, edit, region_detail
        self.right_scroll = 0
        self.status = ""
        
    def run(self):
        curses.wrapper(self._main)
    
    def _init_colors(self):
        if curses.has_colors():
            curses.start_color()
            try:
                curses.use_default_colors()
            except:
                pass
            
            curses.init_pair(PALETTE["added"], curses.COLOR_GREEN, -1)
            curses.init_pair(PALETTE["removed"], curses.COLOR_RED, -1)
            curses.init_pair(PALETTE["modified"], curses.COLOR_YELLOW, -1)
            curses.init_pair(PALETTE["stable"], curses.COLOR_CYAN, -1)
            curses.init_pair(PALETTE["volatile"], curses.COLOR_MAGENTA, -1)
            curses.init_pair(PALETTE["title"], curses.COLOR_CYAN, -1)
            curses.init_pair(PALETTE["selected"], curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(PALETTE["region_highlight"], curses.COLOR_BLACK, curses.COLOR_YELLOW)
            curses.init_pair(PALETTE["hint"], curses.COLOR_WHITE, -1)
    
    def _main(self, scr):
        curses.curs_set(0)
        scr.keypad(True)
        self._init_colors()
        
        while True:
            scr.erase()
            h, w = scr.getmaxyx()
            
            # Layout
            left_width = int(w * 0.4)
            right_width = w - left_width - 1
            mid_y = int(h * 0.5)
            
            # Draw frame
            self._draw_frame(scr, h, w, left_width, mid_y)
            
            # Draw panels based on mode
            if self.mode == "view":
                self._draw_history_panel(scr, 2, 1, left_width - 2, mid_y - 3)
                self._draw_regions_panel(scr, mid_y + 1, 1, left_width - 2, h - mid_y - 3)
                self._draw_document_panel(scr, 2, left_width + 2, right_width - 2, h - 4)
            elif self.mode == "region_detail":
                self._draw_history_panel(scr, 2, 1, left_width - 2, mid_y - 3)
                self._draw_region_detail(scr, mid_y + 1, 1, left_width - 2, h - mid_y - 3)
                self._draw_region_history(scr, 2, left_width + 2, right_width - 2, h - 4)
            # elif self.mode == "edit":
            #     # Editor temporarily disabled
            #     pass
            
            # Status bar
            self._draw_status(scr, h - 1, w)
            
            scr.refresh()
            
            # Handle input
            ch = scr.getch()
            if not self._handle_input(ch):
                break
    
    def _draw_frame(self, scr, h, w, left_width, mid_y):
        """Draw the UI frame and separators"""
        # Title
        title = " DRommage v7 - Git-based Region Tracking "
        scr.addstr(0, max(0, (w - len(title)) // 2), title, 
                   curses.color_pair(PALETTE["title"]) | curses.A_BOLD)
        
        # Vertical separator
        for y in range(1, h - 1):
            try:
                scr.addch(y, left_width, curses.ACS_VLINE)
            except:
                scr.addch(y, left_width, '|')
        
        # Horizontal separator (left panel)
        try:
            scr.hline(mid_y, 0, curses.ACS_HLINE, left_width)
        except:
            for x in range(left_width):
                scr.addch(mid_y, x, '-')
    
    def _draw_history_panel(self, scr, y, x, w, h):
        """Draw version history in top-left panel"""
        scr.addstr(y, x, "📚 Version History", curses.A_BOLD)
        y += 2
        
        for i, hist in enumerate(self.history[:h-2]):
            if i == self.selected_version_idx:
                attr = curses.color_pair(PALETTE["selected"])
                prefix = "→"
            else:
                attr = 0
                prefix = " "
            
            line = f"{prefix} {hist['version']} [{hist['date']}] {hist['title']}"
            try:
                scr.addnstr(y + i, x, line[:w], w, attr)
            except:
                pass
    
    def _draw_regions_panel(self, scr, y, x, w, h):
        """Draw region analysis in bottom-left panel"""
        version = self.versions[self.selected_version_idx]
        regions = self.region_index.get_regions_for_version(version)
        
        scr.addstr(y, x, f"🧩 Regions in {version}", curses.A_BOLD)
        y += 2
        
        # Show volatile regions
        volatile = self.region_index.get_most_volatile_regions(3)
        if volatile:
            scr.addstr(y, x, "Most changed:", curses.color_pair(PALETTE["volatile"]))
            y += 1
            for r in volatile[:min(3, h-4)]:
                preview = r.canonical_text[:30].replace('\n', ' ')
                line = f"  {r.versions_modified}× {preview}..."
                try:
                    scr.addnstr(y, x, line[:w], w)
                except:
                    pass
                y += 1
        
        # Show stable regions
        if y < h - 3:
            stable = self.region_index.get_most_stable_regions(2)
            if stable:
                y += 1
                scr.addstr(y, x, "Most stable:", curses.color_pair(PALETTE["stable"]))
                y += 1
                for r in stable[:min(2, h-y)]:
                    preview = r.canonical_text[:30].replace('\n', ' ')
                    line = f"  ✓ {preview}..."
                    try:
                        scr.addnstr(y, x, line[:w], w)
                    except:
                        pass
                    y += 1
    
    def _draw_document_panel(self, scr, y, x, w, h):
        """Draw document with highlighted regions"""
        version = self.versions[self.selected_version_idx]
        lines = self.engine.get_document_lines(version)
        
        # Header
        scr.addstr(y, x, f"📄 Document: {version}", curses.A_BOLD)
        y += 2
        
        # Document lines with region highlighting
        visible_lines = lines[self.right_scroll:self.right_scroll + h - 2]
        
        for i, line in enumerate(visible_lines):
            line_num = self.right_scroll + i
            
            # Check if this line belongs to a region
            region = self.engine.get_region_at_line(version, line_num)
            
            if region:
                # Highlight based on region volatility
                if region.id in [r.id for r in self.region_index.get_most_volatile_regions()]:
                    attr = curses.color_pair(PALETTE["volatile"])
                elif region.id in [r.id for r in self.region_index.get_most_stable_regions()]:
                    attr = curses.color_pair(PALETTE["stable"])
                else:
                    attr = curses.color_pair(PALETTE["modified"])
                    
                # Add region indicator
                if self.selected_region == region.id:
                    attr = curses.color_pair(PALETTE["region_highlight"])
                    prefix = "▶ "
                else:
                    prefix = "│ "
            else:
                attr = 0
                prefix = "  "
            
            try:
                scr.addstr(y + i, x, prefix)
                scr.addnstr(y + i, x + 2, line[:w-2], w-2, attr)
            except:
                pass
    
    def _draw_region_detail(self, scr, y, x, w, h):
        """Show details of selected region"""
        if not self.selected_region:
            return
            
        region = self.engine.regions.get(self.selected_region)
        if not region:
            return
        
        scr.addstr(y, x, "🔍 Region Details", curses.A_BOLD)
        y += 2
        
        # Region stats
        summary = self.region_index.region_summaries.get(self.selected_region)
        if summary:
            scr.addstr(y, x, f"Changes: {summary.versions_modified}")
            y += 1
            scr.addstr(y, x, f"+{summary.total_additions} -{summary.total_deletions}")
            y += 1
            scr.addstr(y, x, f"Stability: {'█' * int(summary.stability_score * 10)}")
            y += 2
        
        # Region preview
        preview = region.canonical_text[:200]
        for line in preview.split('\n')[:h-6]:
            try:
                scr.addnstr(y, x, line[:w], w)
            except:
                pass
            y += 1
    
    def _draw_region_history(self, scr, y, x, w, h):
        """Show history of selected region"""
        if not self.selected_region:
            return
            
        history = self.region_index.get_region_history(self.selected_region)
        
        scr.addstr(y, x, "📜 Region History", curses.A_BOLD)
        y += 2
        
        for entry in history[:h-2]:
            version = entry["version"]
            action = entry["action"]
            
            if action == "created":
                attr = curses.color_pair(PALETTE["added"])
                symbol = "+"
            elif action == "modify":
                attr = curses.color_pair(PALETTE["modified"])
                symbol = "~"
            elif action == "remove":
                attr = curses.color_pair(PALETTE["removed"])
                symbol = "-"
            else:
                attr = 0
                symbol = " "
            
            line = f"{symbol} {version}: {action}"
            try:
                scr.addnstr(y, x, line[:w], w, attr)
            except:
                pass
            y += 1
            
            # Show diff preview
            if "old_lines" in entry and "new_lines" in entry:
                old = " ".join(entry["old_lines"][:1])[:30]
                new = " ".join(entry["new_lines"][:1])[:30]
                if old:
                    scr.addnstr(y, x + 2, f"- {old}", w-2, curses.color_pair(PALETTE["removed"]))
                    y += 1
                if new:
                    scr.addnstr(y, x + 2, f"+ {new}", w-2, curses.color_pair(PALETTE["added"]))
                    y += 1
    
    def _draw_status(self, scr, y, w):
        """Draw status bar"""
        if self.mode == "view":
            help_text = "↑↓ select version | r toggle regions | q quit"
        elif self.mode == "region_detail":
            help_text = "ESC back | ↑↓ navigate"
        else:
            help_text = ""
        
        if self.status:
            help_text = f"{self.status} | {help_text}"
        
        try:
            scr.addnstr(y, 1, help_text[:w-2], w-2, curses.color_pair(PALETTE["hint"]))
        except:
            pass
    
    def _handle_input(self, ch):
        """Handle keyboard input"""
        if ch in (ord('q'), ord('Q')) and self.mode == "view":
            return False
        
        if self.mode == "view":
            if ch in (curses.KEY_UP, ord('k')):
                self.selected_version_idx = max(0, self.selected_version_idx - 1)
                self.right_scroll = 0
            elif ch in (curses.KEY_DOWN, ord('j')):
                self.selected_version_idx = min(len(self.versions) - 1, self.selected_version_idx + 1)
                self.right_scroll = 0
            elif ch == ord('r'):
                # Toggle region detail mode
                if self.selected_region:
                    self.mode = "region_detail"
            # Редактор временно отключен
            # elif ch == ord('e'):
            #     if self._confirm_edit():
            #         self.mode = "edit"
            elif ch == curses.KEY_NPAGE:
                self.right_scroll += 10
            elif ch == curses.KEY_PPAGE:
                self.right_scroll = max(0, self.right_scroll - 10)
        
        elif self.mode == "region_detail":
            if ch == 27:  # ESC
                self.mode = "view"
        
        return True
    
    def _confirm_edit(self):
        """Show edit confirmation dialog"""
        # For now, return True - you can implement modal later
        return True
    
    # def _run_editor(self, scr, y, x, w, h):
    #     """Editor temporarily disabled"""
    #     pass
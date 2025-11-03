"""
TUI v8 - Enhanced design with LLM-powered diff analysis
Improved visuals with Unicode box drawing and better color scheme
"""

import curses
from typing import List, Optional
from pathlib import Path
from core.git_engine import GitDiffEngine
from core.region_index import RegionIndex
from core.llm_analyzer import LLMAnalyzer, AnalysisLevel, DiffAnalysis, ChangeType

# Enhanced color palette
PALETTE = {
    "border": 1,        # Cyan borders
    "title": 2,         # Bright white titles
    "added": 3,         # Green for additions
    "removed": 4,       # Red for removals  
    "modified": 5,      # Yellow for modifications
    "stable": 6,        # Blue for stable regions
    "volatile": 7,      # Magenta for volatile regions
    "selected": 8,      # Inverted selection
    "llm_summary": 9,   # Bright cyan for LLM text
    "icon": 10,         # Colored icons
    "dim": 11,          # Dimmed text
}

# Unicode box drawing characters
BOX = {
    "tl": "╭", "tr": "╮", "bl": "╰", "br": "╯",  # Corners
    "h": "─", "v": "│",                            # Lines
    "cross": "┼", "t_down": "┬", "t_up": "┴",     # Intersections
    "t_right": "├", "t_left": "┤",
}

class DocTUIView:
    def __init__(self, engine: GitDiffEngine, region_index: RegionIndex, history: List[dict]):
        self.engine = engine
        self.region_index = region_index
        self.history = history
        self.versions = [h["version"] for h in history]
        
        # Initialize LLM analyzer
        self.llm = LLMAnalyzer(model="mistral:latest")
        self.llm_cache = {}  # Cache for LLM analyses
        
        # UI state
        self.selected_version_idx = len(self.versions) - 1
        self.selected_region = None
        self.mode = "view"  # view, region_detail, llm_detail
        self.right_scroll = 0
        self.status = ""
        self.current_analysis = None
        
    def run(self):
        curses.wrapper(self._main)
    
    def _init_colors(self):
        if curses.has_colors():
            curses.start_color()
            try:
                curses.use_default_colors()
            except:
                pass
            
            # Enhanced color scheme
            curses.init_pair(PALETTE["border"], curses.COLOR_CYAN, -1)
            curses.init_pair(PALETTE["title"], curses.COLOR_WHITE, -1)
            curses.init_pair(PALETTE["added"], curses.COLOR_GREEN, -1)
            curses.init_pair(PALETTE["removed"], curses.COLOR_RED, -1)
            curses.init_pair(PALETTE["modified"], curses.COLOR_YELLOW, -1)
            curses.init_pair(PALETTE["stable"], curses.COLOR_BLUE, -1)
            curses.init_pair(PALETTE["volatile"], curses.COLOR_MAGENTA, -1)
            curses.init_pair(PALETTE["selected"], curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(PALETTE["llm_summary"], curses.COLOR_CYAN, -1)
            curses.init_pair(PALETTE["icon"], curses.COLOR_YELLOW, -1)
            curses.init_pair(PALETTE["dim"], curses.COLOR_WHITE, -1)
    
    def _main(self, scr):
        curses.curs_set(0)
        scr.keypad(True)
        self._init_colors()
        
        # Store screen reference for updates
        self.scr = scr
        
        # Don't run initial analysis - let user trigger it
        # This makes startup faster
        self.current_analysis = None
        self.status = "Press ↑↓ to navigate, D for analysis"
        
        while True:
            scr.erase()
            h, w = scr.getmaxyx()
            
            # Layout with golden ratio
            left_width = int(w * 0.382)  # Golden ratio
            right_width = w - left_width - 1
            top_height = int(h * 0.45)
            bottom_height = h - top_height - 2
            
            # Draw enhanced frame
            self._draw_frame(scr, h, w, left_width, top_height)
            
            # Draw panels based on mode
            if self.mode == "view":
                self._draw_history_panel(scr, 2, 2, left_width - 3, top_height - 3)
                self._draw_llm_analysis_panel(scr, top_height + 1, 2, left_width - 3, bottom_height - 2)
                self._draw_document_panel(scr, 2, left_width + 2, right_width - 3, h - 4)
            elif self.mode == "region_detail":
                self._draw_history_panel(scr, 2, 2, left_width - 3, top_height - 3)
                self._draw_region_detail(scr, top_height + 1, 2, left_width - 3, bottom_height - 2)
                self._draw_region_history(scr, 2, left_width + 2, right_width - 3, h - 4)
            elif self.mode == "llm_detail":
                self._draw_history_panel(scr, 2, 2, left_width - 3, top_height - 3)
                self._draw_llm_deep_analysis(scr, top_height + 1, 2, left_width - 3, bottom_height - 2)
                self._draw_document_panel(scr, 2, left_width + 2, right_width - 3, h - 4)
            
            # Status bar with gradient
            self._draw_status_bar(scr, h - 1, w)
            
            scr.refresh()
            
            # Handle input
            ch = scr.getch()
            if not self._handle_input(ch):
                break
    
    def _draw_frame(self, scr, h, w, left_width, top_height):
        """Draw enhanced UI frame with Unicode box drawing"""
        
        # Title with fancy border
        title = "╱ DRommage v8 ╱ LLM-Powered Documentation Analysis ╱"
        title_x = max(0, (w - len(title)) // 2)
        scr.addstr(0, title_x, title, curses.color_pair(PALETTE["title"]) | curses.A_BOLD)
        
        # Top border
        scr.addstr(1, 0, BOX["tl"], curses.color_pair(PALETTE["border"]))
        for x in range(1, left_width):
            scr.addstr(1, x, BOX["h"], curses.color_pair(PALETTE["border"]))
        scr.addstr(1, left_width, BOX["t_down"], curses.color_pair(PALETTE["border"]))
        for x in range(left_width + 1, w - 1):
            scr.addstr(1, x, BOX["h"], curses.color_pair(PALETTE["border"]))
        scr.addstr(1, w - 1, BOX["tr"], curses.color_pair(PALETTE["border"]))
        
        # Vertical separators
        for y in range(2, top_height):
            scr.addstr(y, 0, BOX["v"], curses.color_pair(PALETTE["border"]))
            scr.addstr(y, left_width, BOX["v"], curses.color_pair(PALETTE["border"]))
            scr.addstr(y, w - 1, BOX["v"], curses.color_pair(PALETTE["border"]))
        
        # Middle separator (left panel)
        scr.addstr(top_height, 0, BOX["t_right"], curses.color_pair(PALETTE["border"]))
        for x in range(1, left_width):
            scr.addstr(top_height, x, BOX["h"], curses.color_pair(PALETTE["border"]))
        scr.addstr(top_height, left_width, BOX["cross"], curses.color_pair(PALETTE["border"]))
        
        # Continue vertical lines
        for y in range(top_height + 1, h - 2):
            scr.addstr(y, 0, BOX["v"], curses.color_pair(PALETTE["border"]))
            scr.addstr(y, left_width, BOX["v"], curses.color_pair(PALETTE["border"]))
            scr.addstr(y, w - 1, BOX["v"], curses.color_pair(PALETTE["border"]))
        
        # Bottom border
        scr.addstr(h - 2, 0, BOX["bl"], curses.color_pair(PALETTE["border"]))
        for x in range(1, left_width):
            scr.addstr(h - 2, x, BOX["h"], curses.color_pair(PALETTE["border"]))
        scr.addstr(h - 2, left_width, BOX["t_up"], curses.color_pair(PALETTE["border"]))
        for x in range(left_width + 1, w - 1):
            scr.addstr(h - 2, x, BOX["h"], curses.color_pair(PALETTE["border"]))
        scr.addstr(h - 2, w - 1, BOX["br"], curses.color_pair(PALETTE["border"]))
    
    def _draw_history_panel(self, scr, y, x, w, h):
        """Draw version history with icons"""
        scr.addstr(y, x, "📚 Version History", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
        y += 2
        
        for i, hist in enumerate(self.history[:h-2]):
            if i == self.selected_version_idx:
                attr = curses.color_pair(PALETTE["selected"])
                prefix = "▶"
            else:
                attr = curses.color_pair(PALETTE["dim"])
                prefix = " "
            
            # Version with icon based on title
            icon = "📄"
            if "stable" in hist['title'].lower():
                icon = "✅"
            elif "api" in hist['title'].lower():
                icon = "🔌"
            elif "refactor" in hist['title'].lower():
                icon = "🔧"
            
            line = f"{prefix} {icon} {hist['version']} [{hist['date']}]"
            try:
                scr.addnstr(y + i, x, line[:w], w, attr)
                if len(line) < w - 2:
                    scr.addnstr(y + i, x + len(line) + 1, hist['title'][:w - len(line) - 2], 
                               w - len(line) - 2, attr)
            except:
                pass
    
    def _draw_llm_analysis_panel(self, scr, y, x, w, h):
        """Draw LLM analysis of current version changes"""
        version = self.versions[self.selected_version_idx]
        
        # Header
        scr.addstr(y, x, "🤖 AI Analysis", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
        y += 2
        
        # Show analysis status if we're currently analyzing
        if self.status and any(indicator in self.status for indicator in ["🤖", "📊", "📝", "⏱️", "❌"]):
            scr.addstr(y, x, "⏳ Analysis in progress...", curses.color_pair(PALETTE["modified"]) | curses.A_BOLD)
            y += 1
            # Show the detailed status message
            status_lines = self._word_wrap(self.status, w - 2)
            for line in status_lines[:3]:
                scr.addnstr(y, x, line, w, curses.color_pair(PALETTE["llm_summary"]))
                y += 1
            
            # Show progress animation
            anim_frames = ["◐", "◓", "◑", "◒"]
            import time
            frame = anim_frames[int(time.time() * 2) % len(anim_frames)]
            scr.addstr(y, x, f"{frame} Processing...", curses.color_pair(PALETTE["dim"]))
            y += 2
        
        # Get or generate analysis
        if self.current_analysis:
            # Show change type icon
            scr.addstr(y, x, f"{self.current_analysis.change_type.value} Type: {self.current_analysis.change_type.name}", 
                      curses.color_pair(PALETTE["icon"]))
            y += 1
            
            # Impact level with visual indicator
            impact_bars = {"low": "▁▁▁", "medium": "▃▃▃", "high": "▇▇▇"}
            impact_color = {"low": PALETTE["stable"], "medium": PALETTE["modified"], "high": PALETTE["volatile"]}
            bars = impact_bars.get(self.current_analysis.impact_level, "▁▁▁")
            color = impact_color.get(self.current_analysis.impact_level, PALETTE["dim"])
            scr.addstr(y, x, f"Impact: {bars} {self.current_analysis.impact_level}", 
                      curses.color_pair(color))
            y += 2
            
            # Summary
            scr.addstr(y, x, "Summary:", curses.A_BOLD)
            y += 1
            
            # Word wrap summary
            summary_lines = self._word_wrap(self.current_analysis.summary, w - 2)
            for line in summary_lines[:3]:
                scr.addnstr(y, x, line, w, curses.color_pair(PALETTE["llm_summary"]))
                y += 1
            
            # Show details if available
            if self.current_analysis.details and y < h - 3:
                y += 1
                scr.addstr(y, x, "Details:", curses.A_BOLD)
                y += 1
                detail_lines = self._word_wrap(self.current_analysis.details, w - 2)
                for line in detail_lines[:h - y - 2]:
                    scr.addnstr(y, x, line, w, curses.color_pair(PALETTE["dim"]))
                    y += 1
            
            # Hint for deeper analysis
            if y < h - 1:
                scr.addstr(h - 2, x, "Press 'D' for deeper analysis", 
                          curses.color_pair(PALETTE["dim"]) | curses.A_ITALIC)
        else:
            # No analysis available yet
            if not self.status or not any(indicator in self.status for indicator in ["🤖", "📊", "📝"]):
                scr.addstr(y, x, "⏸️  No analysis yet", curses.color_pair(PALETTE["dim"]))
                y += 2
                scr.addstr(y, x, "Press ↑↓ to navigate versions", curses.color_pair(PALETTE["dim"]))
                y += 1
                scr.addstr(y, x, "Press D for deep analysis", curses.color_pair(PALETTE["dim"]))
    
    def _draw_llm_deep_analysis(self, scr, y, x, w, h):
        """Show detailed LLM analysis"""
        scr.addstr(y, x, "🔍 Deep Analysis", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
        y += 2
        
        if self.current_analysis:
            # Show change type and impact
            scr.addstr(y, x, f"{self.current_analysis.change_type.value} Type: {self.current_analysis.change_type.name}", 
                      curses.color_pair(PALETTE["icon"]))
            y += 1
            
            # Impact level
            impact_bars = {"low": "▁▁▁", "medium": "▃▃▃", "high": "▇▇▇"}
            impact_color = {"low": PALETTE["stable"], "medium": PALETTE["modified"], "high": PALETTE["volatile"]}
            bars = impact_bars.get(self.current_analysis.impact_level, "▁▁▁")
            color = impact_color.get(self.current_analysis.impact_level, PALETTE["dim"])
            scr.addstr(y, x, f"Impact: {bars} {self.current_analysis.impact_level}", 
                      curses.color_pair(color))
            y += 2
            
            # Summary
            scr.addstr(y, x, "📋 Summary:", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
            y += 1
            summary_lines = self._word_wrap(self.current_analysis.summary, w - 2)
            for line in summary_lines[:3]:
                scr.addnstr(y, x, line, w, curses.color_pair(PALETTE["llm_summary"]))
                y += 1
            y += 1
            
            # Detailed explanation
            if self.current_analysis.details:
                scr.addstr(y, x, "📝 Details:", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
                y += 1
                detail_lines = self._word_wrap(self.current_analysis.details, w - 2)
                for line in detail_lines[:5]:
                    scr.addnstr(y, x, line, w, curses.color_pair(PALETTE["dim"]))
                    y += 1
                y += 1
            
            # Risks
            if self.current_analysis.risks and y < h - 4:
                scr.addstr(y, x, "⚠️  Risks:", curses.A_BOLD | curses.color_pair(PALETTE["removed"]))
                y += 1
                for risk in self.current_analysis.risks[:2]:
                    risk_lines = self._word_wrap(f"• {risk}", w - 2)
                    for line in risk_lines[:2]:
                        if y < h - 3:
                            scr.addnstr(y, x, line, w, curses.color_pair(PALETTE["removed"]))
                            y += 1
                y += 1
            
            # Recommendations
            if self.current_analysis.recommendations and y < h - 3:
                scr.addstr(y, x, "💡 Recommendations:", curses.A_BOLD | curses.color_pair(PALETTE["added"]))
                y += 1
                for rec in self.current_analysis.recommendations[:2]:
                    rec_lines = self._word_wrap(f"• {rec}", w - 2)
                    for line in rec_lines[:2]:
                        if y < h - 2:
                            scr.addnstr(y, x, line, w, curses.color_pair(PALETTE["added"]))
                            y += 1
        else:
            # No analysis available
            scr.addstr(y, x, "⏳ No analysis available yet", curses.color_pair(PALETTE["dim"]))
            y += 2
            scr.addstr(y, x, "Press D to run deep analysis", curses.color_pair(PALETTE["dim"]))
        
        # Back hint
        scr.addstr(h - 2, x, "Press ESC to return", curses.color_pair(PALETTE["dim"]) | curses.A_ITALIC)
    
    def _draw_document_panel(self, scr, y, x, w, h):
        """Draw document with enhanced region highlighting"""
        version = self.versions[self.selected_version_idx]
        lines = self.engine.get_document_lines(version)
        
        # Header with version info
        header = f"📄 {version}"
        if self.selected_version_idx > 0:
            prev_ver = self.versions[self.selected_version_idx - 1]
            header += f" (from {prev_ver})"
        scr.addstr(y, x, header, curses.A_BOLD | curses.color_pair(PALETTE["title"]))
        y += 2
        
        # Document lines with region highlighting
        visible_lines = lines[self.right_scroll:self.right_scroll + h - 2]
        
        for i, line in enumerate(visible_lines):
            line_num = self.right_scroll + i
            
            # Check if this line belongs to a region
            region = self.engine.get_region_at_line(version, line_num)
            
            if region:
                # Determine region volatility for coloring
                if region.id in [r.id for r in self.region_index.get_most_volatile_regions()]:
                    attr = curses.color_pair(PALETTE["volatile"])
                    indicator = "!"
                elif region.id in [r.id for r in self.region_index.get_most_stable_regions()]:
                    attr = curses.color_pair(PALETTE["stable"])
                    indicator = "="
                else:
                    attr = curses.color_pair(PALETTE["modified"])
                    indicator = "~"
                    
                # Line number and indicator
                line_str = f"{line_num+1:3d} {indicator} "
            else:
                attr = curses.color_pair(PALETTE["dim"])
                line_str = f"{line_num+1:3d}   "
            
            try:
                scr.addstr(y + i, x, line_str, curses.color_pair(PALETTE["dim"]))
                scr.addnstr(y + i, x + len(line_str), line[:w - len(line_str)], w - len(line_str), attr)
            except:
                pass
    
    def _draw_region_detail(self, scr, y, x, w, h):
        """Show details of selected region"""
        if not self.selected_region:
            return
        
        region = self.engine.regions.get(self.selected_region)
        if not region:
            return
        
        scr.addstr(y, x, "🔍 Region Details", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
        y += 2
        
        # LLM analysis of region with status callback
        def update_status(msg):
            self.status = msg
        
        region_summary = self.llm.analyze_region(region.history, AnalysisLevel.BRIEF, status_callback=update_status)
        scr.addnstr(y, x, region_summary, w, curses.color_pair(PALETTE["llm_summary"]))
        y += 2
        
        # Region stats
        summary = self.region_index.region_summaries.get(self.selected_region)
        if summary:
            scr.addstr(y, x, f"Modified: {summary.versions_modified}×")
            y += 1
            scr.addstr(y, x, f"Changes: +{summary.total_additions} -{summary.total_deletions}")
            y += 1
            
            # Stability meter
            stability_pct = int(summary.stability_score * 10)
            meter = "█" * stability_pct + "░" * (10 - stability_pct)
            scr.addstr(y, x, f"Stability: {meter}")
            y += 2
        
        # Preview
        preview = region.canonical_text[:200]
        for line in preview.split('\n')[:h-8]:
            try:
                scr.addnstr(y, x, line[:w], w)
            except:
                pass
            y += 1
    
    def _draw_region_history(self, scr, y, x, w, h):
        """Show history of selected region with LLM descriptions"""
        if not self.selected_region:
            return
        
        history = self.region_index.get_region_history(self.selected_region)
        
        scr.addstr(y, x, "📜 Region Evolution", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
        y += 2
        
        for entry in history[:h-2]:
            version = entry["version"]
            action = entry["action"]
            
            # Icon based on action
            if action == "created":
                icon = "✨"
                attr = curses.color_pair(PALETTE["added"])
            elif action == "modify":
                icon = "📝"
                attr = curses.color_pair(PALETTE["modified"])
            elif action == "remove":
                icon = "🗑"
                attr = curses.color_pair(PALETTE["removed"])
            else:
                icon = "•"
                attr = 0
            
            line = f"{icon} {version}: {action}"
            try:
                scr.addnstr(y, x, line[:w], w, attr)
            except:
                pass
            y += 1
    
    def _draw_status_bar(self, scr, y, w):
        """Draw gradient status bar"""
        # Clear the line first
        scr.move(y, 0)
        scr.clrtoeol()
        
        if self.mode == "view":
            help_items = [
                ("↑↓", "navigate"),
                ("B", "brief"),
                ("D", "deep analysis"),
                ("R", "regions"),
                ("PgUp/Dn", "scroll"),
                ("Q", "quit")
            ]
        elif self.mode == "llm_detail":
            help_items = [
                ("ESC", "back"),
                ("↑↓", "scroll")
            ]
        else:
            help_items = [("ESC", "back")]
        
        # If we have a status message (like during analysis), show it prominently
        if self.status and ("🤖" in self.status or "📊" in self.status or "📝" in self.status or "✅" in self.status or "⏱️" in self.status):
            # Show analysis status prominently on the left
            try:
                scr.addstr(y, 2, self.status, curses.color_pair(PALETTE["llm_summary"]) | curses.A_BOLD)
            except:
                pass
            
            # Show minimal help on the right
            short_help = "[Q] quit" if self.mode == "view" else "[ESC] back"
            try:
                scr.addstr(y, w - len(short_help) - 2, short_help, curses.color_pair(PALETTE["dim"]))
            except:
                pass
        else:
            # Normal help text
            help_parts = []
            for key, desc in help_items:
                help_parts.append(f"[{key}] {desc}")
            help_text = " │ ".join(help_parts)
            
            # Add status if present (non-analysis status)
            if self.status:
                help_text = f"{self.status} │ {help_text}"
            
            # Center and display
            x = max(1, (w - len(help_text)) // 2)
            try:
                scr.addnstr(y, x, help_text[:w-2], w-2, curses.color_pair(PALETTE["dim"]))
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
                self.current_analysis = None  # Clear previous analysis
                self.status = "Press D to analyze this version"
            elif ch in (curses.KEY_DOWN, ord('j')):
                self.selected_version_idx = min(len(self.versions) - 1, self.selected_version_idx + 1)
                self.right_scroll = 0
                self.current_analysis = None  # Clear previous analysis
                self.status = "Press D to analyze this version"
            elif ch in (ord('b'), ord('B')):
                # Brief analysis
                self.status = "🚀 Running brief analysis..."
                self._refresh_display(self.scr)
                self._analyze_current_version(AnalysisLevel.BRIEF, self.scr)
            elif ch in (ord('d'), ord('D')):
                # Deep analysis
                self.status = "🚀 Running deep analysis..."
                self.mode = "llm_detail"  # Switch mode first
                self._refresh_display(self.scr)
                self._analyze_current_version(AnalysisLevel.DETAILED, self.scr)
                # Ensure we refresh after analysis completes
                self._refresh_display(self.scr)
            elif ch in (ord('r'), ord('R')):
                # Toggle region detail mode
                if self.selected_region:
                    self.mode = "region_detail"
            elif ch == curses.KEY_NPAGE:
                self.right_scroll += 10
            elif ch == curses.KEY_PPAGE:
                self.right_scroll = max(0, self.right_scroll - 10)
        
        elif self.mode in ("region_detail", "llm_detail"):
            if ch == 27:  # ESC
                self.mode = "view"
        
        return True
    
    def _analyze_current_version(self, level: AnalysisLevel, scr=None):
        """Run LLM analysis on current version diff"""
        if self.selected_version_idx == 0:
            # First version - no previous to compare
            self.current_analysis = DiffAnalysis(
                summary="Initial version of the documentation",
                change_type=ChangeType.DOCUMENTATION,
                impact_level="low",
                confidence=1.0
            )
            return
        
        # Get diff
        prev_ver = self.versions[self.selected_version_idx - 1]
        curr_ver = self.versions[self.selected_version_idx]
        
        # Check cache
        cache_key = f"{prev_ver}_{curr_ver}_{level.value}"
        if cache_key in self.llm_cache:
            self.current_analysis = self.llm_cache[cache_key]
            self.status = "📦 Using cached analysis"
            if scr:
                self._refresh_display(scr)
            return
        
        # Get document content
        prev_lines = self.engine.get_document_lines(prev_ver)
        curr_lines = self.engine.get_document_lines(curr_ver)
        
        prev_text = "\n".join(prev_lines)
        curr_text = "\n".join(curr_lines)
        
        # Create status callback for live updates
        def update_status(msg):
            self.status = msg
            if scr:
                # Force immediate screen update
                self._refresh_display(scr)
        
        # Analyze with LLM
        self.status = "🤖 Starting analysis..."
        if scr:
            self._refresh_display(scr)
        
        context = f"Version {prev_ver} to {curr_ver}"
        analysis = self.llm.analyze_diff(
            prev_text, curr_text, context, level, 
            status_callback=update_status
        )
        
        # Cache result
        self.llm_cache[cache_key] = analysis
        self.current_analysis = analysis
        self.status = f"✅ Analysis complete ({level.value} level)"
        if scr:
            self._refresh_display(scr)
    
    def _refresh_display(self, scr):
        """Force immediate screen refresh to show status updates"""
        h, w = scr.getmaxyx()
        
        # Layout calculations
        left_width = int(w * 0.382)
        top_height = int(h * 0.45)
        bottom_height = h - top_height - 2
        
        # Update status bar
        self._draw_status_bar(scr, h - 1, w)
        
        # Update appropriate panel based on mode
        if self.mode == "view":
            # Update the LLM analysis panel in view mode
            self._draw_llm_analysis_panel(scr, top_height + 1, 2, left_width - 3, bottom_height - 2)
        elif self.mode == "llm_detail":
            # Update the deep analysis panel in detail mode
            self._draw_llm_deep_analysis(scr, top_height + 1, 2, left_width - 3, bottom_height - 2)
        
        scr.refresh()
    
    def _word_wrap(self, text: str, width: int) -> List[str]:
        """Simple word wrapping"""
        if not text:
            return []
        
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            word_length = len(word)
            if current_length + word_length + 1 <= width:
                current_line.append(word)
                current_length += word_length + 1
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = word_length
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return lines
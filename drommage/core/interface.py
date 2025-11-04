"""
TUI v8 - Enhanced design with LLM-powered diff analysis
Improved visuals with Unicode box drawing and better color scheme
"""

import curses
from typing import List, Optional
from pathlib import Path
from .diff_tracker import GitDiffEngine
from .region_analyzer import RegionIndex
from .llm_analyzer import LLMAnalyzer, AnalysisLevel, DiffAnalysis, ChangeType
from .analysis_queue import AnalysisQueue, AnalysisTask, TaskStatus
from .git_integration import GitIntegration, GitCommit
import uuid
import time
import subprocess

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
    def __init__(self, engine: GitDiffEngine, region_index: RegionIndex, commits: List[GitCommit], git_integration: GitIntegration):
        self.engine = engine
        self.region_index = region_index
        self.commits = commits
        self.git = git_integration
        
        # Initialize LLM analyzer and async queue
        self.llm = LLMAnalyzer(model="mistral:latest")
        self.analysis_queue = AnalysisQueue(self.llm)
        self.analysis_queue.start()
        
        self.llm_cache = {}  # Cache for LLM analyses
        
        # UI state
        self.selected_commit_idx = 0 if commits else -1
        self.selected_region = None
        self.mode = "view"  # view, region_detail, llm_detail, queue
        self.right_scroll = 0
        self.commit_scroll = 0  # Horizontal scroll for commit list
        self.status = ""
        self.current_analyses = {"brief": None, "deep": None}  # Separate analyses
        self.active_tasks = []  # Track running analysis tasks
        self.animation_frame = 0  # For animated indicators
        
    def run(self):
        # Custom curses wrapper to handle terminal issues
        try:
            import curses
            scr = curses.initscr()
            try:
                # Basic setup without problematic calls
                curses.noecho()
                try:
                    curses.cbreak()
                except:
                    pass  # Ignore cbreak errors
                
                self._main(scr)
            finally:
                try:
                    curses.echo()
                    curses.nocbreak() 
                    curses.endwin()
                except:
                    pass  # Ignore cleanup errors
        except Exception as e:
            print(f"Terminal interface failed: {e}")
            print("Try running in a different terminal or use a simpler interface")
    
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
        try:
            curses.curs_set(0)
        except:
            pass  # Some terminals don't support cursor visibility
        
        try:
            scr.keypad(True)
        except:
            pass
            
        self._init_colors()
        
        # Store screen reference for updates
        self.scr = scr
        
        # Try to load cached analyses for the current version
        self._load_cached_analyses()
        if not any(self.current_analyses.values()):
            self.status = "Press D to analyze commit"
        else:
            # Clear any existing status if we have analyses
            self.status = ""
        
        # Set nodelay for non-blocking input and animation
        try:
            scr.nodelay(True)
        except:
            # Fallback to timeout mode
            scr.timeout(100)
        
        while True:
            try:
                # Update animation frame for visual feedback
                self.animation_frame = (self.animation_frame + 1) % 100
                
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
                
                # Handle input (non-blocking due to nodelay)
                try:
                    ch = scr.getch()
                    if ch != -1:  # Key was pressed
                        if not self._handle_input(ch):
                            break
                except:
                    pass
                
                # Small delay for animation
                import time
                time.sleep(0.1)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                # On any error, try to continue or break gracefully
                try:
                    scr.addstr(0, 0, f"Error: {str(e)[:50]}")
                    scr.refresh()
                    import time
                    time.sleep(1)
                except:
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
        """Draw git commit history"""
        if self.mode == "queue":
            self._draw_queue_panel(scr, y, x, w, h)
            return
            
        scr.addstr(y, x, "📚 Git Commits", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
        y += 1
        
        # Show queue status
        queue_size = self.analysis_queue.get_queue_size()
        if queue_size > 0:
            scr.addstr(y, x, f"🔄 Queue: {queue_size} tasks", curses.color_pair(PALETTE["modified"]))
        else:
            scr.addstr(y, x, "🔄 Queue: empty", curses.color_pair(PALETTE["dim"]))
        y += 2
        
        for i, commit in enumerate(self.commits[:h-4]):
            if i == self.selected_commit_idx:
                attr = curses.color_pair(PALETTE["selected"])
                prefix = "▶"
            else:
                attr = curses.color_pair(PALETTE["dim"])
                prefix = " "
            
            # Commit icon based on message
            icon = "📝"
            msg_lower = commit.message.lower()
            if msg_lower.startswith("feat"):
                icon = "🚀"
            elif msg_lower.startswith("fix"):
                icon = "🐛"
            elif msg_lower.startswith("refactor"):
                icon = "🔧"
            elif msg_lower.startswith("docs"):
                icon = "📚"
            
            # Get analysis status for this commit with exact pattern matching
            prev_short_hash = None
            if i < len(self.commits) - 1:
                prev_short_hash = self.commits[i + 1].short_hash
            
            analysis_status = self.analysis_queue.get_commit_analysis_status(
                commit.hash, commit.short_hash, prev_short_hash)
            brief_status = analysis_status.get("brief")
            deep_status = analysis_status.get("deep")
            
            # Also check cache for completed analyses
            if not brief_status and i < len(self.commits) - 1:
                prev_hash = self.commits[i+1].hash
                brief_key = f"{prev_hash}_{commit.hash}_brief"
                if brief_key in self.llm_cache:
                    brief_status = "completed"
                    
            if not deep_status and i < len(self.commits) - 1:
                prev_hash = self.commits[i+1].hash  
                deep_key = f"{prev_hash}_{commit.hash}_detailed"
                if deep_key in self.llm_cache:
                    deep_status = "completed"
            
            # Show both brief (d) and deep (D) indicators when available
            brief_indicator = ""
            deep_indicator = ""
            
            if brief_status:
                # Brief analysis - use lowercase d
                brief_indicator = self._get_status_indicator(brief_status, "d")
            elif i == self.selected_commit_idx:
                # Show default button for selected commit
                brief_indicator = " d "
            
            if deep_status:
                # Deep analysis - use uppercase D  
                deep_indicator = self._get_status_indicator(deep_status, "D")
            elif i == self.selected_commit_idx:
                # Always show D button for selected commit (regardless of brief status)
                deep_indicator = " D "
            
            # Combine indicators
            indicators = brief_indicator + deep_indicator
            
            # Calculate how much space we need for indicators
            indicator_space = len(indicators) + 1 if indicators else 0
            available_space = w - indicator_space - 2  # Reserve space for indicators + margin
            
            # Format base line and truncate if needed
            base_line = f"{prefix} {icon} {commit.short_hash} {commit.message}"
            if len(base_line) > available_space:
                base_line = base_line[:available_space-1] + "…"
            
            # Combine base line with indicators
            if indicators:
                full_line = base_line.ljust(available_space) + " " + indicators
            else:
                full_line = base_line
            
            # Apply horizontal scrolling (if needed)
            if self.commit_scroll > 0:
                if len(full_line) > self.commit_scroll:
                    line = "←" + full_line[self.commit_scroll + 1:]
                else:
                    line = "←"
            else:
                line = full_line
            
            try:
                scr.addnstr(y + i, x, line[:w], w, attr)
            except:
                pass
    
    def _get_status_indicator(self, status: str, button_type: str) -> str:
        """Generate animated status indicator for analysis buttons (B/D)"""
        if status is None:
            return f" {button_type} "  # Default button
        elif status == "pending":
            # Animate waiting dots
            dots = ["   ", ".  ", ".. ", "..."]
            dot_idx = (self.animation_frame // 5) % len(dots)
            return f"[{button_type}{dots[dot_idx][:-1]}]"
        elif status == "running":
            # Animate spinning indicator
            spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            spinner_idx = (self.animation_frame // 2) % len(spinners)
            return f"[{button_type}{spinners[spinner_idx]}]"
        elif status == "completed":
            return f"[{button_type}✓]"
        elif status == "failed":
            return f"[{button_type}✗]"
        else:
            return f" {button_type} "
    
    def _draw_queue_panel(self, scr, y, x, w, h):
        """Draw analysis queue status"""
        scr.addstr(y, x, "🔄 Analysis Queue", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
        y += 2
        
        active_tasks = self.analysis_queue.get_active_tasks()
        if not active_tasks:
            scr.addstr(y, x, "No active tasks", curses.color_pair(PALETTE["dim"]))
            return
        
        for i, task in enumerate(active_tasks[:h-3]):
            status_icons = {
                "pending": "⏳",
                "running": "🔄",
                "completed": "✅",
                "failed": "❌"
            }
            
            icon = status_icons.get(task["status"], "❓")
            level_short = task["level"][0].upper()  # B/D/T
            
            line = f"{icon} {level_short} {task['context'][:w-8]}"
            try:
                scr.addnstr(y + i, x, line[:w], w, curses.color_pair(PALETTE["dim"]))
            except:
                pass
    
    def _draw_llm_analysis_panel(self, scr, y, x, w, h):
        """Draw LLM analysis of current commit changes"""
        # CLEAR only the content area, not the borders
        for clear_y in range(y, y + h - 1):  # Don't clear the bottom border
            try:
                scr.move(clear_y, x)
                # Clear only the content area, leave space for right border
                for clear_x in range(x, x + w - 1):
                    scr.addch(clear_y, clear_x, ' ')
            except:
                pass
        
        if not self.commits or self.selected_commit_idx < 0:
            scr.addstr(y, x, "🤖 AI Analysis", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
            y += 2
            scr.addstr(y, x, "No commits available", curses.color_pair(PALETTE["dim"]))
            return
            
        current_commit = self.commits[self.selected_commit_idx]
        
        # Header
        scr.addstr(y, x, "🤖 AI Analysis", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
        y += 2
        
        # Check if we're currently analyzing
        is_analyzing = self.status and any(indicator in self.status for indicator in ["🤖", "📊", "📝", "⏱️", "🔄"])
        
        # Get or generate analysis (show brief by default, deep in detailed mode)
        analysis_type = "deep" if self.mode == "llm_detail" else "brief"
        current_analysis = self.current_analyses.get(analysis_type)
        
        # Try to get ANY available analysis if preferred one is not available
        if not current_analysis:
            # Try brief if we were looking for deep
            if analysis_type == "deep":
                current_analysis = self.current_analyses.get("brief")
                if current_analysis:
                    analysis_type = "brief"
            # Try deep if we were looking for brief
            else:
                current_analysis = self.current_analyses.get("deep") 
                if current_analysis:
                    analysis_type = "deep"
        
        if is_analyzing and not current_analysis:
            # Show analysis in progress
            scr.addstr(y, x, "⏳ Analysis in progress...", curses.color_pair(PALETTE["modified"]) | curses.A_BOLD)
            y += 2
            
            # Show progress animation
            anim_frames = ["◐", "◓", "◑", "◒"]
            import time
            frame = anim_frames[int(time.time() * 2) % len(anim_frames)]
            scr.addstr(y, x, f"{frame} Processing...", curses.color_pair(PALETTE["dim"]))
            return
        elif current_analysis:
            # Show completed analysis
            type_label = "📊 Deep Analysis" if analysis_type == "deep" else "📝 Brief Analysis"
            scr.addstr(y, x, type_label, curses.color_pair(PALETTE["icon"]) | curses.A_BOLD)
            y += 1
        else:
            # Show no analysis message
            self._draw_no_analysis_message(scr, y, x, w, h)
            return
            
        # Show change type icon  
        # DEBUG: Check what's in change_type
        try:
            type_text = f"{current_analysis.change_type.value} Type: {current_analysis.change_type.name}"
        except:
            type_text = f"❓ Type: UNKNOWN (error accessing change_type)"
        scr.addstr(y, x, type_text, curses.color_pair(PALETTE["icon"]))
        y += 1
        
        # Impact level with visual indicator
        impact_bars = {"low": "▁▁▁", "medium": "▃▃▃", "high": "▇▇▇"}
        impact_color = {"low": PALETTE["stable"], "medium": PALETTE["modified"], "high": PALETTE["volatile"]}
        bars = impact_bars.get(current_analysis.impact_level, "▁▁▁")
        color = impact_color.get(current_analysis.impact_level, PALETTE["dim"])
        scr.addstr(y, x, f"Impact: {bars} {current_analysis.impact_level}", 
                  curses.color_pair(color))
        y += 2
        
        # Summary
        scr.addstr(y, x, "Summary:", curses.A_BOLD)
        y += 1
        
        # Word wrap summary
        
        if current_analysis.summary:
            summary_lines = self._word_wrap(current_analysis.summary, w - 2)
            # Show summary lines with boundary checking
            start_y_brief = y - 3  # Approximate start of panel
            for line in summary_lines:
                if y >= start_y_brief + h - 3:  # Leave space for details
                    break
                try:
                    scr.addnstr(y, x, line, w, curses.color_pair(PALETTE["llm_summary"]))
                    y += 1
                except:
                    break
        else:
            # Summary is empty
            scr.addstr(y, x, "⚠️ No summary available", curses.color_pair(PALETTE["dim"]))
            y += 1
        
        # Show details if available - with boundary checking
        if current_analysis.details and y < start_y_brief + h - 2:
            y += 1
            scr.addstr(y, x, "Details:", curses.A_BOLD)
            y += 1
            detail_lines = self._word_wrap(current_analysis.details, w - 2)
            # Show detail lines with boundary checking
            for line in detail_lines:
                if y >= start_y_brief + h - 2:
                    break
                try:
                    scr.addnstr(y, x, line, w, curses.color_pair(PALETTE["dim"]))
                    y += 1
                except:
                    break
        
        # Hint for switching analysis type
        if y < h - 1:
            hint = "Press 'D' to switch to brief" if analysis_type == "deep" else "Press 'D' for deep analysis"
            scr.addstr(h - 2, x, hint, curses.color_pair(PALETTE["dim"]) | curses.A_ITALIC)
    
    def _draw_no_analysis_message(self, scr, y, x, w, h):
        """Show message when no analysis is available"""
        # No analysis available yet
        scr.addstr(y, x, "⏸️  No analysis yet", curses.color_pair(PALETTE["dim"]))
        y += 2
        scr.addstr(y, x, "Press D to analyze", curses.color_pair(PALETTE["dim"]))
    
    def _draw_llm_deep_analysis(self, scr, y, x, w, h):
        """Show detailed LLM analysis"""
        start_y = y  # Remember starting position for boundary checks
        scr.addstr(y, x, "🔍 Deep Analysis", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
        y += 2
        
        # Get deep analysis specifically
        deep_analysis = self.current_analyses.get("deep")
        
        if deep_analysis:
            # Show change type and impact
            scr.addstr(y, x, f"{deep_analysis.change_type.value} Type: {deep_analysis.change_type.name}", 
                      curses.color_pair(PALETTE["icon"]))
            y += 1
            
            # Impact level
            impact_bars = {"low": "▁▁▁", "medium": "▃▃▃", "high": "▇▇▇"}
            impact_color = {"low": PALETTE["stable"], "medium": PALETTE["modified"], "high": PALETTE["volatile"]}
            bars = impact_bars.get(deep_analysis.impact_level, "▁▁▁")
            color = impact_color.get(deep_analysis.impact_level, PALETTE["dim"])
            scr.addstr(y, x, f"Impact: {bars} {deep_analysis.impact_level}", 
                      curses.color_pair(color))
            y += 2
            
            # Summary
            scr.addstr(y, x, "📋 Summary:", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
            y += 1
            
            if deep_analysis.summary:
                summary_lines = self._word_wrap(deep_analysis.summary, w - 2)
                # Show summary lines with boundary checking
                for line in summary_lines:
                    if y >= start_y + h - 3:  # Leave space for other sections
                        break
                    try:
                        scr.addnstr(y, x, line, w, curses.color_pair(PALETTE["llm_summary"]))
                        y += 1
                    except:
                        break
            else:
                scr.addstr(y, x, "⚠️ No summary available", curses.color_pair(PALETTE["dim"]))
                y += 1
            y += 1
            
            # Detailed explanation - with boundary checking
            if deep_analysis.details and y < start_y + h - 2:
                scr.addstr(y, x, "📝 Details:", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
                y += 1
                detail_lines = self._word_wrap(deep_analysis.details, w - 2)
                # Show detail lines with boundary checking
                for line in detail_lines:
                    if y >= start_y + h - 2:
                        break
                    try:
                        scr.addnstr(y, x, line, w, curses.color_pair(PALETTE["dim"]))
                        y += 1
                    except:
                        break
                y += 1
            
            # Risks - with boundary checking
            if deep_analysis.risks and y < start_y + h - 1:
                scr.addstr(y, x, "⚠️  Risks:", curses.A_BOLD | curses.color_pair(PALETTE["removed"]))
                y += 1
                for risk in deep_analysis.risks:
                    if y >= start_y + h - 1:
                        break
                    risk_lines = self._word_wrap(f"• {risk}", w - 2)
                    for line in risk_lines:
                        if y >= start_y + h - 1:
                            break
                        try:
                            scr.addnstr(y, x, line, w, curses.color_pair(PALETTE["removed"]))
                            y += 1
                        except:
                            break
                y += 1
            
            # Recommendations - with boundary checking
            if deep_analysis.recommendations and y < start_y + h - 1:
                scr.addstr(y, x, "💡 Recommendations:", curses.A_BOLD | curses.color_pair(PALETTE["added"]))
                y += 1
                for rec in deep_analysis.recommendations:
                    if y >= start_y + h - 1:
                        break
                    rec_lines = self._word_wrap(f"• {rec}", w - 2)
                    for line in rec_lines:
                        if y >= start_y + h - 1:
                            break
                        try:
                            scr.addnstr(y, x, line, w, curses.color_pair(PALETTE["added"]))
                            y += 1
                        except:
                            break
        else:
            # No analysis available
            scr.addstr(y, x, "⏳ No analysis available yet", curses.color_pair(PALETTE["dim"]))
            y += 2
            scr.addstr(y, x, "Press D to run deep analysis", curses.color_pair(PALETTE["dim"]))
        
    
    def _draw_document_panel(self, scr, y, x, w, h):
        """Draw commit diff view"""
        if not self.commits or self.selected_commit_idx < 0:
            scr.addstr(y, x, "📄 No commit selected", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
            return
            
        current_commit = self.commits[self.selected_commit_idx]
        
        # Header with commit info
        header = f"📄 {current_commit.short_hash}: {current_commit.message[:30]}"
        scr.addstr(y, x, header, curses.A_BOLD | curses.color_pair(PALETTE["title"]))
        y += 2
        
        # Show commit stats
        scr.addstr(y, x, f"Author: {current_commit.author}", curses.color_pair(PALETTE["dim"]))
        y += 1
        scr.addstr(y, x, f"Date: {current_commit.date}", curses.color_pair(PALETTE["dim"]))
        y += 1
        scr.addstr(y, x, f"Files: {current_commit.files_changed}, +{current_commit.insertions}, -{current_commit.deletions}", 
                  curses.color_pair(PALETTE["modified"]))
        y += 2
        
        # Get and show diff if available
        if self.selected_commit_idx < len(self.commits) - 1:
            prev_commit = self.commits[self.selected_commit_idx + 1]
            diff = self.git.get_commit_diff(prev_commit.hash, current_commit.hash)
            
            if diff and diff.diff_text:
                scr.addstr(y, x, "Diff:", curses.A_BOLD)
                y += 1
                
                # Show diff lines with proper color preservation
                raw_diff_lines = diff.diff_text.split('\n')
                wrapped_diff_lines = []
                for line in raw_diff_lines:
                    # Get prefix for coloring
                    prefix = line[0] if line and line[0] in '+-@' else ' '
                    
                    if len(line) <= w - 4:
                        # Line fits, keep as is
                        wrapped_diff_lines.append((line, prefix))
                    else:
                        # Need to wrap - break at word boundaries but preserve prefix
                        if len(line) > 1:
                            content = line[1:] if prefix in '+-@' else line
                            # Break into chunks manually to preserve meaning
                            chunk_size = w - 6  # Leave room for prefix and indicators
                            for i in range(0, len(content), chunk_size):
                                chunk = content[i:i + chunk_size]
                                if i == 0:
                                    # First chunk gets original prefix
                                    display_line = (prefix + chunk) if prefix in '+-@' else chunk
                                else:
                                    # Continuation chunks get continuation indicator
                                    display_line = '…' + chunk
                                wrapped_diff_lines.append((display_line, prefix))
                        else:
                            wrapped_diff_lines.append((line, prefix))
                
                # Apply vertical scrolling
                diff_lines = wrapped_diff_lines[self.right_scroll:self.right_scroll + h - y - 2]
                
                for i, (line_text, line_prefix) in enumerate(diff_lines):
                    if y + i >= h - 2:
                        break
                        
                    # Color diff lines based on preserved prefix
                    if line_prefix == '+':
                        attr = curses.color_pair(PALETTE["added"])
                    elif line_prefix == '-':
                        attr = curses.color_pair(PALETTE["removed"])
                    elif line_prefix == '@':
                        attr = curses.color_pair(PALETTE["modified"])
                    else:
                        attr = curses.color_pair(PALETTE["dim"])
                    
                    try:
                        scr.addnstr(y + i, x, line_text[:w], w, attr)
                    except:
                        pass
            else:
                scr.addstr(y, x, "No diff available", curses.color_pair(PALETTE["dim"]))
        else:
            scr.addstr(y, x, "Initial commit", curses.color_pair(PALETTE["dim"]))
    
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
                ("D", "analyze/toggle"),
                ("Q", "queue/quit"),
                ("R", "regions"),
                ("←→/hl", "scroll"),
                ("i", "copy commits"),
                ("o", "copy analysis"),
                ("p", "copy diff")
            ]
        elif self.mode == "queue":
            help_items = [
                ("Q", "quit"),
                ("any key", "back")
            ]
        elif self.mode == "llm_detail":
            help_items = [
                ("D", "back to brief"),
                ("any key", "back")
            ]
        else:
            help_items = [("ESC", "back")]
        
        # Status messages are no longer shown to avoid cluttering navigation
        # Always show normal help text
        help_parts = []
        for key, desc in help_items:
            help_parts.append(f"[{key}] {desc}")
        help_text = " │ ".join(help_parts)
        
        # Add status if present (only basic status, no analysis messages)
        if self.status and not any(indicator in self.status for indicator in ["🔄", "⏳", "🤖", "❌", "✅"]):
            help_text = f"{self.status} │ {help_text}"
        
        # Center and display
        x = max(1, (w - len(help_text)) // 2)
        try:
            scr.addnstr(y, x, help_text[:w-2], w-2, curses.color_pair(PALETTE["dim"]))
        except:
            pass
    
    def _handle_input(self, ch):
        """Handle keyboard input"""
        
        if self.mode == "view":
            if ch in (curses.KEY_UP, ord('k')):
                self.selected_commit_idx = max(0, self.selected_commit_idx - 1)
                self.right_scroll = 0
                self._load_cached_analyses()
            elif ch in (curses.KEY_DOWN, ord('j')):
                self.selected_commit_idx = min(len(self.commits) - 1, self.selected_commit_idx + 1)
                self.right_scroll = 0
                self._load_cached_analyses()
            elif ch in (ord('d'), ord('D')):
                # Smart D button logic
                self._handle_d_button()
            elif ch in (ord('q'), ord('Q')):
                # Show queue or quit
                if self.mode == "queue":
                    return False  # Quit
                else:
                    self.mode = "queue"  # Show queue
            elif ch in (ord('r'), ord('R')):
                # Toggle region detail mode
                if self.selected_region:
                    self.mode = "region_detail"
            elif ch in (curses.KEY_RIGHT, ord('l')):
                self.right_scroll += 10
            elif ch in (curses.KEY_LEFT, ord('h')):
                self.right_scroll = max(0, self.right_scroll - 10)
            elif ch == ord('L'):  # Shift+L - scroll commits right
                self.commit_scroll += 5
            elif ch == ord('H'):  # Shift+H - scroll commits left  
                self.commit_scroll = max(0, self.commit_scroll - 5)
            elif ch == ord('i'):  # Copy commits to clipboard
                self._copy_commits()
            elif ch == ord('o'):  # Copy analysis to clipboard
                self._copy_analysis()
            elif ch == ord('p'):  # Copy diff to clipboard
                self._copy_diff()
        
        elif self.mode == "llm_detail":
            # Allow navigation in deep mode
            if ch in (curses.KEY_UP, ord('k')):
                self.selected_commit_idx = max(0, self.selected_commit_idx - 1)
                self.right_scroll = 0
                self._load_cached_analyses()
            elif ch in (curses.KEY_DOWN, ord('j')):
                self.selected_commit_idx = min(len(self.commits) - 1, self.selected_commit_idx + 1)
                self.right_scroll = 0
                self._load_cached_analyses()
            elif ch in (ord('d'), ord('D')):
                # Smart D button logic
                self._handle_d_button()
            elif ch in (ord('q'), ord('Q')):
                # Show queue or quit
                if self.mode == "queue":
                    return False  # Quit
                else:
                    self.mode = "queue"  # Show queue
            else:
                # Any other key returns to main view
                self.mode = "view"
        elif self.mode == "region_detail":
            # Return to main view on any key
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
        # No status message to avoid cluttering navigation bar
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
        # No completion status message to avoid cluttering navigation bar
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
    
    def _load_cached_analyses(self):
        """Load cached analyses if available"""
        if not self.commits or self.selected_commit_idx < 0:
            self.current_analyses = {"brief": None, "deep": None}
            self.status = "No commits available"
            return
            
        if self.selected_commit_idx >= len(self.commits) - 1:
            # Last commit - no previous to compare  
            initial_analysis = DiffAnalysis(
                summary="Initial commit of the repository",
                change_type=ChangeType.DOCUMENTATION,
                impact_level="low",
                confidence=1.0
            )
            self.current_analyses = {"brief": initial_analysis, "deep": initial_analysis}
            return
        
        # Get commits for diff
        current_commit = self.commits[self.selected_commit_idx]
        prev_commit = self.commits[self.selected_commit_idx + 1]  # Git history is reverse chronological
        
        # Check cache for both types of analysis
        brief_key = f"{prev_commit.hash}_{current_commit.hash}_{AnalysisLevel.BRIEF.value}"
        deep_key = f"{prev_commit.hash}_{current_commit.hash}_{AnalysisLevel.DETAILED.value}"
        
        # Load cached analyses with correct mapping
        brief_analysis = self.llm_cache.get(brief_key)
        deep_analysis = self.llm_cache.get(deep_key)
        
        self.current_analyses = {
            "brief": brief_analysis,
            "deep": deep_analysis
        }
        
        if self.current_analyses["brief"] or self.current_analyses["deep"]:
            self.status = ""  # Clear status when we have analyses - they show in panel
        else:
            self.status = "Press D to analyze commit"
    
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
    
    def _queue_analysis(self, level: AnalysisLevel):
        """Queue analysis task for current commit"""
        if self.selected_commit_idx < 0 or self.selected_commit_idx >= len(self.commits):
            self.status = "❌ No commit selected"
            return
        
        current_commit = self.commits[self.selected_commit_idx]
        
        # Get previous commit for diff
        if self.selected_commit_idx < len(self.commits) - 1:
            prev_commit = self.commits[self.selected_commit_idx + 1]
        else:
            self.status = "❌ No previous commit to compare"
            return
        
        # Check if analysis already exists or is in progress
        cache_key = f"{prev_commit.hash}_{current_commit.hash}_{level.value}"
        if cache_key in self.llm_cache:
            self.status = f"📦 {level.value.title()} analysis already cached"
            return
        
        # Check if already queued/running
        context_pattern = f"{prev_commit.short_hash}→{current_commit.short_hash}"
        for task in self.analysis_queue.tasks.values():
            if (context_pattern in task.context and 
                task.level == level and 
                task.status.value in ["pending", "running"]):
                self.status = f"🔄 {level.value.title()} analysis already {task.status.value}"
                return
        
        # Get diff
        diff = self.git.get_commit_diff(prev_commit.hash, current_commit.hash)
        if not diff:
            self.status = "❌ Could not get commit diff"
            return
        
        if not diff.diff_text:
            self.status = "❌ Empty diff"
            return
        
        # Create task
        task_id = str(uuid.uuid4())[:8]
        context = f"{prev_commit.short_hash}→{current_commit.short_hash}: {current_commit.message[:30]}"
        
        def on_complete(result: DiffAnalysis):
            try:
                # Store result and update cache
                
                # Cache first
                cache_key = f"{prev_commit.hash}_{current_commit.hash}_{level.value}"
                self.llm_cache[cache_key] = result
                
                # ПРИНУДИТЕЛЬНО обновить current_analyses прямо сейчас
                if self.selected_commit_idx < len(self.commits):
                    selected_hash = self.commits[self.selected_commit_idx].hash
                    if selected_hash == current_commit.hash:
                        # Правильное соответствие значений level и ключей 
                        if level.value == "brief":
                            analysis_key = "brief"
                        elif level.value == "detailed":  # AnalysisLevel.DETAILED.value == "detailed"
                            analysis_key = "deep"
                        else:
                            analysis_key = "brief"  # fallback
                        self.current_analyses[analysis_key] = result
                        # Clear status so analysis shows in panel, not status bar
                        self.status = ""
                
                # ПРИНУДИТЕЛЬНО обновить весь интерфейс
                if hasattr(self, 'scr') and self.scr:
                    try:
                        h, w = self.scr.getmaxyx()
                        left_width = int(w * 0.382)
                        top_height = int(h * 0.45)
                        bottom_height = h - top_height - 2
                        
                        # Обновить панель анализа
                        if self.mode == "llm_detail":
                            self._draw_llm_deep_analysis(self.scr, top_height + 1, 2, left_width - 3, bottom_height - 2)
                        else:
                            self._draw_llm_analysis_panel(self.scr, top_height + 1, 2, left_width - 3, bottom_height - 2)
                        
                        # Обновить панель коммитов для показа индикаторов
                        self._draw_history_panel(self.scr, 2, 2, left_width - 3, top_height - 3)
                        
                        self.scr.refresh()
                    except:
                        pass
                    
            except Exception as e:
                self.status = f"❌ Callback error: {str(e)[:40]}"
        
        def status_update(msg: str):
            self.status = msg
            # Force UI refresh during analysis for real-time feedback
            if hasattr(self, 'scr') and self.scr:
                try:
                    h, w = self.scr.getmaxyx()
                    self._draw_status_bar(self.scr, h - 1, w)
                    self.scr.refresh()
                except:
                    pass
        
        # Get file contents for proper analysis
        prev_content = ""
        curr_content = ""
        
        # Try to get representative file content from the diff
        if diff.files:
            # Get content of the first changed file as representative
            main_file = diff.files[0]
            
            prev_file_content = self.git.get_file_content_at_commit(prev_commit.hash, main_file)
            curr_file_content = self.git.get_file_content_at_commit(current_commit.hash, main_file)
            
            if prev_file_content is not None:
                prev_content = prev_file_content
                
            if curr_file_content is not None:
                curr_content = curr_file_content
        
        # If we can't get file contents, use the diff as new_text
        if not curr_content:
            curr_content = diff.diff_text
        
        task = AnalysisTask(
            id=task_id,
            old_text=prev_content,
            new_text=curr_content,
            context=context,
            level=level,
            callback=on_complete,
            status_callback=status_update
        )
        
        self.analysis_queue.add_task(task)
        self.status = f"🔄 Queued {level.value} analysis: {context}"
        
        # Force immediate status update for user feedback
        if hasattr(self, 'scr') and self.scr:
            try:
                self._draw_status_bar(self.scr, self.scr.getmaxyx()[0] - 1, self.scr.getmaxyx()[1])
                self.scr.refresh()
            except:
                pass
    
    def _handle_d_button(self):
        """Smart D button: starts brief → deep → toggles view"""
        if self.selected_commit_idx < 0 or self.selected_commit_idx >= len(self.commits):
            return
        
        current_commit = self.commits[self.selected_commit_idx]
        brief_analysis = self.current_analyses.get("brief")
        deep_analysis = self.current_analyses.get("deep")
        
        if not brief_analysis:
            # No analysis yet - start brief
            self._queue_analysis(AnalysisLevel.BRIEF)
        elif not deep_analysis:
            # Have brief, no deep - start deep
            self._queue_analysis(AnalysisLevel.DETAILED)
        else:
            # Have both - toggle view between brief and deep
            if self.mode == "llm_detail":
                self.mode = "view"  # Switch to brief view
                self.status = "📝 Showing brief analysis"
            else:
                self.mode = "llm_detail"  # Switch to deep view  
                self.status = "📊 Showing deep analysis"
            # Force refresh of current analyses
            self._load_cached_analyses()
    
    def _copy_to_clipboard(self, text: str):
        """Copy text to system clipboard"""
        try:
            # Try different clipboard commands
            if subprocess.run(["which", "pbcopy"], capture_output=True).returncode == 0:
                # macOS
                subprocess.run(["pbcopy"], input=text.encode(), check=True)
            elif subprocess.run(["which", "xclip"], capture_output=True).returncode == 0:
                # Linux with xclip
                subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=True)
            elif subprocess.run(["which", "xsel"], capture_output=True).returncode == 0:
                # Linux with xsel
                subprocess.run(["xsel", "--clipboard", "--input"], input=text.encode(), check=True)
            else:
                self.status = "❌ No clipboard utility found (install pbcopy/xclip/xsel)"
                return False
            return True
        except Exception as e:
            self.status = f"❌ Copy failed: {str(e)[:30]}"
            return False
    
    def _copy_commits(self):
        """Copy commit list to clipboard (i key)"""
        if not self.commits:
            self.status = "❌ No commits to copy"
            return
            
        lines = []
        for commit in self.commits:
            lines.append(f"{commit.short_hash} {commit.message}")
        
        text = "\n".join(lines)
        if self._copy_to_clipboard(text):
            self.status = f"📋 Copied {len(self.commits)} commits to clipboard"
    
    def _copy_analysis(self):
        """Copy current analysis to clipboard (o key)"""
        if not self.current_analyses:
            self.status = "❌ No analysis to copy"
            return
            
        lines = []
        
        # Add brief if available
        brief = self.current_analyses.get("brief")
        if brief:
            lines.append("=== BRIEF ANALYSIS ===")
            lines.append(f"Summary: {brief.summary}")
            lines.append(f"Type: {brief.change_type.name}")
            lines.append(f"Impact: {brief.impact_level}")
            if brief.details:
                lines.append(f"Details: {brief.details}")
            lines.append("")
        
        # Add deep if available  
        deep = self.current_analyses.get("deep")
        if deep:
            lines.append("=== DEEP ANALYSIS ===")
            lines.append(f"Summary: {deep.summary}")
            lines.append(f"Type: {deep.change_type.name}")
            lines.append(f"Impact: {deep.impact_level}")
            if deep.details:
                lines.append(f"Details: {deep.details}")
            if deep.risks:
                lines.append("Risks:")
                for risk in deep.risks:
                    lines.append(f"  - {risk}")
            if deep.recommendations:
                lines.append("Recommendations:")
                for rec in deep.recommendations:
                    lines.append(f"  - {rec}")
        
        text = "\n".join(lines)
        if self._copy_to_clipboard(text):
            self.status = "📋 Copied analysis to clipboard"
    
    def _copy_diff(self):
        """Copy current diff to clipboard (p key)"""
        if self.selected_commit_idx < 0 or self.selected_commit_idx >= len(self.commits):
            self.status = "❌ No commit selected"
            return
            
        current_commit = self.commits[self.selected_commit_idx]
        
        # Get previous commit for diff
        if self.selected_commit_idx < len(self.commits) - 1:
            prev_commit = self.commits[self.selected_commit_idx + 1]
        else:
            self.status = "❌ No previous commit for diff"
            return
        
        # Get diff
        diff = self.git.get_commit_diff(prev_commit.hash, current_commit.hash)
        if not diff or not diff.diff_text:
            self.status = "❌ No diff available"
            return
        
        # Format diff with header
        lines = [
            f"Commit: {current_commit.short_hash} {current_commit.message}",
            f"Author: {current_commit.author}",
            f"Date: {current_commit.date}",
            "",
            diff.diff_text
        ]
        
        text = "\n".join(lines)
        if self._copy_to_clipboard(text):
            self.status = "📋 Copied diff to clipboard"
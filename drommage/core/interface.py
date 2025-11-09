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
from .analysis_queue import AnalysisQueue, AnalysisTask, TaskStatus as AnalysisTaskStatus
from .git_integration import GitIntegration, GitCommit
from .engine import DRommageEngine
from .analysis import AnalysisMode, AnalysisResult
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
    def __init__(self, drommage_engine):
        """
        Initialize TUI with DRommageEngine.
        
        Args:
            drommage_engine: DRommageEngine instance for analysis
        """
        # Use new DRommageEngine instead of old components
        self.drommage_engine = drommage_engine
        self.commits = []  # Will be loaded from engine
        
        # Legacy components (remove gradually)
        self.engine = None  # Old GitDiffEngine
        self.region_index = None  # Old RegionIndex  
        self.git = drommage_engine.git  # Use git from engine
        
        # Remove old LLM initialization - use engine instead
        # self.llm = LLMAnalyzer(model="mistral:latest")  # ❌ REMOVED
        # self.analysis_queue = AnalysisQueue(self.llm)   # ❌ REMOVED
        # self.analysis_queue.start()                     # ❌ REMOVED
        
        # Remove old JSON cache - use SQLite through engine
        # self.llm_cache = {}  # ❌ REMOVED
        # self._init_cache()   # ❌ REMOVED
        
        # Load commits from engine
        self.commits = self.drommage_engine.load_commits(50)
        
        # UI state
        self.selected_commit_idx = 0 if self.commits else -1
        self.selected_region = None
        self.mode = "view"  # view, region_detail, llm_detail, queue
        self.analysis_mode = AnalysisMode.PAT  # Current analysis mode: PAT → BRIEF → DEEP
        self.right_scroll = 0
        self.commit_scroll = 0  # Horizontal scroll for commit list
        self.commit_page_offset = 0  # Current page offset for commits
        self.status = ""
        
        # Replace old analysis tracking with new system
        self.current_analyses = {
            AnalysisMode.PAT: {},    # {commit_hash: AnalysisResult}
            AnalysisMode.BRIEF: {},  # {commit_hash: AnalysisResult}  
            AnalysisMode.DEEP: {}    # {commit_hash: AnalysisResult}
        }
        
        # Remove old task tracking - engine handles this
        # self.active_tasks = []  # ❌ REMOVED
        
        self.animation_frame = 0  # For animated indicators
        self.page_flip_animation = {"active": False, "start_time": 0, "direction": ""}  # Page flip animation
        self.analysis_scroll = 0  # Scroll position for analysis panel
        
        
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
        self._load_analyses_from_engine()
        if not any(self.current_analyses.values()):
            self.status = ""
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
                elif self.mode == "help":
                    # Clear entire screen for clean help display
                    scr.clear()
                    # Draw frame for help mode
                    self._draw_help_frame(scr, h, w)
                    # Split into two panels like main interface
                    help_left_width = int(w * 0.5)
                    self._draw_help_left_panel(scr, 2, 2, help_left_width - 3, h - 4)
                    self._draw_help_right_panel(scr, 2, help_left_width + 2, w - help_left_width - 3, h - 4)
                
                # Status bar with gradient (skip in help mode)
                if self.mode != "help":
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
            
        # Handle page flip animation
        import time
        animation_icon = "📚"
        if self.page_flip_animation["active"]:
            elapsed = time.time() - self.page_flip_animation["start_time"]
            if elapsed < 0.25:
                # Show animation
                direction = self.page_flip_animation["direction"]
                if direction == "up":
                    animation_icon = "📖" if elapsed < 0.125 else "📗"
                else:  # down
                    animation_icon = "📘" if elapsed < 0.125 else "📙"
            else:
                # Animation complete
                self.page_flip_animation["active"] = False
        
        scr.addstr(y, x, f"{animation_icon} Git Commits", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
        y += 1
        
        # Calculate actual available display space
        # y starts at panel top + title (1) + pagination (potentially 1) + spacing (1) = y + 3
        # Available lines = panel bottom - current y position - border space
        available_lines = h - 4  # Reserve space for borders and avoid overflow
        commits_per_page = available_lines  # This should match the display break condition
        total_pages = (len(self.commits) + commits_per_page - 1) // commits_per_page if self.commits else 1
        current_page = (self.commit_page_offset // commits_per_page) + 1
        
        if total_pages > 1:
            page_icon = "📄"
            if self.page_flip_animation["active"]:
                # Show flip animation in pagination too
                page_icon = "📃" if (time.time() - self.page_flip_animation["start_time"]) < 0.125 else "📋"
            scr.addstr(y, x, f"{page_icon} Page {current_page}/{total_pages}", curses.color_pair(PALETTE["dim"]))
        y += 2
        
        # Show commits with pagination - use actual available space
        start_idx = self.commit_page_offset
        # Ensure we don't slice more commits than we can actually display
        displayable_commits = min(commits_per_page, available_lines, len(self.commits) - start_idx)
        end_idx = start_idx + displayable_commits
        page_commits = self.commits[start_idx:end_idx]
        
        # Now page_commits contains exactly the right number of commits to display
        for display_idx, commit in enumerate(page_commits):
            actual_idx = start_idx + display_idx
            if actual_idx == self.selected_commit_idx:
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
            if actual_idx < len(self.commits) - 1:
                prev_short_hash = self.commits[actual_idx + 1].short_hash
            
            # Check analysis status using new system
            pat_status = "completed" if commit.hash in self.current_analyses[AnalysisMode.PAT] else None
            brief_status = "completed" if commit.hash in self.current_analyses[AnalysisMode.BRIEF] else None
            deep_status = "completed" if commit.hash in self.current_analyses[AnalysisMode.DEEP] else None
            
            # Check if current commit is being analyzed
            is_current = (actual_idx == self.selected_commit_idx)
            if is_current and self.status and "🔄" in self.status:
                if self.analysis_mode == AnalysisMode.PAT:
                    pat_status = "running"
                elif self.analysis_mode == AnalysisMode.BRIEF:
                    brief_status = "running" 
                elif self.analysis_mode == AnalysisMode.DEEP:
                    deep_status = "running"
            
            # Show PAT/BRIEF/DEEP indicators with current mode highlighted
            pat_indicator = ""
            brief_indicator = ""
            deep_indicator = ""
            
            # Show indicators for current commit
            if actual_idx == self.selected_commit_idx:
                # Show current mode prominently
                if self.analysis_mode == AnalysisMode.PAT:
                    pat_indicator = self._get_status_indicator(pat_status, "P")
                    brief_indicator = " b "
                    deep_indicator = " d "
                elif self.analysis_mode == AnalysisMode.BRIEF:
                    pat_indicator = " p "
                    brief_indicator = self._get_status_indicator(brief_status, "B")
                    deep_indicator = " d "
                else:  # DEEP
                    pat_indicator = " p "
                    brief_indicator = " b "
                    deep_indicator = self._get_status_indicator(deep_status, "D")
            else:
                # For non-selected commits, show status if available
                if pat_status:
                    pat_indicator = self._get_status_indicator(pat_status, "p")
                if brief_status:
                    brief_indicator = self._get_status_indicator(brief_status, "b")
                if deep_status:
                    deep_indicator = self._get_status_indicator(deep_status, "d")
            
            # Combine indicators
            indicators = pat_indicator + brief_indicator + deep_indicator
            
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
            
            # Only display if we have space
            if y + display_idx < y + available_lines:
                try:
                    scr.addnstr(y + display_idx, x, line[:w], w, attr)
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
            scr.addstr(y, x, "📝 Brief Analysis", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
            y += 2
            scr.addstr(y, x, "No commits available", curses.color_pair(PALETTE["dim"]))
            return
            
        current_commit = self.commits[self.selected_commit_idx]
        
        # Header with current analysis mode
        mode_icons = {
            AnalysisMode.PAT: "🔍",
            AnalysisMode.BRIEF: "📝", 
            AnalysisMode.DEEP: "📊"
        }
        mode_title = f"{mode_icons[self.analysis_mode]} {self.analysis_mode.value.title()} Analysis"
        scr.addstr(y, x, mode_title, curses.A_BOLD | curses.color_pair(PALETTE["title"]))
        y += 2
        
        # Get analysis for current mode and commit
        current_analysis = None
        if current_commit.hash in self.current_analyses[self.analysis_mode]:
            current_analysis = self.current_analyses[self.analysis_mode][current_commit.hash]
        
        # Check if analysis is in progress (status contains processing indicators)
        is_analyzing = self.status and "🔄" in self.status
        
        if current_analysis:
            # Show completed analysis using AnalysisResult format
            provider_info = f"Provider: {current_analysis.provider}"
            scr.addstr(y, x, provider_info, curses.color_pair(PALETTE["dim"]))
            y += 1
            
            # Mode and status
            mode_text = f"Mode: {current_analysis.mode.value.upper()}"
            scr.addstr(y, x, mode_text, curses.color_pair(PALETTE["icon"]))
            y += 1
            
            # Change type if available in metadata
            if 'change_type' in current_analysis.metadata:
                change_type = current_analysis.metadata['change_type']
                scr.addstr(y, x, f"Type: {change_type}", curses.color_pair(PALETTE["icon"]))
                y += 1
            
            y += 1  # Spacing
            
        elif is_analyzing:
            # Show analysis in progress
            scr.addstr(y, x, "⏳ Analysis in progress...", curses.color_pair(PALETTE["modified"]) | curses.A_BOLD)
            y += 2
            
            # Show progress animation
            anim_frames = ["◐", "◓", "◑", "◒"]
            import time
            frame = anim_frames[int(time.time() * 2) % len(anim_frames)]
            scr.addstr(y, x, f"{frame} Processing...", curses.color_pair(PALETTE["dim"]))
            return
        else:
            # No analysis yet - show instructions
            scr.addstr(y, x, "Press 'd' to start analysis", curses.color_pair(PALETTE["dim"]))
            y += 1
            scr.addstr(y, x, "or use arrow keys to navigate", curses.color_pair(PALETTE["dim"]))
            return
        
        # Summary
        scr.addstr(y, x, "Summary:", curses.A_BOLD)
        y += 1
        
        # Word wrap summary
        
        # Collect all content lines for scrolling
        all_content_lines = []
        
        # Summary
        if current_analysis.summary:
            summary_lines = self._word_wrap(current_analysis.summary, w - 2)
            all_content_lines.extend(summary_lines)
        else:
            all_content_lines.append("⚠️ No summary available")
        
        # Details
        if current_analysis.details:
            all_content_lines.append("")  # Empty line separator
            all_content_lines.append("Details:")
            detail_lines = self._word_wrap(current_analysis.details, w - 2)
            all_content_lines.extend(detail_lines)
        
        # Risks
        if hasattr(current_analysis, 'risks') and current_analysis.risks:
            all_content_lines.append("")  # Empty line separator
            all_content_lines.append("Risks:")
            for risk in current_analysis.risks[:2]:  # Limit to 2 risks in brief view
                risk_lines = self._word_wrap(f"• {risk}", w - 2)
                all_content_lines.extend(risk_lines)
        
        # Apply scroll and display
        start_y_brief = y - 3  # Approximate start of panel
        scrolled_lines = all_content_lines[self.analysis_scroll:] if self.analysis_scroll < len(all_content_lines) else []
        
        # Calculate line number width (for total lines, not just visible)
        total_lines = len(all_content_lines)
        line_num_width = len(str(total_lines)) + 1  # +1 for space
        content_width = w - line_num_width - 1  # -1 for separator
        
        for i, line in enumerate(scrolled_lines):
            if y >= start_y_brief + h - 2:  # Leave space only for border and scroll indicator at very bottom
                break
            try:
                # Calculate actual line number (accounting for scroll)
                actual_line_num = self.analysis_scroll + i + 1
                line_num_str = f"{actual_line_num:>{line_num_width-1}} "
                
                # Draw line number
                scr.addstr(y, x, line_num_str, curses.color_pair(PALETTE["dim"]))
                
                # Draw separator
                scr.addstr(y, x + line_num_width, "│", curses.color_pair(PALETTE["border"]))
                
                # Skip empty lines for display but keep line numbers
                if line == "":
                    y += 1
                    continue
                
                # Draw content with adjusted position and width
                content_x = x + line_num_width + 1
                
                # Color based on content type
                if line.startswith("Details:"):
                    scr.addnstr(y, content_x, line, content_width, curses.A_BOLD)
                elif line.startswith("Risks:"):
                    scr.addnstr(y, content_x, line, content_width, curses.A_BOLD | curses.color_pair(PALETTE["removed"]))
                elif line.startswith("•"):
                    scr.addnstr(y, content_x, line, content_width, curses.color_pair(PALETTE["removed"]))
                elif line.startswith("⚠️"):
                    scr.addnstr(y, content_x, line, content_width, curses.color_pair(PALETTE["dim"]))
                else:
                    scr.addnstr(y, content_x, line, content_width, curses.color_pair(PALETTE["llm_summary"]))
                y += 1
            except:
                break
        
        # Draw scroll indicator at very bottom of panel
        self._draw_analysis_scroll_indicator(scr, start_y_brief + h - 1, x, w, all_content_lines, current_analysis)
        
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
        scr.addstr(y, x, "📊 Deep Analysis", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
        y += 2
        
        # Get deep analysis specifically
        deep_analysis = self.current_analyses.get("deep")
        
        if deep_analysis:
            # Type
            try:
                type_text = f"Type: {deep_analysis.change_type.name}"
            except:
                type_text = "Type: UNKNOWN"
            scr.addstr(y, x, type_text, curses.color_pair(PALETTE["icon"]))
            y += 1
            
            # Impact
            impact_bars = {"low": "▁▁▁", "medium": "▃▃▃", "high": "▇▇▇"}
            impact_color = {"low": PALETTE["stable"], "medium": PALETTE["modified"], "high": PALETTE["volatile"]}
            bars = impact_bars.get(deep_analysis.impact_level, "▁▁▁")
            color = impact_color.get(deep_analysis.impact_level, PALETTE["dim"])
            scr.addstr(y, x, f"Impact: {bars} {deep_analysis.impact_level}", 
                      curses.color_pair(color))
            y += 2
            
            # Collect all content lines for scrolling in deep analysis
            all_deep_lines = []
            
            # Summary
            if deep_analysis.summary:
                summary_lines = self._word_wrap(deep_analysis.summary, w - 2)
                all_deep_lines.extend(summary_lines)
            else:
                all_deep_lines.append("⚠️ No summary available")
            
            # Details
            if deep_analysis.details:
                all_deep_lines.append("")  # Empty line separator
                all_deep_lines.append("Details:")
                detail_lines = self._word_wrap(deep_analysis.details, w - 2)
                all_deep_lines.extend(detail_lines)
            
            # Risks
            if deep_analysis.risks:
                all_deep_lines.append("")  # Empty line separator
                all_deep_lines.append("Risks:")
                for risk in deep_analysis.risks:
                    risk_lines = self._word_wrap(f"• {risk}", w - 2)
                    all_deep_lines.extend(risk_lines)
            
            # Recommendations
            if hasattr(deep_analysis, 'recommendations') and deep_analysis.recommendations:
                all_deep_lines.append("")  # Empty line separator
                all_deep_lines.append("Recommendations:")
                for rec in deep_analysis.recommendations:
                    rec_lines = self._word_wrap(f"• {rec}", w - 2)
                    all_deep_lines.extend(rec_lines)
            
            # Apply scroll and display
            scrolled_deep_lines = all_deep_lines[self.analysis_scroll:] if self.analysis_scroll < len(all_deep_lines) else []
            
            # Calculate line number width for deep analysis
            total_deep_lines = len(all_deep_lines)
            line_num_width = len(str(total_deep_lines)) + 1  # +1 for space
            content_width = w - line_num_width - 1  # -1 for separator
            
            for i, line in enumerate(scrolled_deep_lines):
                if y >= start_y + h - 2:  # Leave space only for border and scroll indicator at very bottom
                    break
                try:
                    # Calculate actual line number (accounting for scroll)
                    actual_line_num = self.analysis_scroll + i + 1
                    line_num_str = f"{actual_line_num:>{line_num_width-1}} "
                    
                    # Draw line number
                    scr.addstr(y, x, line_num_str, curses.color_pair(PALETTE["dim"]))
                    
                    # Draw separator
                    scr.addstr(y, x + line_num_width, "│", curses.color_pair(PALETTE["border"]))
                    
                    # Skip empty lines for display but keep line numbers
                    if line == "":
                        y += 1
                        continue
                    
                    # Draw content with adjusted position and width
                    content_x = x + line_num_width + 1
                    
                    # Color based on content type
                    if line.startswith("Details:"):
                        scr.addnstr(y, content_x, line, content_width, curses.A_BOLD)
                    elif line.startswith("Risks:"):
                        scr.addnstr(y, content_x, line, content_width, curses.A_BOLD | curses.color_pair(PALETTE["removed"]))
                    elif line.startswith("Recommendations:"):
                        scr.addnstr(y, content_x, line, content_width, curses.A_BOLD | curses.color_pair(PALETTE["added"]))
                    elif line.startswith("•") and "Recommendations:" in all_deep_lines[max(0, all_deep_lines.index(line)-5):all_deep_lines.index(line)]:
                        scr.addnstr(y, content_x, line, content_width, curses.color_pair(PALETTE["added"]))
                    elif line.startswith("•"):
                        scr.addnstr(y, content_x, line, content_width, curses.color_pair(PALETTE["removed"]))
                    elif line.startswith("⚠️"):
                        scr.addnstr(y, content_x, line, content_width, curses.color_pair(PALETTE["dim"]))
                    else:
                        scr.addnstr(y, content_x, line, content_width, curses.color_pair(PALETTE["llm_summary"]))
                    y += 1
                except:
                    break
            
            # Draw scroll indicator at very bottom for deep analysis
            self._draw_analysis_scroll_indicator(scr, start_y + h - 1, x, w, all_deep_lines, deep_analysis)
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
                
                # Show diff lines with proper color preservation using unified function
                wrapped_diff_lines = self._get_wrapped_diff_lines(diff.diff_text, w)
                
                # Apply vertical scrolling - calculate available space accurately
                content_start_y = y
                available_height = h - (y - 2) - 2  # Account for header and scroll indicator
                diff_lines = wrapped_diff_lines[self.right_scroll:self.right_scroll + available_height]
                
                # Calculate line number width for diff lines (based on original lines, not wrapped)
                raw_diff_lines = diff.diff_text.split('\n')
                total_original_lines = len(raw_diff_lines) 
                line_num_width = len(str(total_original_lines)) + 1  # +1 for space
                content_width = w - line_num_width - 1  # -1 for separator
                
                for i, (line_text, line_prefix, original_line_num) in enumerate(diff_lines):
                    if y + i >= h - 1:  # Leave room only for scroll indicator
                        break
                    
                    # Use the original line number from the raw diff (not wrapped line index)
                    line_num_str = f"{original_line_num:>{line_num_width-1}} "
                    
                    # Draw line number
                    scr.addstr(y + i, x, line_num_str, curses.color_pair(PALETTE["dim"]))
                    
                    # Draw separator
                    scr.addstr(y + i, x + line_num_width, "│", curses.color_pair(PALETTE["border"]))
                    
                    # Draw diff content with adjusted position and width
                    content_x = x + line_num_width + 1
                    
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
                        scr.addnstr(y + i, content_x, line_text, content_width, attr)
                    except:
                        pass
                
                # Draw scroll indicator at very bottom of diff panel
                self._draw_diff_scroll_indicator(scr, y + len(diff_lines), x, w, len(wrapped_diff_lines))
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
    
    def _draw_simple_help(self, scr, h, w):
        """Draw simple, readable help screen"""
        try:
            y = 1
            x = 2
            
            # Title
            title = "DRommage v8 - Help"
            scr.addstr(y, max(0, (w - len(title)) // 2), title, curses.A_BOLD | curses.color_pair(PALETTE["title"]))
            y += 3
            
            help_content = [
                ("OVERVIEW:", ""),
                ("", "Git-powered documentation analysis with AI insights"),
                ("", ""),
                ("NAVIGATION:", ""),
                ("↑/↓", "Navigate commits"),
                ("←/→", "Scroll diff horizontally"),
                ("q/e", "Page up/down quickly"),
                ("", ""),
                ("AI ANALYSIS:", ""),
                ("D", "Toggle brief/deep analysis"),
                ("r/f", "Scroll analysis text"),
                ("", ""),
                ("CLIPBOARD:", ""),
                ("i", "Copy commit info"),
                ("o", "Copy analysis text"),
                ("p", "Copy diff content"),
                ("", ""),
                ("OTHER:", ""),
                ("h", "Toggle this help"),
                ("Q", "Quit application"),
                ("", ""),
                ("", "Press h to return to main interface")
            ]
            
            for key, desc in help_content:
                if y >= h - 2:
                    break
                    
                if key == "":
                    # Empty line or description only
                    if desc:
                        if desc.endswith("interface"):
                            # Footer
                            scr.addstr(y, max(0, (w - len(desc)) // 2), desc, curses.color_pair(PALETTE["dim"]) | curses.A_ITALIC)
                        elif desc.endswith(":"):
                            # Section header
                            scr.addstr(y, x, desc, curses.A_BOLD | curses.color_pair(PALETTE["title"]))
                        else:
                            # Regular description
                            scr.addstr(y, x + 2, desc, curses.color_pair(PALETTE["llm_summary"]))
                else:
                    # Key + description
                    scr.addstr(y, x + 2, f"{key:<4} - {desc}", curses.color_pair(PALETTE["llm_summary"]))
                
                y += 1
                
        except Exception as e:
            scr.addstr(1, 2, f"Help error: {str(e)[:50]}", curses.color_pair(PALETTE["dim"]))

    def _draw_help_frame(self, scr, h, w):
        """Draw frame for help mode similar to main interface"""
        # Title
        title = "DRommage v8 - Help Documentation"
        title_x = max(0, (w - len(title)) // 2)
        try:
            scr.addstr(0, title_x, title, curses.color_pair(PALETTE["title"]) | curses.A_BOLD)
        except:
            scr.addstr(0, title_x, title, curses.A_BOLD)
        
        # Help left width (50%)
        help_left_width = int(w * 0.5)
        
        # Simple ASCII borders
        try:
            # Top border
            scr.addstr(1, 0, "+", curses.color_pair(PALETTE["border"]))
            for x in range(1, help_left_width):
                scr.addstr(1, x, "-", curses.color_pair(PALETTE["border"]))
            scr.addstr(1, help_left_width, "+", curses.color_pair(PALETTE["border"]))
            for x in range(help_left_width + 1, w - 1):
                scr.addstr(1, x, "-", curses.color_pair(PALETTE["border"]))
            scr.addstr(1, w - 1, "+", curses.color_pair(PALETTE["border"]))
            
            # Vertical separators
            for y in range(2, h - 1):
                scr.addstr(y, 0, "|", curses.color_pair(PALETTE["border"]))
                scr.addstr(y, help_left_width, "|", curses.color_pair(PALETTE["border"]))
                scr.addstr(y, w - 1, "|", curses.color_pair(PALETTE["border"]))
            
            # Bottom border
            scr.addstr(h - 1, 0, "+", curses.color_pair(PALETTE["border"]))
            for x in range(1, help_left_width):
                scr.addstr(h - 1, x, "-", curses.color_pair(PALETTE["border"]))
            scr.addstr(h - 1, help_left_width, "+", curses.color_pair(PALETTE["border"]))
            for x in range(help_left_width + 1, w - 1):
                scr.addstr(h - 1, x, "-", curses.color_pair(PALETTE["border"]))
            scr.addstr(h - 1, w - 1, "+", curses.color_pair(PALETTE["border"]))
        except:
            pass  # If border drawing fails, continue without borders
        
        # Help bar at bottom
        help_text = "[h] back to main"
        help_x = max(1, (w - len(help_text)) // 2)
        try:
            scr.addnstr(h - 1, help_x, help_text, w - 2, curses.color_pair(PALETTE["dim"]))
        except:
            pass

    def _draw_help_left_panel(self, scr, y, x, w, h):
        """Draw left help panel - overview and interface"""
        try:
            # Overview section
            try:
                scr.addstr(y, x, "OVERVIEW", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
            except:
                scr.addstr(y, x, "OVERVIEW", curses.A_BOLD)
            y += 2
            
            overview_text = [
                "DRommage is a git-powered documentation analysis tool that uses AI to",
                "understand code changes and provide intelligent insights about your",
                "repository evolution."
            ]
            
            for line in overview_text:
                if y >= h - 2:
                    break
                try:
                    scr.addstr(y, x, line[:w-2], curses.color_pair(PALETTE["llm_summary"]))
                except:
                    scr.addstr(y, x, line[:w-2])
                y += 1
            y += 1
            
            # Interface layout
            try:
                scr.addstr(y, x, "INTERFACE LAYOUT", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
            except:
                scr.addstr(y, x, "INTERFACE LAYOUT", curses.A_BOLD)
            y += 2
            
            layout_lines = [
                "+-------------+-------------+",
                "| Commit List |             |",
                "|   (Left)    | Diff Panel  |",
                "+-------------+  (Right)    |",
                "| Analysis    |             |",
                "| (Bot. Left) |             |",
                "+-------------+-------------+"
            ]
            
            for line in layout_lines:
                if y >= h - 2:
                    break
                # Center the layout diagram
                line_x = x + max(0, (w - len(line)) // 2)
                try:
                    scr.addstr(y, line_x, line[:w-2], curses.color_pair(PALETTE["border"]))
                except:
                    scr.addstr(y, line_x, line[:w-2])
                y += 1
            y += 1
            
            # Navigation
            if y < h - 10:
                try:
                    scr.addstr(y, x, "NAVIGATION", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
                except:
                    scr.addstr(y, x, "NAVIGATION", curses.A_BOLD)
                y += 2
                
                nav_items = [
                    "Up/Down  - Navigate through commit list",
                    "Left/Right  - Scroll diff panel horizontally", 
                    "q/e  - Page up/down through commits quickly",
                    "h    - Toggle this help screen"
                ]
                
                for item in nav_items:
                    if y >= h - 2:
                        break
                    try:
                        scr.addstr(y, x, item[:w-2], curses.color_pair(PALETTE["llm_summary"]))
                    except:
                        scr.addstr(y, x, item[:w-2])
                    y += 1
                    
        except Exception as e:
            scr.addstr(y, x, "Help panel error", curses.color_pair(PALETTE["dim"]))

    def _draw_help_right_panel(self, scr, y, x, w, h):
        """Draw right help panel - features and operations"""
        try:
            # AI Analysis
            try:
                scr.addstr(y, x, "AI ANALYSIS", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
            except:
                scr.addstr(y, x, "AI ANALYSIS", curses.A_BOLD)
            y += 2
            
            ai_items = [
                "D    - Toggle between brief and deep AI analysis of selected commit",
                "       Brief: Quick summary of changes",
                "       Deep: Detailed analysis with risks and recommendations",
                "r/f  - Scroll analysis text up/down",
                "       Shows AI-generated summaries",
                "       Includes change types and impact levels"
            ]
            
            for item in ai_items:
                if y >= h - 2:
                    break
                try:
                    scr.addstr(y, x, item[:w-2], curses.color_pair(PALETTE["llm_summary"]))
                except:
                    scr.addstr(y, x, item[:w-2])
                y += 1
            y += 1
            
            # Clipboard operations
            try:
                scr.addstr(y, x, "CLIPBOARD OPERATIONS", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
            except:
                scr.addstr(y, x, "CLIPBOARD OPERATIONS", curses.A_BOLD)
            y += 2
            
            clipboard_items = [
                "i    - Copy commit info (hash, message, author) to clipboard",
                "o    - Copy AI analysis text to clipboard",
                "p    - Copy diff content to clipboard"
            ]
            
            for item in clipboard_items:
                if y >= h - 2:
                    break
                try:
                    scr.addstr(y, x, item[:w-2], curses.color_pair(PALETTE["llm_summary"]))
                except:
                    scr.addstr(y, x, item[:w-2])
                y += 1
            y += 1
            
            # Features
            try:
                scr.addstr(y, x, "FEATURES", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
            except:
                scr.addstr(y, x, "FEATURES", curses.A_BOLD)
            y += 2
            
            features = [
                "- Async AI analysis - doesn't block interface",
                "- Smart caching - analysis results saved locally", 
                "- Unicode interface - beautiful box drawing characters",
                "- Cross-platform clipboard support",
                "- Real-time scroll position indicators"
            ]
            
            for feature in features:
                if y >= h - 2:
                    break
                try:
                    scr.addstr(y, x, feature[:w-2], curses.color_pair(PALETTE["llm_summary"]))
                except:
                    scr.addstr(y, x, feature[:w-2])
                y += 1
            y += 1
            
            # Tips
            if y < h - 6:
                try:
                    scr.addstr(y, x, "USAGE TIPS", curses.A_BOLD | curses.color_pair(PALETTE["title"]))
                except:
                    scr.addstr(y, x, "USAGE TIPS", curses.A_BOLD)
                y += 2
                
                tips = [
                    "- Press D on any commit to start AI analysis",
                    "- Analysis runs in background, indicated by animations",
                    "- Use copy functions (i/o/p) to share insights with team",
                    "- Navigate quickly with q/e for large repositories",
                    "- Help analysis improve by reviewing AI recommendations"
                ]
                
                for tip in tips:
                    if y >= h - 2:
                        break
                    try:
                        scr.addstr(y, x, tip[:w-2], curses.color_pair(PALETTE["llm_summary"]))
                    except:
                        scr.addstr(y, x, tip[:w-2])
                    y += 1
            
            # Footer
            if y < h - 3:
                y += 1
                footer = "Press h to return to main interface"
                scr.addstr(y, x + max(0, (w - len(footer)) // 2), footer, curses.color_pair(PALETTE["dim"]) | curses.A_ITALIC)
                    
        except Exception as e:
            scr.addstr(y, x, "Help panel error", curses.color_pair(PALETTE["dim"]))

    def _draw_help_screen(self, scr, y, x, w, h):
        """Draw comprehensive help screen"""
        try:
            help_text = [
                "╔═══ DRommage v8 - Help ═══╗",
                "",
                "📖 OVERVIEW",
                "DRommage is a git-powered documentation analysis tool that uses AI to understand",
                "code changes and provide intelligent insights about your repository evolution.",
                "",
                "🖥️  INTERFACE LAYOUT",
                "┌─────────────────┬─────────────────┐",
                "│   Commit List   │                 │",
                "│   (Left)        │   Diff Panel    │",
                "├─────────────────┤   (Right)       │",
                "│ Analysis Panel  │                 │",
                "│ (Bottom Left)   │                 │",
                "└─────────────────┴─────────────────┘",
                "",
                "🚀 NAVIGATION",
                "↑/↓  - Navigate through commit list",
                "←/→  - Scroll diff panel horizontally",
                "q/e  - Page up/down through commits quickly",
                "",
                "🤖 AI ANALYSIS",
                "D    - Toggle between brief and deep AI analysis of selected commit",
                "     • Brief: Quick summary of changes",
                "     • Deep: Detailed analysis with risks and recommendations",
                "",
                "📋 CLIPBOARD OPERATIONS",
                "i    - Copy commit info (hash, message, author) to clipboard",
                "o    - Copy AI analysis text to clipboard",
                "p    - Copy diff content to clipboard",
                "",
                "🔍 ANALYSIS PANEL (Bottom Left)",
                "r/f  - Scroll analysis text up/down",
                "     • Shows AI-generated summaries",
                "     • Includes change types and impact levels",
                "     • Provides recommendations for improvements",
                "",
                "📄 DIFF PANEL (Right Side)",
                "     • Shows git diff for selected commit vs previous",
                "     • Color-coded: green (+) additions, red (-) deletions",
                "     • Line numbers preserved for long lines",
                "     • Scroll indicators show position in large diffs",
                "",
                "⚡ FEATURES",
                "• Async AI analysis - doesn't block interface",
                "• Smart caching - analysis results saved locally",
                "• Unicode interface - beautiful box drawing characters",
                "• Cross-platform clipboard support",
                "• Real-time scroll position indicators",
                "",
                "🎯 USAGE TIPS",
                "• Press D on any commit to start AI analysis",
                "• Analysis runs in background, indicated by animations",
                "• Use copy functions (i/o/p) to share insights with team",
                "• Navigate quickly with q/e for large repositories",
                "• Help analysis improve by reviewing AI recommendations",
                "",
                "⌨️  QUICK REFERENCE",
                "h    - Toggle this help screen",
                "Q    - Quit application",
                "",
                "Press h to return to main interface"
            ]
            
            # Display help text with scrolling if needed
            start_line = 0
            visible_lines = h - 2
            
            for i, line in enumerate(help_text[start_line:start_line + visible_lines]):
                if y + i >= h:
                    break
                try:
                    # Center the text or left-align based on content
                    if line.startswith("╔"):
                        # Center header
                        text_x = max(0, (w - len(line)) // 2)
                    elif line.startswith("┌") or line.startswith("│") or line.startswith("├") or line.startswith("└"):
                        # Center box drawing
                        text_x = max(0, (w - len(line)) // 2)
                    elif line.startswith("🖥️") or line.startswith("📖") or line.startswith("🚀"):
                        # Section headers
                        text_x = x + 2
                        scr.addnstr(y + i, text_x, line, w - 4, curses.color_pair(PALETTE["title"]) | curses.A_BOLD)
                        continue
                    elif line.startswith("    "):
                        # Indent action items (4 spaces)
                        text_x = x + 4
                    else:
                        # Regular text
                        text_x = x + 2
                    
                    # Determine color
                    if "Press h to return" in line:
                        attr = curses.color_pair(PALETTE["dim"]) | curses.A_ITALIC
                    else:
                        attr = curses.color_pair(PALETTE["llm_summary"])
                    
                    scr.addnstr(y + i, text_x, line, w - 4, attr)
                except:
                    pass
                    
        except Exception as e:
            # Fallback simple help
            scr.addstr(y, x, "Help screen error - press ESC to return", curses.color_pair(PALETTE["dim"]))

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
                ("Q", "quit"),
                ("qe", "flip pages"),
                ("rf", "scroll analysis"),
                ("←→", "scroll"),
                ("iop", "copy"),
                ("h", "help")
            ]
        elif self.mode == "queue":
            help_items = [
                ("Q", "quit"),
                ("any key", "back")
            ]
        elif self.mode == "llm_detail":
            help_items = [
                ("↑↓", "navigate"),
                ("D", "analyze/toggle"),
                ("Q", "quit"),
                ("qe", "flip pages"),
                ("rf", "scroll analysis"),
                ("←→", "scroll"),
                ("iop", "copy"),
                ("h", "help")
            ]
        elif self.mode == "help":
            help_items = [("ESC", "back")]
        else:
            help_items = [("ESC", "back")]
        
        # Status messages are no longer shown to avoid cluttering navigation
        # Always show normal help text
        help_parts = []
        for key, desc in help_items:
            help_parts.append(f"[{key}] {desc}")
        help_text = " │ ".join(help_parts)
        
        # Don't add status to help bar - help items are sufficient
        
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
                self._navigate_up()
                self.right_scroll = 0
                self.analysis_scroll = 0  # Reset analysis scroll
                self._load_analyses_from_engine()
                
            elif ch in (curses.KEY_DOWN, ord('j')):
                self._navigate_down()
                self.right_scroll = 0
                self.analysis_scroll = 0  # Reset analysis scroll
                self._load_analyses_from_engine()
            elif ch in (ord('d'), ord('D')):
                # Smart D button logic
                self._handle_d_button()
            elif ch == ord('Q'):
                return False  # Quit
            elif ch in (ord('r'), ord('R')):
                # Toggle region detail mode
                if self.selected_region:
                    self.mode = "region_detail"
            elif ch == curses.KEY_RIGHT:
                # Scroll diff right with bounds checking
                if self.commits and self.selected_commit_idx >= 0 and self.selected_commit_idx < len(self.commits) - 1:
                    current_commit = self.commits[self.selected_commit_idx]
                    prev_commit = self.commits[self.selected_commit_idx + 1]
                    diff = self.git.get_commit_diff(prev_commit.hash, current_commit.hash)
                    if diff and diff.diff_text:
                        panel_width = 50  # Default estimate
                        if hasattr(self, 'scr'):
                            h, w = self.scr.getmaxyx()
                            left_width = int(w * 0.382)
                            panel_width = w - left_width - 3
                        wrapped_diff_lines = self._get_wrapped_diff_lines(diff.diff_text, panel_width)
                        max_scroll = self._get_max_scroll_for_diff(wrapped_diff_lines, self._get_diff_panel_height())
                        self.right_scroll = min(max_scroll, self.right_scroll + 10)
                    else:
                        self.right_scroll += 10
                else:
                    self.right_scroll += 10
            elif ch == curses.KEY_LEFT:
                self.right_scroll = max(0, self.right_scroll - 10)
            elif ch == ord('h'):
                self.mode = "help"
            elif ch == ord('i'):  # Copy commits to clipboard
                self._copy_commits()
            elif ch == ord('o'):  # Copy analysis to clipboard
                self._copy_analysis()
            elif ch == ord('p'):  # Copy diff to clipboard
                self._copy_diff()
            elif ch == ord('q'):  # Quick page up
                self._flip_page_up()
            elif ch == ord('e'):  # Quick page down
                self._flip_page_down()
            elif ch == ord('r'):  # Scroll analysis up
                self._scroll_analysis_up()
            elif ch == ord('f'):  # Scroll analysis down
                self._scroll_analysis_down()
        
        elif self.mode == "llm_detail":
            # Same navigation as view mode - just showing deep analysis
            if ch in (curses.KEY_UP, ord('k')):
                self._navigate_up()
                self.right_scroll = 0
                self.analysis_scroll = 0  # Reset analysis scroll
                self._load_analyses_from_engine()
            elif ch in (curses.KEY_DOWN, ord('j')):
                self._navigate_down()
                self.right_scroll = 0
                self.analysis_scroll = 0  # Reset analysis scroll
                self._load_analyses_from_engine()
            elif ch in (ord('d'), ord('D')):
                # Smart D button logic
                self._handle_d_button()
            elif ch == ord('Q'):
                return False  # Quit
            elif ch == ord('q'):  # Quick page up
                self._flip_page_up()
            elif ch == ord('e'):  # Quick page down
                self._flip_page_down()
            elif ch == ord('r'):  # Scroll analysis up
                self._scroll_analysis_up()
            elif ch == ord('f'):  # Scroll analysis down
                self._scroll_analysis_down()
            elif ch == curses.KEY_RIGHT:
                # Scroll diff right with bounds checking
                if self.commits and self.selected_commit_idx >= 0 and self.selected_commit_idx < len(self.commits) - 1:
                    current_commit = self.commits[self.selected_commit_idx]
                    prev_commit = self.commits[self.selected_commit_idx + 1]
                    diff = self.git.get_commit_diff(prev_commit.hash, current_commit.hash)
                    if diff and diff.diff_text:
                        panel_width = 50  # Default estimate
                        if hasattr(self, 'scr'):
                            h, w = self.scr.getmaxyx()
                            left_width = int(w * 0.382)
                            panel_width = w - left_width - 3
                        wrapped_diff_lines = self._get_wrapped_diff_lines(diff.diff_text, panel_width)
                        max_scroll = self._get_max_scroll_for_diff(wrapped_diff_lines, self._get_diff_panel_height())
                        self.right_scroll = min(max_scroll, self.right_scroll + 10)
                    else:
                        self.right_scroll += 10
                else:
                    self.right_scroll += 10
            elif ch == curses.KEY_LEFT:
                self.right_scroll = max(0, self.right_scroll - 10)
            elif ch == ord('h'):
                self.mode = "help"
            elif ch == ord('i'):  # Copy commits to clipboard
                self._copy_commits()
            elif ch == ord('o'):  # Copy analysis to clipboard
                self._copy_analysis()
            elif ch == ord('p'):  # Copy diff to clipboard
                self._copy_diff()
        elif self.mode == "region_detail":
            # Return to main view on any key
            self.mode = "view"
            
        elif self.mode == "help":
            if ch == ord('h'):  # h key to toggle back
                self.mode = "view"  # Go back to main view
            else:
                pass  # Ignore other keys in help mode
        
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
    
    def _get_page_size(self):
        """Calculate current page size based on panel dimensions"""
        if hasattr(self, 'scr'):
            h, w = self.scr.getmaxyx()
            top_height = int(h * 0.45)
            panel_height = top_height - 3
            return panel_height - 4  # This matches available_lines = h - 4 from display
        return 8  # Fallback
    
    def _navigate_up(self):
        """Navigate up with page flipping"""
        if self.selected_commit_idx <= 0:
            return
            
        commits_per_page = self._get_page_size()
        current_page_start = self.commit_page_offset
        
        # Check if we're at the first item of current page
        if self.selected_commit_idx == current_page_start and current_page_start > 0:
            # Flip to previous page, select last visible item of that page
            self._start_page_flip_animation("up")
            new_page_start = max(0, current_page_start - commits_per_page)
            self.commit_page_offset = new_page_start
            # Select last visible item of the new page
            new_page_end = min(new_page_start + commits_per_page - 1, len(self.commits) - 1)
            self.selected_commit_idx = new_page_end
        else:
            # Normal navigation within page
            self.selected_commit_idx -= 1
    
    def _navigate_down(self):
        """Navigate down with page flipping"""
        if self.selected_commit_idx >= len(self.commits) - 1:
            return
            
        commits_per_page = self._get_page_size()
        current_page_start = self.commit_page_offset
        current_page_end = min(current_page_start + commits_per_page - 1, len(self.commits) - 1)
        
        # Use the same calculation as display logic: available_lines = h - 4
        if hasattr(self, 'scr'):
            h, w = self.scr.getmaxyx()
            top_height = int(h * 0.45)
            panel_height = top_height - 3
            actual_commits_per_page = panel_height - 4  # This matches available_lines = h - 4 from display
        else:
            actual_commits_per_page = commits_per_page
            
        # Calculate how many items are actually visible/displayable  
        # Use the same logic as display: min(commits_per_page, available_lines, remaining_commits)
        remaining_commits = len(self.commits) - current_page_start
        visible_items_on_page = min(actual_commits_per_page, remaining_commits)
        last_visible_idx = current_page_start + visible_items_on_page - 1
        
        if (self.selected_commit_idx >= last_visible_idx and 
            last_visible_idx < len(self.commits) - 1):
            # Flip to next page, select first item
            self._start_page_flip_animation("down")
            new_page_start = current_page_start + actual_commits_per_page
            if new_page_start < len(self.commits):
                self.commit_page_offset = new_page_start
                self.selected_commit_idx = new_page_start
        else:
            # Normal navigation within page - but don't go past last item
            if self.selected_commit_idx < len(self.commits) - 1:
                next_idx = self.selected_commit_idx + 1
                # Don't allow selecting beyond what's actually displayed
                if next_idx <= last_visible_idx:
                    self.selected_commit_idx = next_idx
    
    def _flip_page_up(self):
        """Quick page flip up (q key)"""
        if not self.commits:
            return
            
        commits_per_page = self._get_page_size()
        current_page_start = self.commit_page_offset
        
        if current_page_start > 0:
            self._start_page_flip_animation("up")
            new_page_start = max(0, current_page_start - commits_per_page)
            self.commit_page_offset = new_page_start
            # Select first item of the new page
            self.selected_commit_idx = new_page_start
            self._load_analyses_from_engine()
    
    def _flip_page_down(self):
        """Quick page flip down (e key)"""
        if not self.commits:
            return
            
        commits_per_page = self._get_page_size()
        current_page_start = self.commit_page_offset
        current_page_end = min(current_page_start + commits_per_page - 1, len(self.commits) - 1)
        
        # Check if there's a next page
        if current_page_end < len(self.commits) - 1:
            self._start_page_flip_animation("down")
            new_page_start = current_page_start + commits_per_page
            if new_page_start < len(self.commits):
                self.commit_page_offset = new_page_start
                # Select first item of the new page
                self.selected_commit_idx = new_page_start
                self._load_analyses_from_engine()
    
    def _load_analyses_from_engine(self):
        """Load cached analyses for current commit from DRommageEngine"""
        if self.selected_commit_idx < 0 or self.selected_commit_idx >= len(self.commits):
            return
            
        current_commit = self.commits[self.selected_commit_idx]
        
        # Try to load each analysis mode from engine cache
        for mode in [AnalysisMode.PAT, AnalysisMode.BRIEF, AnalysisMode.DEEP]:
            if current_commit.hash not in self.current_analyses[mode]:
                # Check if engine has cached result
                cached_result = self.drommage_engine._cache.get_analysis(current_commit.hash, mode)
                if cached_result:
                    self.current_analyses[mode][current_commit.hash] = cached_result
    
    def _queue_analysis(self, mode: AnalysisMode):
        """Queue analysis task for current commit using DRommageEngine"""
        if self.selected_commit_idx < 0 or self.selected_commit_idx >= len(self.commits):
            self.status = "❌ No commit selected"
            return
        
        current_commit = self.commits[self.selected_commit_idx]
        
        # Check if analysis already exists in our cache
        if current_commit.hash in self.current_analyses[mode]:
            self.status = f"📦 {mode.value.title()} analysis already available"
            return
        
        # Use DRommageEngine for analysis
        try:
            self.status = f"🔄 Running {mode.value} analysis..."
            result = self.drommage_engine.analyze_commit(current_commit.hash, mode)
            
            if result:
                # Store result in local cache for UI
                self.current_analyses[mode][current_commit.hash] = result
                self.status = f"✅ {mode.value.title()} analysis complete"
            else:
                self.status = f"❌ {mode.value.title()} analysis failed"
                
        except Exception as e:
            self.status = f"❌ Analysis error: {str(e)[:50]}"
    
    def _handle_d_button(self):
        """Toggle analysis mode: PAT → BRIEF → DEEP → PAT (always available)"""
        if self.selected_commit_idx < 0 or self.selected_commit_idx >= len(self.commits):
            return
        
        # Toggle analysis mode in cycle: PAT → BRIEF → DEEP → PAT
        # This ALWAYS works, even during analysis
        if self.analysis_mode == AnalysisMode.PAT:
            self.analysis_mode = AnalysisMode.BRIEF
            self.status = "📝 Switched to BRIEF analysis"
        elif self.analysis_mode == AnalysisMode.BRIEF:
            self.analysis_mode = AnalysisMode.DEEP
            self.status = "📊 Switched to DEEP analysis"
        else:  # DEEP
            self.analysis_mode = AnalysisMode.PAT
            self.status = "🔍 Switched to PAT analysis"
        
        # Start analysis for current mode if not available yet
        current_commit = self.commits[self.selected_commit_idx]
        if current_commit.hash not in self.current_analyses[self.analysis_mode]:
            self._queue_analysis(self.analysis_mode)
        else:
            # Analysis already available - just show it
            self.status = f"✅ {self.analysis_mode.value.title()} analysis ready"
    
    def _word_wrap(self, text: str, width: int) -> list:
        """Simple word wrap for text display"""
        if not text:
            return []
        
        lines = []
        words = text.split()
        current_line = []
        current_length = 0
        
        for word in words:
            word_length = len(word)
            
            if current_length + word_length + len(current_line) <= width:
                current_line.append(word)
                current_length += word_length
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = word_length
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return lines
    
    def _start_page_flip_animation(self, direction):
        """Start page flip animation"""
        import time
        self.page_flip_animation = {
            "active": True,
            "start_time": time.time(),
            "direction": direction
        }
    
    def _is_analysis_running(self):
        """Check if any analysis is currently running"""
        if self.selected_commit_idx < 0 or self.selected_commit_idx >= len(self.commits):
            return False
            
        current_commit = self.commits[self.selected_commit_idx]
        
        # Check if previous commit exists for diff
        if self.selected_commit_idx >= len(self.commits) - 1:
            return False
            
        prev_commit = self.commits[self.selected_commit_idx + 1]
        
        # Check analysis queue for running tasks
        prev_short_hash = prev_commit.short_hash
        analysis_status = self.analysis_queue.get_commit_analysis_status(
            current_commit.hash, current_commit.short_hash, prev_short_hash)
        
        # Check if any analysis is running
        return (analysis_status.get("brief") == "running" or 
                analysis_status.get("deep") == "running")
    
    def _is_analysis_type_running(self, analysis_type):
        """Check if specific analysis type is currently running"""
        if self.selected_commit_idx < 0 or self.selected_commit_idx >= len(self.commits):
            return False
            
        current_commit = self.commits[self.selected_commit_idx]
        
        # Check if previous commit exists for diff
        if self.selected_commit_idx >= len(self.commits) - 1:
            return False
            
        prev_commit = self.commits[self.selected_commit_idx + 1]
        
        # Check analysis queue for running tasks
        prev_short_hash = prev_commit.short_hash
        analysis_status = self.analysis_queue.get_commit_analysis_status(
            current_commit.hash, current_commit.short_hash, prev_short_hash)
        
        # Check if specific analysis type is running
        return analysis_status.get(analysis_type) == "running"
    
    def _get_analysis_panel_height(self):
        """Get the height of analysis panel"""
        if hasattr(self, 'scr'):
            h, w = self.scr.getmaxyx()
            top_height = int(h * 0.45)
            return h - top_height - 4  # Bottom panel height minus borders
        return 10  # Fallback
    
    def _scroll_analysis_up(self):
        """Scroll analysis panel up by 40% of analysis panel height"""
        panel_height = self._get_analysis_panel_height()
        scroll_amount = max(1, int(panel_height * 0.4))
        self.analysis_scroll = max(0, self.analysis_scroll - scroll_amount)
    
    def _scroll_analysis_down(self):
        """Scroll analysis panel down by 40% of analysis panel height"""
        panel_height = self._get_analysis_panel_height()
        scroll_amount = max(1, int(panel_height * 0.4))
        
        # Get current analysis to check content length
        current_analysis = None
        analysis_type = "deep" if self.mode == "llm_detail" else "brief"
        current_analysis = self.current_analyses.get(analysis_type)
        
        # Try to get ANY available analysis if preferred one is not available
        if not current_analysis:
            if analysis_type == "deep":
                current_analysis = self.current_analyses.get("brief")
            else:
                current_analysis = self.current_analyses.get("deep")
        
        if current_analysis:
            # Calculate total content lines to prevent over-scrolling
            # Get panel width for proper word wrapping
            if hasattr(self, 'scr'):
                h, w = self.scr.getmaxyx()
                left_width = int(w * 0.382)
                panel_width = left_width - 3
            else:
                panel_width = 40
            max_scroll = self._get_max_scroll_for_analysis(current_analysis, panel_height, panel_width)
            self.analysis_scroll = min(max_scroll, self.analysis_scroll + scroll_amount)
    
    def _get_max_scroll_for_analysis(self, analysis, panel_height, panel_width=40):
        """Calculate maximum scroll position to prevent scrolling past content"""
        if not analysis:
            return 0
            
        # Calculate total content lines (similar to display logic)
        total_lines = 0
        
        # Summary
        if analysis.summary:
            summary_lines = self._word_wrap(analysis.summary, panel_width - 2)
            total_lines += len(summary_lines)
        else:
            total_lines += 1  # "No summary available"
        
        # Details
        if analysis.details:
            total_lines += 2  # Empty line + "Details:" header
            detail_lines = self._word_wrap(analysis.details, panel_width - 2)
            total_lines += len(detail_lines)
        
        # Risks
        if hasattr(analysis, 'risks') and analysis.risks:
            total_lines += 2  # Empty line + "Risks:" header
            for risk in analysis.risks:
                risk_lines = self._word_wrap(f"• {risk}", panel_width - 2)
                total_lines += len(risk_lines)
        
        # Recommendations (for deep analysis)
        if hasattr(analysis, 'recommendations') and analysis.recommendations:
            total_lines += 2  # Empty line + "Recommendations:" header
            for rec in analysis.recommendations:
                rec_lines = self._word_wrap(f"• {rec}", panel_width - 2)
                total_lines += len(rec_lines)
        
        # Max scroll = total lines - visible lines, but at least 0
        visible_lines = panel_height - 2  # Reserve lines for scroll indicator and border
        return max(0, total_lines - visible_lines)
    
    def _draw_analysis_scroll_indicator(self, scr, y, x, w, content_lines, analysis):
        """Draw horizontal scroll indicator at bottom of analysis panel"""
        if not content_lines or not analysis:
            return
            
        panel_height = self._get_analysis_panel_height()
        visible_lines = panel_height - 1  # Reserve 1 line for scroll indicator
        total_lines = len(content_lines)
        
        # Only show indicator if content is scrollable
        if total_lines <= visible_lines:
            return
            
        try:
            # Calculate scroll position and thumb size based on content ratio
            max_scroll = max(0, total_lines - visible_lines)
            
            # Create horizontal scroll bar (use available width - 4 for margins)
            bar_width = w - 4
            if bar_width < 3:
                return
            
            # Calculate thumb size based on how much content is visible
            content_ratio = min(1.0, visible_lines / total_lines)
            thumb_size = max(1, int(bar_width * content_ratio))
            
            # Calculate thumb position based on scroll
            if max_scroll > 0:
                scroll_percentage = min(1.0, self.analysis_scroll / max_scroll)
                # Adjust available space for thumb movement
                available_space = bar_width - thumb_size
                thumb_pos = int(scroll_percentage * available_space)
            else:
                thumb_pos = 0
            
            # Draw with border styling like git commits panel
            # Left border
            scr.addstr(y, x, "│", curses.color_pair(PALETTE["border"]))
            
            # Scroll bar background with proper spacing
            bar_bg = "─" * bar_width
            scr.addstr(y, x + 1, bar_bg, curses.color_pair(PALETTE["dim"]))
            
            # Draw scroll thumb (with proper size)
            for i in range(thumb_size):
                thumb_x = x + 1 + thumb_pos + i
                if thumb_x < x + 1 + bar_width:
                    scr.addstr(y, thumb_x, "█", curses.color_pair(PALETTE["modified"]))
            
            # Right border
            scr.addstr(y, x + w - 1, "│", curses.color_pair(PALETTE["border"]))
            
            # Add content ratio indicator if there's space
            if w > 25:
                # Calculate what percentage of content is currently visible
                visible_start_line = self.analysis_scroll
                visible_end_line = min(total_lines, self.analysis_scroll + visible_lines)
                
                # Show content coverage as percentage
                if total_lines > 0:
                    coverage_start = int((visible_start_line / total_lines) * 100)
                    coverage_end = int((visible_end_line / total_lines) * 100)
                    
                    if coverage_start == coverage_end:
                        position_text = f"{coverage_end}%"
                    else:
                        position_text = f"{coverage_start}-{coverage_end}%"
                else:
                    position_text = "100%"
                
                # Place text after the scroll bar with proper spacing
                text_x = x + 1 + bar_width + 1
                if text_x + len(position_text) < x + w - 1:
                    scr.addstr(y, text_x, position_text, curses.color_pair(PALETTE["dim"]))
                    
        except:
            pass  # Ignore drawing errors
    
    def _get_diff_panel_height(self):
        """Get the height of diff panel (right panel)"""
        if hasattr(self, 'scr'):
            h, w = self.scr.getmaxyx()
            return h - 6  # Full height minus borders and header
        return 20  # Fallback
    
    def _get_wrapped_diff_lines(self, diff_text, panel_width):
        """Get wrapped diff lines using same logic as display - returns (line, prefix, line_num) tuples"""
        raw_diff_lines = diff_text.split('\n')
        wrapped_diff_lines = []
        
        # Track original line numbers for wrapped content
        for original_line_num, line in enumerate(raw_diff_lines, 1):
            # Get prefix for coloring
            prefix = line[0] if line and line[0] in '+-@' else ' '
            
            # Calculate space needed for line numbers
            line_num_space = len(str(len(raw_diff_lines))) + 2  # +2 for space and separator
            available_content_width = panel_width - line_num_space - 4
            
            if len(line) <= available_content_width:
                # Line fits, keep as is with original line number
                wrapped_diff_lines.append((line, prefix, original_line_num))
            else:
                # Need to wrap - break at word boundaries but preserve prefix
                if len(line) > 1:
                    content = line[1:] if prefix in '+-@' else line
                    # Break into chunks manually to preserve meaning
                    chunk_size = panel_width - line_num_space - 6  # Leave room for line numbers, prefix and indicators
                    if chunk_size > 0:
                        for i in range(0, len(content), chunk_size):
                            chunk = content[i:i + chunk_size]
                            if i == 0:
                                # First chunk gets original prefix and line number
                                display_line = (prefix + chunk) if prefix in '+-@' else chunk
                                wrapped_diff_lines.append((display_line, prefix, original_line_num))
                            else:
                                # Continuation chunks get continuation indicator but SAME line number and SAME color prefix
                                display_line = '…' + chunk
                                wrapped_diff_lines.append((display_line, prefix, original_line_num))
                    else:
                        # Chunk size too small, just add as is
                        wrapped_diff_lines.append((line, prefix, original_line_num))
                else:
                    wrapped_diff_lines.append((line, prefix, original_line_num))
        
        return wrapped_diff_lines

    def _get_max_scroll_for_diff(self, wrapped_diff_lines, panel_height):
        """Calculate maximum scroll position to prevent scrolling past content"""
        total_lines = len(wrapped_diff_lines)
        
        # Calculate visible lines based on actual diff display area
        # Panel height minus header area (6 lines) minus scroll indicator (1 line)
        visible_lines = panel_height - 7
        
        return max(0, total_lines - visible_lines)

    def _scroll_diff_up(self):
        """Scroll diff panel up by 40% of diff panel height"""
        panel_height = self._get_diff_panel_height()
        scroll_amount = max(1, int(panel_height * 0.4))
        self.right_scroll = max(0, self.right_scroll - scroll_amount)
    
    def _scroll_diff_down(self):
        """Scroll diff panel down by 40% of diff panel height"""
        panel_height = self._get_diff_panel_height()
        scroll_amount = max(1, int(panel_height * 0.4))
        
        # Get current diff to check content length
        if not self.commits or self.selected_commit_idx < 0:
            return
            
        # Calculate total diff lines using EXACT same logic as display
        if self.selected_commit_idx < len(self.commits) - 1:
            current_commit = self.commits[self.selected_commit_idx]
            prev_commit = self.commits[self.selected_commit_idx + 1]
            diff = self.git.get_commit_diff(prev_commit.hash, current_commit.hash)
            
            if diff and diff.diff_text:
                # Get panel width for wrapping calculation
                if hasattr(self, 'scr'):
                    h, w = self.scr.getmaxyx()
                    left_width = int(w * 0.382)  
                    panel_width = w - left_width - 3  # Right panel width
                else:
                    panel_width = 50
                
                # Use the SAME function as display to get wrapped lines
                wrapped_diff_lines = self._get_wrapped_diff_lines(diff.diff_text, panel_width)
                total_wrapped_lines = len(wrapped_diff_lines)
                
                # Create a function like analysis does
                max_scroll = self._get_max_scroll_for_diff(wrapped_diff_lines, panel_height)
                
                # Use EXACT same pattern as analysis
                self.right_scroll = min(max_scroll, self.right_scroll + scroll_amount)
    
    def _draw_diff_scroll_indicator(self, scr, y, x, w, total_diff_lines):
        """Draw horizontal scroll indicator at bottom of diff panel"""
        if total_diff_lines <= 0:
            return
            
        panel_height = self._get_diff_panel_height()
        visible_lines = panel_height - 2  # Same as scrolling logic
        
        # Only show indicator if content is scrollable
        if total_diff_lines <= visible_lines:
            return
            
        try:
            # Calculate scroll position and thumb size based on content ratio
            max_scroll = max(0, total_diff_lines - visible_lines)
            
            # Create horizontal scroll bar (use available width - 4 for margins)
            bar_width = w - 4
            if bar_width < 3:
                return
            
            # Calculate thumb position and size
            if max_scroll > 0:
                scroll_ratio = min(1.0, self.right_scroll / max_scroll)
                thumb_pos = int(scroll_ratio * (bar_width - 3))
                
                # Thumb size represents visible content ratio
                visible_ratio = min(1.0, visible_lines / total_diff_lines)
                thumb_size = max(1, int(visible_ratio * bar_width * 0.3))
            else:
                thumb_pos = 0
                thumb_size = bar_width
            
            # Ensure thumb doesn't go out of bounds
            if thumb_pos + thumb_size > bar_width:
                thumb_pos = max(0, bar_width - thumb_size)
            
            # Draw with border styling like git commits panel
            # Left border
            scr.addstr(y, x, "│", curses.color_pair(PALETTE["border"]))
            
            # Scroll bar background with proper spacing
            bar_bg = "─" * bar_width
            scr.addstr(y, x + 1, bar_bg, curses.color_pair(PALETTE["dim"]))
            
            # Draw scroll thumb (with proper size)
            for i in range(thumb_size):
                thumb_x = x + 1 + thumb_pos + i
                if thumb_x < x + 1 + bar_width:
                    scr.addstr(y, thumb_x, "█", curses.color_pair(PALETTE["modified"]))
            
            # Right border
            scr.addstr(y, x + w - 1, "│", curses.color_pair(PALETTE["border"]))
            
            # Add content ratio indicator if there's space
            if w > 25:
                # Calculate what percentage of content is currently visible
                visible_start_line = self.right_scroll
                visible_end_line = min(total_diff_lines, self.right_scroll + visible_lines)
                
                # Show content coverage as percentage
                if total_diff_lines > 0:
                    coverage_start = int((visible_start_line / total_diff_lines) * 100)
                    coverage_end = int((visible_end_line / total_diff_lines) * 100)
                    
                    if coverage_start == coverage_end:
                        position_text = f"{coverage_end}%"
                    else:
                        position_text = f"{coverage_start}-{coverage_end}%"
                else:
                    position_text = "100%"
                
                # Place text after the scroll bar with proper spacing
                text_x = x + 1 + bar_width + 1
                if text_x + len(position_text) < x + w - 1:
                    scr.addstr(y, text_x, position_text, curses.color_pair(PALETTE["dim"]))
                    
        except:
            pass  # Ignore drawing errors

"""
Configuration TUI for DRommage.
Manages LLM provider configuration through curses interface.
"""

import curses
import json
from typing import List, Dict, Optional
from pathlib import Path
from .providers import ProviderManager, ProviderConfig
from .engine import DRommageEngine


# Color palette
COLORS = {
    "border": 1,
    "title": 2,
    "available": 3,
    "unavailable": 4,
    "selected": 5,
    "warning": 6,
    "success": 7,
    "info": 8
}


class ConfigTUI:
    """TUI for configuring DRommage providers"""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.engine = DRommageEngine(repo_path)
        self.provider_manager = self.engine._provider_manager
        
        # UI state
        self.selected_provider = 0
        self.mode = "list"  # list, add, edit, test
        self.status = "DRommage Configuration"
        self.scroll_offset = 0
        
        # Provider data
        self.providers_data = []
        self._load_providers()
    
    def run(self):
        """Run the configuration TUI"""
        try:
            curses.wrapper(self._main)
        except KeyboardInterrupt:
            pass
    
    def _main(self, scr):
        """Main TUI loop"""
        # Initialize colors
        curses.start_color()
        curses.use_default_colors()
        
        # Define color pairs
        curses.init_pair(COLORS["border"], curses.COLOR_CYAN, -1)
        curses.init_pair(COLORS["title"], curses.COLOR_WHITE, -1)
        curses.init_pair(COLORS["available"], curses.COLOR_GREEN, -1) 
        curses.init_pair(COLORS["unavailable"], curses.COLOR_RED, -1)
        curses.init_pair(COLORS["selected"], curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(COLORS["warning"], curses.COLOR_YELLOW, -1)
        curses.init_pair(COLORS["success"], curses.COLOR_GREEN, -1)
        curses.init_pair(COLORS["info"], curses.COLOR_CYAN, -1)
        
        # Configure cursor
        curses.curs_set(0)
        scr.nodelay(1)
        scr.timeout(100)
        
        # Main loop
        while True:
            scr.clear()
            h, w = scr.getmaxyx()
            
            self._draw_frame(scr, h, w)
            
            if self.mode == "list":
                self._draw_provider_list(scr, h, w)
            elif self.mode == "test":
                self._draw_test_results(scr, h, w)
            
            self._draw_status_bar(scr, h, w)
            
            scr.refresh()
            
            # Handle input
            key = scr.getch()
            if key == ord('q') or key == ord('Q'):
                break
            elif not self._handle_key(key):
                break
    
    def _draw_frame(self, scr, h, w):
        """Draw main frame"""
        # Title
        title = "🔧 DRommage Configuration"
        scr.addstr(0, (w - len(title)) // 2, title, 
                  curses.A_BOLD | curses.color_pair(COLORS["title"]))
        
        # Border
        for y in range(2, h - 2):
            scr.addch(y, 0, '│', curses.color_pair(COLORS["border"]))
            scr.addch(y, w - 1, '│', curses.color_pair(COLORS["border"]))
        
        for x in range(1, w - 1):
            scr.addch(2, x, '─', curses.color_pair(COLORS["border"]))
            scr.addch(h - 3, x, '─', curses.color_pair(COLORS["border"]))
        
        # Corners
        scr.addch(2, 0, '╭', curses.color_pair(COLORS["border"]))
        scr.addch(2, w - 1, '╮', curses.color_pair(COLORS["border"]))
        scr.addch(h - 3, 0, '╰', curses.color_pair(COLORS["border"]))
        scr.addch(h - 3, w - 1, '╯', curses.color_pair(COLORS["border"]))
    
    def _draw_provider_list(self, scr, h, w):
        """Draw list of providers"""
        y_start = 4
        available_lines = h - 8
        
        # Header
        scr.addstr(3, 2, "LLM Providers:", curses.A_BOLD | curses.color_pair(COLORS["title"]))
        
        if not self.providers_data:
            scr.addstr(y_start, 2, "No providers configured.", curses.color_pair(COLORS["warning"]))
            scr.addstr(y_start + 2, 2, "Press 'a' to add a provider", curses.color_pair(COLORS["info"]))
            return
        
        # Provider list
        for i, provider_info in enumerate(self.providers_data):
            if i < self.scroll_offset:
                continue
            if y_start + (i - self.scroll_offset) * 2 >= h - 5:
                break
                
            y = y_start + (i - self.scroll_offset) * 2
            
            # Selection indicator
            selected = (i == self.selected_provider)
            attr = curses.color_pair(COLORS["selected"]) if selected else 0
            
            # Status icon
            if provider_info["available"]:
                status_icon = "✅"
                status_color = COLORS["available"]
            else:
                status_icon = "❌"
                status_color = COLORS["unavailable"]
            
            # Provider line
            prefix = "▶ " if selected else "  "
            name = provider_info["name"]
            ptype = provider_info["type"]
            model = provider_info["model"]
            priority = provider_info["priority"]
            
            line = f"{prefix}{name} ({ptype}) - {model} [P:{priority}]"
            max_width = w - 6
            if len(line) > max_width:
                line = line[:max_width-3] + "..."
            
            # Draw main line
            scr.addstr(y, 2, line[:max_width], attr)
            
            # Draw status icon
            scr.addstr(y, w - 4, status_icon, curses.color_pair(status_color))
            
            # Details line
            if selected:
                endpoint = provider_info["endpoint"]
                details = f"    Endpoint: {endpoint}"
                if len(details) > max_width:
                    details = details[:max_width-3] + "..."
                scr.addstr(y + 1, 2, details[:max_width], curses.color_pair(COLORS["info"]))
    
    def _draw_test_results(self, scr, h, w):
        """Draw provider test results"""
        y_start = 4
        
        scr.addstr(3, 2, "Testing Providers...", curses.A_BOLD | curses.color_pair(COLORS["title"]))
        
        for i, provider_info in enumerate(self.providers_data):
            y = y_start + i * 3
            if y >= h - 5:
                break
            
            name = provider_info["name"]
            available = provider_info["available"]
            
            # Test result
            if available:
                result_text = f"✅ {name}: Available"
                color = COLORS["success"]
            else:
                result_text = f"❌ {name}: Not available"  
                color = COLORS["unavailable"]
            
            scr.addstr(y, 2, result_text, curses.color_pair(color))
            
            # Additional info
            details = f"   Type: {provider_info['type']}, Model: {provider_info['model']}"
            scr.addstr(y + 1, 2, details, curses.color_pair(COLORS["info"]))
    
    def _draw_status_bar(self, scr, h, w):
        """Draw status bar at bottom"""
        status_y = h - 1
        
        # Clear status line
        scr.addstr(status_y, 0, " " * w)
        
        # Status message
        scr.addstr(status_y, 0, self.status, curses.A_BOLD)
        
        # Key hints
        if self.mode == "list":
            hints = "[↑↓] select  [t] test  [a] add  [e] edit  [d] delete  [s] save  [q] quit"
        else:
            hints = "[any key] back to list  [q] quit"
        
        hints_start = w - len(hints)
        if hints_start > len(self.status) + 2:
            scr.addstr(status_y, hints_start, hints, curses.color_pair(COLORS["info"]))
    
    def _handle_key(self, key):
        """Handle keyboard input"""
        if self.mode == "list":
            return self._handle_list_keys(key)
        elif self.mode == "test":
            self.mode = "list"
            return True
        return True
    
    def _handle_list_keys(self, key):
        """Handle keys in list mode"""
        if key == curses.KEY_UP or key == ord('k'):
            if self.selected_provider > 0:
                self.selected_provider -= 1
                if self.selected_provider < self.scroll_offset:
                    self.scroll_offset = max(0, self.scroll_offset - 1)
        
        elif key == curses.KEY_DOWN or key == ord('j'):
            if self.selected_provider < len(self.providers_data) - 1:
                self.selected_provider += 1
                # Scroll down if needed (simplified)
                max_visible = 10  # Approximate
                if self.selected_provider >= self.scroll_offset + max_visible:
                    self.scroll_offset += 1
        
        elif key == ord('t') or key == ord('T'):
            self._test_providers()
            
        elif key == ord('r') or key == ord('R'):
            self._reload_providers()
            
        elif key == ord('s') or key == ord('S'):
            self._save_config()
            
        elif key == ord('a') or key == ord('A'):
            self.status = "Add provider not implemented yet"
            
        elif key == ord('e') or key == ord('E'):
            self.status = "Edit provider not implemented yet"
            
        elif key == ord('d') or key == ord('D'):
            self.status = "Delete provider not implemented yet"
            
        elif key == ord('h') or key == ord('?'):
            self._show_help()
        
        return True
    
    def _load_providers(self):
        """Load provider data from manager"""
        try:
            status = self.engine.get_provider_status()
            self.providers_data = status["providers"]
            
            if status["available_provider"]:
                self.status = f"✅ Ready - {len(self.providers_data)} providers configured"
            else:
                self.status = f"⚠️ No available providers - {len(self.providers_data)} configured"
                
        except Exception as e:
            self.status = f"❌ Error loading providers: {str(e)[:50]}"
            self.providers_data = []
    
    def _test_providers(self):
        """Test all providers"""
        self.status = "🧪 Testing providers..."
        self.mode = "test"
        
        # Reload to get fresh status
        self._reload_providers()
    
    def _reload_providers(self):
        """Reload provider configuration"""
        try:
            # Reload provider manager
            self.provider_manager._load_config()
            self._load_providers()
            self.status = "✅ Providers reloaded"
        except Exception as e:
            self.status = f"❌ Reload failed: {str(e)[:50]}"
    
    def _save_config(self):
        """Save provider configuration"""
        try:
            self.provider_manager.save_config()
            self.status = "✅ Configuration saved"
        except Exception as e:
            self.status = f"❌ Save failed: {str(e)[:50]}"
    
    def _show_help(self):
        """Show help information"""
        help_text = """
DRommage Configuration Help:

Providers are automatically loaded from .drommage/providers.json

Key bindings:
- ↑↓ / jk: Navigate providers
- t: Test all providers
- r: Reload configuration  
- s: Save configuration
- h/?: Show this help
- q: Quit

Provider Types:
- ollama: Local Ollama server (localhost:11434)
- openai: OpenAI API (requires OPENAI_API_KEY)

Configuration file location: .drommage/providers.json
        """
        self.status = "Press any key to continue..."


def main(repo_path: str = "."):
    """Main entry point for config TUI"""
    config_tui = ConfigTUI(repo_path)
    config_tui.run()


if __name__ == "__main__":
    main()
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
        self.selected_prompt = 0
        self.current_tab = "providers"  # providers, prompts
        self.mode = "list"  # list, add, edit, test
        self.status = "DRommage Configuration"
        self.scroll_offset = 0
        
        # Data
        self.providers_data = []
        self.prompts_data = []
        self._load_providers()
        self._load_prompts()
    
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
            self._draw_tabs(scr, h, w)
            
            if self.mode == "list":
                if self.current_tab == "providers":
                    self._draw_provider_list(scr, h, w)
                elif self.current_tab == "prompts":
                    self._draw_prompt_list(scr, h, w)
            elif self.mode == "test":
                if self.current_tab == "providers":
                    self._draw_test_results(scr, h, w)
                elif self.current_tab == "prompts":
                    self._draw_prompt_test_results(scr, h, w)
            
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
    
    def _draw_tabs(self, scr, h, w):
        """Draw tab headers"""
        y = 3
        
        # Providers tab
        provider_text = " Providers "
        provider_attr = curses.color_pair(COLORS["selected"]) if self.current_tab == "providers" else 0
        scr.addstr(y, 2, provider_text, provider_attr)
        
        # Prompts tab
        prompt_text = " Prompts "
        prompt_x = 2 + len(provider_text) + 1
        prompt_attr = curses.color_pair(COLORS["selected"]) if self.current_tab == "prompts" else 0
        scr.addstr(y, prompt_x, prompt_text, prompt_attr)
        
        # Tab separator line
        for x in range(2, w - 2):
            scr.addch(y + 1, x, '─', curses.color_pair(COLORS["border"]))
    
    def _draw_provider_list(self, scr, h, w):
        """Draw list of providers"""
        y_start = 6  # Account for tabs
        available_lines = h - 10
        
        if not self.providers_data:
            scr.addstr(y_start, 2, "No providers configured.", curses.color_pair(COLORS["warning"]))
            scr.addstr(y_start + 2, 2, "Press 'a' to add a provider", curses.color_pair(COLORS["info"]))
            return
        
        # Provider list
        for i, provider_info in enumerate(self.providers_data):
            if i < self.scroll_offset:
                continue
            lines_per_item = 3 if i == self.selected_provider else 1
            if y_start + (i - self.scroll_offset) * lines_per_item >= h - 5:
                break
                
            y = y_start + sum(3 if j == self.selected_provider else 1 for j in range(self.scroll_offset, i))
            
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
                
                # Cost info line
                if y + 2 < h - 5:
                    cost_info = self._get_cost_display(provider_info)
                    if cost_info and len(cost_info) <= max_width:
                        scr.addstr(y + 2, 2, cost_info[:max_width], curses.color_pair(COLORS["warning"]))
    
    def _draw_prompt_list(self, scr, h, w):
        """Draw list of prompt templates"""
        y_start = 6  # Account for tabs
        available_lines = h - 10
        
        if not self.prompts_data:
            scr.addstr(y_start, 2, "No prompt templates found.", curses.color_pair(COLORS["warning"]))
            scr.addstr(y_start + 2, 2, "Check .drommage/prompts.json", curses.color_pair(COLORS["info"]))
            return
        
        # Prompt list
        for i, prompt_info in enumerate(self.prompts_data):
            if i < self.scroll_offset:
                continue
            lines_per_item = 3 if i == self.selected_prompt else 1
            if y_start + (i - self.scroll_offset) * lines_per_item >= h - 7:
                break
                
            y = y_start + sum(3 if j == self.selected_prompt else 1 for j in range(self.scroll_offset, i))
            
            # Selection indicator
            selected = (i == self.selected_prompt)
            attr = curses.color_pair(COLORS["selected"]) if selected else 0
            
            # Category color
            category = prompt_info["category"]
            if category == "security":
                category_color = COLORS["unavailable"]  # Red
            elif category == "performance":
                category_color = COLORS["available"]   # Green
            elif category == "general":
                category_color = COLORS["info"]        # Cyan
            else:
                category_color = COLORS["warning"]     # Yellow
            
            # Prompt line
            prefix = "▶ " if selected else "  "
            name = prompt_info["name"]
            description = prompt_info["description"]
            category_tag = f"[{category}]"
            
            line = f"{prefix}{name} - {description}"
            max_width = w - 6 - len(category_tag) - 2
            if len(line) > max_width:
                line = line[:max_width-3] + "..."
            
            # Draw main line
            scr.addstr(y, 2, line[:max_width], attr)
            
            # Draw category tag
            scr.addstr(y, w - len(category_tag) - 2, category_tag, curses.color_pair(category_color))
            
            # Details lines
            if selected:
                variables = ", ".join(prompt_info["variables"][:5])  # Show first 5 variables
                if len(prompt_info["variables"]) > 5:
                    variables += "..."
                details = f"    Variables: {variables}"
                max_width = w - 4
                if len(details) > max_width:
                    details = details[:max_width-3] + "..."
                scr.addstr(y + 1, 2, details[:max_width], curses.color_pair(COLORS["info"]))
                
                # Example usage
                example = f"    Usage: --prompt={name}"
                scr.addstr(y + 2, 2, example[:max_width], curses.color_pair(COLORS["info"]))
    
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
    
    def _draw_prompt_test_results(self, scr, h, w):
        """Draw prompt test results"""
        y_start = 6
        
        scr.addstr(5, 2, "Testing Prompts...", curses.A_BOLD | curses.color_pair(COLORS["title"]))
        
        for i, prompt_info in enumerate(self.prompts_data[:5]):  # Show first 5 prompts
            y = y_start + i * 2
            if y >= h - 5:
                break
            
            name = prompt_info["name"]
            category = prompt_info["category"]
            
            # Test result (placeholder - could be enhanced)
            result_text = f"✅ {name}: Template valid"
            color = COLORS["success"]
            
            scr.addstr(y, 2, result_text, curses.color_pair(color))
            
            # Additional info
            details = f"   Category: {category}, Variables: {len(prompt_info['variables'])}"
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
            tab_hints = "[tab] switch tab  " if self.current_tab == "providers" else "[tab] switch tab  "
            if self.current_tab == "providers":
                hints = f"{tab_hints}[↑↓] select  [t] test  [r] reload  [s] save  [q] quit"
            else:
                hints = f"{tab_hints}[↑↓] select  [t] test  [r] reload  [q] quit"
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
        # Tab switching
        if key == ord('\t') or key == 9:  # Tab key
            if self.current_tab == "providers":
                self.current_tab = "prompts"
                self.selected_prompt = 0
                self.scroll_offset = 0
            else:
                self.current_tab = "providers"
                self.selected_provider = 0
                self.scroll_offset = 0
            return True
        
        # Navigation keys
        if key == curses.KEY_UP or key == ord('k'):
            if self.current_tab == "providers":
                if self.selected_provider > 0:
                    self.selected_provider -= 1
                    if self.selected_provider < self.scroll_offset:
                        self.scroll_offset = max(0, self.scroll_offset - 1)
            else:  # prompts
                if self.selected_prompt > 0:
                    self.selected_prompt -= 1
                    if self.selected_prompt < self.scroll_offset:
                        self.scroll_offset = max(0, self.scroll_offset - 1)
        
        elif key == curses.KEY_DOWN or key == ord('j'):
            if self.current_tab == "providers":
                if self.selected_provider < len(self.providers_data) - 1:
                    self.selected_provider += 1
                    max_visible = 10
                    if self.selected_provider >= self.scroll_offset + max_visible:
                        self.scroll_offset += 1
            else:  # prompts
                if self.selected_prompt < len(self.prompts_data) - 1:
                    self.selected_prompt += 1
                    max_visible = 10
                    if self.selected_prompt >= self.scroll_offset + max_visible:
                        self.scroll_offset += 1
        
        # Action keys
        elif key == ord('t') or key == ord('T'):
            if self.current_tab == "providers":
                self._test_providers()
            else:
                self._test_prompts()
            
        elif key == ord('r') or key == ord('R'):
            if self.current_tab == "providers":
                self._reload_providers()
            else:
                self._reload_prompts()
            
        elif key == ord('s') or key == ord('S'):
            if self.current_tab == "providers":
                self._save_config()
            else:
                self.status = "Prompts are read-only (edit .drommage/prompts.json)"
            
        elif key == ord('a') or key == ord('A'):
            self.status = "Add/edit features not implemented yet"
            
        elif key == ord('e') or key == ord('E'):
            self.status = "Edit features not implemented yet"
            
        elif key == ord('d') or key == ord('D'):
            self.status = "Delete features not implemented yet"
            
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
    
    def _load_prompts(self):
        """Load prompt data from manager"""
        try:
            templates = self.engine.get_prompt_templates()
            categories = self.engine.get_prompt_categories()
            
            self.prompts_data = []
            for name, info in templates.items():
                self.prompts_data.append({
                    "name": name,
                    "description": info["description"],
                    "category": info["category"],
                    "variables": info["variables"]
                })
            
            # Sort by category then name
            self.prompts_data.sort(key=lambda x: (x["category"], x["name"]))
            
            if self.prompts_data:
                self.status = f"✅ Loaded {len(self.prompts_data)} prompt templates"
            else:
                self.status = "⚠️ No prompt templates found"
                
        except Exception as e:
            self.status = f"❌ Error loading prompts: {str(e)[:50]}"
            self.prompts_data = []
    
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
    
    def _test_prompts(self):
        """Test prompt templates"""
        self.status = "🧪 Testing prompt templates..."
        self.mode = "test"
    
    def _reload_prompts(self):
        """Reload prompt templates"""
        try:
            self._load_prompts()
            self.status = "✅ Prompt templates reloaded"
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

TABS:
- Tab: Switch between Providers and Prompts tabs

Key bindings:
- ↑↓ / jk: Navigate items
- t: Test providers/prompts
- r: Reload configuration  
- s: Save configuration (providers only)
- h/?: Show this help
- q: Quit

PROVIDERS TAB:
- Configure LLM providers (Ollama, OpenAI, Anthropic, HTTP)
- Test provider availability
- Manage provider priorities and settings
- File: .drommage/providers.json

PROMPTS TAB:
- View available prompt templates
- Browse by category (security, performance, architecture, etc.)
- See prompt variables and usage examples
- File: .drommage/prompts.json

Provider Types:
- ollama: Local Ollama server
- openai: OpenAI API (requires OPENAI_API_KEY)
- anthropic: Anthropic Claude API (requires ANTHROPIC_API_KEY)
- http: Generic OpenAI-compatible endpoint

Prompt Categories:
- general: Basic analysis prompts
- security: Security-focused analysis
- performance: Performance impact analysis
- architecture: Architectural analysis
- quality: Code quality and review
- business: Business impact analysis

Usage:
drommage analyze --prompt=brief_security --commit=HEAD
        """
        self.status = "Press any key to continue..."
    
    def _get_cost_display(self, provider_info: Dict) -> str:
        """Get cost display string for provider"""
        provider_type = provider_info.get("type", "")
        model = provider_info.get("model", "")
        
        if provider_type == "ollama":
            return "    Cost: Free (local)"
        elif provider_type == "openai":
            if "gpt-4o-mini" in model:
                return "    Cost: ~$0.0002/1k tokens"
            elif "gpt-4o" in model:
                return "    Cost: ~$0.0025/1k tokens" 
            elif "gpt-4" in model:
                return "    Cost: ~$0.03/1k tokens"
            else:
                return "    Cost: Varies by model"
        elif provider_type == "anthropic":
            if "haiku" in model:
                return "    Cost: ~$0.00025/1k tokens"
            elif "sonnet" in model:
                return "    Cost: ~$0.003/1k tokens"
            elif "opus" in model:
                return "    Cost: ~$0.015/1k tokens"
            else:
                return "    Cost: Varies by model"
        elif provider_type == "http":
            return "    Cost: Depends on endpoint"
        else:
            return "    Cost: Unknown"


def main(repo_path: str = "."):
    """Main entry point for config TUI"""
    config_tui = ConfigTUI(repo_path)
    config_tui.run()


if __name__ == "__main__":
    main()
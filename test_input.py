#!/usr/bin/env python3
"""
Test keyboard input handling for DRommage TUI
"""

import curses
import time

def test_input(stdscr):
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(1)   # Non-blocking input
    stdscr.timeout(100) # 100ms timeout
    
    # Initialize colors
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
    
    # Clear screen
    stdscr.clear()
    
    # Instructions
    stdscr.addstr(0, 0, "🧪 DRommage Input Test", curses.A_BOLD | curses.color_pair(1))
    stdscr.addstr(2, 0, "Test these keys:", curses.A_BOLD)
    stdscr.addstr(3, 0, "- ↑↓ : Navigate (should show KEY_UP/KEY_DOWN)")
    stdscr.addstr(4, 0, "- D   : Deep analysis (should show 68)")
    stdscr.addstr(5, 0, "- H/L : Horizontal scroll (should show 72/76)")
    stdscr.addstr(6, 0, "- Q   : Quit (should show 81)")
    stdscr.addstr(8, 0, "Last key pressed:", curses.A_BOLD)
    stdscr.addstr(10, 0, "Status:", curses.A_BOLD)
    
    key_count = 0
    start_time = time.time()
    
    while True:
        try:
            ch = stdscr.getch()
            
            if ch != -1:  # Key was pressed
                key_count += 1
                
                # Clear previous output
                for y in range(8, 15):
                    stdscr.move(y, 20)
                    stdscr.clrtoeol()
                
                # Show key info
                stdscr.addstr(8, 20, f"Code: {ch}", curses.color_pair(2))
                
                if ch == ord('Q') or ch == ord('q'):
                    stdscr.addstr(9, 20, "QUIT - Exiting...", curses.color_pair(3))
                    stdscr.refresh()
                    time.sleep(1)
                    break
                elif ch == ord('D'):
                    stdscr.addstr(9, 20, "DEEP ANALYSIS key detected ✓", curses.color_pair(1))
                elif ch == ord('H'):
                    stdscr.addstr(9, 20, "SCROLL LEFT key detected ✓", curses.color_pair(1))
                elif ch == ord('L'):
                    stdscr.addstr(9, 20, "SCROLL RIGHT key detected ✓", curses.color_pair(1))
                elif ch == curses.KEY_UP:
                    stdscr.addstr(9, 20, "UP ARROW key detected ✓", curses.color_pair(1))
                elif ch == curses.KEY_DOWN:
                    stdscr.addstr(9, 20, "DOWN ARROW key detected ✓", curses.color_pair(1))
                else:
                    # Try to show character if printable
                    try:
                        char = chr(ch) if 32 <= ch <= 126 else "?"
                        stdscr.addstr(9, 20, f"Character: '{char}'", curses.color_pair(2))
                    except:
                        stdscr.addstr(9, 20, "Special key (non-printable)", curses.color_pair(2))
            
            # Update status
            elapsed = time.time() - start_time
            stdscr.addstr(10, 20, f"Running {elapsed:.1f}s, {key_count} keys pressed")
            
            stdscr.refresh()
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            stdscr.addstr(12, 0, f"Error: {str(e)[:50]}", curses.color_pair(3))
            stdscr.refresh()

def main():
    print("🚀 Starting keyboard input test...")
    print("   This will test if DRommage keys work in your terminal")
    print("   Press any key to continue, Ctrl+C to cancel")
    
    try:
        input()
        curses.wrapper(test_input)
        print("\n✅ Input test completed!")
        print("   If keys were detected properly, DRommage should work fine.")
        print("   If some keys didn't work, try running DRommage in:")
        print("   - Terminal.app")
        print("   - iTerm2") 
        print("   - Standard terminal (not Claude Code)")
        
    except KeyboardInterrupt:
        print("\n❌ Test cancelled")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    main()
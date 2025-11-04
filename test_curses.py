#!/usr/bin/env python3
import curses
import time

def test_curses(scr):
    scr.addstr(0, 0, "Testing curses...")
    scr.refresh()
    time.sleep(2)
    return "OK"

if __name__ == "__main__":
    try:
        result = curses.wrapper(test_curses)
        print(f"Curses test: {result}")
    except Exception as e:
        print(f"Curses failed: {e}")
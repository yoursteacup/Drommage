import curses

class DocTUIView:
    def __init__(self, engine, history):
        self.engine = engine
        self.history = history
        self.current_index = len(history) - 1

    def run(self):
        curses.wrapper(self._main)

    def _main(self, scr):
        curses.curs_set(0)
        scr.nodelay(False)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_RED, -1)
        curses.init_pair(3, curses.COLOR_CYAN, -1)
        curses.init_pair(4, curses.COLOR_YELLOW, -1)

        while True:
            scr.clear()
            h, w = scr.getmaxyx()
            left_w = w // 2

            # История
            scr.attron(curses.color_pair(3))
            scr.addstr(0, 2, "History")
            scr.attroff(curses.color_pair(3))
            for i, item in enumerate(self.history):
                mark = "→" if i == self.current_index else " "
                scr.addstr(2 + i, 2, f"{mark} {item['version']} {item['date']} - {item['title']}")

            # Описание изменений
            scr.attron(curses.color_pair(4))
            scr.addstr(h // 2, 2, "Diff Summary")
            scr.attroff(curses.color_pair(4))
            if self.current_index > 0:
                prev = self.history[self.current_index - 1]['version']
                curr = self.history[self.current_index]['version']
                summary = self.engine.get_diff_summary(prev, curr)
                scr.addstr(h // 2 + 2, 2, f"{prev} → {curr}: {summary}")

            # Документ
            doc = self.engine.get_document(self.history[self.current_index]['version'])
            for i, line in enumerate(doc[:h - 2]):
                scr.addstr(i, left_w + 2, line[:left_w - 4])

            scr.refresh()
            key = scr.getch()
            if key in (ord('q'), 27):  # ESC или q — выход
                break
            elif key in (curses.KEY_UP, ord('k')) and self.current_index > 0:
                self.current_index -= 1
            elif key in (curses.KEY_DOWN, ord('j')) and self.current_index < len(self.history) - 1:
                self.current_index += 1

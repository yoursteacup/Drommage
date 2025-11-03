#!/usr/bin/env python3
import curses
import difflib
from pathlib import Path

DOCS_DIR = Path("docs")

HISTORY = [
    {"version": "v0.1", "date": "2024-04-12", "desc": "Initial draft", "changes": []},
    {
        "version": "v0.3",
        "date": "2024-05-02",
        "desc": "Added API examples",
        "changes": ["+ Добавлены примеры API", "+ Расширен раздел 'Обзор'"],
    },
    {
        "version": "v0.6",
        "date": "2024-06-10",
        "desc": "Refactoring and cleanup",
        "changes": ["- Убраны дубли", "+ Упрощена структура модулей"],
    },
    {
        "version": "v1.0",
        "date": "2024-08-01",
        "desc": "Stable release",
        "changes": [
            "+ Добавлен раздел 'Архитектура'",
            "+ Улучшено описание цели проекта",
            "- Удалён устаревший пример API",
        ],
    },
    {
        "version": "v1.2",
        "date": "2024-09-14",
        "desc": "Minor revisions",
        "changes": ["+ Добавлена таблица маршрутов", "+ Обновлены комментарии в коде"],
    },
]


class DRommageViewer:
    def __init__(self):
        self.index = len(HISTORY) - 1
        self.max_index = len(HISTORY) - 1

    def run(self):
        curses.wrapper(self._main)

    def _main(self, scr):
        curses.curs_set(0)
        scr.nodelay(False)
        scr.timeout(-1)

        # Инициализация цветов
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_GREEN, -1)   # добавления
            curses.init_pair(2, curses.COLOR_RED, -1)     # удаления
            curses.init_pair(3, curses.COLOR_CYAN, -1)    # заголовки
            curses.init_pair(4, curses.COLOR_YELLOW, -1)  # подсказки

        while True:
            scr.erase()
            h, w = scr.getmaxyx()

            left_w = int(w * 0.4)
            right_w = w - left_w - 1
            mid_y = h // 2

            # Разделительные линии
            try:
                scr.vline(0, left_w, curses.ACS_VLINE, h)
                scr.hline(mid_y, 0, curses.ACS_HLINE, left_w)
            except curses.error:
                # fallback если ACS_* не поддерживается
                for y in range(h):
                    scr.addch(y, left_w, "|")
                for x in range(left_w):
                    scr.addch(mid_y, x, "-")

            # Заголовок и подсказки
            scr.addstr(0, 2, " DRommage Data Service — История версий ", curses.color_pair(3))
            scr.addstr(h - 1, 2, "↑↓ — перемещение   q — выход", curses.color_pair(4))

            # Окна
            self._draw_history(scr, 2, 1, left_w - 2, mid_y - 3)
            self._draw_changes(scr, mid_y + 1, 1, left_w - 2, h - mid_y - 3)
            self._draw_document(scr, 1, left_w + 2, right_w - 2, h - 3)

            scr.refresh()
            key = scr.getch()

            if key == ord("q"):
                break
            elif key in (curses.KEY_UP, ord("k")):
                self.index = max(0, self.index - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                self.index = min(self.max_index, self.index + 1)

    # Верхнее левое окно — история
    def _draw_history(self, scr, y, x, w, h):
        for i, item in enumerate(HISTORY[:h]):
            prefix = "→ " if i == self.index else "  "
            line = f"{prefix}{item['version']} [{item['date']}] {item['desc']}"
            color = curses.color_pair(3) if i == self.index else curses.A_NORMAL
            scr.addnstr(y + i, x, line, w, color)

    # Нижнее левое окно — изменения
    def _draw_changes(self, scr, y, x, w, h):
        item = HISTORY[self.index]
        scr.addnstr(y, x, f"Изменения {item['version']}:", w, curses.color_pair(4))
        for i, ch in enumerate(item["changes"][:h - 2]):
            color = curses.color_pair(1) if ch.startswith("+") else curses.color_pair(2)
            scr.addnstr(y + 1 + i, x + 2, ch, w - 2, color)

    # Правая часть — документ
    def _draw_document(self, scr, y, x, w, h):
        cur_doc = DOCS_DIR / f"{HISTORY[self.index]['version']}.txt"
        prev_doc = DOCS_DIR / f"{HISTORY[self.index - 1]['version']}.txt" if self.index > 0 else None

        if not cur_doc.exists():
            scr.addstr(y, x, f"[Нет файла {cur_doc.name}]", curses.color_pair(2))
            return

        cur_lines = cur_doc.read_text(encoding="utf-8").splitlines()
        prev_lines = prev_doc.read_text(encoding="utf-8").splitlines() if prev_doc and prev_doc.exists() else []

        diff = difflib.ndiff(prev_lines, cur_lines)
        visible_lines = [line for line in diff if not line.startswith("? ")]
        for i, line in enumerate(visible_lines[:h]):
            text = line[2:]
            if line.startswith("+ "):
                scr.addnstr(y + i, x, text, w, curses.color_pair(1))
            elif line.startswith("- "):
                scr.addnstr(y + i, x, text, w, curses.color_pair(2))
            else:
                scr.addnstr(y + i, x, text, w)


if __name__ == "__main__":
    viewer = DRommageViewer()
    viewer.run()


import curses
from datetime import datetime

# ────────────────────────────── MOCK DATA ──────────────────────────────
MOCK_VERSIONS = [
    {
        "id": "v0.1",
        "date": "2024-04-12",
        "title": "Initial draft",
        "changes": [
            "Создан базовый документ описания сервиса.",
            "Добавлены разделы: 'Обзор' и 'Архитектура'.",
            "Формулировки черновые, без примеров API."
        ],
        "diff": """+ Раздел 'Обзор': базовое описание цели проекта
+ Раздел 'Архитектура': схема взаимодействия модулей
- Нет примеров использования API
"""
    },
    {
        "id": "v0.3",
        "date": "2024-05-02",
        "title": "Added API examples",
        "changes": [
            "Добавлены примеры запросов/ответов API.",
            "Введён раздел 'Аутентификация'.",
            "Обновлён раздел 'Архитектура'."
        ],
        "diff": """+ Раздел 'Аутентификация': OAuth2 flow
+ Примеры API: /data/upload, /data/status
~ Обновлён текст раздела 'Архитектура'
"""
    },
    {
        "id": "v0.6",
        "date": "2024-06-10",
        "title": "Refactoring and cleanup",
        "changes": [
            "Удалён дублирующийся раздел 'Форматы данных'.",
            "Сокращены примеры API.",
            "Добавлены комментарии по безопасности."
        ],
        "diff": """- Раздел 'Форматы данных' (дублирование)
~ Упрощены примеры /data/upload
+ Добавлены примечания о безопасном хранении токенов
"""
    },
    {
        "id": "v1.0",
        "date": "2024-08-01",
        "title": "Stable release",
        "changes": [
            "Всё приведено к единообразному стилю.",
            "Добавлен changelog и оглавление.",
            "Документ опубликован в общий репозиторий."
        ],
        "diff": """+ Добавлен раздел 'Changelog'
+ Единый стиль Markdown
~ Исправлены орфографические ошибки
"""
    },
]

# ────────────────────────────── PALETTE ──────────────────────────────
PALETTE = {
    "title": 1,
    "added": 2,
    "removed": 3,
    "modified": 4,
    "highlight": 5,
}

# ────────────────────────────── TUI VIEWER ──────────────────────────────
class VersionViewer:
    def __init__(self, versions):
        self.versions = versions
        self.selected_index = 0

    def run(self):
        curses.wrapper(self._main)

    def _main(self, scr):
        curses.curs_set(0)
        scr.nodelay(False)
        scr.keypad(True)

        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(PALETTE["title"], curses.COLOR_CYAN, -1)
            curses.init_pair(PALETTE["added"], curses.COLOR_GREEN, -1)
            curses.init_pair(PALETTE["removed"], curses.COLOR_RED, -1)
            curses.init_pair(PALETTE["modified"], curses.COLOR_YELLOW, -1)
            curses.init_pair(PALETTE["highlight"], curses.COLOR_BLACK, curses.COLOR_WHITE)

        while True:
            scr.clear()
            self._draw(scr)
            scr.refresh()
            key = scr.getch()

            if key in (ord("q"), 27):  # ESC or q
                break
            elif key == curses.KEY_DOWN:
                self.selected_index = min(len(self.versions) - 1, self.selected_index + 1)
            elif key == curses.KEY_UP:
                self.selected_index = max(0, self.selected_index - 1)

    # ────────────────────────────── DRAW ──────────────────────────────
    def _draw(self, scr):
        h, w = scr.getmaxyx()
        mid = w // 2
        title = "DRommage Data Service — История версий"
        scr.addstr(0, max(0, (w - len(title)) // 2), title, curses.color_pair(PALETTE["title"]) | curses.A_BOLD)
        scr.hline(1, 0, "-", w)

        # Левая колонка — список версий
        scr.addstr(2, 2, "История:", curses.A_BOLD)
        for i, v in enumerate(self.versions):
            y = 4 + i
            label = f"{v['id']}  [{v['date']}]  {v['title']}"
            if i == self.selected_index:
                scr.addstr(y, 4, label[:mid - 6], curses.color_pair(PALETTE["highlight"]) | curses.A_BOLD)
            else:
                scr.addstr(y, 4, label[:mid - 6])

        # Разделитель
        for y in range(2, h - 1):
            scr.addch(y, mid, ord("|"))

        # Правая колонка — diff
        selected = self.versions[self.selected_index]
        scr.addstr(2, mid + 3, f"Δ {selected['id']} — {selected['title']}", curses.A_BOLD)
        scr.addstr(3, mid + 3, f"Дата: {selected['date']}")
        scr.addstr(5, mid + 3, "Изменения:", curses.A_UNDERLINE)

        for i, line in enumerate(selected["diff"].splitlines()):
            color = 0
            if line.startswith("+"):
                color = curses.color_pair(PALETTE["added"])
            elif line.startswith("-"):
                color = curses.color_pair(PALETTE["removed"])
            elif line.startswith("~"):
                color = curses.color_pair(PALETTE["modified"])
            scr.addstr(7 + i, mid + 5, line[:mid - 8], color)

        scr.hline(h - 2, 0, "-", w)
        scr.addstr(h - 1, 2, "↑↓ — перемещение   q — выход", curses.A_DIM)


# ────────────────────────────── MAIN ──────────────────────────────
if __name__ == "__main__":
    viewer = VersionViewer(MOCK_VERSIONS)
    viewer.run()


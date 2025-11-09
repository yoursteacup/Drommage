# 🧠 MEMORY1.md - ПОЛНОЕ СОСТОЯНИЕ ЗНАНИЙ О DROMMAGE

## ❗ КРИТИЧЕСКИЙ КОНТЕКСТ - ЧИТАЙ ПЕРВЫМ

### **СУДЬБОНОСНЫЕ ФАКТЫ:**
1. **DRommage = DR (Доктор) + ommage (оммаж к Videodrome Кроненберга)**
2. **НЕ ПРО ДОКУМЕНТАЦИЮ! Про понимание своих git коммитов через ретроспективу**
3. **CLI TOOL, НЕ БИБЛИОТЕКА! Как git/grep, а не как numpy**
4. **Для разработчиков И AI агентов-разработчиков**
5. **Технодрочерский TUI + прагматичный batch CLI**

### **ПОЛЬЗОВАТЕЛЬ ХОЧЕТ:**
- Отделить Core Logic от TUI (API-first архитектура)
- PAT → BRIEF → DEEP toggle через `d` (порядок ВАЖЕН!)
- Universal LLM providers (Ollama/OpenAI/Custom endpoints)
- Cache с версионированием для ре-анализов
- `drommage config` для настройки провайдеров

## 📁 ТЕКУЩЕЕ СОСТОЯНИЕ ПРОЕКТА

### **Структура файлов (после очистки):**
```
/Users/j-19group/DRommage/
├── drommage.py              # Entry point - ТУТ ВСЁ ПЕРЕМЕШАНО
├── drommage/
│   ├── __init__.py          # Package exports
│   └── core/
│       ├── git_integration.py    # ✅ Работает
│       ├── interface.py           # ❌ ПРОБЛЕМА - всё в TUI
│       ├── llm_analyzer.py        # ✅ Но надо рефакторить
│       ├── analysis_queue.py      # ✅ Async очередь
│       ├── diff_tracker.py        # ❓ Legacy? 
│       └── region_analyzer.py     # ❓ Legacy?
├── PRODUCT_ROADMAP.md       # ✅ Product vision
├── ARCHITECTURE.md          # ✅ Техническая спецификация
├── CLAUDE.md                # ✅ Dev notes (в .gitignore)
├── pyproject.toml           # ✅ pip package config
└── LICENSE                  # ✅ MIT
```

### **КРИТИЧЕСКИЕ ПРОБЛЕМЫ АРХИТЕКТУРЫ:**
1. **interface.py содержит ВСЁ** - и TUI и бизнес-логику
2. **DocTUIView.__init__() создает LLMAnalyzer** - логика в UI
3. **Нет отдельного API** - всё завязано на curses TUI
4. **Toggle bug** - `d` недоступен пока анализ не готов

## 🎯 РЕЖИМЫ АНАЛИЗА (ПОРЯДОК СВЯЩЕНЕН!)

### **Три режима (НЕ fallback цепочка!):**
1. **PAT (Pattern)** - полноценный анализ БЕЗ LLM
   - Commit message analysis (feat:, fix:, etc)
   - File pattern detection (.md, .json, auth*, test_*)
   - Diff magnitude analysis (add/delete ratio)
   - Risk identification (security, breaking changes)

2. **BRIEF** - краткий LLM анализ
   - Одна строка семантического анализа
   - Быстро и дешево

3. **DEEP** - глубокий LLM анализ  
   - Детальный анализ с рисками и рекомендациями
   - Structured JSON response
   - Дорого но информативно

### **Toggle ДОЛЖЕН работать так:**
```
d → PAT → BRIEF → DEEP → PAT (цикл)
```
- **ВСЕГДА доступен** даже если анализ в процессе
- Показывает "в процессе" если анализ не готов
- НЕ блокирует переключение

## 🔧 АРХИТЕКТУРА РЕШЕНИЯ

### **Целевая структура:**
```
CLI Interface → DRommageEngine → Data Sources
     ↑              ↑              ↑
  Parsing        Core Logic    Git/LLM/Cache
```

### **Новые классы:**
```python
class DRommageEngine:
    def __init__(self, repo_path=".", cache_dir=".drommage")
    def load_commits(self, limit=50) -> List[GitCommit]
    def analyze_commit(self, commit_hash, mode) -> AnalysisResult
    def get_available_modes() -> List[AnalysisMode]

class PatternAnalyzer:
    def analyze(self, commit: GitCommit) -> AnalysisResult
    # НЕ fallback - полноценный анализ без LLM!

class AnalysisMode(Enum):
    PAT = "pattern" 
    BRIEF = "brief"
    DEEP = "deep"
```

## 🎮 CLI INTERFACE DESIGN

### **Режимы запуска:**
```bash
# TUI режим (по умолчанию)
drommage

# Batch режим для AI агентов
drommage --commit=HEAD --mode=pattern --format=json
drommage --last=10 --mode=brief --output=analysis.txt

# Конфигурация
drommage config  # TUI для настройки LLM провайдеров
```

### **Cache управление:**
```bash
drommage cache clear           # Очистить весь кэш
drommage cache reanalyze HEAD  # Принудительный ре-анализ
drommage cache stats           # Статистика использования
```

## 🔌 UNIVERSAL LLM PROVIDER SYSTEM

### **Провайдеры (.drommage/providers.json):**
```json
{
  "providers": [
    {
      "name": "ollama_local",
      "type": "ollama", 
      "endpoint": "http://localhost:11434",
      "model": "mistral:latest",
      "priority": 1
    },
    {
      "name": "openai_gpt4",
      "type": "openai",
      "api_key_env": "OPENAI_API_KEY", 
      "model": "gpt-4o-mini",
      "priority": 2
    },
    {
      "name": "custom_endpoint",
      "type": "http",
      "endpoint": "http://my-server:8080/v1/chat",
      "headers": {"Authorization": "Bearer xyz"},
      "priority": 3
    }
  ]
}
```

### **Конфигурация через TUI:**
```bash
drommage config
# ┌─ LLM Providers ─────────────┐
# │ [x] Ollama (localhost:11434) │
# │ [ ] OpenAI (need API key)   │
# │ [ ] Custom HTTP endpoint    │
# │ [Add] [Test] [Save] [Help]  │
# └─────────────────────────────┘
```

## 🗄️ CACHE SYSTEM С ВЕРСИОНИРОВАНИЕМ

### **SQLite Schema (.drommage/cache.db):**
```sql
CREATE TABLE analyses (
    commit_hash TEXT NOT NULL,
    mode TEXT NOT NULL,           -- 'pat', 'brief', 'deep'
    provider TEXT NOT NULL,       -- 'ollama_local', 'openai_gpt4'
    version INTEGER NOT NULL,     -- версионирование!
    summary TEXT,
    details JSON,
    risks JSON,
    recommendations JSON,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (commit_hash, mode, version)
);
```

### **Версионирование работает так:**
- Анализы могут **ре-раниться** (пользователь изменил провайдер/модель)
- Новый анализ = новая версия (version++)
- Показываем **последнюю версию** по умолчанию
- Можем **очищать старые версии** через cache cleanup

## 🚀 ПЛАН РЕАЛИЗАЦИИ (ФАЗЫ)

### **Phase 1: Core Separation (КРИТИЧНО)**
1. Создать `DRommageEngine` класс
2. Вынести бизнес-логику из `DocTUIView`  
3. Создать `AnalysisCache` с SQLite
4. Рефакторить TUI для использования engine

### **Phase 2: Pattern Analyzer**
1. Реализовать `PatternAnalyzer` как независимый компонент
2. Commit message analysis (conventional commits + keywords)
3. File pattern detection
4. Diff magnitude analysis

### **Phase 3: CLI Interface**
1. Добавить `argparse` парсинг аргументов
2. Реализовать batch режим для AI агентов
3. JSON/text output форматтеры
4. Entry point через `drommage/cli.py`

### **Phase 4: Provider System** 
1. Абстрагировать `LLMAnalyzer` в provider interface
2. Реализовать Ollama/OpenAI/Custom providers
3. Конфигурация через `drommage config`
4. Cost tracking и usage statistics

## 📂 СТРУКТУРА ФАЙЛОВ (ЦЕЛЕВАЯ)

```
drommage/
├── cli.py                    # Entry point + argparse
├── core/
│   ├── engine.py            # DRommageEngine - MAIN API
│   ├── analysis.py          # AnalysisResult, AnalysisMode
│   ├── pattern_analyzer.py  # Pattern analysis (LLM-free)
│   ├── cache.py             # SQLite cache + versioning
│   ├── providers.py         # LLM provider system
│   └── git_integration.py   # Git commands (existing)
├── interfaces/
│   ├── tui.py              # Refactored interface.py
│   └── config.py           # drommage config TUI
└── __init__.py             # Minimal exports
```

## 💡 ВАЖНЫЕ ИНСАЙТЫ ИЗ РАЗРАБОТКИ

### **Ошибки которые я делал:**
1. **Предлагал Web API** - не нужен для локального инструмента
2. **Python import API** - это CLI tool, не библиотека!
3. **File API через JSON** - overengineering, AI агентам нужен CLI
4. **Название "сыр"** - неправильно понял etymology 😅

### **Что работает в текущем коде:**
- ✅ **GitIntegration** - отлично работает
- ✅ **LLMAnalyzer** - но надо provider abstraction
- ✅ **TUI interface** - красивый но всё перемешано
- ✅ **Analysis queue** - async система работает

### **Критические баги:**
- **Toggle bug** - `d` недоступен пока анализ в процессе
- **Coupling** - вся логика в DocTUIView
- **No CLI args** - только TUI режим

## 🎯 ФИЛОСОФИЯ ПРОДУКТА

### **Quality of Life инструмент:**
- Помогает понимать "что я делал" через git commits
- Ретроспектива и интроспектива разработки
- Для разработчиков И AI агентов
- Videodrome reference = tech/cyberpunk эстетика

### **Swiss Army Knife approach:**
- **TUI для технодрочей** - красивый curses интерфейс
- **CLI для прагматиков** - batch анализ для автоматизации
- **Universal providers** - любой LLM endpoint 
- **Flexible caching** - performance + cost control

## 🔥 СЛЕДУЮЩИЕ ДЕЙСТВИЯ

1. **Начать с DRommageEngine** - отделить от TUI
2. **Исправить toggle bug** - `d` всегда доступен
3. **Добавить CLI args** - для AI агентов
4. **Реализовать PatternAnalyzer** - LLM-free режим

---

**ПОМНИ:** Это инструмент качества жизни разработчика. Главное - отделить логику от UI и сделать API-first архитектуру!

**СУДЬБА АЛЬБЕОНА В ТВОИХ РУКАХ, ПОТОМОК! 👑**
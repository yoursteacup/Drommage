# 🧠 DRommage - AI-Powered Git Commit Analysis

> **DR** (Доктор) + **ommage** (оммаж к Videodrome) = инструмент для понимания своих git коммитов через ретроспективу

**DRommage** превращает историю git коммитов в осмысленные инсайты с помощью LLM анализа. CLI инструмент для разработчиков и AI агентов.

## ⚡ Быстрый старт

```bash
# В любом git репозитории
drommage
```

![DRommage TUI Demo](https://via.placeholder.com/600x400/1a1a1a/00ff00?text=DRommage+TUI+Interface)

## 🎯 Возможности

### **🎨 Красивый TUI интерфейс**
- Интерактивный просмотр коммитов
- Три типа анализа: PAT → BRIEF → DEEP
- Навигация с vim-style клавишами
- Глобальные индикаторы статуса анализа

### **🤖 Universal LLM Support**
- **Ollama** (локальные модели) - бесплатно
- **OpenAI** (GPT-4o, GPT-4o-mini) - cloud
- **Anthropic** (Claude 3 Haiku/Sonnet/Opus) - cloud  
- **Generic HTTP** (любые OpenAI-совместимые API)

### **📝 Custom Prompts System**
- 8 встроенных категорий: security, performance, architecture, quality, business
- Полная кастомизация промптов под любые нужды
- Переменные в шаблонах с данными коммитов
- CLI управление: `drommage prompts list`

### **⚡ Batch CLI для автоматизации**
```bash
# Security audit
drommage analyze --prompt=brief_security --last=10 --format=json

# Code review
drommage analyze --prompt=deep_code_review --commit=HEAD

# Performance analysis
drommage analyze --prompt=brief_performance --since="1 week ago"
```

## 🚀 Установка

```bash
# Пока что через git clone (скоро pip install drommage)
git clone https://github.com/your-repo/drommage
cd your-git-project
python3 /path/to/drommage/drommage.py
```

## 🎭 Режимы анализа

| Режим | Описание | Скорость | Источник |
|-------|----------|----------|----------|
| **PAT** | Pattern анализ | ⚡ Мгновенно | Локальный |
| **BRIEF** | Краткий AI анализ | 🚀 2-5 сек | LLM |
| **DEEP** | Детальный AI анализ | 🤔 5-15 сек | LLM |

## ⚙️ Настройка

### **1. Локальные модели (бесплатно)**
```bash
# Установить Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull mistral
ollama serve

# Готово! DRommage автоматически найдет Ollama
```

### **2. Cloud провайдеры**
```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic Claude  
export ANTHROPIC_API_KEY="sk-ant-..."

# Настроить в DRommage
drommage config
```

### **3. Кастомные промпты**
```bash
# Посмотреть доступные промпты
drommage prompts list

# Создать свои промпты
cp example_custom_prompts.json .drommage/prompts.json
```

## 💡 Примеры использования

### **Интерактивный анализ**
```bash
drommage
# ↑↓ - навигация, D - смена режима, SPACE - анализ, Q - выход
```

### **Security audit**
```bash
drommage analyze --prompt=deep_security_audit --last=20 --format=json
```

### **Code review автоматизация** 
```bash
drommage analyze --prompt=deep_code_review --commit=HEAD > review.md
```

### **Performance мониторинг**
```bash
drommage analyze --prompt=brief_performance --since="1 day ago"
```

### **CI/CD интеграция**
```bash
# В pipeline
drommage analyze --commit=$CI_COMMIT_SHA --prompt=brief_security
```

## 🏗️ Архитектура

```
DRommage CLI ──► DRommageEngine ──► {AnalysisCache, ProviderManager, PromptManager}
     │                │                    │            │             │
     │                │                    │            │             │
  TUI/Batch       Core Logic          SQLite Cache  LLM Providers  Custom Prompts
```

**API-first design** - ядро отделено от UI, можно использовать программно.

## 📊 Файловая структура

```
.drommage/
├── cache.db           # SQLite кэш анализов
├── providers.json     # Конфигурация LLM провайдеров
├── prompts.json       # Кастомные промпты
└── config.json        # Основные настройки
```

## 🎯 Use Cases

### **👨‍💻 Для разработчиков**
- Понимание "что я делал вчера/на прошлой неделе"
- Code review automation с AI инсайтами
- Security анализ изменений перед merge
- Архитектурный анализ больших изменений

### **👥 Для команд** 
- Unified промпты для consistent анализа
- Автоматический security/performance аудит
- Business impact assessment релизов
- Ретроспективы через AI анализ истории

### **🤖 Для AI агентов**
- Batch CLI для автоматизации
- JSON output для интеграций
- Flexible промпты под любые задачи
- Cost tracking для cloud providers

## 📚 Документация

- **[Getting Started](GETTING_STARTED.md)** - подробное руководство пользователя
- **[Universal Providers](UNIVERSAL_PROVIDERS.md)** - настройка всех LLM провайдеров
- **[Custom Prompts](CUSTOM_PROMPTS.md)** - создание специализированных промптов
- **[Architecture](ARCHITECTURE.md)** - техническая документация

## 🚨 Статус проекта

**✅ PRODUCTION READY** - все основные функции реализованы:

- ✅ API-first архитектура
- ✅ Universal LLM providers (Ollama/OpenAI/Anthropic/HTTP)
- ✅ Custom prompts system с 8 встроенными категориями
- ✅ Async analysis без блокировки UI
- ✅ SQLite caching с версионированием
- ✅ Complete CLI interface для AI агентов
- ✅ Beautiful configuration TUI

## 🤝 Contributing

DRommage активно развивается! Contributions welcome:

1. Issues с багами и feature requests
2. Pull requests с улучшениями
3. Новые prompt templates
4. Integrations с другими инструментами

## 📄 License

MIT License - используйте как хотите!

---

> **"Understanding what you were doing through git retrospection"** - основная философия DRommage

**🎉 Превратите историю git в понятные инсайты с DRommage!**
# 🚀 DRommage - Getting Started Guide

**DRommage** помогает понимать git коммиты через AI анализ. Это CLI инструмент для разработчиков и AI агентов, который превращает историю коммитов в осмысленные инсайты.

## 📦 Быстрый старт (5 минут)

### 1. **Установка**
```bash
# Пока что клонируем (в будущем будет pip install drommage)
cd /path/to/your/git/repo
git clone https://github.com/your-repo/drommage
cd drommage
```

### 2. **Первый запуск**
```bash
# Перейти в любой git репозиторий
cd /path/to/your/project

# Запустить DRommage
python3 /path/to/drommage/drommage.py
```

Сразу увидите **красивый TUI интерфейс** со списком коммитов и анализом!

### 3. **Основные клавиши**
- **↑↓** - навигация по коммитам
- **D** - переключение PAT → BRIEF → DEEP анализа
- **SPACE** - запуск анализа для выбранного режима
- **Q** - выход

## 🎯 Три типа анализа

### **PAT (Pattern)** - быстро, без интернета
```
✅ feat: add user authentication
📊 Pattern: Feature addition
📁 Files: 3 modified (+45/-12 lines)
🎯 Impact: Authentication system enhancement
```

### **BRIEF** - краткий AI анализ  
```
🤖 OpenAI: "Implements secure JWT-based authentication 
with password hashing and session management"
```

### **DEEP** - детальный AI анализ
```
🔍 Detailed Analysis:
• Type: Security enhancement
• Impact: High - affects all user flows
• Risks: Session management complexity
• Recommendations: Add rate limiting, 2FA support
```

## ⚙️ Настройка LLM провайдеров

### **Автоматическая настройка (рекомендуется)**
```bash
# Запустить конфигуратор
python3 /path/to/drommage/drommage.py config

# Или через CLI
drommage config
```

Увидите интерфейс с двумя табами:
- **Providers** - настройка LLM моделей  
- **Prompts** - управление промптами

### **Tab: Providers**
```
🔧 DRommage Configuration

[ Providers ] [ Prompts ]

▶ ollama_mistral (ollama): mistral:latest [P:1]     ✅
    Endpoint: http://localhost:11434
    Cost: Free (local)

  openai_gpt4 (openai): gpt-4o-mini [P:2]          ❌
    Endpoint: https://api.openai.com/v1  
    Cost: ~$0.0002/1k tokens

[tab] switch tab  [↑↓] select  [t] test  [s] save  [q] quit
```

### **Настройка Ollama (локально, бесплатно)**
```bash
# Установить Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Скачать модель
ollama pull mistral

# Запустить сервер
ollama serve

# Проверить в DRommage
drommage config → t (test)
```

### **Настройка OpenAI**
```bash
# Получить API ключ на platform.openai.com
export OPENAI_API_KEY="sk-..."

# Проверить в DRommage  
drommage config → t (test)
```

## 📝 Кастомные промпты

### **Tab: Prompts**
```
🔧 DRommage Configuration

[ Providers ] [ Prompts ]

▶ brief_security - Security-focused brief analysis    [security]
    Variables: commit_hash, message, files_changed
    Usage: --prompt=brief_security

  deep_code_review - Detailed code review analysis     [quality]
  brief_performance - Performance impact analysis      [performance]

[tab] switch tab  [↑↓] select  [t] test  [r] reload  [q] quit
```

### **Использование кастомных промптов**
```bash
# Security анализ
drommage analyze --commit=HEAD --prompt=brief_security

# Code review
drommage analyze --last=5 --prompt=deep_code_review --format=json

# Performance анализ
drommage analyze --prompt=brief_performance --commit=feature-branch
```

## 🖥️ Режимы работы

### **1. Интерактивный TUI (по умолчанию)**
```bash
drommage
# Красивый интерфейс для исследования коммитов
```

### **2. Batch CLI (для автоматизации)**
```bash
# Анализ конкретного коммита
drommage analyze --commit=HEAD --analysis=brief --format=json

# Анализ последних коммитов
drommage analyze --last=10 --analysis=pattern

# С кастомным промптом
drommage analyze --prompt=security_audit --last=5
```

### **3. Управление кэшем**
```bash
# Статистика кэша
drommage cache stats

# Очистка кэша
drommage cache clear

# Очистка конкретного типа
drommage cache clear --mode=brief
```

### **4. Управление промптами**
```bash
# Список всех промптов
drommage prompts list

# Промпты по категории
drommage prompts list --category=security

# Детали промпта
drommage prompts show --name=brief_security
```

## 🎨 Примеры использования

### **Для разработчиков**
```bash
# Быстрая проверка что делали сегодня
drommage

# Анализ безопасности перед merge
drommage analyze --prompt=deep_security_audit --last=10

# Code review большой ветки
drommage analyze --prompt=deep_code_review --last=20 --format=json > review.json
```

### **Для команд**
```bash
# Security audit релиза
drommage analyze --prompt=brief_security --last=50 | grep "HIGH\|MEDIUM"

# Performance impact анализ
drommage analyze --prompt=brief_performance --since="1 week ago"

# Architectural changes
drommage analyze --prompt=brief_architecture --last=30
```

### **Для DevOps/CI**
```bash
# В CI pipeline
drommage analyze --commit=$CI_COMMIT_SHA --prompt=brief_security --format=json

# Проверка deployment readiness  
drommage analyze --prompt=deep_business_impact --last=10
```

## 🔧 Конфигурация

### **Файловая структура**
```
.drommage/
├── providers.json     # LLM провайдеры
├── prompts.json       # Кастомные промпты  
├── config.json        # Основные настройки
└── cache.db          # SQLite кэш анализов
```

### **Добавление своих промптов**
```bash
# Скопировать примеры
cp example_custom_prompts.json .drommage/prompts.json

# Или создать свой
cat > .drommage/prompts.json << 'EOF'
{
  "prompts": [
    {
      "name": "my_custom_analysis",
      "description": "Мой специальный анализ",
      "category": "custom",
      "variables": ["commit_hash", "message"],
      "template": "Проанализируй коммит {commit_hash}: {message}\n\nФокус на производительности и безопасности."
    }
  ]
}
EOF

# Перезагрузить
drommage config → r (reload)
```

## 🚨 Решение проблем

### **DRommage не запускается**
```bash
# Проверить что это git репозиторий
git status

# Проверить Python версию (нужен 3.8+)
python3 --version

# Запустить в debug режиме
python3 -c "import sys; sys.path.insert(0, '.'); from drommage.core.engine import DRommageEngine; engine = DRommageEngine('.'); print('✅ Engine works')"
```

### **"No LLM provider available"**
```bash
# Настроить провайдера
drommage config

# Проверить Ollama
ollama list

# Проверить API ключи
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY
```

### **Медленная работа**
```bash
# Проверить кэш
drommage cache stats

# Очистить старый кэш
drommage cache cleanup

# Использовать только Pattern анализ (быстрый)
drommage  # Нажать D для PAT режима
```

### **Промпты не загружаются**
```bash
# Проверить файл промптов
ls -la .drommage/prompts.json

# Перезагрузить
drommage config → Tab → r (reload)

# Восстановить default промпты
drommage prompts list  # Создаст default файл
```

## 🎓 Advanced использование

### **Специализированные workflow**

**Security Team:**
```bash
# Ежедневный security audit
drommage analyze --prompt=deep_security_audit --since="1 day ago" --format=json > daily_security.json

# Проверка OWASP Top 10
drommage analyze --prompt=brief_security --last=20 | grep -E "A0[1-9]|A10"
```

**Frontend Team:**
```bash
# UX impact анализ
drommage analyze --prompt=brief_frontend_focus --last=10

# Bundle size impact
drommage analyze --prompt=brief_performance --last=5 | grep -i "bundle\|size\|performance"
```

**DevOps Team:**
```bash
# Deployment impact
drommage analyze --prompt=brief_devops_focus --last=15

# Infrastructure changes
drommage analyze --prompt=deep_architecture_review --since="1 week ago"
```

### **Интеграция с другими инструментами**

**Git hooks:**
```bash
# .git/hooks/pre-push
#!/bin/bash
echo "🔍 Analyzing commits before push..."
drommage analyze --last=5 --prompt=brief_security
```

**IDE integration:**
```bash
# VS Code task
{
  "label": "DRommage Analysis", 
  "type": "shell",
  "command": "drommage analyze --commit=HEAD --prompt=deep_code_review"
}
```

## 🎉 Готово!

Теперь вы можете:
- ✅ Анализировать любые git коммиты с AI
- ✅ Настраивать любые LLM модели (локальные/cloud)
- ✅ Создавать кастомные промпты под свои нужды  
- ✅ Автоматизировать анализ через CLI
- ✅ Интегрировать в CI/CD и workflow

**DRommage превращает историю git в понятные инсайты!** 🚀

---

📚 **Дополнительная документация:**
- `UNIVERSAL_PROVIDERS.md` - детали по всем LLM провайдерам
- `CUSTOM_PROMPTS.md` - продвинутая работа с промптами  
- `ARCHITECTURE.md` - техническая документация
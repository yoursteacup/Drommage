# 🌐 Universal LLM Providers Guide

DRommage теперь поддерживает любые LLM модели через унифицированную систему провайдеров!

## 🚀 Поддерживаемые типы провайдеров

### 1. **Ollama (локальные модели)**
```json
{
  "name": "ollama_mistral",
  "type": "ollama",
  "endpoint": "http://localhost:11434",
  "model": "mistral:latest",
  "priority": 1,
  "enabled": true
}
```

### 2. **OpenAI API**
```json
{
  "name": "openai_gpt4",
  "type": "openai", 
  "endpoint": "https://api.openai.com/v1",
  "model": "gpt-4o-mini",
  "api_key_env": "OPENAI_API_KEY",
  "priority": 2,
  "enabled": false
}
```

### 3. **Anthropic Claude API**
```json
{
  "name": "anthropic_haiku",
  "type": "anthropic",
  "endpoint": "https://api.anthropic.com", 
  "model": "claude-3-haiku-20240307",
  "api_key_env": "ANTHROPIC_API_KEY",
  "priority": 3,
  "enabled": false
}
```

### 4. **Generic HTTP (любые OpenAI-совместимые endpoints)**
```json
{
  "name": "local_llama",
  "type": "http",
  "endpoint": "http://localhost:8080/v1",
  "model": "llama-3-8b",
  "priority": 4,
  "enabled": false,
  "headers": {
    "Authorization": "Bearer your-api-key"
  }
}
```

## 🔧 Настройка провайдеров

### Интерактивная настройка
```bash
drommage config
```

### Ручная настройка
Создайте/отредактируйте `.drommage/providers.json`:

```bash
cp example_providers.json .drommage/providers.json
```

## 🌟 Примеры популярных сервисов

### **Groq** (быстрые open-source модели)
```json
{
  "name": "groq_llama",
  "type": "http",
  "endpoint": "https://api.groq.com/openai/v1",
  "model": "llama3-8b-8192",
  "headers": {
    "Authorization": "Bearer your-groq-api-key"
  }
}
```

### **Together.ai** (множество open-source моделей)
```json
{
  "name": "together_mixtral",
  "type": "http", 
  "endpoint": "https://api.together.xyz/v1",
  "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
  "headers": {
    "Authorization": "Bearer your-together-api-key"
  }
}
```

### **LocalAI** (self-hosted)
```json
{
  "name": "localai_gpt",
  "type": "http",
  "endpoint": "http://localhost:8080/v1", 
  "model": "gpt-3.5-turbo"
}
```

### **Text Generation WebUI** (oobabooga)
```json
{
  "name": "text_gen_webui",
  "type": "http",
  "endpoint": "http://localhost:5000/v1",
  "model": "any-model-name"
}
```

### **LM Studio**
```json
{
  "name": "lm_studio",
  "type": "http",
  "endpoint": "http://localhost:1234/v1",
  "model": "local-model"
}
```

## 🔑 API ключи

Установите переменные окружения:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GROQ_API_KEY="gsk_..."
export TOGETHER_API_KEY="..."
```

## 💰 Cost Tracking

DRommage автоматически отслеживает стоимость:

- **Ollama**: Бесплатно (локальные модели)
- **OpenAI GPT-4o-mini**: ~$0.0002/1k tokens
- **Anthropic Haiku**: ~$0.00025/1k tokens 
- **HTTP endpoints**: Зависит от провайдера

## 🎯 Приоритеты провайдеров

Провайдеры выбираются по `priority` (меньше = выше приоритет):

1. **Ollama** (локальные, быстрые, бесплатные)
2. **Дешевые cloud модели** (GPT-4o-mini, Claude Haiku)
3. **Премиум модели** (GPT-4o, Claude Sonnet)

## ⚡ Быстрый старт

1. **Запустите Ollama** (если есть):
   ```bash
   ollama pull mistral
   ollama serve
   ```

2. **Настройте провайдеры**:
   ```bash
   drommage config
   ```

3. **Анализируйте коммиты**:
   ```bash
   drommage  # TUI режим
   drommage analyze --last=5 --analysis=brief  # CLI режим
   ```

## 🔬 Проверка статуса

```bash
# Показать доступные провайдеры
drommage cache stats

# Тестировать конфигурацию
drommage config
# Нажмите 't' для тестирования всех провайдеров
```

## 🏗️ Создание custom провайдера

Любой OpenAI-совместимый API работает через тип `"http"`:

```json
{
  "name": "my_custom_llm",
  "type": "http",
  "endpoint": "https://my-api.com/v1",
  "model": "custom-model-name",
  "headers": {
    "Authorization": "Bearer token",
    "X-Custom-Header": "value"
  },
  "timeout": 60
}
```

---

**🎉 Готово!** Теперь DRommage может использовать любые LLM модели для анализа ваших git коммитов.
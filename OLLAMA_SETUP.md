# Бесплатный локальный режим Ollama

В этом режиме фотографии и запросы рецептов обрабатываются локальной моделью.
OpenAI API-ключ и платные API-кредиты не требуются.

## 1. Установка Ollama

Скачайте Ollama для Windows с официальной страницы:

https://ollama.com/download/windows

Закройте и заново откройте PowerShell, затем проверьте установку:

```powershell
ollama --version
```

## 2. Загрузка модели

```powershell
ollama pull gemma3:4b
```

Модель занимает примерно 3,3 ГБ. Ollama обычно запускает локальный сервер
автоматически. Проверить его можно так:

```powershell
ollama list
```

## 3. Настройки бота

Существующий `.env` с `TELEGRAM_BOT_TOKEN` можно оставить. При желании добавьте:

```env
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b
```

`OPENAI_API_KEY` в локальном режиме не используется.

## 4. Запуск

Сначала остановите старую версию бота сочетанием `Ctrl+C`, затем выполните:

```powershell
.\.venv\Scripts\python.exe run_ollama.py
```

Если Ollama не запущен или модель отсутствует, бот теперь сообщает конкретную
команду для исправления вместо совета сделать более чёткую фотографию.

## Архитектура

```text
Telegram → bot → http://localhost:11434/api/chat → gemma3:4b
                    ↓ structured JSON
                 confirmation → database
```

OpenAI-реализация сохранена в `pantry_bot/ai.py` как альтернативный облачный
провайдер. Локальная реализация находится в `pantry_bot/ollama_ai.py`.

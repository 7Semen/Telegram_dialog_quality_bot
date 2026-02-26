# Telegram Dialog Quality Bot

## Описание проекта
Telegram Dialog Quality Bot — это сервис для автоматической оценки качества корпоративных сообщений в Telegram-чатах.

Бот анализирует переписку и определяет:

- тональность сообщения (позитивная / нейтральная / негативная),

- наличие проблем коммуникации (агрессия, токсичность, уход от темы, неясность формулировки).

Система предназначена для мониторинга качества деловой коммуникации.

## Архитектура
Проект реализован по модульной архитектуре:

- Модуль Telegram-интеграции (commands.py, app.py)

Обрабатывает команды администратора и сообщения чатов.

- Модуль анализа качества (analyzer.py)

Интеграция с Yandex Cloud Foundation Models API через OpenAI-совместимый endpoint.

- Модуль работы с базой данных (db.py, repo.py)

Сохранение сообщений, результатов анализа и формирование отчётов.

- Общий модуль конфигурации (config.py)

Управление токенами и настройками среды.

## Стек технологий
- Python 3.12

- aiogram (Telegram Bot API)

- PostgreSQL

- asyncpg

- Yandex Cloud LLM (Foundation Models API)

- requests

- dotenv

## Сценарий использования
1. Бот добавляется в корпоративный чат.

2. Администратор вызывает команду:

/analyze YYYY-MM-DD YYYY-MM-DD

3. Бот:

- получает сообщения за период,

- отправляет текст в Yandex GPT,

- сохраняет результаты анализа в БД,

- возвращает статистику.

4. Команда:

/issues YYYY-MM-DD YYYY-MM-DD

выводит список проблемных сообщений.

5. Команда:

/report YYYY-MM-DD YYYY-MM-DD

формирует сводный отчёт:

- количество проанализированных сообщений

- количество проблем

- типы выявленных нарушений

## Хранение данных

В базе данных используются следующие основные таблицы:

### messages
- message_id
- chat_id
- user_id
- message_text
- created_at

### analysis_results
- analysis_id
- message_id
- sentiment (positive / neutral / negative)
- detected_problem (ok / aggressive_tone / toxic / impolite / unclear / off_topic)
- analysis_date

## Метрики качества
Система оценивает:

1. Тональность:

- позитивная

- нейтральная

- негативная

2. Тип проблемы:

- агрессивный тон

- токсичность

- неясность формулировки

- уход от темы

- отсутствие проблемы

3. Количество проблемных сообщений за период

## Алгоритм определения времени ответа

Метрика времени ответа рассчитывается как разница между временем сообщения пользователя и следующим сообщением в чате от другого пользователя.

## Инициализация базы данных

```bash
psql -U postgres -d telegram_analysis_db -f sql/init.sql
```

## Запуск проекта
1. Клонирование репозитория
   
```git clone https://github.com/USERNAME/Telegram_dialog_quality_bot.git```

```cd Telegram_dialog_quality_bot```

2. Создание виртуального окружения
   
```python -m venv venv```

```source venv/bin/activate```

3. Скопируйте .env.example в .env

4. Установка зависимостей
   
```pip install -r requirements.txt```

5. Настройка переменных окружения

Создать файл .env на основе .env.example:

### Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=telegram_analysis_db
DB_USER=postgres
DB_PASSWORD=postgres

### Telegram
BOT_TOKEN=your_telegram_bot_token
ADMIN_IDS=123456789

### Yandex AI
YANDEX_API_KEY=your_yandex_api_key
YANDEX_FOLDER_ID=your_folder_id
YANDEX_MODEL=gpt://your_folder_id/qwen3-235b-a22b-fp8/latest

6. Запуск

```python -m quality_bot.app```

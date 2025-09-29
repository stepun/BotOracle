# AI Consultant Telegram Bot

Telegram-бот с подпиской и интеграцией GPT для персональных консультаций.

## Возможности

- 📨 **Ежедневные сообщения** — мотивирующие цитаты каждый день
- 💬 **Персональные вопросы** — ответы от GPT-консультанта
- 💳 **Подписка** — через Robokassa (неделя/месяц)
- 📊 **Аналитика** — статистика пользователей и доходов
- 🔧 **Админ-панель** — команды и веб-API

## Быстрый старт

### 1. Настройка окружения

```bash
# Клонировать проект
git clone git@NTMY:stepun/ai-consultant.git
cd ai-consultant

# Создать .env из шаблона
cp .env.example .env

# Отредактировать .env с вашими токенами
```

### 2. Локальная разработка

```bash
# Запустить окружение разработки
./scripts/local-setup.sh

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

### 3. Деплой на сервер

```bash
# Деплой на Pi4-2
./scripts/deploy.sh
```

## Настройка

### Обязательные параметры в .env:

```env
# Telegram
BOT_TOKEN=your_bot_token

# Robokassa
ROBO_LOGIN=your_login
ROBO_PASS1=your_password1
ROBO_PASS2=your_password2

# OpenAI
OPENAI_API_KEY=your_api_key

# Админы
ADMIN_IDS=123456789,987654321
```

### Настройка бота в BotFather:

1. Создать бота через @BotFather
2. Получить токен и добавить в .env
3. Настроить команды:

```
start - Запуск бота
```

### Настройка Robokassa:

1. Зарегистрировать магазин
2. Получить пароли
3. Настроить Result URL: `https://consultant.sh3.su/robokassa/result`
4. Success URL: `https://consultant.sh3.su/robokassa/success`
5. Fail URL: `https://consultant.sh3.su/robokassa/fail`

## Архитектура

```
app/
├── bot/           # Telegram bot логика
├── api/           # FastAPI endpoints
├── database/      # Модели и подключение к БД
├── utils/         # Утилиты (GPT, Robokassa)
└── main.py        # Точка входа

config/
├── init.sql       # Инициализация БД
└── nginx.conf     # Настройки Nginx

scripts/
├── deploy.sh      # Деплой на сервер
└── local-setup.sh # Локальная настройка
```

## Команды бота

### Пользовательские:
- `/start` — главное меню

### Административные:
- `/admin_today` — статистика за сегодня
- `/admin_range YYYY-MM-DD YYYY-MM-DD` — статистика за период
- `/admin_export YYYY-MM-DD YYYY-MM-DD` — выгрузка TSV
- `/admin_paid` — список подписчиков
- `/admin_blocked` — список заблокированных

## API

### Robokassa callbacks:
- `POST /robokassa/result` — обработка платежей
- `POST /robokassa/success` — успешная оплата
- `POST /robokassa/fail` — неудачная оплата

### Admin API:
- `GET /admin/stats` — статистика в JSON
- `GET /admin/users` — список пользователей
- `GET /admin/export` — экспорт данных
- `GET /health` — проверка здоровья сервиса

Авторизация: `Bearer <ADMIN_TOKEN>`

## База данных

### Основные таблицы:
- `users` — пользователи
- `subscriptions` — подписки
- `questions` — вопросы и ответы
- `daily_messages` — сообщения дня
- `events` — события для аналитики
- `fact_daily_metrics` — агрегированная статистика

## Мониторинг

### Логи:
```bash
# Все сервисы
docker-compose -f docker-compose.prod.yml logs -f

# Только приложение
docker-compose -f docker-compose.prod.yml logs -f app
```

### Метрики:
- Health check: `https://consultant.sh3.su/health`
- Admin stats: `https://consultant.sh3.su/admin/stats`

## Техподдержка

При проблемах проверьте:

1. **Бот не отвечает:**
   - Проверьте токен бота
   - Убедитесь, что webhook настроен правильно
   - Проверьте логи: `docker-compose logs app`

2. **Платежи не проходят:**
   - Проверьте настройки Robokassa
   - Убедитесь, что Result URL доступен
   - Проверьте пароли в .env

3. **SSL проблемы:**
   - Перевыпустить сертификат: `sudo certbot renew`
   - Перезапустить nginx: `docker-compose restart nginx`

## Разработка

### Структура проекта следует принципам:
- Разделение на модули (bot, api, database)
- Использование async/await
- Логирование всех операций
- Обработка ошибок

### Добавление нового функционала:
1. Создать модель в `database/models.py`
2. Добавить обработчик в `bot/handlers.py`
3. Создать API endpoint в `api/`
4. Обновить миграции БД

## Лицензия

Проект создан для заказчика. Все права защищены.
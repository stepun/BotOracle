# Claude Code Configuration

## Project Overview
Bot Oracle - двухперсонный Telegram бот с GPT-5 интеграцией и CRM системой.

## Development Commands

### Testing & Linting
```bash
# Проверка кода (если есть)
python -m pytest tests/

# Линтер (если настроен)
flake8 app/
```

### Database Management
```bash
# Применение миграции
ssh Pi4-2 "cd /home/lexun/ai-consultant && docker compose -f docker-compose.prod.yml exec db psql -U postgres -d telegram_bot -f /migrations/002_bot_oracle_upgrade.sql"

# Подключение к БД
ssh Pi4-2 "cd /home/lexun/ai-consultant && docker compose -f docker-compose.prod.yml exec db psql -U postgres -d telegram_bot"
```

### Deployment Commands
```bash
# Полное развертывание на сервере
ssh Pi4-2 "cd /home/lexun/ai-consultant && git pull && docker compose -f docker-compose.prod.yml build --no-cache app && docker compose -f docker-compose.prod.yml up -d app"

# Просмотр логов
ssh Pi4-2 "cd /home/lexun/ai-consultant && docker compose -f docker-compose.prod.yml logs app -f"

# Перезапуск контейнера
ssh Pi4-2 "cd /home/lexun/ai-consultant && docker compose -f docker-compose.prod.yml restart app"
```

### API Testing
```bash
# Проверка здоровья системы
curl -s "https://consultant.sh3.su/health"

# Тестирование админских эндпоинтов
curl -X POST "https://consultant.sh3.su/admin/trigger/daily-messages" -H "Authorization: Bearer supersecret_admin_token"

curl -X POST "https://consultant.sh3.su/admin/trigger/crm-planning" -H "Authorization: Bearer supersecret_admin_token"

curl -X POST "https://consultant.sh3.su/admin/trigger/crm-dispatch" -H "Authorization: Bearer supersecret_admin_token"

# Тестирование GPT-5 интеграции
curl -X POST "https://consultant.sh3.su/admin/test/ai-responses?question=Как%20дела?&persona=admin&age=22&gender=female" -H "Authorization: Bearer supersecret_admin_token"

curl -X POST "https://consultant.sh3.su/admin/test/ai-responses?question=В%20чем%20смысл%20жизни?&persona=oracle&age=35&gender=male" -H "Authorization: Bearer supersecret_admin_token"
```

### Database Utilities
```bash
# Удаление пользователя для тестирования
ssh Pi4-2 "cd /home/lexun/ai-consultant && docker compose -f docker-compose.prod.yml exec db psql -U postgres -d telegram_bot -c \"DELETE FROM users WHERE tg_user_id = USER_ID;\""

# Проверка таблиц Oracle
ssh Pi4-2 "cd /home/lexun/ai-consultant && docker compose -f docker-compose.prod.yml exec db psql -U postgres -d telegram_bot -c \"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'admin_%';\""
```

## Architecture Notes

### Bot Oracle System
- **Двухперсонная система**: Administrator (эмоциональный) + Oracle (мудрый)
- **GPT-5 интеграция**: Настоящий ИИ для обеих ролей с fallback
- **CRM система**: Проактивные контакты с антиспам ограничениями
- **Персонализация**: Обращения по возрасту и полу пользователя

### Key Files
- `app/main.py` - Основное приложение (webhook режим)
- `app/bot/oracle_handlers.py` - Обработчики двухперсонной системы
- `app/bot/onboarding.py` - FSM анкета пользователя
- `app/services/ai_client.py` - GPT-5 интеграция
- `app/services/persona.py` - Система персонализации
- `app/crm/planner.py` - Планировщик CRM задач
- `app/crm/dispatcher.py` - Исполнитель CRM задач
- `migrations/002_bot_oracle_upgrade.sql` - Миграция Oracle

### Environment Variables
```
OPENAI_API_KEY=your_openai_api_key_here
FREE_QUESTIONS=5
HUMANIZED_MAX_CONTACTS_PER_DAY=3
NUDGE_MIN_HOURS=48
NUDGE_MAX_PER_WEEK=2
ADMIN_TOKEN=supersecret_admin_token
```

## Common Issues & Solutions

### Import Errors
- Убедитесь что `app/crm/__init__.py` существует
- Проверьте все пути импортов после переименования файлов

### Database Connection
- База данных называется `telegram_bot`, не `app`
- Пользователь БД: `postgres`, пароль: `password`

### Deployment Issues
- Всегда используйте `--no-cache` при пересборке Docker
- Проверяйте логи после каждого деплоя
- При изменении main.py нужна полная пересборка контейнера

## Testing Checklist

### После деплоя проверить:
- [ ] Здоровье API: `curl -s "https://consultant.sh3.su/health"`
- [ ] Логи содержат: "Bot Oracle startup completed!"
- [ ] Логи содержат: "CRM planning, CRM dispatcher"
- [ ] Telegram webhook работает: отправить `/start` в бот
- [ ] Анкета работает: ввод возраста и выбор пола
- [ ] GPT-5 отвечает или fallback срабатывает
- [ ] Админские эндпоинты доступны с токеном

### Типичный пользовательский флоу:
1. `/start` → анкета (возраст + пол)
2. Задать вопрос → ответ от Администратора (5 бесплатных)
3. `💎 Подписка` → выбор тарифа
4. После подписки → вопросы отвечает Оракул (10/день)
5. CRM система автоматически отправляет проактивные сообщения

## Production Environment
- **Server**: Pi4-2
- **Domain**: consultant.sh3.su
- **Docker**: docker-compose.prod.yml
- **Database**: PostgreSQL в контейнере
- **SSL**: Let's Encrypt автоматически
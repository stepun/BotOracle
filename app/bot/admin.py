from aiogram import types, Router
from aiogram.filters import Command
from datetime import datetime, date, timedelta
from io import BytesIO

from app.database.models import MetricsModel
from app.database.connection import db
from app.config import config
import logging

logger = logging.getLogger(__name__)
admin_router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

@admin_router.message(Command("admin_today"))
async def admin_today(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    try:
        today = date.today()
        metrics = await MetricsModel.calculate_daily_metrics(today)

        text = f"""
📊 **Статистика за {today.strftime('%d.%m.%Y')}**

👥 DAU: {metrics['dau']}
🆕 Новые пользователи: {metrics['new_users']}
🔄 Активные пользователи: {metrics['active_users']}
🚫 Заблокировано всего: {metrics['blocked_total']}
📨 Получили сообщение дня: {metrics['daily_sent']}
💎 Активные подписчики: {metrics['paid_active']}
🆕💎 Новые подписчики: {metrics['paid_new']}
❓ Задано вопросов: {metrics['questions']}
💰 Выручка: {metrics['revenue']} ₽
"""

        await message.answer(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Admin today command error: {e}")
        await message.answer("❌ Ошибка при получении статистики")

@admin_router.message(Command("admin_range"))
async def admin_range(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    try:
        parts = message.text.split()
        if len(parts) != 3:
            await message.answer("❌ Формат: /admin_range YYYY-MM-DD YYYY-MM-DD")
            return

        date1_str, date2_str = parts[1], parts[2]
        date1 = datetime.strptime(date1_str, '%Y-%m-%d').date()
        date2 = datetime.strptime(date2_str, '%Y-%m-%d').date()

        if date1 > date2:
            date1, date2 = date2, date1

        rows = await db.fetch(
            """
            SELECT * FROM fact_daily_metrics
            WHERE d BETWEEN $1 AND $2
            ORDER BY d
            """,
            date1, date2
        )

        if not rows:
            await message.answer("📭 Нет данных за указанный период")
            return

        # Calculate totals
        total_dau = sum(row['dau'] for row in rows)
        total_new = sum(row['new_users'] for row in rows)
        total_revenue = sum(row['revenue'] for row in rows)
        total_questions = sum(row['questions'] for row in rows)
        avg_dau = total_dau / len(rows) if rows else 0

        text = f"""
📊 **Статистика за период {date1_str} — {date2_str}**

📅 Дней: {len(rows)}
👥 Общий DAU: {total_dau}
📊 Средний DAU: {avg_dau:.1f}
🆕 Новых пользователей: {total_new}
❓ Всего вопросов: {total_questions}
💰 Общая выручка: {total_revenue} ₽

Для подробной выгрузки используйте /admin_export
"""

        await message.answer(text, parse_mode="Markdown")

    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте YYYY-MM-DD")
    except Exception as e:
        logger.error(f"Admin range command error: {e}")
        await message.answer("❌ Ошибка при получении статистики")

@admin_router.message(Command("admin_export"))
async def admin_export(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    try:
        parts = message.text.split()
        if len(parts) != 3:
            await message.answer("❌ Формат: /admin_export YYYY-MM-DD YYYY-MM-DD")
            return

        date1_str, date2_str = parts[1], parts[2]
        date1 = datetime.strptime(date1_str, '%Y-%m-%d').date()
        date2 = datetime.strptime(date2_str, '%Y-%m-%d').date()

        if date1 > date2:
            date1, date2 = date2, date1

        rows = await db.fetch(
            """
            SELECT * FROM fact_daily_metrics
            WHERE d BETWEEN $1 AND $2
            ORDER BY d
            """,
            date1, date2
        )

        if not rows:
            await message.answer("📭 Нет данных за указанный период")
            return

        # Create TSV content
        headers = ['date', 'dau', 'new_users', 'active_users', 'blocked_total',
                  'daily_sent', 'paid_active', 'paid_new', 'questions', 'revenue']

        tsv_lines = ['\t'.join(headers)]

        for row in rows:
            line = '\t'.join([str(row[header] if row[header] is not None else 0) for header in headers])
            tsv_lines.append(line)

        tsv_content = '\n'.join(tsv_lines)

        # Create file
        file_buffer = BytesIO(tsv_content.encode('utf-8'))
        filename = f"stats_{date1_str}_{date2_str}.tsv"

        file = types.BufferedInputFile(file_buffer.getvalue(), filename=filename)

        await message.answer_document(
            file,
            caption=f"📊 Экспорт статистики за период {date1_str} — {date2_str}"
        )

    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте YYYY-MM-DD")
    except Exception as e:
        logger.error(f"Admin export command error: {e}")
        await message.answer("❌ Ошибка при создании экспорта")

@admin_router.message(Command("admin_paid"))
async def admin_paid(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    try:
        rows = await db.fetch(
            """
            SELECT u.tg_user_id, u.username, s.plan_code, s.ends_at
            FROM subscriptions s
            JOIN users u ON s.user_id = u.id
            WHERE s.status = 'active' AND s.ends_at > now()
            ORDER BY s.ends_at DESC
            LIMIT 50
            """
        )

        if not rows:
            await message.answer("📭 Нет активных подписчиков")
            return

        text = "💎 **Активные подписчики (последние 50):**\n\n"

        for row in rows:
            username = f"@{row['username']}" if row['username'] else f"ID:{row['tg_user_id']}"
            plan = row['plan_code']
            end_date = row['ends_at'].strftime('%d.%m.%Y')
            text += f"• {username} — {plan} до {end_date}\n"

        if len(text) > 4000:
            text = text[:3900] + "\n\n... (список обрезан)"

        await message.answer(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Admin paid command error: {e}")
        await message.answer("❌ Ошибка при получении списка подписчиков")

@admin_router.message(Command("admin_blocked"))
async def admin_blocked(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    try:
        rows = await db.fetch(
            """
            SELECT tg_user_id, username, blocked_at
            FROM users
            WHERE is_blocked = true
            ORDER BY blocked_at DESC
            LIMIT 50
            """
        )

        if not rows:
            await message.answer("✅ Нет заблокированных пользователей")
            return

        text = "🚫 **Заблокированные пользователи (последние 50):**\n\n"

        for row in rows:
            username = f"@{row['username']}" if row['username'] else f"ID:{row['tg_user_id']}"
            blocked_date = row['blocked_at'].strftime('%d.%m.%Y') if row['blocked_at'] else "неизвестно"
            text += f"• {username} — {blocked_date}\n"

        if len(text) > 4000:
            text = text[:3900] + "\n\n... (список обрезан)"

        await message.answer(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Admin blocked command error: {e}")
        await message.answer("❌ Ошибка при получении списка заблокированных")

def setup_admin_handlers(dp):
    dp.include_router(admin_router)
from datetime import datetime, date
from typing import Optional, Dict, Any
from app.database.connection import db
from app.config import config
import logging
import json

logger = logging.getLogger(__name__)

class UserModel:
    @staticmethod
    async def get_or_create_user(tg_user_id: int, username: str = None) -> dict:
        user = await db.fetchrow(
            "SELECT * FROM users WHERE tg_user_id = $1",
            tg_user_id
        )

        if not user:
            await db.execute(
                """
                INSERT INTO users (tg_user_id, username, first_seen_at, free_questions_left)
                VALUES ($1, $2, now(), $3)
                """,
                tg_user_id, username, config.FREE_QUESTIONS
            )

            await EventModel.log_event(
                user_id=None,
                event_type='start',
                meta={'tg_user_id': tg_user_id, 'username': username}
            )

            user = await db.fetchrow(
                "SELECT * FROM users WHERE tg_user_id = $1",
                tg_user_id
            )

        return dict(user)

    @staticmethod
    async def update_last_seen(user_id: int):
        await db.execute(
            "UPDATE users SET last_seen_at = now() WHERE id = $1",
            user_id
        )

    @staticmethod
    async def set_blocked(user_id: int, blocked: bool = True):
        await db.execute(
            "UPDATE users SET is_blocked = $1, blocked_at = now() WHERE id = $2",
            blocked, user_id
        )

    @staticmethod
    async def use_free_question(user_id: int) -> bool:
        result = await db.execute(
            """
            UPDATE users
            SET free_questions_left = free_questions_left - 1
            WHERE id = $1 AND free_questions_left > 0
            """,
            user_id
        )
        return result == "UPDATE 1"

class SubscriptionModel:
    @staticmethod
    async def get_active_subscription(user_id: int) -> Optional[dict]:
        subscription = await db.fetchrow(
            """
            SELECT * FROM subscriptions
            WHERE user_id = $1 AND status = 'active' AND ends_at > now()
            ORDER BY ends_at DESC LIMIT 1
            """,
            user_id
        )
        return dict(subscription) if subscription else None

    @staticmethod
    async def create_subscription(user_id: int, plan_code: str, amount: float,
                                inv_id: str = None) -> int:
        days = 7 if plan_code == 'WEEK' else 30

        subscription_id = await db.fetchval(
            """
            INSERT INTO subscriptions (user_id, plan_code, ends_at, robokassa_inv_id, amount)
            VALUES ($1, $2, now() + interval '%s days', $3, $4)
            RETURNING id
            """ % days,
            user_id, plan_code, inv_id, amount
        )

        await EventModel.log_event(
            user_id=user_id,
            event_type='subscription_started',
            meta={'plan_code': plan_code, 'amount': amount, 'days': days}
        )

        return subscription_id

    @staticmethod
    async def extend_subscription(user_id: int, plan_code: str, amount: float):
        days = 7 if plan_code == 'WEEK' else 30

        await db.execute(
            """
            UPDATE subscriptions
            SET ends_at = GREATEST(ends_at, now()) + interval '%s days'
            WHERE user_id = $1 AND status = 'active'
            """ % days,
            user_id
        )

class QuestionModel:
    @staticmethod
    async def count_today_questions(user_id: int) -> int:
        count = await db.fetchval(
            """
            SELECT COUNT(*) FROM questions
            WHERE user_id = $1 AND DATE(created_at) = CURRENT_DATE
            """,
            user_id
        )
        return count or 0

    @staticmethod
    async def save_question(user_id: int, question: str, answer: str, tokens: int = 0):
        await db.execute(
            """
            INSERT INTO questions (user_id, question_text, answer_text, tokens_used)
            VALUES ($1, $2, $3, $4)
            """,
            user_id, question, answer, tokens
        )

        await EventModel.log_event(
            user_id=user_id,
            event_type='question_asked',
            meta={'tokens': tokens}
        )

class DailyMessageModel:
    @staticmethod
    async def get_random_message() -> Optional[dict]:
        message = await db.fetchrow(
            """
            SELECT * FROM daily_messages
            WHERE is_active = true
            ORDER BY RANDOM()
            LIMIT 1
            """
        )
        return dict(message) if message else None

    @staticmethod
    async def mark_sent(user_id: int, message_id: int):
        await db.execute(
            "INSERT INTO daily_sent (user_id, message_id) VALUES ($1, $2)",
            user_id, message_id
        )

    @staticmethod
    async def is_sent_today(user_id: int) -> bool:
        count = await db.fetchval(
            """
            SELECT COUNT(*) FROM daily_sent
            WHERE user_id = $1 AND sent_date = CURRENT_DATE
            """,
            user_id
        )
        return (count or 0) > 0

class EventModel:
    @staticmethod
    async def log_event(user_id: Optional[int], event_type: str, meta: Dict[str, Any] = None):
        await db.execute(
            "INSERT INTO events (user_id, type, meta) VALUES ($1, $2, $3)",
            user_id, event_type, json.dumps(meta or {})
        )

class MetricsModel:
    @staticmethod
    async def calculate_daily_metrics(target_date: date = None) -> dict:
        if not target_date:
            target_date = date.today()

        metrics = await db.fetchrow(
            """
            SELECT
                COUNT(DISTINCT e1.user_id) as dau,
                COUNT(DISTINCT CASE WHEN e1.type = 'start' THEN e1.user_id END) as new_users,
                COUNT(DISTINCT CASE WHEN e1.type IN ('daily_sent', 'question_asked') THEN e1.user_id END) as active_users,
                COUNT(DISTINCT CASE WHEN e1.type = 'message_failed_blocked' THEN e1.user_id END) as blocked_today,
                COUNT(DISTINCT CASE WHEN e1.type = 'daily_sent' THEN e1.user_id END) as daily_sent,
                COUNT(DISTINCT CASE WHEN e1.type = 'question_asked' THEN e1.user_id END) as questions,
                COALESCE(SUM(CASE WHEN e1.type = 'payment_success' THEN (e1.meta->>'amount')::numeric ELSE 0 END), 0) as revenue
            FROM events e1
            WHERE DATE(e1.occurred_at) = $1
            """,
            target_date
        )

        # Count active subscriptions
        paid_active = await db.fetchval(
            """
            SELECT COUNT(DISTINCT user_id)
            FROM subscriptions
            WHERE status = 'active' AND $1 BETWEEN DATE(started_at) AND DATE(ends_at)
            """,
            target_date
        ) or 0

        # Count new paid subscriptions today
        paid_new = await db.fetchval(
            """
            SELECT COUNT(DISTINCT user_id)
            FROM subscriptions
            WHERE DATE(started_at) = $1
            """,
            target_date
        ) or 0

        # Total blocked users
        blocked_total = await db.fetchval(
            "SELECT COUNT(*) FROM users WHERE is_blocked = true"
        ) or 0

        return {
            'date': target_date,
            'dau': metrics['dau'] or 0,
            'new_users': metrics['new_users'] or 0,
            'active_users': metrics['active_users'] or 0,
            'blocked_total': blocked_total,
            'daily_sent': metrics['daily_sent'] or 0,
            'paid_active': paid_active,
            'paid_new': paid_new,
            'questions': metrics['questions'] or 0,
            'revenue': float(metrics['revenue'] or 0)
        }

    @staticmethod
    async def save_daily_metrics(metrics: dict):
        await db.execute(
            """
            INSERT INTO fact_daily_metrics
            (d, dau, new_users, active_users, blocked_total, daily_sent, paid_active, paid_new, questions, revenue)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (d) DO UPDATE SET
                dau = EXCLUDED.dau,
                new_users = EXCLUDED.new_users,
                active_users = EXCLUDED.active_users,
                blocked_total = EXCLUDED.blocked_total,
                daily_sent = EXCLUDED.daily_sent,
                paid_active = EXCLUDED.paid_active,
                paid_new = EXCLUDED.paid_new,
                questions = EXCLUDED.questions,
                revenue = EXCLUDED.revenue
            """,
            metrics['date'], metrics['dau'], metrics['new_users'], metrics['active_users'],
            metrics['blocked_total'], metrics['daily_sent'], metrics['paid_active'],
            metrics['paid_new'], metrics['questions'], metrics['revenue']
        )


class PaymentModel:
    @staticmethod
    async def create_payment(user_id: int, inv_id: int, plan_code: str, amount: float) -> int:
        payment_id = await db.fetchval(
            """
            INSERT INTO payments (user_id, inv_id, plan_code, amount, status, created_at)
            VALUES ($1, $2, $3, $4, 'pending', now())
            RETURNING id
            """,
            user_id, inv_id, plan_code, amount
        )
        return payment_id

    @staticmethod
    async def get_payment_by_inv_id(inv_id: int):
        return await db.fetchrow(
            "SELECT * FROM payments WHERE inv_id = $1",
            inv_id
        )

    @staticmethod
    async def mark_payment_success(inv_id: int, raw_payload: dict = None):
        await db.execute(
            """
            UPDATE payments
            SET status = 'success', paid_at = now(), raw_payload = $2
            WHERE inv_id = $1
            """,
            inv_id, raw_payload
        )

    @staticmethod
    async def mark_payment_failed(inv_id: int, raw_payload: dict = None):
        await db.execute(
            """
            UPDATE payments
            SET status = 'failed', raw_payload = $2
            WHERE inv_id = $1
            """,
            inv_id, raw_payload
        )
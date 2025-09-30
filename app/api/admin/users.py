from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
import logging

from app.database.connection import db
from app.api.admin.auth import verify_admin_token

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/admin/users")
async def get_users(
    status: Optional[str] = Query(None, description="Filter by status: active, blocked, paid"),
    limit: int = Query(50, description="Limit results"),
    _: bool = Depends(verify_admin_token)
):
    try:
        query = "SELECT u.*, s.ends_at as subscription_end FROM users u LEFT JOIN subscriptions s ON u.id = s.user_id AND s.status = 'active' AND s.ends_at > now()"
        params = []

        if status == "blocked":
            query += " WHERE u.is_blocked = true"
        elif status == "paid":
            query += " WHERE s.id IS NOT NULL"
        elif status == "active":
            query += " WHERE u.is_blocked = false"

        query += " ORDER BY u.last_seen_at DESC LIMIT $1"
        params.append(limit)

        rows = await db.fetch(query, *params)

        users = []
        for row in rows:
            users.append({
                'id': row['id'],
                'tg_user_id': row['tg_user_id'],
                'username': row['username'],
                'first_seen_at': row['first_seen_at'].isoformat() if row['first_seen_at'] else None,
                'last_seen_at': row['last_seen_at'].isoformat() if row['last_seen_at'] else None,
                'is_blocked': row['is_blocked'],
                'free_questions_left': row['free_questions_left'],
                'has_subscription': row['subscription_end'] is not None,
                'subscription_end': row['subscription_end'].isoformat() if row['subscription_end'] else None
            })

        return {
            'users': users,
            'total': len(users),
            'filter': status
        }

    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/admin/users/{user_id}")
async def get_user_details(
    user_id: int,
    _: bool = Depends(verify_admin_token)
):
    """Get detailed user information including history"""
    try:
        # Get user info
        user = await db.fetchrow(
            """
            SELECT u.*,
                   s.ends_at as subscription_end
            FROM users u
            LEFT JOIN subscriptions s ON s.user_id = u.id
                AND s.status = 'active' AND s.ends_at > now()
            WHERE u.id = $1
            """,
            user_id
        )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get daily messages history
        daily_messages = await db.fetch(
            """
            SELECT sent_date
            FROM daily_sent
            WHERE user_id = $1
            ORDER BY sent_date DESC
            LIMIT 50
            """,
            user_id
        )

        # Get Oracle questions history
        oracle_questions = await db.fetch(
            """
            SELECT question, answer, source, asked_date, asked_at, tokens_used
            FROM oracle_questions
            WHERE user_id = $1
            ORDER BY asked_at DESC
            LIMIT 50
            """,
            user_id
        )

        # Get payments history
        payments = await db.fetch(
            """
            SELECT plan_code, amount, status, created_at, paid_at
            FROM payments
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT 50
            """,
            user_id
        )

        # Get CRM tasks history (logs)
        crm_logs = await db.fetch(
            """
            SELECT type, status, due_at, sent_at, result_code, payload, created_at
            FROM admin_tasks
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT 100
            """,
            user_id
        )

        return {
            'user': {
                'id': user['id'],
                'tg_user_id': user['tg_user_id'],
                'username': user['username'],
                'age': user['age'],
                'gender': user['gender'],
                'first_seen_at': user['first_seen_at'].isoformat() if user['first_seen_at'] else None,
                'last_seen_at': user['last_seen_at'].isoformat() if user['last_seen_at'] else None,
                'is_blocked': user['is_blocked'],
                'free_questions_left': user['free_questions_left'],
                'has_subscription': user['subscription_end'] is not None,
                'subscription_end': user['subscription_end'].isoformat() if user['subscription_end'] else None
            },
            'daily_messages': [{
                'date': msg['sent_date'].isoformat()
            } for msg in daily_messages],
            'oracle_questions': [{
                'question': q['question'],
                'answer': q['answer'],
                'source': q['source'],
                'date': q['asked_date'].isoformat(),
                'asked_at': q['asked_at'].isoformat() if q['asked_at'] else None,
                'tokens': q['tokens_used']
            } for q in oracle_questions],
            'payments': [{
                'plan': p['plan_code'],
                'amount': float(p['amount']),
                'status': p['status'],
                'created_at': p['created_at'].isoformat() if p['created_at'] else None,
                'paid_at': p['paid_at'].isoformat() if p['paid_at'] else None
            } for p in payments],
            'crm_logs': [{
                'type': log['type'],
                'status': log['status'],
                'due_at': log['due_at'].isoformat() if log['due_at'] else None,
                'sent_at': log['sent_at'].isoformat() if log['sent_at'] else None,
                'result_code': log['result_code'],
                'created_at': log['created_at'].isoformat() if log['created_at'] else None
            } for log in crm_logs]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user details: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
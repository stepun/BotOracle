from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import logging

from app.database.models import MetricsModel
from app.database.connection import db
from app.config import config
from app.scheduler import get_scheduler

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != config.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    return True

@router.get("/admin/stats")
async def get_stats(
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    _: bool = Depends(verify_admin_token)
):
    try:
        if not date_from:
            date_from = date.today().strftime('%Y-%m-%d')
        if not date_to:
            date_to = date.today().strftime('%Y-%m-%d')

        start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        end_date = datetime.strptime(date_to, '%Y-%m-%d').date()

        rows = await db.fetch(
            """
            SELECT * FROM fact_daily_metrics
            WHERE d BETWEEN $1 AND $2
            ORDER BY d
            """,
            start_date, end_date
        )

        stats = []
        for row in rows:
            stats.append({
                'date': row['d'].isoformat(),
                'dau': row['dau'],
                'new_users': row['new_users'],
                'active_users': row['active_users'],
                'blocked_total': row['blocked_total'],
                'daily_sent': row['daily_sent'],
                'paid_active': row['paid_active'],
                'paid_new': row['paid_new'],
                'questions': row['questions'],
                'revenue': float(row['revenue'])
            })

        # Calculate summary
        summary = {
            'total_days': len(stats),
            'total_dau': sum(s['dau'] for s in stats),
            'total_new_users': sum(s['new_users'] for s in stats),
            'total_questions': sum(s['questions'] for s in stats),
            'total_revenue': sum(s['revenue'] for s in stats),
            'avg_dau': sum(s['dau'] for s in stats) / len(stats) if stats else 0
        }

        return {
            'stats': stats,
            'summary': summary,
            'period': {
                'from': date_from,
                'to': date_to
            }
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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

@router.get("/admin/export")
async def export_stats(
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)"),
    format: str = Query("json", description="Export format: json, csv"),
    _: bool = Depends(verify_admin_token)
):
    try:
        start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        end_date = datetime.strptime(date_to, '%Y-%m-%d').date()

        rows = await db.fetch(
            """
            SELECT * FROM fact_daily_metrics
            WHERE d BETWEEN $1 AND $2
            ORDER BY d
            """,
            start_date, end_date
        )

        if format == "csv":
            from fastapi.responses import Response

            headers = ['date', 'dau', 'new_users', 'active_users', 'blocked_total',
                      'daily_sent', 'paid_active', 'paid_new', 'questions', 'revenue']

            csv_lines = [','.join(headers)]

            for row in rows:
                line = ','.join([str(row[header] if row[header] is not None else 0) for header in headers])
                csv_lines.append(line)

            csv_content = '\n'.join(csv_lines)

            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=stats_{date_from}_{date_to}.csv"}
            )

        # JSON format (default)
        stats = []
        for row in rows:
            stats.append({
                'date': row['d'].isoformat(),
                'dau': row['dau'],
                'new_users': row['new_users'],
                'active_users': row['active_users'],
                'blocked_total': row['blocked_total'],
                'daily_sent': row['daily_sent'],
                'paid_active': row['paid_active'],
                'paid_new': row['paid_new'],
                'questions': row['questions'],
                'revenue': float(row['revenue'])
            })

        return {
            'data': stats,
            'period': {'from': date_from, 'to': date_to},
            'exported_at': datetime.now().isoformat()
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        logger.error(f"Error exporting stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/admin/trigger/daily-messages")
async def trigger_daily_messages(_: bool = Depends(verify_admin_token)):
    try:
        scheduler = get_scheduler()
        if scheduler:
            await scheduler.trigger_daily_messages()
            return {"status": "success", "message": "Daily messages triggered successfully"}
        else:
            return {"status": "error", "message": "Scheduler not available"}
    except Exception as e:
        logger.error(f"Error triggering daily messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger daily messages")

@router.post("/admin/trigger/crm-planning")
async def trigger_crm_planning(_: bool = Depends(verify_admin_token)):
    """Manually trigger CRM daily task planning"""
    try:
        scheduler = get_scheduler()
        if scheduler:
            stats = await scheduler.trigger_crm_planning()
            return {
                "status": "success",
                "message": "CRM planning triggered successfully",
                "stats": stats
            }
        else:
            return {"status": "error", "message": "Scheduler not available"}
    except Exception as e:
        logger.error(f"Error triggering CRM planning: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger CRM planning")

@router.post("/admin/trigger/crm-dispatch")
async def trigger_crm_dispatch(_: bool = Depends(verify_admin_token)):
    """Manually trigger CRM task dispatch"""
    try:
        scheduler = get_scheduler()
        if scheduler:
            stats = await scheduler.trigger_crm_dispatch()
            return {
                "status": "success",
                "message": "CRM dispatch triggered successfully",
                "stats": stats
            }
        else:
            return {"status": "error", "message": "Scheduler not available"}
    except Exception as e:
        logger.error(f"Error triggering CRM dispatch: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger CRM dispatch")

@router.get("/admin/crm/tasks")
async def get_crm_tasks(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Limit results"),
    _: bool = Depends(verify_admin_token)
):
    """Get CRM tasks"""
    try:
        query = """
            SELECT t.*, u.tg_user_id, u.username, u.age, u.gender
            FROM admin_tasks t
            JOIN users u ON u.id = t.user_id
            WHERE 1=1
        """
        params = []
        param_count = 0

        if user_id:
            param_count += 1
            query += f" AND t.user_id = ${param_count}"
            params.append(user_id)

        if status:
            param_count += 1
            query += f" AND t.status = ${param_count}"
            params.append(status)

        param_count += 1
        query += f" ORDER BY t.created_at DESC LIMIT ${param_count}"
        params.append(limit)

        rows = await db.fetch(query, *params)

        tasks = []
        for row in rows:
            tasks.append({
                'id': row['id'],
                'user_id': row['user_id'],
                'tg_user_id': row['tg_user_id'],
                'username': row['username'],
                'type': row['type'],
                'status': row['status'],
                'due_at': row['due_at'].isoformat() if row['due_at'] else None,
                'sent_at': row['sent_at'].isoformat() if row['sent_at'] else None,
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'payload': row['payload']
            })

        return {
            'tasks': tasks,
            'total': len(tasks),
            'filters': {'user_id': user_id, 'status': status}
        }

    except Exception as e:
        logger.error(f"Error getting CRM tasks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/admin/test/ai-responses")
async def test_ai_responses(
    question: str = Query(..., description="Test question"),
    persona: str = Query("admin", description="Persona to test: admin or oracle"),
    age: int = Query(25, description="User age for personalization"),
    gender: str = Query("other", description="User gender: male, female, other"),
    _: bool = Depends(verify_admin_token)
):
    """Test AI responses for both personas"""
    try:
        from app.services.ai_client import call_admin_ai, call_oracle_ai

        user_context = {'age': age, 'gender': gender}

        if persona == "admin":
            response = await call_admin_ai(question, user_context)
            response_type = "Administrator (эмоциональный помощник)"
        elif persona == "oracle":
            response = await call_oracle_ai(question, user_context)
            response_type = "Oracle (мудрый наставник)"
        else:
            raise HTTPException(status_code=400, detail="Invalid persona. Use 'admin' or 'oracle'")

        return {
            "status": "success",
            "persona": response_type,
            "question": question,
            "response": response,
            "user_context": user_context,
            "response_length": len(response)
        }

    except Exception as e:
        logger.error(f"Error testing AI responses: {e}")
        raise HTTPException(status_code=500, detail="Failed to test AI responses")

@router.get("/health")
async def health_check():
    try:
        # Simple database check
        await db.fetchval("SELECT 1")
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")
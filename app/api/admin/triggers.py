from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime
from typing import Optional
import logging

from app.database.connection import db
from app.api.admin.auth import verify_admin_token
from app.scheduler import get_scheduler
from app.config import config

logger = logging.getLogger(__name__)
router = APIRouter()

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

@router.post("/admin/test/crm")
async def test_crm_for_admin(_: bool = Depends(verify_admin_token)):
    """Test CRM system for admin user"""
    try:
        from app.crm.planner import crm_planner
        from app.crm.dispatcher import crm_dispatcher

        if not crm_dispatcher:
            return {
                "status": "error",
                "message": "CRM dispatcher not initialized"
            }

        # Get admin user from config
        admin_id = config.ADMIN_IDS[0] if config.ADMIN_IDS else None
        if not admin_id:
            return {
                "status": "error",
                "message": "No admin ID configured"
            }

        # Get admin user data
        user_row = await db.fetchrow(
            """
            SELECT id, tg_user_id, username, age, gender, last_seen_at, free_questions_left
            FROM users
            WHERE tg_user_id = $1
            """,
            admin_id
        )

        if not user_row:
            return {
                "status": "error",
                "message": f"Admin user {admin_id} not found in database"
            }

        user_data = dict(user_row)

        # Test 1: CRM Planner
        logger.info(f"Testing CRM planner for admin {admin_id}")
        tasks_created = await crm_planner.plan_for_user(user_data)

        # Get created tasks
        created_tasks = await db.fetch(
            """
            SELECT id, type, due_at, status
            FROM admin_tasks
            WHERE user_id = $1 AND status = 'pending'
            ORDER BY due_at DESC
            LIMIT 10
            """,
            user_data['id']
        )

        # Test 2: CRM Dispatcher
        logger.info(f"Testing CRM dispatcher for admin {admin_id}")
        dispatch_stats = await crm_dispatcher.dispatch_due_tasks(limit=5)

        return {
            "status": "success",
            "admin_id": admin_id,
            "planner": {
                "tasks_created": tasks_created,
                "created_tasks": [
                    {
                        "id": t['id'],
                        "type": t['type'],
                        "due_at": t['due_at'].isoformat(),
                        "status": t['status']
                    } for t in created_tasks
                ]
            },
            "dispatcher": dispatch_stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error testing CRM: {e}")
        raise HTTPException(status_code=500, detail=str(e))
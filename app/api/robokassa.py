from fastapi import APIRouter, Request, HTTPException, Form
from typing import Dict, Any
import logging

from app.database.models import UserModel, SubscriptionModel, EventModel
from app.utils.robokassa import verify_signature_result, parse_robokassa_callback
from app.config import config

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/robokassa/result")
async def robokassa_result(request: Request):
    try:
        # Parse form data
        form = await request.form()
        form_data = dict(form)

        logger.info(f"Robokassa callback received: {form_data}")

        # Parse callback data
        callback_data = parse_robokassa_callback(form_data)

        amount = callback_data['amount']
        inv_id = callback_data['inv_id']
        signature = callback_data['signature']

        if not amount or not inv_id or not signature:
            logger.warning("Missing required parameters in Robokassa callback")
            raise HTTPException(status_code=400, detail="Missing parameters")

        # Verify signature
        if not verify_signature_result(amount, inv_id, signature):
            logger.warning(f"Invalid signature for payment {inv_id}")
            raise HTTPException(status_code=400, detail="Invalid signature")

        # Parse invoice ID to get user info
        # Format: {user_id}_{plan}_{timestamp}
        try:
            parts = inv_id.split('_')
            user_id = int(parts[0])
            plan = parts[1]  # week or month
            plan_code = "WEEK" if plan == "week" else "MONTH"
        except (ValueError, IndexError):
            logger.error(f"Invalid invoice ID format: {inv_id}")
            raise HTTPException(status_code=400, detail="Invalid invoice ID")

        # Process payment
        await process_successful_payment(
            user_id=user_id,
            inv_id=inv_id,
            plan_code=plan_code,
            amount=float(amount),
            raw_payload=form_data
        )

        logger.info(f"Payment {inv_id} processed successfully")
        return "OK"

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Robokassa callback: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/robokassa/success")
async def robokassa_success(request: Request):
    # Success redirect - show user-friendly page
    return {"status": "success", "message": "Оплата прошла успешно! Подписка активирована."}

@router.post("/robokassa/fail")
async def robokassa_fail(request: Request):
    # Fail redirect - show error page
    return {"status": "error", "message": "Оплата не прошла. Попробуйте еще раз."}

async def process_successful_payment(user_id: int, inv_id: str, plan_code: str,
                                   amount: float, raw_payload: Dict[str, Any]):
    try:
        # Save payment record
        await EventModel.log_event(
            user_id=user_id,
            event_type='payment_success',
            meta={
                'inv_id': inv_id,
                'plan_code': plan_code,
                'amount': amount,
                'raw_payload': raw_payload
            }
        )

        # Check if user has active subscription
        existing_subscription = await SubscriptionModel.get_active_subscription(user_id)

        if existing_subscription:
            # Extend existing subscription
            await SubscriptionModel.extend_subscription(user_id, plan_code, amount)
            logger.info(f"Extended subscription for user {user_id}, plan {plan_code}")
        else:
            # Create new subscription
            await SubscriptionModel.create_subscription(user_id, plan_code, amount, inv_id)
            logger.info(f"Created new subscription for user {user_id}, plan {plan_code}")

        # TODO: Send confirmation message to user via bot
        # This would require bot instance to be accessible here

    except Exception as e:
        logger.error(f"Error processing payment for user {user_id}: {e}")
        raise
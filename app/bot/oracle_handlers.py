"""
Bot Oracle main handlers implementing two-role system:
1. Administrator - emotional, proactive, handles daily messages and free questions
2. Oracle - wise, calm, answers only subscription questions (10/day limit)
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from datetime import date
import logging

from app.database.models import (
    UserModel, DailyMessageModel, OracleQuestionModel,
    SubscriptionModel, AdminTaskModel
)
from app.services.persona import persona_factory, get_admin_response
from app.bot.keyboards import get_main_menu, get_subscription_menu
from app.bot.states import OnboardingStates

logger = logging.getLogger(__name__)
router = Router()

# AI integration
from app.services.ai_client import call_admin_ai, call_oracle_ai

@router.message(F.text == "📨 Сообщение дня")
async def daily_message_handler(message: types.Message):
    """Handle daily message requests"""
    try:
        user = await UserModel.get_by_tg_id(message.from_user.id)
        if not user:
            await message.answer("Напиши /start чтобы начать!")
            return

        # Check if user completed onboarding
        if not user.get('age') or not user.get('gender'):
            await message.answer("Сначала давай познакомимся! Напиши /start")
            return

        persona = persona_factory(user)

        # Check if already received today
        if await DailyMessageModel.is_sent_today(user['id']):
            repeat_message = persona.format_daily_repeat()
            await message.answer(repeat_message)
            return

        # Get random daily message
        daily_msg = await DailyMessageModel.get_random_message()
        if not daily_msg:
            await message.answer(persona.wrap("сегодня без новостей, но я слежу 😌"))
            return

        # Send message and mark as sent
        await message.answer(
            persona.wrap(f"сегодняшнее сообщение: {daily_msg['text']}")
        )

        await DailyMessageModel.mark_sent(user['id'], daily_msg['id'])

        # Update last seen
        await UserModel.update_last_seen(user['id'])

    except Exception as e:
        logger.error(f"Error in daily message handler: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@router.message(F.text == "💎 Подписка")
async def subscription_menu_handler(message: types.Message):
    """Handle subscription menu"""
    try:
        user = await UserModel.get_by_tg_id(message.from_user.id)
        if not user:
            await message.answer("Напиши /start чтобы начать!")
            return

        # Check if user completed onboarding
        if not user.get('age') or not user.get('gender'):
            await message.answer("Сначала давай познакомимся! Напиши /start")
            return

        persona = persona_factory(user)

        # Check current subscription
        subscription = await SubscriptionModel.get_active_subscription(user['id'])

        if subscription:
            await message.answer(
                persona.wrap(f"у тебя уже есть подписка до {subscription['ends_at'].strftime('%d.%m.%Y')} ✅\n"
                           "можешь задавать вопросы оракулу (до 10 в день)")
            )
        else:
            menu_text = get_admin_response("subscription_menu", persona)
            await message.answer(menu_text, reply_markup=get_subscription_menu())

        await UserModel.update_last_seen(user['id'])

    except Exception as e:
        logger.error(f"Error in subscription menu: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@router.message(F.text == "ℹ️ Мой статус")
async def status_handler(message: types.Message):
    """Show user status and limits"""
    try:
        user = await UserModel.get_by_tg_id(message.from_user.id)
        if not user:
            await message.answer("Напиши /start чтобы начать!")
            return

        persona = persona_factory(user)

        # Get subscription info
        subscription = await SubscriptionModel.get_active_subscription(user['id'])

        status_text = "📊 Твой статус:\n\n"

        if subscription:
            oracle_used = await OracleQuestionModel.count_today_questions(user['id'], 'SUB')
            status_text += f"✅ Подписка активна до {subscription['ends_at'].strftime('%d.%m.%Y')}\n"
            status_text += f"🔮 Вопросов оракулу сегодня: {oracle_used}/10\n"
        else:
            status_text += f"🎁 Бесплатных ответов: {user.get('free_questions_left', 0)}/5\n"
            status_text += f"💎 Подписка: не активна\n"

        daily_sent = await DailyMessageModel.is_sent_today(user['id'])
        status_text += f"📨 Сообщение дня: {'✅ получено' if daily_sent else '⏳ доступно'}\n"

        await message.answer(persona.wrap(status_text))
        await UserModel.update_last_seen(user['id'])

    except Exception as e:
        logger.error(f"Error in status handler: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@router.message(lambda message: not message.text.startswith('/') and message.text not in ["📨 Сообщение дня", "💎 Подписка", "ℹ️ Мой статус"])
async def question_handler(message: types.Message, state: FSMContext):
    """Handle all text questions - route to Administrator or Oracle"""
    try:
        # Check if user is in onboarding
        current_state = await state.get_state()
        if current_state in [OnboardingStates.waiting_for_age.state, OnboardingStates.waiting_for_gender.state]:
            # Let onboarding handler process this
            return

        user = await UserModel.get_by_tg_id(message.from_user.id)
        if not user:
            await message.answer("Напиши /start чтобы начать!")
            return

        # Check if user completed onboarding
        if not user.get('age') or not user.get('gender'):
            await message.answer("Сначала давай познакомимся! Напиши /start")
            return

        persona = persona_factory(user)
        question = message.text.strip()

        # Check if user has active subscription
        subscription = await SubscriptionModel.get_active_subscription(user['id'])

        if subscription:
            # ORACLE MODE - subscription active
            oracle_used = await OracleQuestionModel.count_today_questions(user['id'], 'SUB')

            if oracle_used >= 10:
                # Daily Oracle limit reached
                limit_message = persona.format_oracle_limit()
                await message.answer(limit_message)
                return

            # Call Oracle AI (wise, profound response)
            user_context = {'age': user.get('age'), 'gender': user.get('gender')}
            answer = await call_oracle_ai(question, user_context)

            # Save question and answer
            await OracleQuestionModel.save_question(
                user['id'], question, answer, source='SUB'
            )

            # Send Oracle response (without persona wrapping - Oracle speaks directly)
            remaining = 10 - oracle_used - 1
            oracle_response = f"🔮 **Оракул отвечает:**\n\n{answer}"

            if remaining > 0:
                oracle_response += f"\n\n_Остался {remaining} вопрос{'ов' if remaining > 1 else ''} на сегодня._"
            else:
                oracle_response += f"\n\n_Лимит вопросов на сегодня исчерпан. Завтра будет новый день._"

            await message.answer(oracle_response, parse_mode="Markdown")

        else:
            # ADMINISTRATOR MODE - no subscription, use free questions
            free_left = user.get('free_questions_left', 0)

            if free_left <= 0:
                # No free questions left
                exhausted_message = persona.format_free_exhausted()
                await message.answer(
                    f"{exhausted_message}\n\n💎 Получи подписку:",
                    reply_markup=get_subscription_menu()
                )
                return

            # Use one free question
            success = await UserModel.use_free_question(user['id'])
            if not success:
                await message.answer(persona.wrap("упс, что-то пошло не так. попробуй ещё раз"))
                return

            # Call Administrator AI (emotional, helpful response)
            user_context = {'age': user.get('age'), 'gender': user.get('gender')}
            answer = await call_admin_ai(question, user_context)

            # Save question and answer
            await OracleQuestionModel.save_question(
                user['id'], question, answer, source='FREE'
            )

            remaining = free_left - 1
            if remaining > 0:
                response = persona.format_free_remaining(remaining)
                full_response = f"{answer}\n\n{response}"
            else:
                response = persona.format_free_exhausted()
                full_response = f"{answer}\n\n{response}\n\n💎 Получи подписку:"
                await message.answer(full_response, reply_markup=get_subscription_menu())
                return

            await message.answer(full_response)

        await UserModel.update_last_seen(user['id'])

        # Create THANKS task for CRM
        await AdminTaskModel.create_task(
            user['id'],
            'THANKS',
            due_at=None,  # Immediate
            payload={'triggered_by': 'user_message'}
        )

    except Exception as e:
        logger.error(f"Error in question handler: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

# Callback handlers for subscription
@router.callback_query(F.data.startswith("BUY_"))
async def buy_subscription_callback(callback: types.CallbackQuery):
    """Handle subscription purchase callbacks"""
    try:
        plan = callback.data.replace("BUY_", "")  # DAY, WEEK, MONTH

        user = await UserModel.get_by_tg_id(callback.from_user.id)
        if not user:
            await callback.answer("Ошибка: пользователь не найден")
            return

        persona = persona_factory(user)

        # Import here to avoid circular imports
        from app.utils.robokassa import create_payment_url
        from datetime import datetime
        import uuid

        # Create payment record
        inv_id = int(datetime.now().timestamp())
        plan_prices = {"DAY": 99.0, "WEEK": 299.0, "MONTH": 899.0}
        amount = plan_prices.get(plan, 99.0)

        from app.database.models import PaymentModel
        await PaymentModel.create_payment(user['id'], inv_id, plan, amount)

        # Generate payment URL
        payment_url = create_payment_url(inv_id, plan, amount)

        await callback.message.answer(
            persona.wrap(f"отличный выбор! переходи к оплате:\n{payment_url}")
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in subscription callback: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")

@router.message(F.text == "/help")
async def help_handler(message: types.Message):
    """Show help information"""
    help_text = """
🤖 **Bot Oracle - Справка**

**Доступные команды:**
• 📨 Сообщение дня - получить ежедневное сообщение
• 💎 Подписка - управление подпиской
• ℹ️ Мой статус - показать текущий статус
• /help - эта справка

**Как это работает:**
1. **Администратор** (я) - отвечаю на бесплатные вопросы (5 шт), выдаю сообщения дня, помогаю с подпиской
2. **Оракул** - мудрые ответы по подписке (до 10 вопросов в день)

**Подписка:**
• День - 99₽
• Неделя - 299₽
• Месяц - 899₽

Просто задавай вопросы текстом! 💫
    """

    await message.answer(help_text, parse_mode="Markdown")
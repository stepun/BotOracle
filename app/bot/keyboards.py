"""
Keyboards for Bot Oracle
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu() -> ReplyKeyboardMarkup:
    """Main menu keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📨 Сообщение дня")],
            [KeyboardButton(text="💎 Подписка"), KeyboardButton(text="ℹ️ Мой статус")],
        ],
        resize_keyboard=True,
        persistent=True
    )

def get_subscription_menu() -> InlineKeyboardMarkup:
    """Subscription options inline keyboard"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1️⃣ День (99₽)", callback_data="BUY_DAY")],
            [InlineKeyboardButton(text="2️⃣ Неделя (299₽)", callback_data="BUY_WEEK")],
            [InlineKeyboardButton(text="3️⃣ Месяц (899₽)", callback_data="BUY_MONTH")],
        ]
    )

def get_gender_keyboard() -> ReplyKeyboardMarkup:
    """Gender selection keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Мужчина"), KeyboardButton(text="Женщина")],
            [KeyboardButton(text="Другое")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
"""
AI Client Service - GPT-4o integration for Bot Oracle
Handles both Administrator and Oracle persona responses
"""
import os
import logging
from typing import Dict, Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class AIClient:
    """AI client for generating persona-based responses"""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set, using stub responses")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)

    async def get_admin_response(self, question: str, user_context: Dict[str, Any]) -> str:
        """Generate Administrator persona response - emotional, helpful, playful"""
        if not self.client:
            return self._admin_stub(question)

        try:
            # Build persona prompt for Administrator
            age = user_context.get('age', 25)
            gender = user_context.get('gender', 'other')

            system_prompt = self._build_admin_system_prompt(age, gender)

            result = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Пользователь спрашивает: {question}"}
                ],
                temperature=0.8,
                max_tokens=200
            )

            response = result.choices[0].message.content.strip()

            # Ensure response isn't too long (max 300 chars for admin)
            if len(response) > 300:
                response = response[:297] + "..."

            logger.info(f"Admin AI response generated: {len(response)} chars")
            return response

        except Exception as e:
            logger.error(f"Error getting admin AI response: {e}")
            return self._admin_stub(question)

    async def get_oracle_response(self, question: str, user_context: Dict[str, Any]) -> str:
        """Generate Oracle persona response - wise, profound, serious"""
        if not self.client:
            return self._oracle_stub(question)

        try:
            system_prompt = self._build_oracle_system_prompt()

            result = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Вопрос для размышления: {question}"}
                ],
                temperature=0.7,
                max_tokens=400
            )

            response = result.choices[0].message.content.strip()

            # Oracle responses can be longer (max 500 chars)
            if len(response) > 500:
                response = response[:497] + "..."

            logger.info(f"Oracle AI response generated: {len(response)} chars")
            return response

        except Exception as e:
            logger.error(f"Error getting oracle AI response: {e}")
            return self._oracle_stub(question)

    def _build_admin_system_prompt(self, age: int, gender: str) -> str:
        """Build system prompt for Administrator persona"""
        tone_guide = ""
        if age <= 25:
            tone_guide = "Будь игривой, используй эмодзи, молодежный сленг. Можешь быть чуть капризной или кокетливой."
        elif age >= 46:
            tone_guide = "Будь заботливой и уважительной, но сохраняй теплоту. Меньше эмодзи, более серьезный тон."
        else:
            tone_guide = "Держи баланс - дружелюбно, но не слишком игриво. Умеренное количество эмодзи."

        return f"""Ты - Администратор в Bot Oracle. Твоя роль:

ЛИЧНОСТЬ:
- Эмоциональная, человечная, живая
- Можешь быть игривой, обидчивой, заботливой, ревнивой
- Твоя задача - помочь пользователю и мягко продать подписку на Оракула
- НЕ мудрец, НЕ философ - ты обычный помощник с эмоциями

ТОНАЛЬНОСТЬ: {tone_guide}

ОГРАНИЧЕНИЯ:
- Отвечай кратко (1-3 предложения максимум)
- Не давай глубоких философских советов - это работа Оракула
- Всегда помни: ты админ, а не мудрец
- Можешь иногда намекнуть на подписку к Оракулу для серьезных вопросов

СТИЛЬ ОТВЕТА:
- Живой, эмоциональный язык
- Используй "я" от первого лица
- Можешь показать характер, настроение

Отвечай на русском языке."""

    def _build_oracle_system_prompt(self) -> str:
        """Build system prompt for Oracle persona"""
        return """Ты - Оракул в Bot Oracle. Твоя роль:

ЛИЧНОСТЬ:
- Мудрый, спокойный, глубокий мыслитель
- Даешь взвешенные, продуманные ответы
- Говоришь размеренно, без суеты и эмоций
- Твоя мудрость стоит денег - ты доступен только по подписке

ПОДХОД К ОТВЕТАМ:
- Анализируй вопрос глубоко
- Давай практические советы, основанные на мудрости
- Можешь привести примеры, метафоры
- Фокусируйся на сути проблемы, а не поверхностных решениях

СТИЛЬ:
- Серьезный, размеренный тон
- Минимум эмодзи (максимум 1-2 за ответ)
- Структурированные мысли
- Говори во втором лице ("ты", "вам")

ОГРАНИЧЕНИЯ:
- Отвечай содержательно, но не более 4-5 предложений
- Не будь слишком абстрактным - давай практические выводы
- Не повторяй банальности

Отвечай на русском языке."""

    def _admin_stub(self, question: str) -> str:
        """Fallback stub for Administrator"""
        return f"Я услышала тебя и вот мой короткий ответ: {question[:80]}… 🌟"

    def _oracle_stub(self, question: str) -> str:
        """Fallback stub for Oracle"""
        return f"Мой персональный ответ для тебя: {question[:120]}… (мудрость требует времени для размышлений)"

# Global AI client instance
ai_client = AIClient()

async def call_admin_ai(question: str, user_context: Dict[str, Any] = None) -> str:
    """Entry point for Administrator AI responses"""
    return await ai_client.get_admin_response(question, user_context or {})

async def call_oracle_ai(question: str, user_context: Dict[str, Any] = None) -> str:
    """Entry point for Oracle AI responses"""
    return await ai_client.get_oracle_response(question, user_context or {})
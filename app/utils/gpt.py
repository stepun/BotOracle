import openai
from app.config import config
import logging

logger = logging.getLogger(__name__)

openai.api_key = config.OPENAI_API_KEY

SYSTEM_PROMPT = """
Ты — доброжелательный аналитик и консультант.
Отвечай на русском языке коротко и ясно, структурируй ответ в 3–5 пунктов.
Будь полезным, конкретным и практичным в своих советах.
Избегай общих фраз, давай действенные рекомендации.
"""

async def get_gpt_response(user_question: str) -> tuple[str, int]:
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_question}
            ],
            max_tokens=800,
            temperature=0.7
        )

        answer = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens

        logger.info(f"GPT response generated, tokens used: {tokens_used}")
        return answer, tokens_used

    except Exception as e:
        logger.error(f"GPT request failed: {e}")
        return "Извините, произошла ошибка при обработке вашего вопроса. Попробуйте позже.", 0
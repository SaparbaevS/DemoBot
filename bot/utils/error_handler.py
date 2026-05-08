import logging

from google.genai.errors import ClientError, ServerError

logger = logging.getLogger(__name__)


def gemini_error_message(e: Exception, context: str = "", user_id: int = 0) -> str:
    """Map a Gemini exception to a user-friendly Russian HTML string."""
    if isinstance(e, ServerError):
        err = str(e)
        if "503" in err or "UNAVAILABLE" in err:
            return (
                "⏳ <b>Серверы Gemini перегружены.</b>\n\n"
                "Подождите 30–60 секунд и попробуйте снова."
            )
        logger.exception("Gemini ServerError [%s] user=%s", context, user_id)
        return "❌ Ошибка сервера Gemini. Попробуйте позже."

    if isinstance(e, ClientError):
        err = str(e)
        if "429" in err or "RESOURCE_EXHAUSTED" in err:
            return (
                "⚠️ <b>Квота Gemini API исчерпана.</b>\n\n"
                "Free tier: 5 запросов/мин, 20 запросов/день."
            )
        if "404" in err or "NOT_FOUND" in err:
            logger.error("Gemini model not found [%s]: %s", context, err)
            return "⚠️ <b>Модель Gemini недоступна.</b>\n\nНапишите разработчику."
        logger.exception("Gemini ClientError [%s] user=%s", context, user_id)
        return "❌ Ошибка Gemini API. Попробуйте позже."

    logger.exception("Unexpected error [%s] user=%s", context, user_id)
    return "❌ Произошла ошибка. Попробуйте позже."

import logging

from aiogram import F, Router
from aiogram.types import Message

from bot.services.database import save_activity

router = Router()
logger = logging.getLogger(__name__)

# Ignore very short inputs — likely accidental taps
_MIN_LENGTH = 5


@router.message(F.text)
async def handle_text(message: Message) -> None:
    text = (message.text or "").strip()

    if len(text) < _MIN_LENGTH:
        return

    user_id  = message.from_user.id
    username = message.from_user.username or message.from_user.full_name

    try:
        await save_activity(user_id, username, text)
        await message.answer(
            f"📝 <b>Записано:</b>\n<i>{text}</i>\n\n"
            "Отправьте /analyze для анализа дня.",
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("Text handler error for user %s", user_id)
        await message.answer("❌ Не удалось сохранить запись. Попробуйте ещё раз.")

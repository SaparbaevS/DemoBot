import logging

from aiogram import F, Router
from aiogram.types import Message

from bot.services.database import save_activity
from bot.utils.timezone import now_db, now_str

router = Router()
logger = logging.getLogger(__name__)

_MIN_LENGTH = 5


@router.message(F.text)
async def handle_text(message: Message) -> None:
    text = (message.text or "").strip()

    # Skip commands and very short inputs
    if len(text) < _MIN_LENGTH or text.startswith("/"):
        return

    user_id  = message.from_user.id
    username = message.from_user.username or message.from_user.full_name

    try:
        recorded_at = now_str()
        await save_activity(user_id, username, text, created_at=now_db())
        await message.answer(
            f"📝 <b>Записано в {recorded_at}:</b>\n<i>{text}</i>\n\n"
            "Отправьте /analyze для анализа дня.",
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("Text handler error user=%s", user_id)
        await message.answer("❌ Не удалось сохранить запись. Попробуйте ещё раз.")

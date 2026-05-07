import io
import logging

from aiogram import Bot, F, Router
from aiogram.types import Message
from google.genai.errors import ClientError, ServerError

from bot.services.database import save_activity
from bot.services.gemini_service import transcribe_voice

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.voice)
async def handle_voice(message: Message, bot: Bot) -> None:
    user_id  = message.from_user.id
    username = message.from_user.username or message.from_user.full_name

    status = await message.answer("🎤 Распознаю голосовое сообщение...")

    try:
        file = await bot.get_file(message.voice.file_id)
        buf  = io.BytesIO()
        await bot.download_file(file.file_path, buf)

        text = await transcribe_voice(buf.getvalue())

        if not text:
            await status.edit_text(
                "❌ Не удалось распознать речь. Попробуйте говорить чётче."
            )
            return

        await save_activity(user_id, username, text)

        await status.edit_text(
            f"✅ <b>Записано:</b>\n<i>{text}</i>\n\n"
            "Продолжайте рассказывать о своём дне! "
            "Когда будете готовы — отправьте /analyze",
            parse_mode="HTML",
        )

    except ServerError as e:
        if "503" in str(e) or "UNAVAILABLE" in str(e):
            await status.edit_text(
                "⏳ <b>Серверы Gemini перегружены.</b>\n\nПодождите 30–60 секунд и отправьте сообщение снова.",
                parse_mode="HTML",
            )
        else:
            logger.exception("Gemini server error for user %s", user_id)
            await status.edit_text("❌ Ошибка сервера Gemini. Попробуйте ещё раз.")
    except ClientError as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            await status.edit_text(
                "⚠️ <b>Квота Gemini API исчерпана.</b>\n\nFree tier: 5 запросов/мин, 20 запросов/день.",
                parse_mode="HTML",
            )
        else:
            logger.exception("Gemini API error for user %s", user_id)
            await status.edit_text("❌ Ошибка Gemini API. Попробуйте ещё раз.")
    except Exception:
        logger.exception("Voice handler error for user %s", user_id)
        await status.edit_text("❌ Ошибка при обработке голосового сообщения. Попробуйте ещё раз.")

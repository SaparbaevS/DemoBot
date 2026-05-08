import io
import logging

from aiogram import Bot, F, Router
from aiogram.types import Message
from google.genai.errors import ClientError, ServerError

from bot.services.database import save_activity
from bot.services.gemini_service import transcribe_voice
from bot.utils.error_handler import gemini_error_message
from bot.utils.timezone import now_db, now_str

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.voice)
async def handle_voice(message: Message, bot: Bot) -> None:
    user_id  = message.from_user.id
    username = message.from_user.username or message.from_user.full_name
    status   = None

    try:
        status = await message.answer("🎤 Распознаю голосовое сообщение...")

        file = await bot.get_file(message.voice.file_id)
        buf  = io.BytesIO()
        await bot.download_file(file.file_path, buf)

        text = await transcribe_voice(buf.getvalue())

        if not text:
            await status.edit_text("❌ Не удалось распознать речь. Попробуйте говорить чётче.")
            return

        recorded_at = now_str()
        await save_activity(user_id, username, text, created_at=now_db())

        await status.edit_text(
            f"✅ <b>Записано в {recorded_at}:</b>\n<i>{text}</i>\n\n"
            "Продолжайте рассказывать о своём дне! "
            "Когда будете готовы — отправьте /analyze",
            parse_mode="HTML",
        )

    except (ServerError, ClientError) as e:
        msg   = gemini_error_message(e, context="voice", user_id=user_id)
        reply = status.edit_text if status else message.answer
        await reply(msg, parse_mode="HTML")
    except Exception:
        logger.exception("Unexpected error in voice handler user=%s", user_id)
        reply = status.edit_text if status else message.answer
        await reply("❌ Ошибка при обработке голосового сообщения. Попробуйте ещё раз.")

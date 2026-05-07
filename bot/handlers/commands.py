import logging
from datetime import date

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from google.genai.errors import ClientError, ServerError

from bot.services.database import (
    clear_today_activities,
    get_today_activities,
)
from bot.services.gemini_service import analyze_daily_activities
from bot.utils.formatter import format_summary, format_table

router = Router()
logger = logging.getLogger(__name__)

_WELCOME = (
    "👋 <b>Привет! Я — ваш личный дневник активностей.</b>\n\n"
    "🎤 Отправляйте <b>голосовые сообщения</b> о своих действиях в течение дня.\n"
    "   Я запомню всё, что вы рассказываете.\n\n"
    "💬 Также можно просто написать текстом что вы делали.\n\n"
    "📋 <b>Команды:</b>\n"
    "/analyze — анализ сегодняшних активностей в виде таблицы\n"
    "/clear   — очистить записи за сегодня\n"
    "/help    — справка"
)

_HELP = (
    "ℹ️ <b>Как пользоваться ботом:</b>\n\n"
    "1️⃣ <b>Записывайте активности голосом или текстом</b>\n"
    "   Пример: «Я встал в 8 утра, выпил чай и пошёл на работу»\n\n"
    "2️⃣ <b>Отправляйте несколько сообщений</b> в течение дня — бот копит историю\n\n"
    "3️⃣ <b>/analyze</b> — получите анализ дня в виде таблицы\n\n"
    "💡 <i>Совет: упоминайте время и продолжительность действий для точного анализа</i>"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(_WELCOME, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(_HELP, parse_mode="HTML")


@router.message(Command("analyze"))
async def cmd_analyze(message: Message) -> None:
    user_id = message.from_user.id
    thinking = await message.answer("🔍 Анализирую ваш день, подождите...")

    try:
        raw_activities = await get_today_activities(user_id)

        if not raw_activities:
            await thinking.edit_text(
                "📭 У вас нет записей за сегодня.\n\n"
                "Отправьте голосовое сообщение или напишите, что вы делали!",
                parse_mode="HTML",
            )
            return

        structured = await analyze_daily_activities(raw_activities)

        if not structured:
            await thinking.edit_text(
                "⚠️ Не удалось обработать активности. Попробуйте ещё раз.",
                parse_mode="HTML",
            )
            return

        today_label = date.today().strftime("%d.%m.%Y")
        table   = format_table(structured)
        summary = format_summary(structured, today_label)

        full_text = f"{summary}\n\n{table}"

        # Telegram limit is 4096 chars — send as two messages if needed
        if len(full_text) <= 4096:
            await thinking.edit_text(full_text, parse_mode="HTML")
        else:
            await thinking.edit_text(summary, parse_mode="HTML")
            await message.answer(table, parse_mode="HTML")

    except ServerError as e:
        if "503" in str(e) or "UNAVAILABLE" in str(e):
            await thinking.edit_text(
                "⏳ <b>Серверы Gemini перегружены.</b>\n\nПодождите 30–60 секунд и попробуйте /analyze снова.",
                parse_mode="HTML",
            )
        else:
            logger.exception("Gemini server error in /analyze for user %s", user_id)
            await thinking.edit_text("❌ Ошибка сервера Gemini. Попробуйте позже.")
    except ClientError as e:
        err = str(e)
        if "429" in err or "RESOURCE_EXHAUSTED" in err:
            await thinking.edit_text(
                "⚠️ <b>Квота Gemini API исчерпана.</b>\n\nFree tier: 5 запросов/мин, 20 запросов/день.",
                parse_mode="HTML",
            )
        elif "404" in err or "NOT_FOUND" in err:
            logger.error("Gemini model not found: %s", err)
            await thinking.edit_text(
                "⚠️ <b>Модель Gemini недоступна.</b>\n\nНапишите разработчику.",
                parse_mode="HTML",
            )
        else:
            logger.exception("Gemini API error in /analyze for user %s", user_id)
            await thinking.edit_text("❌ Ошибка Gemini API. Попробуйте позже.")
    except Exception:
        logger.exception("Error in /analyze for user %s", user_id)
        await thinking.edit_text("❌ Произошла ошибка при анализе. Попробуйте позже.")


@router.message(Command("clear"))
async def cmd_clear(message: Message) -> None:
    user_id = message.from_user.id
    deleted = await clear_today_activities(user_id)
    if deleted:
        await message.answer(f"🗑 Удалено {deleted} записей за сегодня.")
    else:
        await message.answer("📭 Записей за сегодня не было.")

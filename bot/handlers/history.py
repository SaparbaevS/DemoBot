import logging
from datetime import date, datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from google.genai.errors import ClientError, ServerError

from bot.services.database import get_activities_by_date
from bot.services.gemini_service import analyze_daily_activities
from bot.utils.error_handler import gemini_error_message
from bot.utils.formatter import format_summary, format_table

router = Router()
logger = logging.getLogger(__name__)


def _history_keyboard() -> InlineKeyboardMarkup:
    yesterday   = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    day_before  = (date.today() - timedelta(days=2)).strftime("%Y-%m-%d")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Вчера",      callback_data=f"history:{yesterday}"),
                InlineKeyboardButton(text="📅 Позавчера",  callback_data=f"history:{day_before}"),
            ]
        ]
    )


@router.message(Command("history"))
async def cmd_history(message: Message) -> None:
    yesterday  = (date.today() - timedelta(days=1)).strftime("%d.%m.%Y")
    day_before = (date.today() - timedelta(days=2)).strftime("%d.%m.%Y")
    await message.answer(
        f"📂 <b>История активностей</b>\n\n"
        f"Выберите день:\n"
        f"  • Вчера — <b>{yesterday}</b>\n"
        f"  • Позавчера — <b>{day_before}</b>",
        reply_markup=_history_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("history:"))
async def cb_history(callback: CallbackQuery) -> None:
    target_date = callback.data.split(":")[1]           # YYYY-MM-DD
    user_id     = callback.from_user.id
    date_label  = datetime.strptime(target_date, "%Y-%m-%d").strftime("%d.%m.%Y")

    await callback.answer()
    thinking = None

    try:
        thinking = await callback.message.answer(
            f"🔍 Загружаю историю за {date_label}..."
        )

        raw_activities = await get_activities_by_date(user_id, target_date)

        if not raw_activities:
            await thinking.edit_text(
                f"📭 За <b>{date_label}</b> записей нет.",
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

        table   = format_table(structured)
        summary = format_summary(structured, date_label)
        full    = f"{summary}\n\n{table}"

        if len(full) <= 4096:
            await thinking.edit_text(full, parse_mode="HTML")
        else:
            await thinking.edit_text(summary, parse_mode="HTML")
            await callback.message.answer(table, parse_mode="HTML")

    except (ServerError, ClientError) as e:
        msg   = gemini_error_message(e, context="history", user_id=user_id)
        reply = thinking.edit_text if thinking else callback.message.answer
        await reply(msg, parse_mode="HTML")
    except Exception:
        logger.exception("History error user=%s", user_id)
        reply = thinking.edit_text if thinking else callback.message.answer
        await reply("❌ Ошибка при загрузке истории. Попробуйте позже.")

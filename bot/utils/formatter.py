import unicodedata

CATEGORY_EMOJI: dict[str, str] = {
    "сон":        "😴",
    "еда":        "🍽",
    "работа":     "💼",
    "отдых":      "🎮",
    "спорт":      "🏃",
    "транспорт":  "🚗",
    "общение":    "💬",
    "другое":     "📌",
}


def _visual_width(text: str) -> int:
    """Return the visual width of a string in a monospace context.
    Wide/fullwidth chars (e.g. CJK) count as 2; everything else as 1.
    Emoji are intentionally excluded from table cells to avoid width ambiguity.
    """
    width = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            width += 2
        else:
            width += 1
    return width


def _pad(text: str, width: int) -> str:
    """Pad text to visual width with spaces."""
    return text + " " * max(0, width - _visual_width(text))


def format_table(activities: list[dict]) -> str:
    """Return a monospace HTML table ready for Telegram (<pre> wrapped)."""
    if not activities:
        return "📭 <i>Нет активностей для отображения.</i>"

    headers = ["Время", "Активность", "Длит.", "Категория"]
    rows: list[list[str]] = []

    for item in activities:
        time_val = str(item.get("time") or "—")
        activity = str(item.get("activity") or "—")
        dur_val  = item.get("duration")
        duration = f"{dur_val} мин" if dur_val else "—"
        cat      = str(item.get("category") or "другое")
        rows.append([time_val, activity, duration, cat])

    # Column widths based on visual width (emoji = 2 chars)
    widths = [_visual_width(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], _visual_width(cell))

    def make_row(cells: list[str]) -> str:
        parts = [_pad(c, widths[i]) for i, c in enumerate(cells)]
        return "│ " + " │ ".join(parts) + " │"

    sep    = "├" + "┼".join("─" * (w + 2) for w in widths) + "┤"
    top    = "┌" + "┬".join("─" * (w + 2) for w in widths) + "┐"
    bottom = "└" + "┴".join("─" * (w + 2) for w in widths) + "┘"

    lines = [top, make_row(headers), sep]
    lines += [make_row(row) for row in rows]
    lines.append(bottom)

    return "<pre>" + "\n".join(lines) + "</pre>"


def format_summary(activities: list[dict], day_label: str) -> str:
    total     = len(activities)
    total_min = sum(a.get("duration") or 0 for a in activities)

    cat_counts: dict[str, int] = {}
    for a in activities:
        cat = a.get("category") or "другое"
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    lines = [f"📅 <b>Анализ дня — {day_label}</b>", ""]

    if total_min:
        h, m     = divmod(total_min, 60)
        time_str = f"{h} ч {m} мин" if h else f"{m} мин"
        lines.append(f"⏱ Суммарное время: <b>{time_str}</b>")

    lines.append(f"📌 Всего активностей: <b>{total}</b>")

    if cat_counts:
        lines.append("")
        lines.append("По категориям:")
        for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
            emoji = CATEGORY_EMOJI.get(cat, "📌")
            lines.append(f"  {emoji} {cat}: {count}")

    return "\n".join(lines)

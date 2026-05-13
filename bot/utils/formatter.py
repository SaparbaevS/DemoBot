import unicodedata

CATEGORY_EMOJI: dict[str, str] = {
    "сон":        "😴",
    "еда":        "🍽",
    "работа":     "💼",
    "отдых":      "🎮",
    "спорт":      "🏃",
    "транспорт":  "🚗",
    "общение":    "💬",
    "покупка":    "🛒",
    "другое":     "📌",
}


def _visual_width(text: str) -> int:
    """Visual width in monospace: wide/fullwidth chars count as 2."""
    width = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            width += 2
        else:
            width += 1
    return width


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _visual_width(text))


def _fmt_amount(amount) -> str:
    """Format number as '50 000 сум'."""
    try:
        return f"{int(amount):,}".replace(",", " ") + " сум"
    except (TypeError, ValueError):
        return "—"


def format_table(activities: list[dict]) -> str:
    """Return a monospace HTML table ready for Telegram (<pre> wrapped)."""
    if not activities:
        return "📭 <i>Нет активностей для отображения.</i>"

    has_amounts = any(a.get("amount") for a in activities)

    headers = ["Время", "Активность", "Длит.", "Категория"]
    if has_amounts:
        headers.append("Сумма")

    rows: list[list[str]] = []
    for item in activities:
        time_val = str(item.get("time") or "—")
        activity = str(item.get("activity") or "—")
        dur_val  = item.get("duration")
        duration = f"{dur_val} мин" if dur_val else "—"
        cat      = str(item.get("category") or "другое")
        row      = [time_val, activity, duration, cat]
        if has_amounts:
            amount = item.get("amount")
            row.append(_fmt_amount(amount) if amount else "—")
        rows.append(row)

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
    total       = len(activities)
    total_min   = sum(a.get("duration") or 0 for a in activities)
    total_spent = sum(a.get("amount") or 0 for a in activities)

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

    if total_spent:
        lines.append(f"💰 Потрачено за день: <b>{_fmt_amount(total_spent)}</b>")

    if cat_counts:
        lines.append("")
        lines.append("По категориям:")
        for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
            emoji = CATEGORY_EMOJI.get(cat, "📌")
            lines.append(f"  {emoji} {cat}: {count}")

    return "\n".join(lines)

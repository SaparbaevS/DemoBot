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


def _pad(text: str, width: int) -> str:
    # CJK / emoji chars are wider — simple left-pad for ASCII-safe columns
    return text.ljust(width)


def format_table(activities: list[dict]) -> str:
    """Return a monospace HTML table ready for Telegram (<pre> wrapped)."""
    if not activities:
        return "📭 <i>Нет активностей для отображения.</i>"

    headers = ["Время", "Активность", "Длит.", "Категория"]
    rows: list[list[str]] = []

    for item in activities:
        time     = str(item.get("time") or "—")
        activity = str(item.get("activity") or "—")
        dur_val  = item.get("duration")
        duration = f"{dur_val} мин" if dur_val else "—"
        cat      = str(item.get("category") or "другое")
        emoji    = CATEGORY_EMOJI.get(cat, "📌")
        rows.append([time, activity, duration, f"{emoji} {cat}"])

    # Column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

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
    total = len(activities)
    total_min = sum(a.get("duration") or 0 for a in activities)

    cat_counts: dict[str, int] = {}
    for a in activities:
        cat = a.get("category") or "другое"
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    lines = [f"📅 <b>Анализ дня — {day_label}</b>", ""]

    if total_min:
        h, m = divmod(total_min, 60)
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

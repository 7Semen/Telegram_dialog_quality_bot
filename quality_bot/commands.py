from aiogram import Router, F
from aiogram.types import Message

from .repo import Repo, date_range_from_args
from .analyzer import analyze_text

router = Router()


def _is_admin(message: Message, admin_ids: set[int]) -> bool:
    return bool(message.from_user) and message.from_user.id in admin_ids

SENTIMENT_RU = {
    "positive": "положительная",
    "neutral": "нейтральная",
    "negative": "негативная",
}

PROBLEM_RU = {
    "ok": "нет нарушений",
    "aggressive_tone": "агрессивный тон",
    "toxic": "токсичность",
    "impolite": "невежливость",
    "unclear": "неясное сообщение",
    "off_topic": "не по теме",
}

@router.message(F.text.regexp(r"^/start(@\w+)?(\s|$)"))
async def cmd_start(message: Message, admin_ids: set[int]):
    is_admin = _is_admin(message, admin_ids)
    role = "админ" if is_admin else "пользователь"
    await message.answer(
        "DialogQualityBot\nЯ работаю ✅\n"
        f"Роль: {role}\n\n"
        "Команды:\n"
        "/start\n/help\n"
        "/history YYYY-MM-DD YYYY-MM-DD [limit]\n"
        "/analyze YYYY-MM-DD YYYY-MM-DD [limit]\n"
        "/issues YYYY-MM-DD YYYY-MM-DD [limit]\n"
        "/report YYYY-MM-DD YYYY-MM-DD"
    )


@router.message(F.text.regexp(r"^/help(@\w+)?(\s|$)"))
async def cmd_help(message: Message):
    await message.answer(
        "Команды:\n"
        "/history YYYY-MM-DD YYYY-MM-DD [limit]\n"
        "/analyze YYYY-MM-DD YYYY-MM-DD [limit]\n"
        "/issues YYYY-MM-DD YYYY-MM-DD [limit]\n"
        "/report YYYY-MM-DD YYYY-MM-DD"
    )


@router.message(F.text.regexp(r"^/history(@\w+)?(\s|$)"))
async def cmd_history(message: Message, repo: Repo, admin_ids: set[int]):
    if not _is_admin(message, admin_ids):
        return await message.answer("Недостаточно прав.")

    parts = message.text.split()
    if len(parts) < 3:
        return await message.answer("Формат: /history YYYY-MM-DD YYYY-MM-DD [limit]")

    d1, d2 = parts[1], parts[2]
    limit = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else 30
    start, end = date_range_from_args(d1, d2)

    rows = await repo.list_messages(message.chat.id, start, end, limit=limit)
    if not rows:
        return await message.answer("Сообщений нет за период.")

    out = []
    for r in rows[-limit:]:
        out.append(f"{r['created_at']:%Y-%m-%d %H:%M} {r['username']}: {r['message_text'][:200]}")
    await message.answer("\n".join(out))


@router.message(F.text.regexp(r"^/analyze(@\w+)?(\s|$)"))
async def cmd_analyze(message: Message, repo: Repo, admin_ids: set[int]):
    if not _is_admin(message, admin_ids):
        return await message.answer("Недостаточно прав.")

    parts = message.text.split()
    if len(parts) < 3:
        return await message.answer("Формат: /analyze YYYY-MM-DD YYYY-MM-DD [limit]")

    d1, d2 = parts[1], parts[2]
    limit = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else 200
    start, end = date_range_from_args(d1, d2)

    rows = await repo.list_messages(message.chat.id, start, end, limit=limit)
    if not rows:
        return await message.answer("Нет сообщений для анализа.")

    analyzed = 0
    problems = 0

    for r in rows:
        txt = r["message_text"] or ""

        # пропускаем команды
        if txt.strip().startswith("/"):
            continue

        sentiment, problem = analyze_text(txt)
        await repo.save_analysis(int(r["message_id"]), sentiment, problem)

        analyzed += 1
        if problem != "ok":
            problems += 1
    
    await message.answer(f"Готово. Проанализировано: {analyzed}. Проблем: {problems}.")


@router.message(F.text.regexp(r"^/issues(@\w+)?(\s|$)"))
async def cmd_issues(message: Message, repo: Repo, admin_ids: set[int]):
    if not _is_admin(message, admin_ids):
        return await message.answer("Недостаточно прав.")

    parts = message.text.split()
    if len(parts) < 3:
        return await message.answer("Формат: /issues YYYY-MM-DD YYYY-MM-DD [limit]")

    d1, d2 = parts[1], parts[2]
    limit = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else 20
    start, end = date_range_from_args(d1, d2)

    rows = await repo.list_issues(message.chat.id, start, end, limit=limit)
    if not rows:
        return await message.answer("Проблем не найдено за период (или анализ ещё не запускали).")

    out = []
    for r in rows:
            sent_ru = SENTIMENT_RU.get(r["sentiment"], r["sentiment"])
            prob_ru = PROBLEM_RU.get(r["detected_problem"], r["detected_problem"])

            out.append(
                f"[{r['analysis_date']:%Y-%m-%d %H:%M}] {r['username']} | "
                f"{sent_ru} | {prob_ru}\n"
                f"msg: {r['message_text'][:220]}"
            )
    await message.answer("\n\n".join(out))


@router.message(F.text.regexp(r"^/report(@\w+)?(\s|$)"))
async def cmd_report(message: Message, repo: Repo, admin_ids: set[int]):
    if not _is_admin(message, admin_ids):
        return await message.answer("Недостаточно прав.")

    parts = message.text.split()
    if len(parts) < 3:
        return await message.answer("Формат: /report YYYY-MM-DD YYYY-MM-DD")

    d1, d2 = parts[1], parts[2]
    start, end = date_range_from_args(d1, d2)

    agg, top = await repo.report(message.chat.id, start, end)
    total = int(agg["total_analyzed"] or 0)
    problems = int(agg["problems"] or 0)

    lines = [
        f"Отчёт за {d1} — {d2}",
        f"Проанализировано: {total}",
        f"Проблемных: {problems}",
        "",
        "Топ проблем:"
    ]
    if top:
        for r in top:
            prob_ru = PROBLEM_RU.get(r["detected_problem"], r["detected_problem"])
            lines.append(f"- {prob_ru}: {int(r['cnt'])}")
    else:
        lines.append("- (нет)")
    await message.answer("\n".join(lines))
from __future__ import annotations

import asyncpg
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

UTC = timezone.utc


def _parse_dt(s: str) -> datetime:
    # формат: YYYY-MM-DD (в твоих командах)
    s = (s or "").strip().strip("\\")
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=UTC)


def date_range_from_args(d1: str, d2: str):
    start = _parse_dt(d1)
    end = _parse_dt(d2) + timedelta(days=1)  # включаем весь день d2
    return start, end


@dataclass
class Repo:
    pool: asyncpg.Pool

    # ---------- справочники ----------
    async def get_role_id(self, role_name: str) -> int:
        q_sel = "SELECT role_id FROM public.user_role WHERE role_name=$1"
        q_ins = "INSERT INTO public.user_role(role_name) VALUES($1) RETURNING role_id"

        async with self.pool.acquire() as con:
            row = await con.fetchrow(q_sel, role_name)
            if row:
                return int(row["role_id"])
            row2 = await con.fetchrow(q_ins, role_name)
            return int(row2["role_id"])

    # ---------- сущности ----------
    async def ensure_chat(self, chat_id: int, chat_name: str) -> None:
        q = """
        INSERT INTO public.chats(chat_id, chat_name)
        VALUES($1, $2)
        ON CONFLICT (chat_id) DO UPDATE
            SET chat_name = EXCLUDED.chat_name
        """

        async with self.pool.acquire() as con:
            await con.execute(q, chat_id, chat_name or "Unnamed chat")

    async def ensure_user(self, tg_user_id: int, username: str | None, role_name: str = "viewer") -> int:
        role_id = await self.get_role_id(role_name)

        q_sel = "SELECT user_id FROM public.users WHERE tg_user_id=$1"
        q_upd = "UPDATE public.users SET username=$2, role_id=$3 WHERE user_id=$1"
        q_ins = """
        INSERT INTO public.users(tg_user_id, username, role_id)
        VALUES ($1, $2, $3)
        RETURNING user_id
        """

        async with self.pool.acquire() as con:
            row = await con.fetchrow(q_sel, tg_user_id)
            if row:
                await con.execute(q_upd, int(row["user_id"]), username or "", role_id)
                return int(row["user_id"])

            row2 = await con.fetchrow(q_ins, tg_user_id, username or "", role_id)
            return int(row2["user_id"])

    async def add_message(
        self,
        chat_id: int,
        user_id: int,
        text: str,
        tg_message_id: int,
        created_at: datetime | None = None,
    ) -> int:
        q = """
        INSERT INTO public.messages(chat_id, user_id, message_text, tg_message_id, created_at)
        VALUES ($1, $2, $3, $4, COALESCE($5, now()))
        ON CONFLICT (chat_id, tg_message_id)
        DO UPDATE SET
            message_text = EXCLUDED.message_text,
            created_at = EXCLUDED.created_at
        RETURNING message_id
        """
        async with self.pool.acquire() as con:
            row = await con.fetchrow(q, chat_id, user_id, text, tg_message_id, created_at)
            return int(row["message_id"])

    # ---------- выборки ----------
    async def list_messages(self, chat_id: int, date_from: datetime, date_to: datetime, limit: int = 200):
        q = """
        SELECT m.message_id, m.message_text, m.created_at, u.username
        FROM public.messages m
        JOIN public.users u ON u.user_id = m.user_id
        WHERE m.chat_id=$1 AND m.created_at >= $2 AND m.created_at < $3
        ORDER BY m.created_at ASC
        LIMIT $4
        """
        async with self.pool.acquire() as con:
            return await con.fetch(q, chat_id, date_from, date_to, limit)

    # ---------- анализ ----------
    async def save_analysis(self, message_id: int, sentiment: str, detected_problem: str) -> None:
        q = """
        INSERT INTO public.analysis_results(message_id, sentiment, detected_problem, analysis_date)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (message_id)
        DO UPDATE SET
          sentiment = EXCLUDED.sentiment,
          detected_problem = EXCLUDED.detected_problem,
          analysis_date = NOW()
        """
        async with self.pool.acquire() as con:
            await con.execute(q, message_id, sentiment, detected_problem)

    async def list_issues(self, chat_id: int, date_from: datetime, date_to: datetime, limit: int = 30):
        q = """
        SELECT ar.analysis_date, ar.sentiment, ar.detected_problem,
               m.message_text, m.created_at, u.username
        FROM public.analysis_results ar
        JOIN public.messages m ON m.message_id = ar.message_id
        JOIN public.users u ON u.user_id = m.user_id
        WHERE m.chat_id=$1
          AND m.created_at >= $2 AND m.created_at < $3
          AND COALESCE(ar.detected_problem,'') <> ''
          AND ar.detected_problem <> 'ok'
        ORDER BY ar.analysis_date DESC
        LIMIT $4
        """
        async with self.pool.acquire() as con:
            return await con.fetch(q, chat_id, date_from, date_to, limit)

    async def report(self, chat_id: int, date_from: datetime, date_to: datetime):
        q_agg = """
        SELECT
          COUNT(*) AS total_analyzed,
          SUM(CASE WHEN COALESCE(ar.detected_problem,'') <> '' AND ar.detected_problem <> 'ok'
                   THEN 1 ELSE 0 END) AS problems
        FROM public.analysis_results ar
        JOIN public.messages m ON m.message_id = ar.message_id
        WHERE m.chat_id=$1 AND m.created_at >= $2 AND m.created_at < $3
        """
        q_top = """
        SELECT ar.detected_problem, COUNT(*) cnt
        FROM public.analysis_results ar
        JOIN public.messages m ON m.message_id = ar.message_id
        WHERE m.chat_id=$1 AND m.created_at >= $2 AND m.created_at < $3
          AND COALESCE(ar.detected_problem,'') <> ''
          AND ar.detected_problem <> 'ok'
        GROUP BY ar.detected_problem
        ORDER BY cnt DESC
        LIMIT 5
        """
        async with self.pool.acquire() as con:
            agg = await con.fetchrow(q_agg, chat_id, date_from, date_to)
            top = await con.fetch(q_top, chat_id, date_from, date_to)
            return agg, top

    async def response_time_stats(self, chat_id: int, start: datetime, end: datetime):
        # “ответ” = первое следующее сообщение ДРУГОГО пользователя (не обязательно Reply)
        q = """
        WITH msgs AS (
          SELECT message_id, user_id, created_at, message_text
          FROM public.messages
          WHERE chat_id = $1
            AND created_at >= $2 AND created_at < $3
            AND message_text NOT LIKE '/%'
        ),
        paired AS (
          SELECT
            m1.message_id,
            EXTRACT(EPOCH FROM (m2.created_at - m1.created_at)) AS response_sec
          FROM msgs m1
          LEFT JOIN LATERAL (
            SELECT created_at
            FROM msgs m2
            WHERE m2.created_at > m1.created_at
              AND m2.user_id <> m1.user_id
            ORDER BY m2.created_at
            LIMIT 1
          ) m2 ON TRUE
        )
        SELECT
          COUNT(*) FILTER (WHERE response_sec IS NOT NULL) AS responded_cnt,
          AVG(response_sec) FILTER (WHERE response_sec IS NOT NULL) AS avg_sec,
          PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY response_sec)
            FILTER (WHERE response_sec IS NOT NULL) AS median_sec
        FROM paired;
        """
        async with self.pool.acquire() as con:
            return await con.fetchrow(q, chat_id, start, end)

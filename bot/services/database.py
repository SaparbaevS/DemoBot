import aiosqlite
from datetime import date

DB_PATH = "activities.db"

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS activities (
    id          INTEGER  PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER  NOT NULL,
    username    TEXT,
    raw_text    TEXT     NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(_CREATE_TABLES)
        await db.commit()


async def save_activity(
    user_id: int, username: str, raw_text: str, created_at: str | None = None
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        if created_at:
            await db.execute(
                "INSERT INTO activities (user_id, username, raw_text, created_at) VALUES (?, ?, ?, ?)",
                (user_id, username, raw_text, created_at),
            )
        else:
            await db.execute(
                "INSERT INTO activities (user_id, username, raw_text) VALUES (?, ?, ?)",
                (user_id, username, raw_text),
            )
        await db.commit()


async def get_today_activities(user_id: int) -> list[dict]:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT id, raw_text, created_at
            FROM activities
            WHERE user_id = ? AND DATE(created_at) = ?
            ORDER BY created_at
            """,
            (user_id, today),
        ) as cursor:
            columns = [col[0] for col in cursor.description]
            rows = await cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]


async def get_activities_by_date(user_id: int, target_date: str) -> list[dict]:
    """target_date format: 'YYYY-MM-DD'"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT id, raw_text, created_at
            FROM activities
            WHERE user_id = ? AND DATE(created_at) = ?
            ORDER BY created_at
            """,
            (user_id, target_date),
        ) as cursor:
            columns = [col[0] for col in cursor.description]
            rows = await cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]


async def clear_today_activities(user_id: int) -> int:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM activities WHERE user_id = ? AND DATE(created_at) = ?",
            (user_id, today),
        )
        await db.commit()
        return cursor.rowcount

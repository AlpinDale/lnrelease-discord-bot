import aiosqlite
import datetime
from datetime import timezone
from pathlib import Path


class BotStorage:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guild_config (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER NOT NULL,
                    timezone TEXT DEFAULT 'UTC'
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS release_state (
                    guild_id INTEGER NOT NULL,
                    release_id TEXT NOT NULL,
                    release_date TEXT NOT NULL,
                    title TEXT NOT NULL,
                    publisher TEXT NOT NULL,
                    volume TEXT NOT NULL,
                    link TEXT NOT NULL,
                    status TEXT NOT NULL,
                    sent_message_id INTEGER,
                    sent_at TEXT,
                    PRIMARY KEY (guild_id, release_id)
                )
            """)

            await db.commit()

    async def set_channel(self, guild_id: int, channel_id: int, timezone: str = "UTC"):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO guild_config (guild_id, channel_id, timezone)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    timezone = excluded.timezone
            """,
                (guild_id, channel_id, timezone),
            )
            await db.commit()

    async def get_guild_config(self, guild_id: int) -> tuple[int, str] | None:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT channel_id, timezone FROM guild_config WHERE guild_id = ?
            """,
                (guild_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return (int(row[0]), str(row[1]))
                return None

    async def get_all_guild_configs(self) -> list[tuple[int, int, str]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT guild_id, channel_id, timezone FROM guild_config"
            ) as cursor:
                rows = await cursor.fetchall()
                return [(int(row[0]), int(row[1]), str(row[2])) for row in rows]

    async def add_release(
        self,
        guild_id: int,
        release_id: str,
        release_date: datetime.date,
        title: str,
        publisher: str,
        volume: str,
        link: str,
        message_id: int | None = None,
    ):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO release_state 
                (guild_id, release_id, release_date, title, publisher, volume, link, status, sent_message_id, sent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'sent', ?, ?)
                ON CONFLICT(guild_id, release_id) DO UPDATE SET
                    sent_message_id = excluded.sent_message_id,
                    sent_at = excluded.sent_at
            """,
                (
                    guild_id,
                    release_id,
                    release_date.isoformat(),
                    title,
                    publisher,
                    volume,
                    link,
                    message_id,
                    datetime.datetime.now(timezone.utc).isoformat(),
                ),
            )
            await db.commit()

    async def is_release_sent(self, guild_id: int, release_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT 1 FROM release_state WHERE guild_id = ? AND release_id = ?
            """,
                (guild_id, release_id),
            ) as cursor:
                return await cursor.fetchone() is not None

    async def mark_done(self, guild_id: int, release_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE release_state SET status = 'done' WHERE guild_id = ? AND release_id = ?
            """,
                (guild_id, release_id),
            )
            await db.commit()

    async def get_uncollected(self, guild_id: int, date: datetime.date | None = None) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            if date:
                query = """
                    SELECT release_id, release_date, title, publisher, volume, link
                    FROM release_state
                    WHERE guild_id = ? AND status = 'sent' AND release_date = ?
                    ORDER BY release_date, title
                """
                params = (guild_id, date.isoformat())
            else:
                query = """
                    SELECT release_id, release_date, title, publisher, volume, link
                    FROM release_state
                    WHERE guild_id = ? AND status = 'sent'
                    ORDER BY release_date, title
                """
                params = (guild_id,)

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "release_id": row[0],
                        "release_date": row[1],
                        "title": row[2],
                        "publisher": row[3],
                        "volume": row[4],
                        "link": row[5],
                    }
                    for row in rows
                ]

    async def get_message_id(self, guild_id: int, release_id: str) -> int | None:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT sent_message_id FROM release_state WHERE guild_id = ? AND release_id = ?
            """,
                (guild_id, release_id),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

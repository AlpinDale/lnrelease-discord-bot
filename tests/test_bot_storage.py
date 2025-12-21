import pytest
import datetime
from lnrelease.bot.storage import BotStorage


@pytest.mark.asyncio
class TestBotStorage:
    async def test_init_db(self, temp_data_dir):
        db_path = temp_data_dir / "test.sqlite"
        storage = BotStorage(db_path)
        await storage.init_db()
        assert db_path.exists()

    async def test_set_and_get_channel(self, temp_data_dir):
        storage = BotStorage(temp_data_dir / "test.sqlite")
        await storage.init_db()

        await storage.set_channel(123456, 789012, "America/New_York")
        config = await storage.get_guild_config(123456)

        assert config is not None
        assert config[0] == 789012
        assert config[1] == "America/New_York"

    async def test_get_nonexistent_guild(self, temp_data_dir):
        storage = BotStorage(temp_data_dir / "test.sqlite")
        await storage.init_db()

        config = await storage.get_guild_config(999999)
        assert config is None

    async def test_add_release(self, temp_data_dir):
        storage = BotStorage(temp_data_dir / "test.sqlite")
        await storage.init_db()

        await storage.add_release(
            guild_id=123,
            release_id="abc123",
            release_date=datetime.date(2024, 12, 25),
            title="Test Book",
            publisher="Test Pub",
            volume="1",
            link="http://example.com",
            message_id=999,
        )

        is_sent = await storage.is_release_sent(123, "abc123")
        assert is_sent

    async def test_is_release_sent_false(self, temp_data_dir):
        storage = BotStorage(temp_data_dir / "test.sqlite")
        await storage.init_db()

        is_sent = await storage.is_release_sent(123, "nonexistent")
        assert not is_sent

    async def test_mark_done(self, temp_data_dir):
        storage = BotStorage(temp_data_dir / "test.sqlite")
        await storage.init_db()

        await storage.add_release(
            guild_id=123,
            release_id="abc123",
            release_date=datetime.date(2024, 12, 25),
            title="Test Book",
            publisher="Test Pub",
            volume="1",
            link="http://example.com",
            message_id=999,
        )

        await storage.mark_done(123, "abc123")

        uncollected = await storage.get_uncollected(123)
        assert len(uncollected) == 0

    async def test_get_uncollected(self, temp_data_dir):
        storage = BotStorage(temp_data_dir / "test.sqlite")
        await storage.init_db()

        await storage.add_release(
            guild_id=123,
            release_id="abc1",
            release_date=datetime.date(2024, 12, 25),
            title="Book 1",
            publisher="Pub",
            volume="1",
            link="http://example.com/1",
            message_id=100,
        )

        await storage.add_release(
            guild_id=123,
            release_id="abc2",
            release_date=datetime.date(2024, 12, 26),
            title="Book 2",
            publisher="Pub",
            volume="2",
            link="http://example.com/2",
            message_id=101,
        )

        await storage.mark_done(123, "abc1")

        uncollected = await storage.get_uncollected(123)
        assert len(uncollected) == 1
        assert uncollected[0]["release_id"] == "abc2"

    async def test_get_uncollected_by_date(self, temp_data_dir):
        storage = BotStorage(temp_data_dir / "test.sqlite")
        await storage.init_db()

        date1 = datetime.date(2024, 12, 25)
        date2 = datetime.date(2024, 12, 26)

        await storage.add_release(123, "abc1", date1, "Book 1", "Pub", "1", "http://ex.com/1", 100)
        await storage.add_release(123, "abc2", date2, "Book 2", "Pub", "2", "http://ex.com/2", 101)

        uncollected = await storage.get_uncollected(123, date1)
        assert len(uncollected) == 1
        assert uncollected[0]["release_date"] == date1.isoformat()

    async def test_get_all_guild_configs(self, temp_data_dir):
        storage = BotStorage(temp_data_dir / "test.sqlite")
        await storage.init_db()

        await storage.set_channel(111, 222, "UTC")
        await storage.set_channel(333, 444, "America/New_York")

        configs = await storage.get_all_guild_configs()
        assert len(configs) == 2

        guild_ids = {c[0] for c in configs}
        assert 111 in guild_ids
        assert 333 in guild_ids

    async def test_update_channel(self, temp_data_dir):
        storage = BotStorage(temp_data_dir / "test.sqlite")
        await storage.init_db()

        await storage.set_channel(123, 456, "UTC")
        await storage.set_channel(123, 789, "America/Chicago")

        config = await storage.get_guild_config(123)
        assert config is not None
        assert config[0] == 789
        assert config[1] == "America/Chicago"

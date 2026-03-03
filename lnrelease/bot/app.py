import asyncio
import datetime
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import discord
from discord import app_commands
from discord.ext import tasks

import lnrelease.parse as parse
import lnrelease.scrape as scrape
from lnrelease.bot.nyaa_search import (
    extract_volume_from_query,
    search_nyaa_with_variants,
)
from lnrelease.bot.releases import get_digital_releases_for_date
from lnrelease.bot.storage import BotStorage
from lnrelease.bot.ui import PaginatedReleasesView, ReleaseView

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("lnrelease.bot")

SCRAPE_INTERVAL_HOURS = float(os.getenv("BOT_SCRAPE_INTERVAL_HOURS", "8"))
DEFAULT_TIMEZONE = os.getenv("BOT_TIMEZONE_DEFAULT", "UTC")

bot_instance = None


class ReleaseBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)
        self.storage: BotStorage = None
        self.executor = ThreadPoolExecutor(max_workers=2)

        global bot_instance
        bot_instance = self

    async def setup_hook(self):
        db_path = os.getenv("BOT_DB_PATH", "./data/bot.sqlite")
        self.storage = BotStorage(db_path)
        await self.storage.init_db()

        logger.info("Registering commands...")
        await self.tree.sync()
        logger.info("Commands synced")

        self.update_loop.change_interval(hours=SCRAPE_INTERVAL_HOURS)
        logger.info(f"Scrape interval set to {SCRAPE_INTERVAL_HOURS} hours")
        self.update_loop.start()

    async def on_ready(self):
        if self.user:
            logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        else:
            logger.info("Logged in (user not available)")
        logger.info("------")

    @tasks.loop(hours=8)
    async def update_loop(self):
        logger.info("Starting update cycle...")

        try:
            await asyncio.get_event_loop().run_in_executor(self.executor, self._run_scrapers)
            logger.info("Scraping and parsing complete")

            await self.post_todays_releases()

        except Exception as e:
            logger.error(f"Error in update loop: {e}", exc_info=True)

    @update_loop.before_loop
    async def before_update_loop(self):
        await self.wait_until_ready()
        logger.info("Running initial update...")
        try:
            await self.update_loop()
        except Exception as e:
            logger.error(f"Error in initial update: {e}", exc_info=True)

    def _run_scrapers(self):
        logger.info("Running scrape.main()...")
        scrape.main()
        logger.info("Running parse.main()...")
        parse.main()

    async def post_todays_releases(self):
        configs = await self.storage.get_all_guild_configs()
        logger.info(f"Found {len(configs)} guild config(s)")

        if not configs:
            logger.warning("No guilds configured. Use /set_channel to configure a channel.")
            return

        for guild_id, channel_id, timezone in configs:
            try:
                await self.post_releases_for_guild(guild_id, channel_id, timezone)
            except Exception as e:
                logger.error(f"Error posting to guild {guild_id}: {e}", exc_info=True)

    async def post_releases_for_guild(self, guild_id: int, channel_id: int, timezone: str):
        import zoneinfo

        tz = zoneinfo.ZoneInfo(timezone)
        today = datetime.datetime.now(tz).date()
        logger.info(f"Checking releases for guild {guild_id}, date {today} (timezone: {timezone})")

        releases = get_digital_releases_for_date(today)
        logger.info(f"Found {len(releases)} digital release(s) for {today}")

        channel = self.get_channel(channel_id)
        if not channel:
            guild = self.get_guild(guild_id)
            if guild:
                channel = guild.get_channel(channel_id)

        if not channel:
            logger.warning(f"Channel {channel_id} not found for guild {guild_id}")
            return

        if not isinstance(channel, discord.TextChannel):
            logger.warning(f"Channel {channel_id} is not a text channel")
            return

        for release in releases:
            if await self.storage.is_release_sent(guild_id, release.release_id):
                continue

            # Secondary check: catch duplicates even if release_id changed
            # (e.g., due to date shift in source data after bot restart)
            if await self.storage.is_release_sent_by_content(
                guild_id, release.name, release.publisher, release.volume
            ):
                logger.info(
                    f"Skipping duplicate (content match): {release.name} vol {release.volume}"
                )
                continue

            embed = discord.Embed(
                title=release.name,
                url=release.link,
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now(),
            )
            embed.add_field(name="Volume", value=release.volume, inline=True)
            embed.add_field(name="Publisher", value=release.publisher, inline=True)
            embed.add_field(
                name="Release Date",
                value=release.date.strftime("%B %d, %Y"),
                inline=True,
            )
            embed.set_footer(text=f"Format: {release.format}")

            view = ReleaseView(release.release_id)

            try:
                message = await channel.send(embed=embed, view=view)
                await self.storage.add_release(
                    guild_id,
                    release.release_id,
                    release.date,
                    release.name,
                    release.publisher,
                    release.volume,
                    release.link,
                    message.id,
                )
                logger.info(f"Posted release {release.name} to guild {guild_id}")
            except Exception as e:
                logger.error(
                    f"Error posting release {release.name} to guild {guild_id}: {e}",
                    exc_info=True,
                )


bot = ReleaseBot()


@bot.tree.command(name="set_channel", description="Set the channel for release notifications")
@app_commands.describe(channel="The channel to send release notifications to")
@app_commands.default_permissions(manage_guild=True)
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.guild_id:
        await interaction.response.send_message(
            "This command can only be used in a server.", ephemeral=True
        )
        return
    await bot.storage.set_channel(interaction.guild_id, channel.id, DEFAULT_TIMEZONE)
    await interaction.response.send_message(
        f"Release notifications will be sent to {channel.mention} (timezone: {DEFAULT_TIMEZONE})",
        ephemeral=True,
    )
    logger.info(f"Guild {interaction.guild_id} set channel to {channel.id}")


@bot.tree.command(name="uncollected", description="Show uncollected releases")
@app_commands.describe(date="Filter by date (YYYY-MM-DD format, optional)")
async def uncollected(interaction: discord.Interaction, date: str | None = None):
    target_date = None
    if date:
        try:
            target_date = datetime.date.fromisoformat(date)
        except ValueError:
            await interaction.response.send_message(
                "Invalid date format. Please use YYYY-MM-DD", ephemeral=True
            )
            return

    if not interaction.guild_id:
        await interaction.response.send_message(
            "This command can only be used in a server.", ephemeral=True
        )
        return

    releases = await bot.storage.get_uncollected(interaction.guild_id, target_date)

    if not releases:
        date_msg = f" for {date}" if date else ""
        await interaction.response.send_message(
            f"No uncollected releases{date_msg}!", ephemeral=True
        )
        return

    embed = discord.Embed(title="Uncollected Releases", color=discord.Color.orange())

    for release in releases[:25]:
        value = f"**Publisher:** {release['publisher']}\n**Volume:** {release['volume']}\n[Link]({release['link']})"
        embed.add_field(
            name=f"{release['release_date']} - {release['title']}",
            value=value,
            inline=False,
        )

    if len(releases) > 25:
        embed.set_footer(text=f"Showing 25 of {len(releases)} uncollected releases")

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="get_releases", description="Show releases for a date or date range")
@app_commands.describe(
    start_date="Start date in YYYY-MM-DD format (required)",
    end_date="End date in YYYY-MM-DD format (optional, defaults to start_date)",
)
async def get_releases(
    interaction: discord.Interaction, start_date: str, end_date: str | None = None
):
    try:
        start = datetime.date.fromisoformat(start_date)
        end = datetime.date.fromisoformat(end_date) if end_date else start
    except ValueError:
        await interaction.response.send_message(
            "Invalid date format. Please use YYYY-MM-DD", ephemeral=True
        )
        return

    if end < start:
        await interaction.response.send_message(
            "End date must be after or equal to start date.", ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:
        all_releases = []
        current_date = start
        while current_date <= end:
            releases = get_digital_releases_for_date(current_date)
            all_releases.extend(releases)
            current_date += datetime.timedelta(days=1)

        if not all_releases:
            date_range_str = (
                f"{start_date} to {end_date}" if end_date and end != start else start_date
            )
            await interaction.followup.send(
                f"No digital releases found for {date_range_str}.", ephemeral=True
            )
            return

        all_releases.sort(key=lambda r: (r.date, r.publisher, r.name))

        date_range_str = f"{start_date} to {end_date}" if end_date and end != start else start_date
        title = f"Releases for {date_range_str}"

        view = PaginatedReleasesView(all_releases, title, per_page=10)
        embed = view.get_embed()
        message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        view.message = message
    except Exception as e:
        logger.error(f"Error in get_releases: {e}", exc_info=True)
        await interaction.followup.send(f"Error fetching releases: {e}", ephemeral=True)


@bot.tree.command(name="resync_today", description="Resend today's releases (admin only)")
@app_commands.default_permissions(administrator=True)
async def resync_today(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    if not interaction.guild_id:
        await interaction.followup.send(
            "This command can only be used in a server.", ephemeral=True
        )
        return

    config = await bot.storage.get_guild_config(interaction.guild_id)
    if not config:
        await interaction.followup.send(
            "No channel configured. Use /set_channel first.", ephemeral=True
        )
        return

    channel_id, timezone = config

    try:
        await bot.post_releases_for_guild(interaction.guild_id, channel_id, timezone)
        await interaction.followup.send("Today's releases have been resynced!", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in resync_today: {e}", exc_info=True)
        await interaction.followup.send(f"Error resyncing: {e}", ephemeral=True)


@bot.tree.command(
    name="nyaa",
    description="Search nyaa.si for torrents in Literature - English-translated category",
)
@app_commands.describe(
    query="Series name and volume (e.g., 'Black Summoner Volume 2' or 'Overlord v5')"
)
async def nyaa_search(interaction: discord.Interaction, query: str):
    await interaction.response.defer(ephemeral=True)

    try:
        series_query, volume = extract_volume_from_query(query)

        results = search_nyaa_with_variants(
            series_query, volume=volume, category="3_1", max_results=10, filter_epub_only=True
        )

        if not results:
            await interaction.followup.send(
                f"No torrents found for '{query}' in Literature - English-translated category.",
                ephemeral=True,
            )
            return

        search_query_display = f"{series_query} {volume}" if volume else series_query
        embed = discord.Embed(
            title=f"Search Results: {query}",
            description=f"Found {len(results)} result{'s' if len(results) != 1 else ''}",
            color=discord.Color.blue(),
            url=f"https://nyaa.si/?q={quote(search_query_display)}&c=3_1",
        )

        for i, torrent in enumerate(results[:10], 1):
            value_parts = [
                f"**Size:** {torrent.size}",
                f"**Seeders:** {torrent.seeders} | **Leechers:** {torrent.leechers}",
            ]

            if torrent.date:
                value_parts.append(f"**Date:** {torrent.date.strftime('%Y-%m-%d')}")

            value_parts.append(f"[View on Nyaa](https://nyaa.si/view/{torrent.id})")

            if torrent.magnet:
                value_parts.append(f"[Magnet Link]({torrent.magnet})")

            embed.add_field(
                name=f"{i}. {torrent.name[:256]}",
                value="\n".join(value_parts),
                inline=False,
            )

        if len(results) == 10:
            embed.set_footer(text="Showing first 10 results")

        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"Error in nyaa_search: {e}", exc_info=True)
        await interaction.followup.send(f"Error searching nyaa.si: {e}", ephemeral=True)


def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN environment variable not set")
        sys.exit(1)

    assert token is not None
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()

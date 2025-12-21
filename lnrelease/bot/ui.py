import discord


class DoneButton(discord.ui.Button):
    def __init__(self, release_id: str):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Done",
            custom_id=f"done_{release_id}",
        )
        self.release_id = release_id

    async def callback(self, interaction: discord.Interaction):
        from .app import bot_instance

        if not bot_instance or not bot_instance.storage:
            await interaction.response.send_message("Bot storage not available", ephemeral=True)
            return

        await bot_instance.storage.mark_done(interaction.guild_id, self.release_id)

        self.disabled = True
        self.label = "✓ Done"
        await interaction.response.edit_message(view=self.view)


class ReleaseView(discord.ui.View):
    def __init__(self, release_id: str):
        super().__init__(timeout=None)
        self.add_item(DoneButton(release_id))


class PaginatedReleasesView(discord.ui.View):
    def __init__(self, releases: list, title: str, per_page: int = 10):
        super().__init__(timeout=300)
        self.releases = releases
        self.title = title
        self.per_page = per_page
        self.current_page = 0
        self.total_pages = (len(releases) + per_page - 1) // per_page
        self.message = None
        self.update_buttons()

    def update_buttons(self):
        self.first_button.disabled = self.current_page == 0
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
        self.last_button.disabled = self.current_page >= self.total_pages - 1

    def get_embed(self) -> discord.Embed:
        start_idx = self.current_page * self.per_page
        end_idx = min(start_idx + self.per_page, len(self.releases))
        page_releases = self.releases[start_idx:end_idx]

        embed = discord.Embed(
            title=self.title,
            description=f"Found {len(self.releases)} digital release(s)",
            color=discord.Color.blue(),
        )

        for release in page_releases:
            value = (
                f"**Date:** {release.date.isoformat()}\n"
                f"**Publisher:** {release.publisher}\n"
                f"**Volume:** {release.volume}\n"
                f"**Format:** {release.format.name}\n"
                f"[Link]({release.link})"
            )
            embed.add_field(
                name=release.name,
                value=value,
                inline=False,
            )

        embed.set_footer(text=f"Page {self.current_page + 1} of {self.total_pages}")
        return embed

    @discord.ui.button(label="⏮", style=discord.ButtonStyle.secondary)
    async def first_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="⏭", style=discord.ButtonStyle.secondary)
    async def last_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.total_pages - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

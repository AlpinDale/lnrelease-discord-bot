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

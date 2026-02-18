# cogs/core/views.py
import discord
from . import database

class ConfirmCancelView(discord.ui.View):
    def __init__(self, log_id: int):
        super().__init__(timeout=30)
        self.log_id = log_id

    @discord.ui.button(label="确认删除", style=discord.ButtonStyle.danger, custom_id="confirm_delete")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        database.delete_poop_log(self.log_id)
        await interaction.response.edit_message(content="✅ **记录已删除，就当无事发生。**", view=None)
        self.stop()

    @discord.ui.button(label="手滑了", style=discord.ButtonStyle.secondary, custom_id="cancel_delete")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="操作已取消，记录被抢救了回来！", view=None)
        self.stop()

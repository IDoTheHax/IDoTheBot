import discord
from discord import app_commands
from discord.ext import commands
import json
import os

class JoinAndLeave(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = 'settings/join_leave_settings.json'
        self.guild_settings = self.load_settings()

    def load_settings(self):
        if not os.path.exists(self.settings_file):
            return {}
        with open(self.settings_file, 'r') as f:
            return json.load(f)

    def save_settings(self):
        with open(self.settings_file, 'w') as f:
            json.dump(self.guild_settings, f, indent=4)

    def get_guild_settings(self, guild_id):
        return self.guild_settings.setdefault(str(guild_id), {
            "join_message": "Welcome {user}!",
            "leave_message": "Goodbye {user}!",
            "notify_join": True,
            "notify_leave": True
        })
        
    @app_commands.command(name='set_join_channel')
    async def set_join_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild_id = interaction.guild.id
        settings = self.get_guild_settings(guild_id)
        settings["join_channel_id"] = channel.id
        self.save_settings()
        await interaction.response.send_message(f"Join channel set to {channel.mention}", ephemeral=True)

    @app_commands.command(name='set_leave_channel')
    async def set_leave_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild_id = interaction.guild.id
        settings = self.get_guild_settings(guild_id)
        settings["leave_channel_id"] = channel.id
        self.save_settings()
        await interaction.response.send_message(f"Leave channel set to {channel.mention}", ephemeral=True)


    @app_commands.command(name='set_join_message')
    async def set_join_message(self, interaction: discord.Interaction, message: str):
        guild_id = interaction.guild.id
        settings = self.get_guild_settings(guild_id)
        settings["join_message"] = message
        self.save_settings()
        await interaction.response.send_message("Join message updated!", ephemeral=True)

    @app_commands.command(name='set_leave_message')
    async def set_leave_message(self, interaction: discord.Interaction, message: str):
        guild_id = interaction.guild.id
        settings = self.get_guild_settings(guild_id)
        settings["leave_message"] = message
        self.save_settings()
        await interaction.response.send_message("Leave message updated!", ephemeral=True)

    @app_commands.command(name='toggle_join_notifications')
    async def toggle_join_notifications(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        settings = self.get_guild_settings(guild_id)
        settings["notify_join"] = not settings["notify_join"]
        self.save_settings()
        state = "enabled" if settings["notify_join"] else "disabled"
        await interaction.response.send_message(f"Join notifications {state}!", ephemeral=True)

    @app_commands.command(name='toggle_leave_notifications')
    async def toggle_leave_notifications(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        settings = self.get_guild_settings(guild_id)
        settings["notify_leave"] = not settings["notify_leave"]
        self.save_settings()
        state = "enabled" if settings["notify_leave"] else "disabled"
        await interaction.response.send_message(f"Leave notifications {state}!", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        settings = self.get_guild_settings(member.guild.id)
        if "join_channel_id" in settings and settings["notify_join"]:
            channel = self.bot.get_channel(settings["join_channel_id"])
            if channel:
                message = settings["join_message"].format(user=member.mention)
                await channel.send(message)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        settings = self.get_guild_settings(member.guild.id)
        if "leave_channel_id" in settings and settings["notify_leave"]:
            channel = self.bot.get_channel(settings["leave_channel_id"])
            if channel:
                message = settings["leave_message"].format(user=member.mention)
                await channel.send(message)

async def setup(bot):
    await bot.add_cog(JoinAndLeave(bot))

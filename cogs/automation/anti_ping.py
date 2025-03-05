import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
import json
import os

class AutoMute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mute_duration = timedelta(minutes=5)
        self.settings_path = 'settings/'
        self.load_all_settings()

    def load_all_settings(self):
        self.protected_users = self.load_json('ping_blacklist.json')
        self.anti_ping_status = self.load_json('config.json')

    def load_json(self, filename):
        filepath = os.path.join(self.settings_path, filename)
        try:
            return json.load(open(filepath, 'r'))
        except FileNotFoundError:
            print(f"{filename} not found, creating an empty structure.")
            return {}

    def save_json(self, data, filename):
        filepath = os.path.join(self.settings_path, filename)
        json.dump(data, open(filepath, 'w'), indent=4)

    def get_guild_settings(self, guild_id):
        guild_id_str = str(guild_id)
        if guild_id_str not in self.protected_users:
            self.protected_users[guild_id_str] = {"protected_users": []}
        if guild_id_str not in self.anti_ping_status:
            self.anti_ping_status[guild_id_str] = {"anti_ping_enabled": True}

    def add_protected_user(self, guild_id, user_id):
        self.get_guild_settings(guild_id)
        guild_id_str = str(guild_id)
        if user_id not in self.protected_users[guild_id_str]["protected_users"]:
            self.protected_users[guild_id_str]["protected_users"].append(user_id)
            self.save_json(self.protected_users, 'ping_blacklist.json')

    def is_anti_ping_enabled(self, guild_id):
        self.get_guild_settings(guild_id)
        return self.anti_ping_status[str(guild_id)]["anti_ping_enabled"]

    def set_anti_ping(self, guild_id, status):
        self.get_guild_settings(guild_id)
        self.anti_ping_status[str(guild_id)]["anti_ping_enabled"] = status
        self.save_json(self.anti_ping_status, 'config.json')

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user or not message.guild:
            return
        if not self.is_anti_ping_enabled(message.guild.id):
            return
        guild_id_str = str(message.guild.id)
        protected_users = self.protected_users.get(guild_id_str, {}).get("protected_users", [])
        for user in message.mentions:
            if user.id in protected_users:
                try:
                    await message.author.timeout(self.mute_duration, reason="Pinging a user")
                    await message.channel.send(f"{message.author.mention} You are not allowed to ping this user.")
                except discord.Forbidden:
                    await message.channel.send(f"I don't have permission to timeout {message.author.mention}.")
                except discord.HTTPException:
                    await message.channel.send(f"Failed to mute {message.author.mention} due to an error.")

    anti_ping = app_commands.Group(name="anti_ping", description="Manage anti-ping settings")

    @anti_ping.command(name="add_protected")
    @commands.has_permissions(administrator=True)
    async def add_protected(self, interaction: discord.Interaction, user: discord.Member):
        self.add_protected_user(interaction.guild.id, user.id)
        await interaction.response.send_message(f"{user.mention} has been added to the protected list.")

    @anti_ping.command(name="remove_protected")
    @commands.has_permissions(administrator=True)
    async def remove_protected(self, interaction: discord.Interaction, user: discord.Member):
        guild_id = str(interaction.guild.id)
        if guild_id in self.protected_users and user.id in self.protected_users[guild_id]:
            self.protected_users[guild_id].remove(user.id)
            self.save_json(self.protected_users, 'ping_blacklist.json')
            await interaction.send(f"{user.mention} has been removed from the protected list.")
        else:
            await interaction.send(f"{user.mention} is not on the protected list.")

    @anti_ping.command(name="toggle_anti_ping")
    @commands.has_permissions(administrator=True)
    async def toggle_anti_ping(self, interaction: discord.Interaction, status: bool):
        self.set_anti_ping(interaction.guild.id, status)
        await interaction.response.send_message(f"Anti-ping functionality has been {'enabled' if status else 'disabled'}.")

    def disable_anti_ping(self, guild_id):
        """Disable anti-ping functionality for a specific guild."""
        self.set_anti_ping(guild_id, False)

    def enable_anti_ping(self, guild_id):
        """Enable anti-ping functionality for a specific guild."""
        self.set_anti_ping(guild_id, True)

async def setup(bot):
    await bot.add_cog(AutoMute(bot))
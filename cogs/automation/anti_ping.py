import discord
from discord.ext import commands
from datetime import timedelta
import json
import os

class AutoMute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mute_duration = timedelta(minutes=5)
        self.settings_path = 'settings/'  # Ensure this matches your settings directory
        self.load_all_settings()

    def load_all_settings(self):
        """Load all settings for protected users and anti-ping status per guild."""
        self.protected_users = self.load_json('ping_blacklist.json')
        self.anti_ping_status = self.load_json('config.json')

    def load_json(self, filename):
        """Load data from a JSON file."""
        filepath = os.path.join(self.settings_path, filename)
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"{filename} not found, creating an empty structure.")
            return {}

    def save_json(self, data, filename):
        """Save data to a JSON file."""
        filepath = os.path.join(self.settings_path, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)

    def get_guild_settings(self, guild_id):
        """Retrieve or initialize settings for a specific guild."""
        guild_id_str = str(guild_id)
        if guild_id_str not in self.protected_users:
            self.protected_users[guild_id_str] = {"protected_users": []}
        if guild_id_str not in self.anti_ping_status:
            self.anti_ping_status[guild_id_str] = {"anti_ping_enabled": True}

    def add_protected_user(self, guild_id, user_id):
        """Add a user to the protected list for a specific guild."""
        self.get_guild_settings(guild_id)
        guild_id_str = str(guild_id)
        if user_id not in self.protected_users[guild_id_str]["protected_users"]:
            self.protected_users[guild_id_str]["protected_users"].append(user_id)
            self.save_json(self.protected_users, 'ping_blacklist.json')

    def is_anti_ping_enabled(self, guild_id):
        """Check if anti-ping is enabled for a specific guild."""
        self.get_guild_settings(guild_id)
        return self.anti_ping_status[str(guild_id)]["anti_ping_enabled"]

    def set_anti_ping(self, guild_id, status):
        """Enable or disable anti-ping for a specific guild."""
        self.get_guild_settings(guild_id)
        self.anti_ping_status[str(guild_id)]["anti_ping_enabled"] = status
        self.save_json(self.anti_ping_status, 'config.json')

    @commands.Cog.listener()
    async def on_message(self, message):
        """Check for pings in a message and mute the sender."""
        if message.author == self.bot.user or not message.guild:
            return  # Ignore bot's own messages and DMs

        if not self.is_anti_ping_enabled(message.guild.id):
            return  # Skip if anti_ping is disabled for this guild

        # Check if the message mentions anyone
        guild_id_str = str(message.guild.id)
        protected_users = self.protected_users.get(guild_id_str, {}).get("protected_users", [])

        for mentioned_user in message.mentions:
            # Timeout the author for 5 minutes if they ping a protected user
            if mentioned_user.id in protected_users:
                try:
                    await message.author.timeout(self.mute_duration, reason="Pinging a user")
                    await message.channel.send(f"{message.author.mention} You are not allowed to ping this user.")
                except discord.Forbidden:
                    await message.channel.send(f"I don't have permission to timeout {message.author.mention}.")
                except discord.HTTPException:
                    await message.channel.send(f"Failed to mute {message.author.mention} due to an error.")

    @discord.app_commands.command(name="add_protected", description="Add a user to the protected list (for administrators)")
    @commands.has_permissions(administrator=True)
    async def add_protected(self, interaction: discord.Interaction, user: discord.Member):
        """Add a user to the protected list for this guild."""
        self.add_protected_user(interaction.guild.id, user.id)
        await interaction.response.send_message(f"{user.mention} has been added to the protected list.")

    @discord.app_commands.command(name="remove_protected", description="Remove a user from the protected list (for administrators).")
    @commands.has_permissions(administrator=True)
    async def remove_protected(self, interaction: discord.Interaction, user: discord.Member):
        guild_id = str(interaction.guild.id)
        if guild_id in self.protected_users and user.id in self.protected_users[guild_id]:
            self.protected_users[guild_id].remove(user.id)
            self.save_ping_blacklist()
            await interaction.send(f"{user.mention} has been removed from the protected list.")
        else:
            await interaction.send(f"{user.mention} is not on the protected list.")

    @discord.app_commands.command(name="toggle_anti_ping", description="Toggle anti-ping functionality for this guild")
    @commands.has_permissions(administrator=True)
    async def toggle_anti_ping(self, interaction: discord.Interaction, status: bool):
        """Enable or disable the anti-ping functionality for the guild."""
        self.set_anti_ping(interaction.guild.id, status)
        await interaction.response.send_message(f"Anti-ping functionality has been {'enabled' if status else 'disabled'}.")

async def setup(bot):
    await bot.add_cog(AutoMute(bot))

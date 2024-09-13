import discord
from discord.ext import commands
import asyncio
from datetime import timedelta
import json
import os

MUTED_USERS = {}

class AutoMute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mute_duration = timedelta(minutes=5)
        self.protected_users = self.load_ping_blacklist()  # Load protected user IDs from JSON

    def load_ping_blacklist(self):
        """Load the list of protected user IDs from a JSON file."""
        try:
            with open('ping_blacklist.json', 'r') as f:
                data = json.load(f)
                return set(data.get('ping_blacklist', []))  # Use a set for quick lookup
        except FileNotFoundError:
            print("ping_blacklist.json not found, creating an empty list.")
            return set()

    @commands.Cog.listener()
    async def on_message(self, message):
        """Check for pings in a message and mute the sender."""
        if message.author == self.bot.user or not message.guild:
            return  # Ignore bot's own messages and DMs

        # Check if the message mentions anyone
        for mentioned_user in message.mentions:
            # Bypass for moderators or a specific user ID (e.g., an admin)
            #if message.author.guild_permissions.manage_messages or message.author.id == 987323487343493110: # 987323487343493191:  # Replace with actual user ID
            #    return

            # Apply timeout (mute) to the user for 5 minutes
            if mentioned_user.id in self.protected_users:
                    # Timeout the author for 5 minutes if they ping a protected user
                try:
                    await message.author.timeout(self.mute_duration, reason="Pinging a user")
                    await message.channel.send(f"{message.author.mention} You are not allowed to ping this user.")
                except discord.Forbidden:
                    await message.channel.send(f"I don't have permission to timeout {message.author.mention}.")
                except discord.HTTPException:
                    await message.channel.send(f"Failed to mute {message.author.mention} due to an error.")


async def setup(bot):
    await bot.add_cog(AutoMute(bot))

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
        self.anti_ping_enabled = True  # Variable to enable/disable anti_ping

    def load_ping_blacklist(self):
        """Load the list of protected user IDs from a JSON file."""
        try:
            with open('ping_blacklist.json', 'r') as f:
                data = json.load(f)
                return set(data.get('ping_blacklist', []))  # Use a set for quick lookup
        except FileNotFoundError:
            print("ping_blacklist.json not found, creating an empty list.")
            return set()

    def disable_anti_ping(self):
        """Disable the anti-ping functionality."""
        self.anti_ping_enabled = False
        print("Anti-ping functionality has been disabled.")

    def enable_anti_ping(self):
        """Enable the anti-ping functionality."""
        self.anti_ping_enabled = True
        print("Anti-ping functionality has been enabled.")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Check for pings in a message and mute the sender."""
        if message.author == self.bot.user or not message.guild:
            return  # Ignore bot's own messages and DMs

        if not self.anti_ping_enabled:
            return  # Skip if anti_ping is disabled


        # Check if the message mentions anyone
        for mentioned_user in message.mentions:
            # Bypass for moderators or a specific user ID (e.g., an admin)
            #if message.author.guild_permissions.manage_messages or message.author.id == 987323487343493110: # 987323487343493191:  # Replace with actual user ID
            #    return

            # Apply timeout (mute) to the user for 5 minutes
            if mentioned_user.id in self.protected_users:
                    # Timeout the author for 5 minutes if they ping a protected user
                try:
                    await message.author.timeout(self.mute_du   ration, reason="Pinging a user")
                    await message.channel.send(f"{message.author.mention} You are not allowed to ping this user.")
                except discord.Forbidden:
                    await message.channel.send(f"I don't have permission to timeout {message.author.mention}.")
                except discord.HTTPException:
                    await message.channel.send(f"Failed to mute {message.author.mention} due to an error.")


    @commands.command(name="forceunmute", help="Force unmute a user before the time expires (for moderators)")
    @commands.has_permissions(manage_messages=True)
    async def force_unmute(self, ctx, user: discord.Member):
        """Unmute the user manually (only for moderators)."""
        if user.id in MUTED_USERS:
            del MUTED_USERS[user.id]
            await ctx.send(f"{user.mention} has been manually unmuted by {ctx.author.mention}.")
        else:
            await ctx.send(f"{user.mention} is not currently muted.")

async def setup(bot):
    await bot.add_cog(AutoMute(bot))

import discord
from discord.ext import commands
import asyncio
from datetime import timedelta

MUTED_USERS = {}

class AutoMute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mute_duration = timedelta(minutes=5)

    async def mute_user(self, message, reason="Pinging a user"):
        """Mute the user for 5 minutes."""
        user = message.author
        if user.id in MUTED_USERS:
            return  # User is already muted

        # Mute the user
        MUTED_USERS[user.id] = discord.utils.utcnow()
        await message.channel.send(f"{user.mention} has been muted for 5 minutes for {reason}.")
  
        # Wait for 5 minutes
        await asyncio.sleep(self.mute_duration)

        # Unmute the user after 5 minutes
        if user.id in MUTED_USERS:
            del MUTED_USERS[user.id]
            await message.channel.send(f"{user.mention} has been unmuted.")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Check for pings in a message and mute the sender."""
        if message.author == self.bot.user or not message.guild:
            return  # Ignore bot's own messages and DMs

        # Check if the user is already muted
        if message.author.id in MUTED_USERS:
            await message.delete()
            await message.channel.send(f"{message.author.mention}, you are muted and cannot send messages.")
            return

        # Check if the message mentions anyone
        if message.mentions:
            # Bypass for moderators or a specific user ID (e.g., an admin)
            #if message.author.guild_permissions.manage_messages or message.author.id == 987323487343493110: # 987323487343493191:  # Replace with actual user ID
            #    return

            # Apply timeout (mute) to the user for 5 minutes
            try:
                await message.author.timeout(self.mute_duration, reason="Pinging a user")
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

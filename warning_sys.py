import discord
from discord.ext import commands

class WarningSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warnings = {}  # Store warnings for each guild and user

    @discord.app_commands.command(name='warn')
    @commands.has_permissions(manage_messages=True)  # Only allow users with manage messages permission to use this command
    async def warn(self, ctx, member: discord.Member, *, reason: str = None):
        """Warn a user and send them a DM."""
        guild_id = ctx.guild.id
        user_id = member.id

        # Initialize warnings for the guild if it doesn't exist
        if guild_id not in self.warnings:
            self.warnings[guild_id] = {}

        # Initialize warnings for the user if they don't exist
        if user_id not in self.warnings[guild_id]:
            self.warnings[guild_id][user_id] = 0

        # Increment the user's warnings
        self.warnings[guild_id][user_id] += 1
        warning_count = self.warnings[guild_id][user_id]

        # Send a DM to the user
        try:
            await member.send(f"You have been warned in **{ctx.guild.name}**. Reason: {reason or 'No reason provided.'} (Warning #{warning_count})")
            await ctx.response.send_message(f"{member} has been warned. Reason: {reason or 'No reason provided.'} (Warning #{warning_count})")
        except discord.Forbidden:
            await ctx.response.send_message(f"Could not send a DM to {member.mention}. They may have DMs disabled. Let this public shaming be a lesson to everyone")

    @discord.app_commands.command(name='warnings', description="View warnings for a user")
    async def warnings(self, ctx, member: discord.Member):
        """Check the number of warnings a user has."""
        guild_id = ctx.guild.id
        user_id = member.id

        if guild_id in self.warnings and user_id in self.warnings[guild_id]:
            count = self.warnings[guild_id][user_id]
            await ctx.response.send_message(f"{member} has {count} warning(s).")
        else:
            await ctx.response.send_message(f"{member} has no warnings. He has been a very good member")

    @discord.app_commands.command(name='clear_warnings', description="Clear Warnings if they've behaved nicely")
    @commands.has_permissions(manage_messages=True)
    async def clear_warnings(self, ctx, member: discord.Member):
        """Clear all warnings for a user."""
        guild_id = ctx.guild.id
        user_id = member.id

        if guild_id in self.warnings and user_id in self.warnings[guild_id]:
            del self.warnings[guild_id][user_id]
            await ctx.response.send_message(f"Cleared all warnings for {member.mention}.")
        else:
            await ctx.response.send_message(f"{member} has no warnings to clear.")

# Setup function to add the cog to the bot
async def setup(bot: commands.Bot):
    await bot.add_cog(WarningSystem(bot))

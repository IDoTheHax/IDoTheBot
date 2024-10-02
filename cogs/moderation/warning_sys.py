import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from cogs.moderation.moderation import Moderation

class WarningSystem(commands.Cog):
    MAX_WARNINGS_BEFORE_KICK = 5  # Number of warnings before a user gets kicked
    WARNINGS_FILE = 'warnings.json'  # Path to the JSON file

    def __init__(self, bot):
        self.bot = bot
        self.warnings = self.load_warnings()  # Load warnings from the JSON file

    def load_warnings(self):
        """Load warnings from the JSON file."""
        if os.path.exists(self.WARNINGS_FILE):
            with open(self.WARNINGS_FILE, 'r') as f:
                return json.load(f)
        return {}

    def save_warnings(self):
        """Save warnings to the JSON file."""
        with open(self.WARNINGS_FILE, 'w') as f:
            json.dump(self.warnings, f, indent=4)

    @app_commands.command(name='warn', description="Warn a user")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        """Warn a user and send them a DM. Kick them if warnings exceed a threshold."""
        guild_id = str(interaction.guild.id)  # Store as string for JSON compatibility
        user_id = str(member.id)

        # Initialize warnings for the guild if it doesn't exist
        if guild_id not in self.warnings:
            self.warnings[guild_id] = {}

        # Initialize warnings for the user if they don't exist
        if user_id not in self.warnings[guild_id]:
            self.warnings[guild_id][user_id] = 0

        # Increment the user's warnings
        self.warnings[guild_id][user_id] += 1
        warning_count = self.warnings[guild_id][user_id]

        # Save the updated warnings to the file
        self.save_warnings()

        # Send a DM to the user
        try:
            await member.send(f"You have been warned in **{interaction.guild.name}**. Reason: {reason or 'No reason provided.'} (Warning #{warning_count})")
            await interaction.response.send_message(f"{member.mention} has been warned. Reason: {reason or 'No reason provided.'} (Warning #{warning_count})")
        except discord.Forbidden:
            await interaction.response.send_message(f"Could not send a DM to {member.mention}. They may have DMs disabled.", ephemeral=True)

        # Check if the user has reached the maximum number of warnings
        if warning_count >= self.MAX_WARNINGS_BEFORE_KICK:
            try:
                await member.kick(reason=f"Reached {warning_count} warnings. You are always able to rejoin")
                await interaction.followup.send(f"{member.mention} has been kicked for reaching {warning_count} warnings.")
            except discord.Forbidden:
                await interaction.followup.send(f"I don't have permission to kick {member.mention}.", ephemeral=True)

    
    @app_commands.command(name='warnings', description="Check warnings of a user")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        """Check the number of warnings a user has."""
        guild_id = str(interaction.guild.id)
        user_id = str(member.id)

        if guild_id in self.warnings and user_id in self.warnings[guild_id]:
            count = self.warnings[guild_id][user_id]
            await interaction.response.send_message(f"{member.mention} has {count} warning(s).")
        else:
            await interaction.response.send_message(f"{member.mention} has no warnings.")

    @app_commands.command(name='clear_warnings', description="Clear warnings for a user")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear_warnings(self, interaction: discord.Interaction, member: discord.Member):
        """Clear all warnings for a user."""
        guild_id = str(interaction.guild.id)
        user_id = str(member.id)

        if guild_id in self.warnings and user_id in self.warnings[guild_id]:
            del self.warnings[guild_id][user_id]
            # If no users remain in the guild, remove the guild entry
            if not self.warnings[guild_id]:
                del self.warnings[guild_id]

            # Save the updated warnings to the file
            self.save_warnings()
            await interaction.response.send_message(f"Cleared all warnings for {member.mention}.")
        else:
            await interaction.response.send_message(f"{member.mention} has no warnings to clear.")

# Error handling
@WarningSystem.warn.error
@Moderation.kick.error
async def command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You do not have the required permissions to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)

# Setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(WarningSystem(bot))

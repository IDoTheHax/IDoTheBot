import discord
from discord import app_commands
from discord.ext import commands
import datetime as dt

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="delete", description="Delete a message by ID")
    @app_commands.describe(message_id="ID of the message to delete")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def delete_message(self, interaction: discord.Interaction, message_id: str):
        try:
            message = await interaction.channel.fetch_message(int(message_id))
            await message.delete()
            await interaction.response.send_message("Message deleted.", ephemeral=True)
        except discord.errors.NotFound:
            await interaction.response.send_message("Message not found.", ephemeral=True)
        except discord.errors.Forbidden:
            await interaction.response.send_message("I don't have permission to delete that message.", ephemeral=True)
    
    @app_commands.command(name="edit", description="Edit a message by ID")
    @app_commands.describe(message_id="ID of the message to edit")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def edit_message(self, interaction: discord.Interaction, message_id: str):
        try:
            message = await interaction.channel.fetch_message(int(message_id))
            await message.edit(content='This message has been edited.')
            await interaction.response.send_message("Message edited.", ephemeral=True)
        except discord.errors.NotFound:
            await interaction.response.send_message("Message not found.", ephemeral=True)
        except discord.errors.Forbidden:
            await interaction.response.send_message("I don't have permission to edit that message.", ephemeral=True)


    @app_commands.command(name="ban", description="Ban a user")
    @app_commands.describe(user="User to ban", reason="Reason for the ban")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban_user(self, interaction: discord.Interaction, user: discord.User, reason: str = "No reason provided"):
        try:
            # Send a DM to the user explaining the ban
            await user.send(f"You have been banned from {interaction.guild.name} for the following reason: {reason}")
        except discord.errors.Forbidden:
            await interaction.response.send_message(f"Could not send DM to {user.mention}, but proceeding with the ban.", ephemeral=True)

        await interaction.guild.ban(user, reason=reason)
        await interaction.response.send_message(f"{user.mention} has been banned.", ephemeral=True)

    @app_commands.command(name="mute", description="Mute a user")
    @app_commands.describe(user="User to mute", duration="Duration in minutes", reason="Reason for the mute")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, user: discord.User, duration: int, reason: str = "No reason provided"):
        if duration <= 0:
            await interaction.response.send_message("Duration must be greater than 0.", ephemeral=True)
            return

        try:
            # Set the mute duration (in seconds)
            mute_duration = dt.timedelta(minutes=duration)
            await user.timeout(mute_duration, reason="Muted by moderator")

            await interaction.response.send_message(f"{user.mention} has been muted for {duration} minutes.")
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to mute this user.", ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message("An error occurred while muting the user.", ephemeral=True)

    @app_commands.command(name='kick', description="Kick a user")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        """Kick a user from the server."""
        if member.guild_permissions.administrator:
            await interaction.response.send_message(f"{member.mention} cannot be kicked because they are an administrator.", ephemeral=True)
            return

        try:
            await member.kick(reason=reason)
            await interaction.response.send_message(f"{member.mention} has been kicked. Reason: {reason or 'No reason provided.'}")
        except discord.Forbidden:
            await interaction.response.send_message(f"I don't have permission to kick {member.mention}.", ephemeral=True)

    @app_commands.command(name="lock_channel", description="Lock the channel so only admins can talk")
    @app_commands.checks.has_permissions(administrator=True)
    async def lock_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        if channel is None:
            channel = interaction.channel

        everyone_role = interaction.guild.default_role
                
        # Set the permissions so that @everyone cannot send messages in the channel
        await channel.set_permissions(everyone_role, send_messages=False)

        # Set the permissions so that the server admins can still send messages
        for role in interaction.guild.roles:
            if role.permissions.administrator:
                await channel.set_permissions(role, send_messages=True)

        await interaction.response.send_message(f"The channel {channel.mention} has been locked. Only admins can send messages.")

    @app_commands.command(name="unlock_channel", description="Unlock the channel so everyone can talk")
    @app_commands.checks.has_permissions(administrator=True)
    async def unlock_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        if channel is None:
            channel = interaction.channel
        guild = interaction.guild  # Access the guild from the interaction object
        everyone_role = guild.default_role  # @everyone role

        # Unlock the channel for @everyone
        await channel.set_permissions(everyone_role, send_messages=True)

        # Respond to the interaction
        await interaction.response.send_message(f"The channel {channel.mention} has been unlocked. Everyone can now send messages.")


async def setup(bot):
    await bot.add_cog(Moderation(bot))
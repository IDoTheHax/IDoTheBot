import discord
from discord.ext import commands
from discord import app_commands
import datetime

class ServerLockdown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Command group for lockdown commands
    lockdown = app_commands.Group(name="lockdown", description="Server lockdown commands")

    @lockdown.command(name="toggle", description="Lock or unlock the server")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(state="Whether to lock or unlock the server (true = lock, false = unlock)")
    async def toggle_lockdown(self, interaction: discord.Interaction, state: bool):
        """Toggle server lockdown state"""
        guild = interaction.guild
        
        # Define permissions to be modified
        lockdown_overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                send_messages=False,
                add_reactions=False,
                create_public_threads=False,
                create_private_threads=False,
                send_messages_in_threads=False
            )
        }
        
        unlock_overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                send_messages=None,  # Reset to default
                add_reactions=None,
                create_public_threads=None,
                create_private_threads=None,
                send_messages_in_threads=None
            )
        }

        try:
            # Get all channels excluding ticket channels and categories
            channels = [ch for ch in guild.channels 
                       if not isinstance(ch, discord.CategoryChannel) 
                       and "ticket" not in ch.name.lower()]

            # Apply the appropriate overwrites based on state
            target_overwrites = lockdown_overwrites if state else unlock_overwrites
            action = "locked" if state else "unlocked"

            for channel in channels:
                try:
                    await channel.edit(
                        overwrites={**channel.overwrites, **target_overwrites},
                        reason=f"Server {action} by {interaction.user}"
                    )
                except discord.Forbidden:
                    await interaction.channel.send(
                        f"Missing permissions to modify {channel.mention}",
                        ephemeral=True
                    )
                    continue

            # Send confirmation
            embed = discord.Embed(
                title=f"Server {action.capitalize()}",
                description=f"The server has been {action} by {interaction.user.mention}",
                color=discord.Color.red() if state else discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            embed.set_footer(text=f"Action performed by {interaction.user}")

            await interaction.response.send_message(embed=embed)

            # Optional: Log the action to a moderation log channel
            log_channel_id = await self.get_mod_log_channel(guild)
            if log_channel_id:
                log_channel = guild.get_channel(log_channel_id)
                if log_channel:
                    await log_channel.send(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                f"Failed to {action} server: {str(e)}",
                ephemeral=True
            )

    async def get_mod_log_channel(self, guild):
        """Placeholder method to get moderation log channel ID
        You would need to implement this based on your server's settings"""
        # This could be stored in a settings file similar to your ticket system
        return None  # Replace with actual channel ID retrieval logic

    @lockdown.command(name="status", description="Check the current lockdown status")
    @commands.has_permissions(manage_guild=True)
    async def lockdown_status(self, interaction: discord.Interaction):
        """Check if the server is currently locked down"""
        guild = interaction.guild
        is_locked = False
        
        # Check a sample channel's permissions
        for channel in guild.text_channels:
            if "ticket" not in channel.name.lower():
                perms = channel.overwrites_for(guild.default_role)
                if perms.send_messages is False:
                    is_locked = True
                    break

        embed = discord.Embed(
            title="Server Lockdown Status",
            description=f"The server is currently {'**locked**' if is_locked else '**unlocked**'}",
            color=discord.Color.red() if is_locked else discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} cog has been loaded")

async def setup(bot):
    await bot.add_cog(ServerLockdown(bot))

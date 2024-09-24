import discord
from discord.ext import commands
import json
import os

class CommandControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.disabled_commands = self.load_disabled_commands()  # Load the disabled commands from the JSON file

    def load_disabled_commands(self):
        """Load the list of disabled commands from a JSON file."""
        try:
            with open('disabled_commands.json', 'r') as f:
                data = json.load(f)
                return set(data.get('disabled_commands', []))  # Use a set for fast lookup
        except FileNotFoundError:
            print("disabled_commands.json not found, creating an empty list.")
            return set()

    def save_disabled_commands(self):
        """Save the list of disabled commands to the JSON file."""
        with open('disabled_commands.json', 'w') as f:
            json.dump({"disabled_commands": list(self.disabled_commands)}, f)

    @discord.app_commands.command(name="shush", description="Disable a specific command (for moderators)")
    @commands.has_permissions(administrator=True)
    async def shush(self, ctx, command_name: str):
        """Disable a specific command."""
        # Fetch all application commands
        all_commands = await self.bot.tree.fetch_commands()

        # Special handling for 'anti_ping'
        if command_name == 'anti_ping':
            # Disable the anti_ping functionality in the AutoMute cog
            auto_mute_cog = self.bot.get_cog('AutoMute')
            if auto_mute_cog:
                auto_mute_cog.disable_anti_ping()  # Disable anti_ping in AutoMute cog
                await ctx.response.send_message(f"The `anti_ping` functionality has been disabled.")
            else:
                await ctx.response.send_message(f"The `AutoMute` cog is not loaded.")
            return

        # Check if the command_name is among the fetched commands
        if command_name in [cmd.name for cmd in all_commands]:
            if command_name in self.disabled_commands:
                await ctx.response.send_message(f"The `{command_name}` command is already disabled.")
            else:
                self.disabled_commands.add(command_name)
                self.save_disabled_commands()
                await ctx.response.send_message(f"The `{command_name}` command has been disabled.")
        else:
            # Format and send the message with available commands
            command_list = [cmd.name for cmd in all_commands]
            available_commands = ", ".join(command_list)
            await ctx.response.send_message(
                f"No command found with the name `{command_name}`. "
                f"Here are the available commands: {available_commands}"
            )

    @discord.app_commands.command(name="unshush", description="Re-enable a disabled command (for moderators)")
    @commands.has_permissions(administrator=True)
    async def unshush(self, ctx, command_name: str):
        """Re-enable a previously disabled command."""
        # Special handling for 'anti_ping'
        if command_name == 'anti_ping':
            # Re-enable the anti_ping functionality in the AutoMute cog
            auto_mute_cog = self.bot.get_cog('anti_ping')
            if auto_mute_cog:
                auto_mute_cog.enable_anti_ping()  # Enable anti_ping in AutoMute cog
                await ctx.response.send_message(f"The `anti_ping` functionality has been re-enabled.")
            else:
                await ctx.response.send_message(f"The `AutoMute` cog is not loaded.")
            return

        if command_name not in self.disabled_commands:
            await ctx.response.send_message(f"The `{command_name}` command is not disabled.")
        else:
            self.disabled_commands.remove(command_name)
            self.save_disabled_commands()
            await ctx.response.send_message(f"The `{command_name}` command has been re-enabled.")


    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Intercept interactions and prevent execution of disabled commands."""
        if interaction.command.name in self.disabled_commands:
            await interaction.response.send_message(f"The {interaction.command.name} command is currently disabled.", ephemeral=True)
            return

    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: discord.Interaction, error: Exception):
        """Handle errors for application commands."""
        if isinstance(error, commands.CommandNotFound):
            await interaction.response.send_message("Command not found.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(CommandControl(bot))

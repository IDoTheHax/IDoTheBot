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
        if command_name in self.disabled_commands:
            await ctx.response.send_message(f"The `{command_name}` command is already disabled.")
        elif command_name not in self.bot.all_commands:
            # Get all the commands in the bot
            all_commands = self.bot.all_commands
            command_list = [command for command in all_commands]

            # Format and send the message with available commands
            available_commands = ", ".join(command_list)
            await ctx.response.send_message(
                f"No command found with the name `{command_name}`. "
                f"Here are the available commands: {available_commands}"
            )
        else:
            self.disabled_commands.add(command_name)
            self.save_disabled_commands()
            await ctx.response.send_message(f"The `{command_name}` command has been disabled.")

    @discord.app_commands.command(name="unshush", description="Re-enable a disabled command (for moderators)")
    @commands.has_permissions(administrator=True)
    async def unshush(self, ctx, command_name: str):
        """Re-enable a previously disabled command."""
        if command_name not in self.disabled_commands:
            await ctx.response.send_message(f"The `{command_name}` command is not disabled.")
        else:
            self.disabled_commands.remove(command_name)
            self.save_disabled_commands()
            await ctx.response.send_message(f"The `{command_name}` command has been re-enabled.")

    async def cog_check(self, ctx):
        """Check if the command is disabled before running it."""
        if ctx.command.name in self.disabled_commands:
            await ctx.response.send_message(f"The `{ctx.command.name}` command is currently disabled.")
            return False  # Prevent the command from running
        return True

async def setup(bot: commands.Bot):
    await bot.add_cog(CommandControl(bot))

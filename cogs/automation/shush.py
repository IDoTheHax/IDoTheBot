import discord
from discord.ext import commands
import json
import os

class CommandControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.disabled_commands = self.load_disabled_commands()

    def load_disabled_commands(self):
        try:
            with open('disabled_commands.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("disabled_commands.json not found, creating an empty config.")
            return {}

    def save_disabled_commands(self):
        with open('disabled_commands.json', 'w') as f:
            json.dump(self.disabled_commands, f, indent=4)

    def get_disabled_commands_for_guild(self, guild_id):
        return self.disabled_commands.get(str(guild_id), set())

    def update_disabled_commands_for_guild(self, guild_id, commands_set):
        self.disabled_commands[str(guild_id)] = list(commands_set)
        self.save_disabled_commands()

    @discord.app_commands.command(name="shush", description="Disable a specific command (for moderators)")
    @commands.has_permissions(administrator=True)
    async def shush(self, ctx, command_name: str):
        guild_id = ctx.guild.id
        all_commands = await self.bot.tree.fetch_commands()

        if command_name == 'anti_ping':
            auto_mute_cog = self.bot.get_cog('AutoMute')
            if auto_mute_cog:
                auto_mute_cog.disable_anti_ping(guild_id)
                await ctx.response.send_message(f"The `anti_ping` functionality has been disabled.")
            return

        if command_name in [cmd.name for cmd in all_commands]:
            disabled_commands = self.get_disabled_commands_for_guild(guild_id)
            if command_name in disabled_commands:
                await ctx.response.send_message(f"The `{command_name}` command is already disabled.")
            else:
                disabled_commands.add(command_name)
                self.update_disabled_commands_for_guild(guild_id, disabled_commands)
                await ctx.response.send_message(f"The `{command_name}` command has been disabled.")
        else:
            await ctx.response.send_message("No such command found.")

    @discord.app_commands.command(name="unshush", description="Re-enable a disabled command (for moderators)")
    @commands.has_permissions(administrator=True)
    async def unshush(self, ctx, command_name: str):
        guild_id = ctx.guild.id

        if command_name == 'anti_ping':
            auto_mute_cog = self.bot.get_cog('AutoMute')
            if auto_mute_cog:
                auto_mute_cog.enable_anti_ping(guild_id)
                await ctx.response.send_message(f"The `anti_ping` functionality has been re-enabled.")
            return

        disabled_commands = self.get_disabled_commands_for_guild(guild_id)
        if command_name in disabled_commands:
            disabled_commands.remove(command_name)
            self.update_disabled_commands_for_guild(guild_id, disabled_commands)
            await ctx.response.send_message(f"The `{command_name}` command has been re-enabled.")
        else:
            await ctx.response.send_message("No such command is currently disabled.")

async def setup(bot):
    await bot.add_cog(CommandControl(bot))

import discord
from discord.ext import commands
import asyncio

class Shush(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="shush", help="Disable a specific command (for moderators)")
    @commands.has_permissions(administrator=True)
    async def shush_command(self, ctx, command_name: str):
        """Disable a specific command."""
        if command_name in self.disabled_commands:
            await ctx.send(f"The `{command_name}` command is already disabled.")
        elif command_name not in self.bot.all_commands:
            await ctx.send(f"No command found with the name `{command_name}`.")
        else:
            self.disabled_commands.add(command_name)
            self.save_disabled_commands()
            await ctx.send(f"The `{command_name}` command has been disabled.")

    @commands.command(name="unshush", help="Re-enable a disabled command (for moderators)")
    @commands.has_permissions(administrator=True)
    async def unshush_command(self, ctx, command_name: str):
        """Re-enable a previously disabled command."""
        if command_name not in self.disabled_commands:
            await ctx.send(f"The `{command_name}` command is not disabled.")
        else:
            self.disabled_commands.remove(command_name)
            self.save_disabled_commands()
            await ctx.send(f"The `{command_name}` command has been re-enabled.")

async def setup(bot):
    await bot.add_cog(Shush(bot))
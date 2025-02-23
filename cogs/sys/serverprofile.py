import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import io

class ServerCustomization(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.has_permissions(manage_nicknames=True)
    async def change_bot_nickname(self, ctx, *, new_nickname: str):
        """Change the bot's nickname in the current server."""
        try:
            await ctx.guild.me.edit(nick=new_nickname)
            await ctx.send(f"Bot nickname changed to: {new_nickname}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to change my nickname.")
        except discord.HTTPException:
            await ctx.send("Failed to change nickname. Please try again later.")

    @app_commands.command()
    @app_commands.has_permissions(manage_webhooks=True)
    async def create_custom_webhook(self, ctx, name: str, avatar_url: str = None):
        """Create a custom webhook for the bot in the current channel."""
        try:
            avatar_bytes = None
            if avatar_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(avatar_url) as resp:
                        if resp.status == 200:
                            avatar_bytes = await resp.read()
                        else:
                            await ctx.send("Failed to fetch the avatar image. Using default avatar.")

            webhook = await ctx.channel.create_webhook(name=name, avatar=avatar_bytes)
            await ctx.send(f"Custom webhook created with name: {name}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to create webhooks in this channel.")
        except discord.HTTPException:
            await ctx.send("Failed to create webhook. Please try again later.")

    @app_commands.command()
    async def send_as_webhook(self, ctx, *, message: str):
        """Send a message using the custom webhook."""
        webhook = discord.utils.get(await ctx.channel.webhooks(), name=self.bot.user.name)
        if webhook:
            try:
                await webhook.send(content=message, username=ctx.guild.me.nick or self.bot.user.name)
            except discord.HTTPException:
                await ctx.send("Failed to send message through webhook. Please try again later.")
        else:
            await ctx.send("Webhook not found. Please create one first using the create_custom_webhook command.")

    @app_commands.command()
    @app_commands.checks.has_permissions(manage_webhooks=True)
    async def list_webhooks(self, ctx):
        """List all webhooks in the current channel."""
        webhooks = await ctx.channel.webhooks()
        if webhooks:
            webhook_list = "\n".join([f"- {webhook.name}" for webhook in webhooks])
            await ctx.send(f"Webhooks in this channel:\n{webhook_list}")
        else:
            await ctx.send("No webhooks found in this channel.")

    @app_commands.command()
    @app_commands.checks.has_permissions(manage_webhooks=True)
    async def delete_webhook(self, ctx, webhook_name: str):
        """Delete a webhook by name."""
        webhook = discord.utils.get(await ctx.channel.webhooks(), name=webhook_name)
        if webhook:
            await webhook.delete()
            await ctx.send(f"Webhook '{webhook_name}' has been deleted.")
        else:
            await ctx.send(f"No webhook found with the name '{webhook_name}'.")

async def setup(bot):
    await bot.add_cog(ServerCustomization(bot))

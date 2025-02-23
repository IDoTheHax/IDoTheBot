import discord
from discord.ext import commands
import json
import asyncio

class Blacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.banned_users_file = "data/banned_users.json"
        self.config_file = "data/config.json"
        self.load_banned_users()
        self.load_config()

    def load_banned_users(self):
        try:
            with open(self.banned_users_file, "r") as f:
                self.banned_users = json.load(f)
        except FileNotFoundError:
            self.banned_users = []

    def save_banned_users(self):
        with open(self.banned_users_file, "w") as f:
            json.dump(self.banned_users, f)

    def load_config(self):
        try:
            with open(self.config_file, "r") as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = {}

    def save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)

    def save_banned_users(self):
        with open(self.banned_users_file, "w") as f:
            json.dump(self.banned_users, f)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if str(member.id) in self.banned_users:
            await member.ban(reason="User is blacklisted")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def blacklist(self, ctx, user_id: int):
        user = await self.bot.fetch_user(user_id)
        if not user:
            await ctx.send("User not found.")
            return

        mutual_servers = [guild for guild in self.bot.guilds if guild.get_member(user_id)]
        
        embed = discord.Embed(title="User Information", color=discord.Color.red())
        embed.add_field(name="Username", value=str(user), inline=False)
        embed.add_field(name="User ID", value=user.id, inline=False)
        embed.add_field(name="Mutual Servers", value="\n".join([guild.name for guild in mutual_servers]) or "None", inline=False)
        embed.set_thumbnail(url=user.avatar.url)

        await ctx.send(embed=embed)

        confirmation = await ctx.send("Do you want to blacklist this user? (yes/no)")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30.0)
            if msg.content.lower() == "yes":
                self.banned_users.append(str(user_id))
                self.save_banned_users()
                await ctx.send(f"User {user} has been blacklisted.")
            else:
                await ctx.send("Blacklist action cancelled.")
        except asyncio.TimeoutError:
            await ctx.send("No response received. Blacklist action cancelled.")

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        if thread.parent_id == YOUR_FORUM_CHANNEL_ID:
            # Extract user ID from thread name
            try:
                user_id = int(thread.name.split()[0])
                user = await self.bot.fetch_user(user_id)
                if user:
                    await self.send_blacklist_application(thread, user)
            except ValueError:
                await thread.send("Invalid thread name format. Please use 'USER_ID Username' format.")

    async def send_blacklist_application(self, thread, user):
        mutual_servers = [guild for guild in self.bot.guilds if guild.get_member(user.id)]
        
        embed = discord.Embed(title="Blacklist Application", color=discord.Color.orange())
        embed.add_field(name="Username", value=str(user), inline=False)
        embed.add_field(name="User ID", value=user.id, inline=False)
        embed.add_field(name="Mutual Servers", value="\n".join([guild.name for guild in mutual_servers]) or "None", inline=False)
        embed.set_thumbnail(url=user.avatar.url)

        await thread.send(embed=embed)
        await thread.send("Administrators can use the /blacklist command to add this user to the blacklist if approved.")


def setup(bot):
    bot.add_cog(Blacklist(bot))

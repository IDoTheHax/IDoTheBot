import discord
from discord.ext import commands
import json
import asyncio

'''
        
                            [ THE BLACKLIST ]                           

The Blacklist is a tool used by IDoTheBot to automatically remove members
from a discord that have been identified to be problematic, designed for use
in minecraft communities this bot creates and reads through a list of Discord 
user IDs that are authorized to use the blacklist command.
        
Only users with these IDs will be able to execute the blacklist functionality.
Add or remove IDs as needed to manage access to this sensitive command.

This is a Very Powerfull command as it bannishes members from all the discords
where IDoTheBot Is Present, an advantage with keeping the bot open source is
that the blacklisted users and those who are able to edit the blacklist are 
open for view by anyone, a flawless system that allows for protection from bad
actors, any updates to this code will have to go through @IDoTheHax on discord
before changes are made.

'''
class Blacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.banned_users_file = "data/banned_users.json"
        self.config_file = "data/config.json"
        self.load_banned_users()
        self.load_config()
        
        self.AUTHORIZED_USERS = [987323487343493191, 1088268266499231764, 726721909374320640, 710863981039845467, 1151136371164065904]

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
    async def blacklist(self, ctx, user_id: int):
        if ctx.author.id not in AUTHORIZED_USERS:
            await ctx.send("You are not authorized to use this command.")
            return

        # Rest of the existing command code
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

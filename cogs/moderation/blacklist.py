import discord
from discord import app_commands, ui
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
class ConfirmButton(ui.View):
    def __init__(self, cog, user_id, reason):
        super().__init__()
        self.cog = cog
        self.user_id = user_id
        self.reason = reason

    @ui.button(label='Confirm Blacklist', style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id not in self.cog.AUTHORIZED_USERS:
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return

        user_id = str(self.user_id)
        user = await self.cog.bot.fetch_user(int(user_id))
        display_name = user.display_name  # This gets the user's display name

        self.cog.banned_users[user_id] = {
            "reason": self.reason,
            "timestamp": discord.utils.utcnow().isoformat(),
            "display_name": display_name
        }
        self.cog.save_banned_users()

        mutual_servers = [guild.name for guild in self.cog.bot.guilds if guild.get_member(int(user_id))]
        
        dm_message = f"Hello {display_name},\n\nYou have been blacklisted for the following reason: {self.reason}\n\n"
        dm_message += "You were a member of the following servers:\n"
        dm_message += "\n".join(mutual_servers) if mutual_servers else "No mutual servers found."

        try:
            await user.send(dm_message)
        except discord.Forbidden:
            await interaction.followup.send("Failed to send a DM to the user.", ephemeral=True)
            
        kicked_servers = []
        for guild in self.cog.bot.guilds:
            member = guild.get_member(int(user_id))
            if member:
                try:
                    await member.kick(reason=f"Blacklisted: {self.reason}")
                    kicked_servers.append(guild.name)
                except discord.Forbidden:
                    pass

        kick_message = f"User {user_id} has been blacklisted and kicked from the following servers:\n" + "\n".join(kicked_servers) if kicked_servers else f"User {user_id} has been blacklisted, but couldn't be kicked from any servers."
        await interaction.response.edit_message(content=kick_message, view=None)
        self.stop()

    @ui.button(label='Cancel', style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Blacklist action cancelled.", view=None)
        self.stop()

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
            self.banned_users = {}

    def save_banned_users(self):
        with open(self.banned_users_file, "w") as f:
            json.dump(self.banned_users, f, indent=4)

    def load_config(self):
        try:
            with open(self.config_file, "r") as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = {}

    def save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if str(member.id) in self.banned_users:
            await member.ban(reason="User is blacklisted")

    @app_commands.command()
    async def setforumchannel(self, interaction: discord.Interaction, channel: discord.ForumChannel):
        if interaction.user.id not in self.AUTHORIZED_USERS:
            await interaction.response.send_message("You are not authorized to use this command.")
            return
        
        self.config["forum_channel_id"] = channel.id
        self.save_config()
        await interaction.response.send_message(f"Forum channel for blacklist applications has been set to {channel.mention}")

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        forum_channel_id = self.config.get("forum_channel_id")
        if forum_channel_id and thread.parent_id == forum_channel_id:
            try:
                # Split the thread name and extract username and user ID
                thread_name_parts = thread.name.split('(')
                username = thread_name_parts[0].strip()
                user_id = thread_name_parts[1].strip(')')
                
                # Fetch the user
                user = await self.bot.fetch_user(int(user_id))
                if user:
                    await self.send_blacklist_application(thread, user)
                else:
                    await thread.send("Invalid user ID. Please use the format 'Username (userid)'.")
            except (ValueError, IndexError):
                await thread.send("Invalid thread name format. Please use 'Username (userid)' format.")

    async def send_blacklist_application(self, thread, user):
        mutual_servers = [guild for guild in self.bot.guilds if guild.get_member(user.id)]
        
        embed = discord.Embed(title="Blacklist Application", color=discord.Color.orange())
        embed.add_field(name="Username", value=str(user), inline=False)
        embed.add_field(name="User ID", value=user.id, inline=False)
        embed.add_field(name="Mutual Servers", value="\n".join([guild.name for guild in mutual_servers]) or "None", inline=False)
        embed.set_thumbnail(url=user.avatar.url)

        reason = thread.starter_message.content if thread.starter_message else "No reason provided"
        embed.add_field(name="Reason", value=reason, inline=False)

        view = ConfirmButton(self, user.id, reason)
        await thread.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Blacklist(bot))

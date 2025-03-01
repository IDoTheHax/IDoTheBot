import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp
import asyncio
import re

class ConfirmButton(ui.View):
    def __init__(self, cog, blacklist_data):
        super().__init__()
        self.cog = cog
        self.blacklist_data = blacklist_data

    @ui.button(label='Confirm Blacklist', style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id not in self.cog.AUTHORIZED_USERS:
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return

        async with aiohttp.ClientSession() as session:
            async with session.post('http://localhost:5000/blacklist', json=self.blacklist_data) as response:
                if response.status != 200:
                    await interaction.response.send_message("Failed to blacklist user.", ephemeral=True)
                    return

        user_id = self.blacklist_data['discord_user_id']
        reason = self.blacklist_data['reason']
        
        user = await self.cog.bot.fetch_user(int(user_id))
        mutual_servers = [guild.name for guild in self.cog.bot.guilds if guild.get_member(int(user_id))]
        
        dm_message = f"Hello {user.display_name},\n\nYou have been blacklisted for the following reason: {reason}\n\n"
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
                    await member.kick(reason=f"Blacklisted: {reason}")
                    kicked_servers.append(guild.name)
                except discord.Forbidden:
                    pass

        kick_message = f"User {user_id} has been blacklisted and kicked from the following servers:\n" + "\n".join(kicked_servers) if kicked_servers else f"User {user_id} has been blacklisted, but couldn't be kicked from any servers."
        if self.blacklist_data.get('minecraft_username') or self.blacklist_data.get('minecraft_uuid'):
            kick_message += f"\nMinecraft info: Username: {self.blacklist_data.get('minecraft_username', 'N/A')}, UUID: {self.blacklist_data.get('minecraft_uuid', 'N/A')}"
        await interaction.response.edit_message(content=kick_message, view=None)
        self.stop()

    @ui.button(label='Cancel', style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Blacklist action cancelled.", view=None)
        self.stop()

class Blacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.AUTHORIZED_USERS = [987323487343493191, 1088268266499231764, 726721909374320640, 710863981039845467, 1151136371164065904]

    def get_correct_format_embed(self):
        embed = discord.Embed(title="Correct Blacklist Request Format", color=discord.Color.blue())
        embed.description = "Please use the following format in your thread description:"
        
        format_text = """
    Discord username:
    Discord user ID:
    Minecraft username (if applicable):
    Minecraft UUID (if applicable):
    Reason:"""
        embed.add_field(name="Format", value=f"```" + format_text + "```", inline=False)
        
        example = """
    Discord username: JohnDoe#1234
    Discord user ID: 123456789012345678
    Minecraft username: JohnDoe123
    Minecraft UUID: 550e8400-e29b-41d4-a716-446655440000
    Reason: Griefing and using hacks"""
        embed.add_field(name="Example", value=f"```" + example + "```", inline=False)
        
        return embed


    @commands.Cog.listener()
    async def on_member_join(self, member):
        async with aiohttp.ClientSession() as session:
            async with session.get(f'http://localhost:5000/check_blacklist/{member.id}') as response:
                if response.status == 200:
                    data = await response.json()
                    if data['blacklisted']:
                        await member.ban(reason="User is blacklisted")

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        if isinstance(thread.parent, discord.ForumChannel):
            await asyncio.sleep(1)  # Wait for the initial message to be posted
            starter_message = await thread.fetch_message(thread.id)
            blacklist_data = self.parse_blacklist_request(starter_message.content)
            
            if not blacklist_data:
                correct_format_embed = self.get_correct_format_embed()
                await thread.send(embed=correct_format_embed)
                return

            embed = discord.Embed(title="Blacklist Application", color=discord.Color.orange())
            embed.add_field(name="Discord Username", value=blacklist_data['discord_username'], inline=False)
            embed.add_field(name="Discord User ID", value=blacklist_data['discord_user_id'], inline=False)
            embed.add_field(name="Reason", value=blacklist_data['reason'], inline=False)
            if blacklist_data.get('minecraft_username'):
                embed.add_field(name="Minecraft Username", value=blacklist_data['minecraft_username'], inline=False)
            if blacklist_data.get('minecraft_uuid'):
                embed.add_field(name="Minecraft UUID", value=blacklist_data['minecraft_uuid'], inline=False)

            view = ConfirmButton(self, blacklist_data)
            await thread.send(embed=embed, view=view)


    def parse_blacklist_request(self, content):
        # First, try to extract Discord username and ID from the thread title
        match = re.match(r'(.*?)\s*\((\d+)\)', content.split('\n')[0])
        data = {}
        if match:
            data['discord_username'] = match.group(1).strip()
            data['discord_user_id'] = match.group(2)
        
        # Then, look for additional information in the description
        lines = content.split('\n')
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                if key in ['discord_username', 'discord_user_id', 'minecraft_username', 'minecraft_uuid']:
                    data[key] = value
        
        # Extract reason (assuming it's everything after the structured data)
        reason_start = content.find('reason:', content.rfind('uuid:') + 1)
        if reason_start == -1:
            reason_start = content.find('reason:', content.rfind('id:') + 1)
        if reason_start != -1:
            data['reason'] = content[reason_start + 7:].strip()
        else:
            # If no explicit reason is found, use the entire content as the reason
            data['reason'] = content.strip()
        
        return data if 'discord_username' in data and 'discord_user_id' in data and 'reason' in data else None

async def setup(bot):
    await bot.add_cog(Blacklist(bot))

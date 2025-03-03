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
        # First, defer the response to prevent interaction timeouts
        await interaction.response.defer(ephemeral=True)
        
        if interaction.user.id not in self.cog.AUTHORIZED_USERS:
            await interaction.followup.send("You are not authorized to confirm blacklist requests.", ephemeral=True)
            return

        # Extract user data
        user_id = self.blacklist_data['discord_user_id']
        username = self.blacklist_data['discord_username']
        reason = self.blacklist_data['reason']
        
        # Create payload with the correct field names expected by the API
        payload = {
            'auth_id': interaction.user.id,
            'user_id': user_id,
            'display_name': username,
            'reason': reason
        }
        
        # Add Minecraft info if available
        if self.blacklist_data.get('minecraft_username') or self.blacklist_data.get('minecraft_uuid'):
            payload['mc_info'] = {
                'username': self.blacklist_data.get('minecraft_username', ''),
                'uuid': self.blacklist_data.get('minecraft_uuid', '')
            }
        
        # Log the payload for debugging
        print(f"Sending blacklist payload: {payload}")
        
        # Send the blacklist request to the API
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post('http://localhost:5000/blacklist', json=payload) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        print(f"API Error: {response.status} - {response_text}")
                        await interaction.followup.send(f"Failed to blacklist user. API returned: {response.status}", ephemeral=True)
                        return
                    else:
                        # API request successful
                        print("Blacklist API request successful")
        except Exception as e:
            print(f"API request error: {e}")
            await interaction.followup.send(f"Failed to connect to blacklist API: {str(e)}", ephemeral=True)
            return
        
        # Process kicks and notifications
        kicked_servers = []
        mutual_servers = []
        
        try:
            # Get user information
            user = await self.cog.bot.fetch_user(int(user_id))
            
            # Find mutual servers
            for guild in self.cog.bot.guilds:
                member = guild.get_member(int(user_id))
                if member:
                    mutual_servers.append(guild.name)
                    try:
                        await member.kick(reason=f"Blacklisted: {reason}")
                        kicked_servers.append(guild.name)
                    except discord.Forbidden:
                        print(f"Missing permissions to kick from {guild.name}")
                    except Exception as e:
                        print(f"Error kicking from {guild.name}: {e}")
            
            # Try to DM the user
            if mutual_servers:
                dm_message = f"Hello {user.display_name},\n\nYou have been blacklisted for the following reason: {reason}\n\n"
                dm_message += "You were a member of the following servers:\n"
                dm_message += "\n".join(mutual_servers)
                
                try:
                    await user.send(dm_message)
                    print(f"Successfully sent DM to {user.display_name}")
                except discord.Forbidden:
                    print(f"User {user.display_name} has DMs disabled")
                except Exception as e:
                    print(f"Error sending DM: {e}")
        except Exception as e:
            print(f"Error processing user actions: {e}")
        
        # Prepare success message
        if kicked_servers:
            kick_message = f"User {username} ({user_id}) has been blacklisted and kicked from the following servers:\n" + "\n".join(kicked_servers)
        else:
            kick_message = f"User {username} ({user_id}) has been blacklisted, but couldn't be kicked from any servers."
        
        # Add Minecraft info to message if available
        if self.blacklist_data.get('minecraft_username'):
            kick_message += f"\nMinecraft Username: {self.blacklist_data.get('minecraft_username')}"
        if self.blacklist_data.get('minecraft_uuid'):
            kick_message += f"\nMinecraft UUID: {self.blacklist_data.get('minecraft_uuid')}"
        
        # Update the message in the thread
        try:
            await interaction.message.edit(content=kick_message, embed=None, view=None)
        except Exception as e:
            print(f"Error updating message: {e}")
            # Try to send a new message if editing fails
            try:
                await interaction.followup.send(kick_message, ephemeral=False)
            except Exception as e2:
                print(f"Error sending followup message: {e2}")
        
        # Send confirmation to the moderator
        await interaction.followup.send("Blacklist operation completed successfully.", ephemeral=True)
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
                        reason = data.get('reason', 'No reason provided')
                        await member.ban(reason=f"Blacklisted: {reason}")


    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        if isinstance(thread.parent, discord.ForumChannel):
            await asyncio.sleep(1)  # Wait for the initial message to be posted
            
            # Get the initial message
            try:
                starter_message = await thread.fetch_message(thread.id)
                
                # Only process blacklist requests in the appropriate channel
                blacklist_channel_ids = [123456789012345678]  # Replace with your actual channel ID
                if thread.parent.id not in blacklist_channel_ids:
                    return
                    
                # Parse the request
                blacklist_data = self.parse_blacklist_request(starter_message.content)
                
                # If parsing failed, send format guidance
                if not blacklist_data:
                    correct_format_embed = self.get_correct_format_embed()
                    await thread.send(embed=correct_format_embed)
                    return
                
                # Create and send the embed for a valid request
                embed = discord.Embed(title="Blacklist Application", color=discord.Color.orange())
                embed.add_field(name="Discord Username", value=blacklist_data['discord_username'], inline=False)
                embed.add_field(name="Discord User ID", value=blacklist_data['discord_user_id'], inline=False)
                embed.add_field(name="Reason", value=blacklist_data['reason'], inline=False)
                
                if blacklist_data.get('minecraft_username'):
                    embed.add_field(name="Minecraft Username", value=blacklist_data['minecraft_username'], inline=False)
                if blacklist_data.get('minecraft_uuid'):
                    embed.add_field(name="Minecraft UUID", value=blacklist_data['minecraft_uuid'], inline=False)
                
                # Create and send the confirmation buttons
                view = ConfirmButton(self, blacklist_data)
                await thread.send(embed=embed, view=view)
                
            except discord.NotFound:
                print(f"Could not find starter message for thread {thread.id}")
            except Exception as e:
                print(f"Error processing thread {thread.id}: {e}")

    def parse_blacklist_request(self, content):
        data = {}
        
        # Extract information using regex patterns
        discord_username_pattern = r"Discord username:\s*([^\n]+)"
        discord_id_pattern = r"Discord user ID:\s*(\d+)"
        minecraft_username_pattern = r"Minecraft username(?:\s*\(if applicable\))?:\s*([^\n]+)"
        minecraft_uuid_pattern = r"Minecraft UUID(?:\s*\(if applicable\))?:\s*([^\n]+)"
        reason_pattern = r"Reason:\s*([\s\S]+)$"  # Match everything to the end
        
        # Extract using regex
        username_match = re.search(discord_username_pattern, content, re.IGNORECASE)
        id_match = re.search(discord_id_pattern, content, re.IGNORECASE)
        mc_username_match = re.search(minecraft_username_pattern, content, re.IGNORECASE)
        mc_uuid_match = re.search(minecraft_uuid_pattern, content, re.IGNORECASE)
        reason_match = re.search(reason_pattern, content, re.IGNORECASE)
        
        # Populate data if matches found
        if username_match:
            data['discord_username'] = username_match.group(1).strip()
        if id_match:
            data['discord_user_id'] = id_match.group(1).strip()
        if mc_username_match:
            data['minecraft_username'] = mc_username_match.group(1).strip()
        if mc_uuid_match:
            data['minecraft_uuid'] = mc_uuid_match.group(1).strip()
        if reason_match:
            data['reason'] = reason_match.group(1).strip()
        
        # If we can't extract via regex, try a fallback for thread-title parsing
        if not ('discord_username' in data and 'discord_user_id' in data):
            # Try to extract from thread title format (username (ID))
            title_match = re.match(r'(.*?)\s*\((\d+)\)', content.split('\n')[0])
            if title_match:
                data['discord_username'] = title_match.group(1).strip()
                data['discord_user_id'] = title_match.group(2).strip()
        
        # Check if we have the minimum required data
        if 'discord_username' in data and 'discord_user_id' in data and 'reason' in data:
            return data
        else:
            return None
async def setup(bot):
    await bot.add_cog(Blacklist(bot))
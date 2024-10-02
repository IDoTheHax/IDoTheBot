import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import datetime as dt
import requests
import json
import os

bot = commands.Bot(command_prefix='/', intents=discord.Intents.all())

# Load blacklists from JSON files
def load_blacklist(filename):
    try:
        with open(filename, 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Creating an empty file.")
        with open(filename, 'w') as f:
            json.dump([], f)
        return set()

BLACKLISTED_USERS = load_blacklist('blacklisted_users.json')
BLACKLISTED_CHANNELS = load_blacklist('blacklisted_channels.json')

# When bot starts
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    
    await bot.load_extension("anti_ping")
    await bot.load_extension("cooldown_adjust")
    await bot.load_extension("moderation")
    await bot.load_extension("shush")
    await bot.load_extension("warning_sys")

    try:
        #BLACKLISTED_USERS = load_blacklist('blacklisted_users.json')
        #BLACKLISTED_CHANNELS = load_blacklist('blacklisted_channels.json')
        synced = await bot.tree.sync()

        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

# Get log channels
def get_log_channel(guild):
    """Find the appropriate logging channel in the given guild."""
    log_channel_names = ["moderator-only", "logs"]
    for channel_name in log_channel_names:
        channel = discord.utils.get(guild.channels, name=channel_name)
        if channel:
            return channel
    return None

def should_log(message):
    """Check if the message should be logged based on blacklists."""
    if str(message.author.id) in BLACKLISTED_USERS:
        return False
    if str(message.channel.id) in BLACKLISTED_CHANNELS:
        return False
    return True

# Log on delete
@bot.event
async def on_message_delete(message):
    # Ignore DMs
    if not message.guild:
        return

    # Check if the message should be logged
    if not should_log(message):
        return

    log_channel = get_log_channel(message.guild)
    
    # If no suitable channel is found, we can't log the deletion
    if not log_channel:
        return

    embed = discord.Embed(title=f"{message.author}'s Message Was Deleted", 
                          description=f"Deleted Message: {message.content}\nAuthor: {message.author.mention}\nLocation: {message.channel.mention}", 
                          timestamp=datetime.now(), 
                          color=discord.Color.red())

    channel2 = bot.get_channel(1260856171905159190)
    embed2 = discord.Embed(title = f"{message.author}'s Message Was Deleted",description = f"Deleted Message: {message.content}\nAuthor: {message.author.mention}\nLocation: {message.channel.mention}", timestamp = datetime.now(), color = 5)
    await channel2.send(embed = embed2)

    await log_channel.send(embed=embed)

# Log on edit
@bot.event
async def on_message_edit(message_before, message_after):
    # Ignore DMs
    if not message_before.guild:
        return

    # Check if the message should be logged
    if not should_log(message_before):
        return

    log_channel = get_log_channel(message_before.guild)
    
    # If no suitable channel is found, we can't log the edit
    if not log_channel:
        return

    embed = discord.Embed(title=f"{message_before.author}'s Message Was Edited", 
                          description=f"Before: {message_before.content}\nAfter: {message_after.content}\nAuthor: {message_before.author.mention}\nLocation: {message_before.channel.mention}", 
                          timestamp=datetime.now(), 
                          color=discord.Color.blue())
    
    channel2 = bot.get_channel(1260856171905159190)
    embed2 = discord.Embed(title = f"{message_before.author}'s Message Was Edited", description = f"Message: {message_before.content}\nAfter: {message_after.content}\nAuthor: {message_before.author.mention}\nLocation: {message_before.channel.mention}", timestamp = datetime.now(), color = 1)
    await channel2.send(embed = embed2)


@bot.tree.command(name="embed", description="Create an embed message")
@app_commands.describe(title="Embed title", description="Embed description", color="Embed color (hex)")
async def embed(interaction: discord.Interaction, title: str, description: str, color: str):
    embed = discord.Embed(title=title, description=description, color=int(color, 16))
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="github", description="Get information about a GitHub repository")
@app_commands.describe(username="GitHub username", repository="Repository name")
async def github(interaction: discord.Interaction, username: str, repository: str):
    url = f'https://api.github.com/repos/{username}/{repository}'
    response = requests.get(url)
    data = json.loads(response.text)

    if response.status_code != 200:
        await interaction.response.send_message(f"Error: {data.get('message', 'Unknown error occurred')}", ephemeral=True)
        return

    embed = discord.Embed(title=data['name'], description=data['description'], color=0x00ff00)
    embed.add_field(name='Stars', value=data['stargazers_count'])
    embed.add_field(name='Forks', value=data['forks_count'])
    embed.add_field(name='Watchers', value=data['watchers_count'])
    embed.set_footer(text=f'Created at {data["created_at"]}')
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="analyze", description="Analyze crash reports")
@app_commands.describe(code="Code to search for in crash reports")
async def analyze(interaction: discord.Interaction, code: str):
    crash_report_channels = ['crash-reports', 'errors']
    for channel_name in crash_report_channels:
        channel = discord.utils.get(interaction.guild.channels, name=channel_name)
        if channel:
            async for message in channel.history(limit=100):
                if code in message.content:
                    await interaction.response.send_message(f'Found crash report in {channel.mention}:\n{message.jump_url}')
                    return
    await interaction.response.send_message('Crash report not found.')

@bot.tree.command(name="analyse", description="Analyze crash reports (alternative spelling)")
@app_commands.describe(code="Code to search for in crash reports")
async def analyse(interaction: discord.Interaction, code: str):
    await analyze(interaction, code)

@bot.tree.command(name="mappings", description="Command for mappings")
@app_commands.describe(mapping="Mapping information")
async def mappings(interaction: discord.Interaction, mapping: str):
    # Implement your mappings logic here
    await interaction.response.send_message(f"Mapping command received: {mapping}")

@bot.tree.command(name="moderate", description="Moderate a message or user")
@app_commands.describe(
    message_id="ID of the message to moderate (optional for ban)", 
    action="Action to take (delete, edit, mute, or ban)", 
    user="User to ban (for ban action)"
)
@app_commands.checks.has_permissions(manage_messages=True, ban_members=True)
async def moderate(interaction: discord.Interaction, action: str, message_id: str = None, user: discord.User = None, duration: int = None, reason: str = "No reason provided"):
    try:
        if action == 'delete':
            if message_id is None:
                await interaction.response.send_message("Please provide a message ID to delete.", ephemeral=True)
                return

            message = await interaction.channel.fetch_message(int(message_id))
            await message.delete()
            await interaction.response.send_message("Message deleted.", ephemeral=True)

        elif action == 'edit':
            if message_id is None:
                await interaction.response.send_message("Please provide a message ID to edit.", ephemeral=True)
                return

            message = await interaction.channel.fetch_message(int(message_id))
            await message.edit(content='This message has been edited.')
            await interaction.response.send_message("Message edited.", ephemeral=True)

        elif action == 'ban':
            if user is None:
                await interaction.response.send_message("Please mention a user to ban.", ephemeral=True)
                return

            try:
                # Send a DM to the user explaining the ban
                await user.send(f"You have been banned from {interaction.guild.name} for the following reason: {reason}")
            except discord.errors.Forbidden:
                # Couldn't send DM, maybe user has DMs disabled
                await interaction.response.send_message(f"Could not send DM to {user.mention}, but proceeding with the ban.", ephemeral=True)
 
            await interaction.guild.ban(user, reason="Moderation action taken")
            await interaction.response.send_message(f"{user.mention} has been banned.", ephemeral=True)
 
        elif action == 'mute':
            if user is None:
                await interaction.response.send_message("Please mention a user to mute.", ephemeral=True)
                return

            if duration is None or duration <= 0:
                await interaction.response.send_message("Please provide a valid mute duration in minutes.", ephemeral=True)
                return

            try:
                # Send a DM to the user explaining the mute
                await user.send(f"You have been muted in {interaction.guild.name} for {duration} minutes for the following reason: {reason}")
            except discord.errors.Forbidden:
                # Couldn't send DM, maybe user has DMs disabled
                await interaction.response.send_message(f"Could not send DM to {user.mention}, but proceeding with the mute.", ephemeral=True)

 
            # Set the mute duration (in seconds)
            mute_duration = dt.timedelta(minutes=duration)
            await user.timeout(mute_duration, reason="Muted by moderator")

            await interaction.response.send_message(f"{user.mention} has been muted for {duration} minutes.", ephemeral=True)

        else:
            await interaction.response.send_message("Invalid action.", ephemeral=True)

    except discord.errors.NotFound:
        await interaction.response.send_message("Message or user not found.", ephemeral=True)
    except discord.errors.Forbidden:
        await interaction.response.send_message("I don't have permission to do that.", ephemeral=True)

@bot.tree.command(name="purge", description="Delete a specified number of messages")
@app_commands.describe(amount="Number of messages to delete (max 100)")
@app_commands.checks.has_permissions(manage_messages=True)
async def purge(interaction: discord.Interaction, amount: int):
   if amount <= 0 or amount > 100:
       await interaction.response.send_message("Please provide a number between 1 and 100.", ephemeral=True)
       return
   
   await interaction.response.defer(ephemeral=True)
    
   deleted = await interaction.channel.purge(limit=amount)
    
   await interaction.followup.send(f"Successfully deleted {len(deleted)} message(s).", ephemeral=True)
   #await interaction.response.send_message("WORK")

@bot.tree.command(name="reload_blacklists", description="Reloads Blacklists")
#@app_commands.checks.has_permissions(administrator=True)
async def reload_blacklists(interaction: discord.Interaction):
    global BLACKLISTED_USERS, BLACKLISTED_CHANNELS
    BLACKLISTED_USERS = load_blacklist('blacklisted_users.json')
    BLACKLISTED_CHANNELS = load_blacklist('blacklisted_channels.json')
    await interaction.response.send_message("Blacklists reloaded.")

@reload_blacklists.error
async def reload_blacklists_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message("An error occurred while executing the command.", ephemeral=True)


# Load the token from file
with open(os.path.expanduser('token.txt'), 'r') as file:
    TOKEN = file.read().strip()

bot.run(TOKEN)
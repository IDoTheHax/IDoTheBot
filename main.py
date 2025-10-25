import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from cogs.sys.tickets import TicketView
import datetime as dt
import aiohttp
import json
import os
import time
from dotenv import load_dotenv
import logging


bot = commands.Bot(command_prefix='/', intents=discord.Intents.all())

# Load environment variables from the .env file
load_dotenv()

# Access the token from the environment variable
TOKEN = os.getenv("BOT_TOKEN")
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", 1362041490779672576))  # Add BOT_OWNER_ID to .env

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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def load_cogs():
    for root, dirs, files in os.walk("./cogs"):  # Recursively walks through the cogs directory
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                # Create a module path, replacing the slashes with dots
                cog_path = os.path.join(root, file).replace("./", "").replace("\\", ".").replace("/", ".")
                cog_path = cog_path[:-3]  # Remove the .py extension
                
                try:
                    await bot.load_extension(cog_path)
                    print(f"Loaded {cog_path}")
                except Exception as e:
                    print(f"Failed to load {cog_path}: {e}")

def is_bot_owner():
    def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.id == BOT_OWNER_ID
    return app_commands.check(predicate)

# When bot starts
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    
    await load_cogs()
    # Register the view for each guild the bot is in
    for guild in bot.guilds:
        view = TicketView(guild.id)
        bot.add_view(view)
    print(f"Views have been registered for {len(bot.guilds)} guilds.")

    try:
        #BLACKLISTED_USERS = load_blacklist('blacklisted_users.json')
        #BLACKLISTED_CHANNELS = load_blacklist('blacklisted_channels.json')
        synced = await bot.tree.sync()

        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

@bot.tree.command(name="reload", description="Reload all cogs or a specific cog (bot owner only)")
@app_commands.describe(cog_name="Name of the specific cog to reload (optional, e.g., sys.tickets)")
@is_bot_owner()
async def reload(interaction: discord.Interaction, cog_name: str = None):
    """Reload all cogs or a specific cog."""
    await interaction.response.defer(ephemeral=True)
    try:
        if cog_name:
            # Reload a specific cog
            try:
                await bot.reload_extension(cog_name)
                logger.info(f"Reloaded cog: {cog_name}")
                await interaction.followup.send(f"Reloaded cog: `{cog_name}`", ephemeral=True)
            except commands.ExtensionNotLoaded:
                await interaction.followup.send(f"Cog `{cog_name}` is not loaded.", ephemeral=True)
            except commands.ExtensionNotFound:
                await interaction.followup.send(f"Cog `{cog_name}` not found.", ephemeral=True)
            except Exception as e:
                logger.error(f"Failed to reload cog {cog_name}: {e}")
                await interaction.followup.send(f"Failed to reload cog `{cog_name}`: {e}", ephemeral=True)
        else:
            # Reload all cogs
            reloaded = []
            for root, dirs, files in os.walk("./cogs"):
                for file in files:
                    if file.endswith(".py") and file != "__init__.py":
                        cog_path = os.path.join(root, file).replace("./", "").replace("\\", ".").replace("/", ".")
                        cog_path = cog_path[:-3]  # Remove .py extension
                        try:
                            await bot.reload_extension(cog_path)
                            reloaded.append(cog_path)
                            logger.info(f"Reloaded cog: {cog_path}")
                        except Exception as e:
                            logger.error(f"Failed to reload cog {cog_path}: {e}")
                            await interaction.followup.send(f"Failed to reload cog `{cog_path}`: {e}", ephemeral=True)
            if reloaded:
                await interaction.followup.send(f"Reloaded cogs: {', '.join(reloaded)}", ephemeral=True)
            else:
                await interaction.followup.send("No cogs were reloaded.", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in reload command: {e}")
        await interaction.followup.send(f"Error: {e}", ephemeral=True)

@reload.error
async def reload_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
    else:
        logger.error(f"Error in reload command: {error}")
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)

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
    if not message.guild or not should_log(message):
        return

    log_channel = get_log_channel(message.guild)
    if not log_channel:
        return

    embed = discord.Embed(
        title=f"{message.author}'s Message Was Deleted",
        description=f"Deleted Message: {message.content}\nAuthor: {message.author.mention}\nLocation: {message.channel.mention}",
        timestamp=datetime.now(),
        color=discord.Color.red()
    )
    await log_channel.send(embed=embed)

# Log on edit
@bot.event
async def on_message_edit(message_before, message_after):
    if not message_before.guild or not should_log(message_before):
        return

    log_channel = get_log_channel(message_before.guild)
    if not log_channel:
        return

    embed = discord.Embed(
        title=f"{message_before.author}'s Message Was Edited",
        description=f"Before: {message_before.content}\nAfter: {message_after.content}\nAuthor: {message_before.author.mention}\nLocation: {message_before.channel.mention}",
        timestamp=datetime.now(),
        color=discord.Color.blue()
    )
    await log_channel.send(embed=embed)

@bot.tree.command(name="embed", description="Create an embed message")
@app_commands.describe(
    title="Embed title", 
    description="Embed description (use \\n for newlines)", 
    color="Embed color (hex code without #, e.g. FF5733)"
)
async def embed(interaction: discord.Interaction, title: str, description: str, color: str = "2F3136"):
    start_time = time.time()
    try:
        # Log and defer immediately
        logger.info(f"Received /embed command, deferring response")
        await interaction.response.defer(ephemeral=False)
        logger.info(f"Deferred response in {time.time() - start_time:.2f} seconds")

        # Validate inputs
        if len(title) > 256:
            await interaction.followup.send("Title is too long (max 256 characters).", ephemeral=True)
            return
        if len(description) > 4096:
            await interaction.followup.send("Description is too long (max 4096 characters).", ephemeral=True)
            return

        # Process description
        formatted_description = description.replace("\\n", "\n")
        
        # Convert hex color to integer
        try:
            color_int = int(color, 16)
        except ValueError:
            color_int = 0x2F3136  # Default color
            
        embed = discord.Embed(
            title=title,
            description=formatted_description,
            color=color_int
        )
        
        # Send the embed
        await interaction.followup.send(embed=embed)
        logger.info(f"Embed sent in {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in embed command after {time.time() - start_time:.2f} seconds: {str(e)}")
        try:
            await interaction.followup.send(f"Error creating embed: {str(e)}", ephemeral=True)
        except Exception as followup_error:
            logger.error(f"Failed to send error message: {str(followup_error)}")

@bot.tree.command(name="editembed", description="Edit embed messages by its id")
@app_commands.describe(message_id="Message ID", title="Embed title", description="Embed description", color="Embed color (hex)")
async def editembed(ctx, message_id: str, title: str, description: str, color: str):
    message = await ctx.channel.fetch_message(int(message_id))  # Fetch the message by ID

    new_embed = discord.Embed(
        title=title,
        description=description,
        color=int(color, 16),
    )
    await message.edit(embed=new_embed)
    await ctx.response.send_message("Successfully Edited Embed", ephemeral=False)

@bot.tree.command(name="github", description="Get information about a GitHub repository")
@app_commands.describe(username="GitHub username", repository="Repository name")
async def github(interaction: discord.Interaction, username: str, repository: str):
    url = f'https://api.github.com/repos/{username}/{repository}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            try:
                data = await resp.json()
            except Exception:
                data = {}
            if resp.status != 200:
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
@app_commands.checks.has_permissions(administrator=True)
async def reload_blacklists(interaction: discord.Interaction):
    global BLACKLISTED_USERS, BLACKLISTED_CHANNELS
    BLACKLISTED_USERS = load_blacklist('blacklisted_users.json')
    BLACKLISTED_CHANNELS = load_blacklist('blacklisted_channels.json')
    await interaction.response.send_message("Blacklists reloaded.")

@bot.tree.command(name="giverole", description="Assign a role to a user by role ID")
@app_commands.describe(member="The user to give the role to", role_id="The ID of the role to assign (e.g., 1201518458739892334)")
@app_commands.checks.has_permissions(administrator=True)
async def giverole(interaction: discord.Interaction, member: discord.Member, role_id: str):
    try:
        # Log the input for debugging
        logger.info(f"Received /giverole: member={member.id}, role_id={role_id}")

        # Validate role_id as a string and convert to integer
        if not role_id.isdigit():
            await interaction.response.send_message(
                "Please provide a valid role ID (must be a positive integer, e.g., 1201518458739892334).",
                ephemeral=True
            )
            return

        role_id_int = int(role_id)  # Convert to integer for role lookup

        # Validate role_id range (Discord snowflake IDs are 64-bit)
        if role_id_int <= 0 or role_id_int > 2**64 - 1:
            await interaction.response.send_message(
                "Please provide a valid role ID (positive integer within Discord's ID range).",
                ephemeral=True
            )
            return

        # Fetch the role
        role = interaction.guild.get_role(role_id_int)
        if role is None:
            await interaction.response.send_message(
                f"No role found with ID `{role_id}`. Please check the ID and try again.",
                ephemeral=True
            )
            return

        # Check if the bot has permission to assign the role
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "I don’t have permission to manage roles. Please check my permissions.",
                ephemeral=True
            )
            return

        # Check if the bot's role is higher than the target role
        if role.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message(
                "I can’t assign this role because it’s higher than or equal to my highest role.",
                ephemeral=True
            )
            return

        # Assign the role
        await member.add_roles(role)
        await interaction.response.send_message(
            f"Successfully assigned {role.name} to {member.mention}",
            ephemeral=True
        )

    except ValueError:
        logger.error(f"ValueError: Invalid role_id format: {role_id}")
        await interaction.response.send_message(
            "Please provide a valid role ID (must be a positive integer, e.g., 1201518458739892334).",
            ephemeral=True
        )
    except discord.app_commands.AppCommandError as ae:
        logger.error(f"AppCommandError in giverole: {ae}")
        await interaction.response.send_message(
            f"Command error: {str(ae)}",
            ephemeral=True
        )
    except discord.Forbidden:
        logger.error("Forbidden error: Bot lacks permissions")
        await interaction.response.send_message(
            "I don’t have permission to assign roles. Please check my permissions and role hierarchy.",
            ephemeral=True
        )
    except Exception as e:
        logger.error(f"Unexpected error in giverole: {e}")
        await interaction.response.send_message(
            f"An unexpected error occurred: {str(e)}. Please try again or contact the bot owner.",
            ephemeral=True
        )

@reload_blacklists.error
async def reload_blacklists_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message("An error occurred while executing the command.", ephemeral=True)

bot.run(TOKEN)
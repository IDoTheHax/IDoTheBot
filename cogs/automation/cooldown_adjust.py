import discord
from discord.ext import commands, tasks
from collections import defaultdict
from datetime import datetime, timedelta
import json
import os

class CooldownManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_activity = defaultdict(list)  # Stores message timestamps per channel
        self.cooldown_settings_path = 'settings/cooldown_manager.json'
        self.update_cooldown.start()  # Starts the task to check and update cooldowns

    def cog_unload(self):
        self.update_cooldown.cancel()  # Cancel the task when cog is unloaded

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore bots or DMs
        if message.author.bot or not message.guild:
            return

        # Add the message's timestamp to the list for the corresponding channel
        self.channel_activity[message.channel.id].append(datetime.utcnow())

    @tasks.loop(minutes=1)
    async def update_cooldown(self):
        """Task that runs every minute to check activity and adjust cooldown."""
        now = datetime.utcnow()

        for channel_id, timestamps in self.channel_activity.items():
            # Remove messages older than 1 minute
            self.channel_activity[channel_id] = [ts for ts in timestamps if now - ts < timedelta(minutes=1)]

            # Calculate messages per minute in this channel
            messages_per_minute = len(self.channel_activity[channel_id])

            # Determine the slow mode based on activity
            cooldown = self.calculate_cooldown(messages_per_minute)

            # Get the channel object
            channel = self.bot.get_channel(channel_id)
            if channel and channel.slowmode_delay != cooldown:  # Only edit if cooldown has changed
                await channel.edit(slowmode_delay=cooldown)
                print(f"Updated slow mode in {channel.name} to {cooldown} seconds.")

    def calculate_cooldown(self, messages_per_minute):
        """Determine the cooldown (slow mode) based on the number of messages per minute."""
        if messages_per_minute > 50:
            return 10  # High activity -> 10 seconds cooldown
        elif messages_per_minute > 30:
            return 5   # Medium activity -> 5 seconds cooldown
        elif messages_per_minute > 10:
            return 3   # Low activity -> 3 seconds cooldown
        else:
            return 0   # Very low activity -> No cooldown

    async def save_cooldown_settings(self, guild_id, settings):
        """Save the cooldown settings for the specified guild to a JSON file."""
        try:
            if os.path.exists(self.cooldown_settings_path):
                with open(self.cooldown_settings_path, 'r') as f:
                    data = json.load(f)
            else:
                data = {}

            data[guild_id] = settings

            with open(self.cooldown_settings_path, 'w') as f:
                json.dump(data, f, indent=4)

        except Exception as e:
            print(f"Error saving cooldown settings: {e}")

    def load_cooldown_settings(self, guild_id):
        """Load the cooldown settings for the specified guild from a JSON file."""
        try:
            with open(self.cooldown_settings_path, 'r') as f:
                data = json.load(f)
                return data.get(guild_id)
        except FileNotFoundError:
            return None

    @discord.app_commands.command(name="set_cooldown", description="Set the cooldown settings for this guild.")
    async def set_cooldown(self, interaction: discord.Interaction, cooldown: int, threshold: int):
        """Set the cooldown time and threshold for the guild."""
        guild_id = str(interaction.guild.id)

        settings = {
            'cooldown': cooldown,
            'threshold': threshold
        }

        await self.save_cooldown_settings(guild_id, settings)
        await interaction.response.send_message(f"Cooldown settings updated:\nCooldown: {cooldown}\nThreshold: {threshold}")

    @discord.app_commands.command(name="get_cooldown", description="Get the current cooldown settings for this guild.")
    async def get_cooldown(self, interaction: discord.Interaction):
        """Retrieve the current cooldown settings for the guild."""
        guild_id = str(interaction.guild.id)
        cooldown_settings = self.load_cooldown_settings(guild_id)

        if cooldown_settings:
            await interaction.response.send_message(
                f"Current cooldown settings for this guild:\n"
                f"Cooldown Time: {cooldown_settings['cooldown']}\n"
                f"Threshold: {cooldown_settings['threshold']}"
            )
        else:
            await interaction.response.send_message("No cooldown settings found for this guild. Please set them first.")

    @update_cooldown.before_loop
    async def before_update_cooldown(self):
        """Wait until the bot is ready before starting the task."""
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(CooldownManager(bot))

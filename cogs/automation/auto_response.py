import discord
from discord.ext import commands
from discord import app_commands
import json
from pathlib import Path

# Path to the directory where autoresponse settings will be stored
AUTORESPONSE_SETTINGS_DIR = Path("settings/autoresponse_settings")

# Ensure the directory exists
AUTORESPONSE_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)

# Load and save functions
def load_autoresponse_settings():
    settings_file = AUTORESPONSE_SETTINGS_DIR / "autoresponses.json"
    if settings_file.exists():
        with open(settings_file, "r") as file:
            return json.load(file)
    return {}

def save_autoresponse_settings(data):
    settings_file = AUTORESPONSE_SETTINGS_DIR / "autoresponses.json"
    with open(settings_file, "w") as file:
        json.dump(data, file, indent=4)

# AutoResponseCog
class AutoResponseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Create a group for the autoresponse commands
    autoresponse = app_commands.Group(name="autoresponse", description="Manage auto-responses")

    @autoresponse.command(name="create", description="Create an auto-response")
    @commands.has_permissions(manage_messages=True)
    async def create_autoresponse(self, interaction: discord.Interaction, trigger: str, response: str):
        """Create a new auto-response."""
        settings = load_autoresponse_settings()

        # Check if the trigger already exists
        if any(item["trigger"] == trigger for item in settings.get("responses", [])):
            await interaction.response.send_message(f"An auto-response already exists for the trigger '{trigger}'.", ephemeral=True)
            return

        # Add the new auto-response
        new_response = {"trigger": trigger, "response": response}
        settings.setdefault("responses", []).append(new_response)
        save_autoresponse_settings(settings)

        await interaction.response.send_message(f"Auto-response created for trigger '{trigger}'.", ephemeral=True)

    @autoresponse.command(name="remove", description="Remove an auto-response")
    @commands.has_permissions(manage_messages=True)
    async def remove_autoresponse(self, interaction: discord.Interaction, trigger: str):
        """Remove an existing auto-response."""
        settings = load_autoresponse_settings()

        # Find the auto-response by trigger
        responses = settings.get("responses", [])
        response_to_remove = next((item for item in responses if item["trigger"] == trigger), None)
        
        if not response_to_remove:
            await interaction.response.send_message(f"No auto-response found for the trigger '{trigger}'.", ephemeral=True)
            return

        # Remove the auto-response
        responses.remove(response_to_remove)
        save_autoresponse_settings(settings)

        await interaction.response.send_message(f"Auto-response for trigger '{trigger}' removed.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages and respond with the appropriate auto-response."""
        # Ensure the bot does not respond to itself
        if message.author == self.bot.user:
            return

        settings = load_autoresponse_settings()
        responses = settings.get("responses", [])

        # Check if there's an auto-response for the message content
        for response in responses:
            if message.content == response["trigger"]:
                await message.reply(response["response"])

async def setup(bot):
    await bot.add_cog(AutoResponseCog(bot))

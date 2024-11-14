import os
import json
import discord
from discord.ext import commands
from discord import app_commands, Interaction
from typing import Optional

CONFIG_PATH = "settings/twitch/config.json"

class Twitch(commands.GroupCog, name="twitch"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ensure_settings_path()

    def ensure_settings_path(self):
        os.makedirs(SETTINGS_PATH, exist_ok=True)

    def get_guild_config(self, guild_id: int):
        """Fetch the configuration for a specific guild."""
        path = os.path.join(SETTINGS_PATH, f"{guild_id}.json")
        if not os.path.exists(path):
            return {"updates_channel": None, "listeners": []}
        with open(path, "r") as f:
            return json.load(f)

    def save_guild_config(self, guild_id: int, config: dict):
        """Save the configuration for a specific guild."""
        path = os.path.join(SETTINGS_PATH, f"{guild_id}.json")
        with open(path, "w") as f:
            json.dump(config, f, indent=4)

    @app_commands.command(name="set_updates_channel", description="Set the channel for Twitch updates.")
    @app_commands.describe(channel="The channel where Twitch updates will be posted.")
    async def set_updates_channel(self, interaction: Interaction, channel: discord.TextChannel):
        """Set the channel for Twitch updates."""
        guild_id = interaction.guild_id
        config = self.get_guild_config(guild_id)

        config["updates_channel"] = channel.id
        self.save_guild_config(guild_id, config)

        await interaction.response.send_message(
            f"Twitch updates channel has been set to {channel.mention}.", ephemeral=True
        )

    @app_commands.command(name="add_listener", description="Add a Twitch streamer to the listener list.")
    @app_commands.describe(handle="The Twitch handle to listen for.")
    async def add_listener(self, interaction: Interaction, handle: str):
        """Add a Twitch streamer to the listener list."""
        guild_id = interaction.guild_id
        config = self.get_guild_config(guild_id)

        if handle in config["listeners"]:
            await interaction.response.send_message(
                f"Twitch handle `{handle}` is already being listened to.", ephemeral=True
            )
            return

        config["listeners"].append(handle)
        self.save_guild_config(guild_id, config)

        await interaction.response.send_message(
            f"Now listening for when `{handle}` goes live.", ephemeral=True
        )

    @app_commands.command(name="remove_listener", description="Remove a Twitch streamer from the listener list.")
    @app_commands.describe(handle="The Twitch handle to remove.")
    async def remove_listener(self, interaction: Interaction, handle: str):
        """Remove a Twitch streamer from the listener list."""
        guild_id = interaction.guild_id
        config = self.get_guild_config(guild_id)

        if handle not in config["listeners"]:
            listeners = "\n".join(config["listeners"]) or "No listeners added."
            await interaction.response.send_message(
                f"The handle `{handle}` is not in the listener list. Current listeners:\n```\n{listeners}\n```",
                ephemeral=True,
            )
            return

        config["listeners"].remove(handle)
        self.save_guild_config(guild_id, config)

        await interaction.response.send_message(
            f"Stopped listening for `{handle}`.", ephemeral=True
        )

    @app_commands.command(name="list_listeners", description="List all Twitch streamers being listened to.")
    async def list_listeners(self, interaction: Interaction):
        """List all Twitch streamers being listened to."""
        guild_id = interaction.guild_id
        config = self.get_guild_config(guild_id)

        listeners = config["listeners"]
        if not listeners:
            await interaction.response.send_message(
                "No Twitch handles are being listened to.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Currently listening for the following Twitch handles:\n```\n{', '.join(listeners)}\n```",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Twitch(bot))
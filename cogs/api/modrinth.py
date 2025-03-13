import discord
from discord.ext import commands, tasks
from discord import app_commands
import requests
import json
import os
from datetime import datetime

class ModrinthStats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data_file = "data/modrinth.json"
        self.tracked_projects = {}  # Dictionary to store tracked project data
        self.notification_channel_id = None  # Channel ID for notifications
        self.load_data()  # Load data from file on startup
        self.check_updates.start()  # Start the background task

    def cog_unload(self):
        self.check_updates.cancel()  # Stop the background task when the cog is unloaded

    def load_data(self):
        """Load tracked projects and notification channel from modrinth.json."""
        if not os.path.exists("data"):
            os.makedirs("data")  # Create data directory if it doesn't exist

        try:
            with open(self.data_file, "r") as f:
                data = json.load(f)
                self.tracked_projects = data.get("tracked_projects", {})
                self.notification_channel_id = data.get("notification_channel_id")
        except FileNotFoundError:
            self.save_data()  # Create the file if it doesn't exist
        except json.JSONDecodeError:
            print("Error decoding modrinth.json. Starting with empty data.")
            self.save_data()

    def save_data(self):
        """Save tracked projects and notification channel to modrinth.json."""
        data = {
            "tracked_projects": self.tracked_projects,
            "notification_channel_id": self.notification_channel_id,
        }
        with open(self.data_file, "w") as f:
            json.dump(data, f, indent=4)

    @tasks.loop(minutes=5)  # Check every 5 minutes
    async def check_updates(self):
        if not self.notification_channel_id:
            return  # Skip if no notification channel is set

        channel = self.bot.get_channel(self.notification_channel_id)
        if not channel:
            print("Notification channel not found!")
            return

        for mod_slug, last_data in self.tracked_projects.items():
            url = f"https://api.modrinth.com/v2/project/{mod_slug}"
            try:
                response = requests.get(url)
                if response.status_code != 200:
                    continue  # Skip if the project is not found

                data = response.json()

                # Check for new versions
                latest_version = data.get("versions", [])[-1] if data.get("versions") else None
                last_version = last_data.get("latest_version")

                if latest_version and latest_version != last_version:
                    embed = discord.Embed(
                        title=f"New Version Released for {data.get('title', 'Unknown')}",
                        description=f"A new version has been released for [{mod_slug}](https://modrinth.com/mod/{mod_slug}).",
                        color=discord.Color.blue(),
                    )
                    embed.add_field(name="Latest Version", value=latest_version, inline=False)
                    await channel.send(embed=embed)

                # Check for changes in follows (hearts)
                current_follows = data.get("follows", 0)
                last_follows = last_data.get("follows", 0)

                if current_follows > last_follows:
                    embed = discord.Embed(
                        title=f"New Follow for {data.get('title', 'Unknown')}",
                        description=f"The mod [{mod_slug}](https://modrinth.com/mod/{mod_slug}) gained a new follow!",
                        color=discord.Color.green(),
                    )
                    embed.add_field(name="Total Follows", value=f"{current_follows:,}", inline=False)
                    await channel.send(embed=embed)

                # Update tracked data
                self.tracked_projects[mod_slug] = {
                    "latest_version": latest_version,
                    "follows": current_follows,
                }
                self.save_data()  # Save updated data to file

            except Exception as e:
                print(f"Error checking updates for {mod_slug}: {e}")

    @check_updates.before_loop
    async def before_check_updates(self):
        await self.bot.wait_until_ready()  # Wait for the bot to ready up before starting the task

    @app_commands.command(name="trackmod", description="Start tracking updates for a Modrinth mod.")
    @app_commands.describe(mod="The slug or name of the mod to track.")
    async def track_mod(self, interaction: discord.Interaction, mod: str):
        """Start tracking updates for a Modrinth mod."""
        await interaction.response.defer()

        url = f"https://api.modrinth.com/v2/project/{mod}"
        try:
            response = requests.get(url)
            if response.status_code != 200:
                await interaction.followup.send("Could not find the mod. Please check the mod name or slug.")
                return

            data = response.json()

            # Store initial data for tracking
            self.tracked_projects[mod] = {
                "latest_version": data.get("versions", [])[-1] if data.get("versions") else None,
                "follows": data.get("follows", 0),
            }
            self.save_data()  # Save updated data to file

            await interaction.followup.send(f"Now tracking updates for `{mod}`. Notifications will be sent to the set notification channel.")
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")

    @app_commands.command(name="setnotificationchannel", description="Set the channel for Modrinth update notifications.")
    @app_commands.describe(channel="The channel to send notifications to.")
    async def set_notification_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the channel for Modrinth update notifications."""
        await interaction.response.defer()

        self.notification_channel_id = channel.id
        self.save_data()  # Save updated data to file

        await interaction.followup.send(f"Notification channel set to {channel.mention}.")

    @app_commands.command(name="mrmodrinth", description="Get stats about a Modrinth mod.")
    @app_commands.describe(mod="The slug or name of the mod to fetch stats for.")
    async def stats(self, interaction: discord.Interaction, mod: str):
        """Fetch and display stats for a Modrinth mod."""
        await interaction.response.defer()

        # Modrinth API Endpoint
        url = f"https://api.modrinth.com/v2/project/{mod}"

        try:
            # Fetch the mod data
            response = requests.get(url)
            if response.status_code != 200:
                await interaction.followup.send("Could not find the mod. Please check the mod name or slug.")
                return

            data = response.json()

            # Extract required fields
            name = data.get("title", "Unknown")
            tags = ", ".join(data.get("categories", [])) or "None"
            downloads = data.get("downloads", 0)
            hearts = data.get("follows", 0)

            # Extract platforms (mod loaders)
            loaders = data.get("loaders", [])
            platforms = ", ".join([loader.capitalize() for loader in loaders]) if loaders else "Unknown"

            # Extract environments (client/server compatibility)
            client_side = data.get("client_side", "unsupported")
            server_side = data.get("server_side", "unsupported")

            environments = []
            if client_side == "required":
                environments.append("Client")
            if server_side == "required":
                environments.append("Server")

            # Format environments
            if not environments:
                environments.append("None")
            environments = ", ".join(environments)

            description = data.get("description", "No description available.")

            versions = data.get("game_versions", [])
            mc_version = ", ".join(versions) if versions else "Unknown"

            if len(mc_version) > 1024:
                mc_version = mc_version[:1021] + "..."  # Safeguard for length

            # Create the embed
            embed = discord.Embed(
                title=f"{name} - Mod Stats",
                description=description,
                color=discord.Color.green(),
                url=f"https://modrinth.com/mod/{mod}",
            )
            embed.add_field(name="Tags", value=tags, inline=False)
            embed.add_field(name="Downloads", value=f"{downloads:,}", inline=True)
            embed.add_field(name="Hearts", value=f"{hearts:,}", inline=True)
            embed.add_field(name="Loaders", value=platforms, inline=True)
            embed.add_field(name="Environments", value=environments, inline=True)
            embed.add_field(name="Versions", value=mc_version, inline=True)
            embed.set_footer(text="Data fetched from Modrinth API")

            # Send the embed
            view = ChangelogButton(mod)
            await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")


class ChangelogButton(discord.ui.View):
    def __init__(self, mod_slug):
        super().__init__()
        self.mod_slug = mod_slug

    @discord.ui.button(label="Show Versions", style=discord.ButtonStyle.primary)
    async def show_versions(self, interaction: discord.Interaction, button: discord.ui.Button):
        url = f"https://api.modrinth.com/v2/project/{self.mod_slug}/version"
        response = requests.get(url)
        if response.status_code != 200:
            await interaction.response.send_message("Could not fetch versions.")
            return

        versions = response.json()
        embed = discord.Embed(title=f"Versions for {self.mod_slug}", color=discord.Color.blue())

        for version in versions[:5]:  # Limit to 5 versions
            embed.add_field(
                name=version.get("version_number", "Unknown"),
                value=version.get("changelog", "No changelog available."),
                inline=False,
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ModrinthStats(bot))

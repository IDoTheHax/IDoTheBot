import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from cachetools import TTLCache

class ModrinthStats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data_file = "data/modrinth.json"
        self.tracked_projects = {}  # Dictionary to store tracked project data
        self.notification_channel_id = None  # Channel ID for notifications
        self.cache = TTLCache(maxsize=100, ttl=300)  # Cache for 5 minutes
        self.request_semaphore = asyncio.Semaphore(10)  # Rate limiting
        self.milestones = [1000, 5000, 10000, 25000, 50000, 100000, 250000, 500000, 1000000]
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
                
                # Migrate old data structure to new format with milestones
                for mod_slug, mod_data in self.tracked_projects.items():
                    if "achieved_milestones" not in mod_data:
                        mod_data["achieved_milestones"] = []
                    if "last_checked" not in mod_data:
                        mod_data["last_checked"] = datetime.now().isoformat()
                    if "title" not in mod_data:
                        mod_data["title"] = mod_slug
                        
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

    async def fetch_with_cache(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Fetch data from URL with caching and rate limiting."""
        cache_key = f"{url}:{headers}"
        
        # Check cache first
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Rate limiting
        async with self.request_semaphore:
            try:
                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            self.cache[cache_key] = data
                            return data
                        elif resp.status == 429:  # Rate limited
                            retry_after = int(resp.headers.get("Retry-After", 60))
                            print(f"Rate limited, waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                            return await self.fetch_with_cache(url, headers)
                        return None
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                return None

    async def get_modrinth_data(self, mod_slug: str) -> Optional[Dict[str, Any]]:
        """Fetch mod data from Modrinth API with caching."""
        url = f"https://api.modrinth.com/v2/project/{mod_slug}"
        return await self.fetch_with_cache(url)

    async def check_milestones(self, mod_slug: str, current_downloads: int, last_downloads: int, mod_title: str, channel) -> None:
        """Check and notify about download milestones."""
        achieved = self.tracked_projects[mod_slug].get("achieved_milestones", [])
        
        for milestone in self.milestones:
            if current_downloads >= milestone and milestone not in achieved:
                # New milestone reached!
                achieved.append(milestone)
                embed = discord.Embed(
                    title=f"🎉 Milestone Reached: {mod_title}",
                    description=f"The mod [{mod_slug}](https://modrinth.com/mod/{mod_slug}) just hit **{milestone:,}** downloads!",
                    color=discord.Color.gold(),
                    timestamp=datetime.now()
                )
                embed.set_footer(text=f"Total Downloads: {current_downloads:,}")
                await channel.send(embed=embed)
        
        self.tracked_projects[mod_slug]["achieved_milestones"] = achieved

    async def check_milestones(self, mod_slug: str, current_downloads: int, last_downloads: int, mod_title: str, channel) -> None:
        """Check and notify about download milestones."""
        achieved = self.tracked_projects[mod_slug].get("achieved_milestones", [])
        
        for milestone in self.milestones:
            if current_downloads >= milestone and milestone not in achieved:
                # New milestone reached!
                achieved.append(milestone)
                embed = discord.Embed(
                    title=f"🎉 Milestone Reached: {mod_title}",
                    description=f"The mod [{mod_slug}](https://modrinth.com/mod/{mod_slug}) just hit **{milestone:,}** downloads!",
                    color=discord.Color.gold(),
                    timestamp=datetime.now()
                )
                embed.set_footer(text=f"Total Downloads: {current_downloads:,}")
                await channel.send(embed=embed)
        
        self.tracked_projects[mod_slug]["achieved_milestones"] = achieved

    @tasks.loop(minutes=5)  # Check every 5 minutes
    async def check_updates(self):
        if not self.notification_channel_id:
            return  # Skip if no notification channel is set

        channel = self.bot.get_channel(self.notification_channel_id)
        if not channel:
            print("Notification channel not found!")
            return

        for mod_slug, last_data in self.tracked_projects.items():
            try:
                data = await self.get_modrinth_data(mod_slug)
                if not data:
                    continue

                mod_title = data.get("title", last_data.get("title", mod_slug))
                
                # Update title if changed
                self.tracked_projects[mod_slug]["title"] = mod_title
                self.tracked_projects[mod_slug]["last_checked"] = datetime.now().isoformat()

                # Check for new versions
                latest_version = data.get("versions", [])[-1] if data.get("versions") else None
                last_version = last_data.get("latest_version")

                if latest_version and latest_version != last_version:
                    embed = discord.Embed(
                        title=f"🆕 New Version: {mod_title}",
                        description=f"A new version has been released for [{mod_slug}](https://modrinth.com/mod/{mod_slug}).",
                        color=discord.Color.blue(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="Latest Version", value=latest_version, inline=False)
                    await channel.send(embed=embed)
                    self.tracked_projects[mod_slug]["latest_version"] = latest_version

                # Check for changes in follows (hearts)
                current_follows = data.get("follows", 0)
                last_follows = last_data.get("follows", 0)

                if current_follows > last_follows:
                    diff = current_follows - last_follows
                    embed = discord.Embed(
                        title=f"❤️ New Followers: {mod_title}",
                        description=f"The mod [{mod_slug}](https://modrinth.com/mod/{mod_slug}) gained **{diff:,}** new follower(s)!",
                        color=discord.Color.green(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="Total Follows", value=f"{current_follows:,}", inline=False)
                    await channel.send(embed=embed)
                    self.tracked_projects[mod_slug]["follows"] = current_follows

                # Check downloads and milestones
                current_downloads = data.get("downloads", 0)
                last_downloads = last_data.get("total_downloads", 0)
                
                if current_downloads > last_downloads:
                    await self.check_milestones(mod_slug, current_downloads, last_downloads, mod_title, channel)
                    self.tracked_projects[mod_slug]["total_downloads"] = current_downloads

                self.save_data()  # Save updated data to file

            except Exception as e:
                print(f"Error checking updates for {mod_slug}: {e}")

    @check_updates.before_loop
    async def before_check_updates(self):
        await self.bot.wait_until_ready()  # Wait for the bot to ready up before starting the task

    # Create command group
    mcmod_group = app_commands.Group(name="mcmod", description="Minecraft mod tracking and statistics")

    @mcmod_group.command(name="stats", description="Get detailed stats about a Minecraft mod")
    @app_commands.describe(mod="The Modrinth slug or name of the mod")
    async def stats(self, interaction: discord.Interaction, mod: str):
        """Fetch and display stats for a mod from Modrinth."""
        await interaction.response.defer()

        data = await self.get_modrinth_data(mod)
        if not data:
            await interaction.followup.send("Could not find the mod on Modrinth. Please check the mod name or slug.")
            return

        # Extract stats
        name = data.get("title", "Unknown")
        tags = ", ".join(data.get("categories", [])) or "None"
        downloads = data.get("downloads", 0)
        follows = data.get("follows", 0)
        loaders = ", ".join([loader.capitalize() for loader in data.get("loaders", [])]) or "Unknown"
        client_side = data.get("client_side", "unsupported")
        server_side = data.get("server_side", "unsupported")
        environments = []
        if client_side == "required":
            environments.append("Client")
        if server_side == "required":
            environments.append("Server")
        environments = ", ".join(environments) or "None"
        description = data.get("description", "No description available.")
        mc_version = ", ".join(data.get("game_versions", [])[:10]) or "Unknown"
        if len(data.get("game_versions", [])) > 10:
            mc_version += f" (+{len(data.get('game_versions', [])) - 10} more)"

        # Create the embed
        embed = discord.Embed(
            title=f"📊 {name}",
            description=description,
            color=discord.Color.green(),
            url=f"https://modrinth.com/mod/{mod}",
            timestamp=datetime.now()
        )
        embed.add_field(name="Categories", value=tags, inline=False)
        embed.add_field(name="Downloads", value=f"{downloads:,}", inline=True)
        embed.add_field(name="Followers", value=f"{follows:,}", inline=True)
        embed.add_field(name="Loaders", value=loaders, inline=True)
        embed.add_field(name="Environments", value=environments, inline=True)
        embed.add_field(name="MC Versions", value=mc_version, inline=False)
        
        # Check if tracked
        is_tracked = mod in self.tracked_projects
        if is_tracked:
            embed.set_footer(text="✅ This mod is currently being tracked")
        else:
            embed.set_footer(text="Use /mcmod track to start tracking this mod")

        # Send with version button
        view = VersionButton(self, mod)
        await interaction.followup.send(embed=embed, view=view)

    @mcmod_group.command(name="track", description="Start tracking a mod for updates and milestones")
    @app_commands.describe(mod="The Modrinth slug or name of the mod to track")
    async def track(self, interaction: discord.Interaction, mod: str):
        """Start tracking updates for a mod."""
        await interaction.response.defer()

        # Check if already tracked
        if mod in self.tracked_projects:
            await interaction.followup.send(f"❌ `{mod}` is already being tracked!")
            return

        data = await self.get_modrinth_data(mod)
        if not data:
            await interaction.followup.send("Could not find the mod on Modrinth. Please check the mod name or slug.")
            return

        # Store initial data for tracking
        self.tracked_projects[mod] = {
            "title": data.get("title", mod),
            "latest_version": data.get("versions", [])[-1] if data.get("versions") else None,
            "follows": data.get("follows", 0),
            "total_downloads": data.get("downloads", 0),
            "achieved_milestones": [m for m in self.milestones if data.get("downloads", 0) >= m],
            "last_checked": datetime.now().isoformat()
        }

        self.save_data()

        embed = discord.Embed(
            title="✅ Tracking Started",
            description=f"Now tracking **{data.get('title', mod)}** for updates!",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Current Stats", value=f"Downloads: {data.get('downloads', 0):,}\nFollowers: {data.get('follows', 0):,}", inline=False)
        embed.set_footer(text="Notifications will be sent to the configured channel")
        await interaction.followup.send(embed=embed)

    @mcmod_group.command(name="untrack", description="Stop tracking a mod")
    @app_commands.describe(mod="The Modrinth slug of the mod to stop tracking")
    async def untrack(self, interaction: discord.Interaction, mod: str):
        """Stop tracking a mod."""
        await interaction.response.defer()

        if mod not in self.tracked_projects:
            await interaction.followup.send(f"❌ `{mod}` is not being tracked!")
            return

        mod_title = self.tracked_projects[mod].get("title", mod)
        del self.tracked_projects[mod]
        self.save_data()

        embed = discord.Embed(
            title="🛑 Tracking Stopped",
            description=f"No longer tracking **{mod_title}**",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        await interaction.followup.send(embed=embed)

    @mcmod_group.command(name="list", description="List all tracked mods")
    async def list_tracked(self, interaction: discord.Interaction):
        """List all currently tracked mods."""
        await interaction.response.defer()

        if not self.tracked_projects:
            await interaction.followup.send("No mods are currently being tracked. Use `/mcmod track` to start tracking!")
            return

        embed = discord.Embed(
            title="📋 Tracked Mods",
            description=f"Currently tracking **{len(self.tracked_projects)}** mod(s)",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        for mod_slug, mod_data in list(self.tracked_projects.items())[:25]:  # Limit to 25 for embed
            title = mod_data.get("title", mod_slug)
            downloads = mod_data.get("total_downloads", 0)
            follows = mod_data.get("follows", 0)
            milestones = len(mod_data.get("achieved_milestones", []))
            
            embed.add_field(
                name=f"📦 {title}",
                value=f"Slug: `{mod_slug}`\n📥 {downloads:,} | ❤️ {follows:,} | 🏆 {milestones} milestones",
                inline=False
            )

        if len(self.tracked_projects) > 25:
            embed.set_footer(text=f"Showing 25 of {len(self.tracked_projects)} tracked mods")

        await interaction.followup.send(embed=embed)

    @mcmod_group.command(name="setchannel", description="Set the notification channel for mod updates")
    @app_commands.describe(channel="The channel to send notifications to")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the channel for update notifications."""
        await interaction.response.defer()

        self.notification_channel_id = channel.id
        self.save_data()

        embed = discord.Embed(
            title="✅ Notification Channel Set",
            description=f"Mod updates will be sent to {channel.mention}",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        await interaction.followup.send(embed=embed)

    @mcmod_group.command(name="versions", description="Show recent versions of a mod")
    @app_commands.describe(mod="The Modrinth slug of the mod", limit="Number of versions to show (max 10)")
    async def versions(self, interaction: discord.Interaction, mod: str, limit: int = 5):
        """Show recent versions of a mod."""
        await interaction.response.defer()

        if limit > 10:
            limit = 10

        url = f"https://api.modrinth.com/v2/project/{mod}/version"
        versions_data = await self.fetch_with_cache(url)
        
        if not versions_data:
            await interaction.followup.send("Could not fetch versions for this mod.")
            return

        # Get project info for title
        project_data = await self.get_modrinth_data(mod)
        mod_title = project_data.get("title", mod) if project_data else mod

        embed = discord.Embed(
            title=f"📋 Recent Versions: {mod_title}",
            color=discord.Color.blue(),
            url=f"https://modrinth.com/mod/{mod}/versions",
            timestamp=datetime.now()
        )

        for version in versions_data[:limit]:
            version_number = version.get("version_number", "Unknown")
            version_name = version.get("name", version_number)
            mc_versions = ", ".join(version.get("game_versions", [])[:3])
            if len(version.get("game_versions", [])) > 3:
                mc_versions += "..."
            loaders = ", ".join(version.get("loaders", []))
            downloads = version.get("downloads", 0)
            
            changelog = version.get("changelog", "No changelog available.")
            if len(changelog) > 200:
                changelog = changelog[:197] + "..."
            
            embed.add_field(
                name=f"🔖 {version_name}",
                value=f"**Version:** `{version_number}`\n**MC:** {mc_versions} | **Loaders:** {loaders}\n**Downloads:** {downloads:,}\n{changelog}",
                inline=False
            )

        embed.set_footer(text=f"Showing {min(limit, len(versions_data))} of {len(versions_data)} versions")
        await interaction.followup.send(embed=embed)


class VersionButton(discord.ui.View):
    def __init__(self, cog, mod_slug):
        super().__init__()
        self.cog = cog
        self.mod_slug = mod_slug

    @discord.ui.button(label="View Versions", style=discord.ButtonStyle.primary, emoji="📋")
    async def show_versions(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show versions when button is clicked."""
        await interaction.response.defer()
        
        url = f"https://api.modrinth.com/v2/project/{self.mod_slug}/version"
        versions_data = await self.cog.fetch_with_cache(url)
        
        if not versions_data:
            await interaction.followup.send("Could not fetch versions.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📋 Versions: {self.mod_slug}",
            color=discord.Color.blue(),
            url=f"https://modrinth.com/mod/{self.mod_slug}/versions"
        )

        for version in versions_data[:5]:  # Limit to 5 versions
            version_number = version.get("version_number", "Unknown")
            changelog = version.get("changelog", "No changelog available.")
            if len(changelog) > 150:
                changelog = changelog[:147] + "..."
            
            embed.add_field(
                name=f"🔖 {version_number}",
                value=changelog,
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    cog = ModrinthStats(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(cog.mcmod_group)
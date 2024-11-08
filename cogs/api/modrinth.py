import discord
from discord.ext import commands
from discord import app_commands
import requests


class ModrinthStats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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
            project_url = data.get("project_type", "#")

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

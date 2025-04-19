import discord
from discord.ext import commands, tasks
import json
from pathlib import Path

# Path to the directory where guild settings will be stored
GUILD_SETTINGS_DIR = Path("settings/member_count_settings")

# Ensure the directory exists
GUILD_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)

# Load and save functions for guild settings
def load_guild_settings(guild_id):
    guild_settings_file = GUILD_SETTINGS_DIR / f"{guild_id}.json"
    if guild_settings_file.exists():
        with open(guild_settings_file, "r") as file:
            return json.load(file)
    return {}

def save_guild_settings(guild_id, data):
    guild_settings_file = GUILD_SETTINGS_DIR / f"{guild_id}.json"
    with open(guild_settings_file, "w") as file:
        json.dump(data, file, indent=4)

class MemberCount(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.member_count_channels = {}  # Dictionary to store member count channels per guild
        # Load member count channels and autojoin roles from settings on startup
        for guild in bot.guilds:
            settings = load_guild_settings(guild.id)
            if "member_count_channel" in settings:
                self.member_count_channels[guild.id] = settings["member_count_channel"]
        self.update_member_count.start()  # Start the task that updates member counts

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        # Initialize the member count channel if a guild is joined
        await self.update_member_count_for_guild(guild)

    @tasks.loop(minutes=10)  # Update the member count every 10 minutes
    async def update_member_count(self):
        for guild_id, channel_id in self.member_count_channels.items():
            guild = self.bot.get_guild(guild_id)
            if guild:
                channel = guild.get_channel(channel_id)
                if channel:
                    member_count = guild.member_count
                    await channel.edit(name=f"Members: {member_count}")
                    print(f"Updated member count for guild {guild.name} to {member_count}")

    @discord.app_commands.command(name="setmembercount", description="Set the voice channel to display the member count")
    @commands.has_permissions(manage_channels=True)
    async def set_member_count_channel(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        """Set the channel where the member count will be displayed."""
        guild_id = interaction.guild.id
        self.member_count_channels[guild_id] = channel.id

        # Save the channel ID to guild settings
        settings = load_guild_settings(guild_id)
        settings["member_count_channel"] = channel.id
        save_guild_settings(guild_id, settings)

        # Update the channel name immediately when setting it up
        member_count = interaction.guild.member_count
        await channel.edit(name=f"Members: {member_count}")

        await interaction.response.send_message(f"Member count channel set to: {channel.name}", ephemeral=True)

    @discord.app_commands.command(name="setautojoinrole", description="Set the role to auto-assign to new members")
    @commands.has_permissions(manage_roles=True)
    async def set_autojoin_role(self, interaction: discord.Interaction, role: discord.Role):
        """Set the role that will be automatically assigned to new members."""
        guild_id = interaction.guild.id

        # Check if the bot has permission to manage roles and if the role is below the bot's highest role
        bot_member = interaction.guild.me
        if not bot_member.guild_permissions.manage_roles:
            await interaction.response.send_message("I don't have permission to manage roles.", ephemeral=True)
            return
        if role.position >= bot_member.top_role.position:
            await interaction.response.send_message("I cannot assign this role because it is above my highest role.", ephemeral=True)
            return

        # Save the autojoin role ID to guild settings
        settings = load_guild_settings(guild_id)
        settings["autojoin_role_id"] = role.id
        save_guild_settings(guild_id, settings)

        await interaction.response.send_message(f"Autojoin role set to: {role.mention}. New members will automatically receive this role.", ephemeral=True)

    @discord.app_commands.command(name="removeautojoinrole", description="Remove the autojoin role for new members")
    @commands.has_permissions(manage_roles=True)
    async def remove_autojoin_role(self, interaction: discord.Interaction):
        """Remove the autojoin role setting for the guild."""
        guild_id = interaction.guild.id
        settings = load_guild_settings(guild_id)

        if "autojoin_role_id" not in settings:
            await interaction.response.send_message("No autojoin role is currently set for this guild.", ephemeral=True)
            return

        del settings["autojoin_role_id"]
        save_guild_settings(guild_id, settings)

        await interaction.response.send_message("Autojoin role has been removed. New members will no longer receive an autojoin role.", ephemeral=True)

    async def update_member_count_for_guild(self, guild):
        """Update the member count channel for a specific guild."""
        if guild.id in self.member_count_channels:
            channel_id = self.member_count_channels[guild.id]
            channel = guild.get_channel(channel_id)
            if channel:
                member_count = guild.member_count
                await channel.edit(name=f"Members: {member_count}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Update the member count when a new member joins
        await self.update_member_count_for_guild(member.guild)

        # Assign the autojoin role if set
        settings = load_guild_settings(member.guild.id)
        autojoin_role_id = settings.get("autojoin_role_id")
        if autojoin_role_id:
            role = member.guild.get_role(autojoin_role_id)
            if role:
                try:
                    await member.add_roles(role, reason="Autojoin role assignment")
                    print(f"Assigned autojoin role {role.name} to {member.name} in guild {member.guild.name}")
                except discord.Forbidden:
                    print(f"Failed to assign autojoin role to {member.name} in guild {member.guild.name}: Bot lacks permissions")
                except discord.HTTPException as e:
                    print(f"Failed to assign autojoin role to {member.name} in guild {member.guild.name}: {str(e)}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # Update the member count when a member leaves
        await self.update_member_count_for_guild(member.guild)

async def setup(bot):
    await bot.add_cog(MemberCount(bot))
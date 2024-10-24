import discord
import json
from discord.ext import commands
from discord import app_commands
from pathlib import Path

# Path to the directory where guild settings will be stored
GUILD_SETTINGS_DIR = Path("settings/ticket_settings")

# Ensure the directory exists
GUILD_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)

# Load the settings for a specific guild
def load_guild_settings(guild_id):
    guild_settings_file = GUILD_SETTINGS_DIR / f"{guild_id}.json"
    if guild_settings_file.exists():
        with open(guild_settings_file, "r") as file:
            return json.load(file)
    return {}

# Save the settings for a specific guild
def save_guild_settings(guild_id, data):
    guild_settings_file = GUILD_SETTINGS_DIR / f"{guild_id}.json"
    with open(guild_settings_file, "w") as file:
        json.dump(data, file, indent=4)

# Define the buttons for the ticket system
class TicketButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, topic: str):
        super().__init__(style=discord.ButtonStyle.primary, label=label, custom_id=custom_id)
        self.topic = topic

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        # Load guild settings to get the roles allowed and the roles to ping
        settings = load_guild_settings(guild.id)
        allowed_roles = settings.get("allowed_roles", [])  # Whitelisted roles
        roles_to_ping = settings.get("roles_to_ping", [])  # Roles to ping
        category_id = settings.get("category_id")

        # Check if a ticket channel already exists for the user
        existing_channel = discord.utils.get(guild.text_channels, name=f"{self.topic}-ticket-{user.name.lower()}")
        if existing_channel:
            await interaction.response.send_message(f"You already have a ticket open: {existing_channel.mention}", ephemeral=True)
            return

        # Create the ticket channel and set permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        # Add overwrites for allowed roles (if any)
        for role_id in allowed_roles:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True)
        
        category = discord.utils.get(guild.categories, id=category_id) if category_id else None

        # Create the ticket channel
        ticket_channel = await guild.create_text_channel(
            name=f"{self.topic}-ticket-{user.name.lower()}",
            topic=self.topic,
            overwrites=overwrites,
            category=category
        )

        # Send a message in the ticket channel with pings for specific roles
        if roles_to_ping:
            role_mentions = [guild.get_role(role_id).mention for role_id in roles_to_ping if guild.get_role(role_id)]
            await ticket_channel.send(f"{user.mention}, welcome to your ticket! {' '.join(role_mentions)} will assist you shortly.")
        else:
            await ticket_channel.send(f"{user.mention}, welcome to your ticket! Staff will assist you shortly.")

        await interaction.response.send_message(f"Ticket created: {ticket_channel.mention}", ephemeral=True)

# Define the view for the buttons
class TicketView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        settings = load_guild_settings(guild_id)

        # Ensure we are not adding duplicate custom_ids
        custom_ids = set()

        # Check if the guild has custom ticket types, else use default
        guild_ticket_settings = settings.get("tickets", [])
        for idx, ticket in enumerate(guild_ticket_settings):
            custom_id = ticket["custom_id"]

            # Ensure each custom_id is unique by appending an index if needed
            if custom_id in custom_ids:
                custom_id += f"_{idx}"

            custom_ids.add(custom_id)

            # Add the button with a unique custom_id
            self.add_item(TicketButton(label=ticket["label"], custom_id=custom_id, topic=ticket["topic"]))

# Ticket system cog
class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="ticket", description="Open the ticket panel")
    async def ticket(self, interaction: discord.Interaction):
        """Send the ticket system panel with buttons."""
        view = TicketView(interaction.guild.id)  # Pass the guild ID to the view
        await interaction.response.send_message("Select the type of ticket you want to open:", view=view, ephemeral=True)

    @app_commands.command(name="add_ticket_button", description="Add a new ticket button for this guild")
    @commands.has_permissions(administrator=True)
    async def add_ticket_button(self, interaction: discord.Interaction, label: str, topic: str):
        """Command to add a new ticket button dynamically for the guild."""
        settings = load_guild_settings(interaction.guild.id)

        if "tickets" not in settings:
            settings["tickets"] = []

        # Create a new custom ID for the button
        custom_id = f"{label.lower()}_ticket"

        # Add the new button configuration to the guild's settings
        settings["tickets"].append({
            "label": label,
            "custom_id": custom_id,
            "topic": topic
        })

        # Save the settings back to the file
        save_guild_settings(interaction.guild.id, settings)

        await interaction.response.send_message(f"Ticket button '{label}' added for the topic '{topic}'.", ephemeral=True)
    
    @app_commands.command(name="set_ticket_category", description="Set the category for ticket channels")
    @app_commands.default_permissions(administrator=True)
    async def set_ticket_category(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        """Command to set the category where tickets will be created."""
        settings = load_guild_settings(interaction.guild.id)

        # Store the category ID for this guild
        settings["category_id"] = category.id
        save_guild_settings(interaction.guild.id, settings)

        await interaction.response.send_message(f"Ticket category set to {category.name}.", ephemeral=True)

    @app_commands.command(name="set_allowed_roles", description="Set the roles allowed to view ticket channels")
    @app_commands.default_permissions(administrator=True)
    async def set_allowed_roles(self, interaction: discord.Interaction, roles: str):
        """Command to set roles allowed to view ticket channels (comma-separated role IDs)."""
        settings = load_guild_settings(interaction.guild.id)

        role_ids = [int(role_id.strip()) for role_id in roles.split(",")]

        # Store the allowed roles for this guild
        settings["allowed_roles"] = role_ids
        save_guild_settings(interaction.guild.id, settings)

        await interaction.response.send_message("Allowed roles for ticket channels have been set.", ephemeral=True)
    
    @app_commands.command(name="set_roles_to_ping", description="Set the roles to ping when a ticket is created")
    @commands.has_permissions(administrator=True)
    async def set_roles_to_ping(self, interaction: discord.Interaction, roles: str):
        """Set the roles that should be pinged when a ticket is created (comma-separated role IDs)."""
        settings = load_guild_settings(interaction.guild.id)
        role_ids = [int(role_id.strip()) for role_id in roles.split(',')]

        # Save the role IDs to ping in the settings
        settings["roles_to_ping"] = role_ids
        save_guild_settings(interaction.guild.id, settings)

        await interaction.response.send_message(f"Roles to ping set: {roles}", ephemeral=True)

    @app_commands.command(name="place_ticket_buttons", description="Attach ticket buttons to a specific message")
    @commands.has_permissions(administrator=True)
    async def place_ticket_buttons(self, interaction: discord.Interaction, message_id: str):
        """Command to place the ticket buttons under a specified message by deleting and resending it."""
        try:
            message_id = int(message_id)  # Ensure the message ID is a valid integer
            message = await interaction.channel.fetch_message(message_id)
        except ValueError:
            await interaction.response.send_message("Please provide a valid integer for the message ID.", ephemeral=True)
            return
        except discord.NotFound:
            await interaction.response.send_message("Message not found with that ID.", ephemeral=True)
            return

        # Copy the content and attachments of the message
        message_content = message.content
        message_attachments = message.attachments

        # Delete the original message
        try:
            await message.delete()
        except discord.Forbidden:
            await interaction.response.send_message("Unable to delete the original message due to permission issues.", ephemeral=True)
            return

        # Create the view with ticket buttons for this guild
        view = TicketView(interaction.guild.id)

        # Resend the message content as the bot with the ticket buttons
        sent_message = await interaction.channel.send(content=message_content, view=view)

        # Reattach any attachments from the original message
        for attachment in message_attachments:
            await interaction.channel.send(file=await attachment.to_file())

        # Respond to the user confirming the action
        await interaction.response.send_message(f"Ticket buttons have been placed under the new message with ID {sent_message.id}.", ephemeral=True)

    @app_commands.command(name="close_ticket", description="Close the current ticket")
    async def close_ticket(self, interaction: discord.Interaction):
        """Command to close the ticket channel."""
        if "ticket" in interaction.channel.name:  # Check if "ticket" is anywhere in the channel name
            # TODO: Dm the user with the log and maybe send a log in moderator only?
            await interaction.channel.delete(reason="Ticket closed")   
        else:
            await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
import discord
import json
from discord.ext import commands
from discord import app_commands
from pathlib import Path

# Path to the directory where guild settings will be stored
GUILD_SETTINGS_DIR = Path("settings/ticket_settings")

# Ensure the directory exists
GUILD_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)

# Load and save functions
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

# Button and View classes
class TicketButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, topic: str):
        super().__init__(style=discord.ButtonStyle.primary, label=label, custom_id=custom_id)
        self.topic = topic

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        settings = load_guild_settings(guild.id)
        allowed_roles = settings.get("allowed_roles", [])
        roles_to_ping = settings.get("roles_to_ping", [])
        category_id = settings.get("category_id")

        existing_channel = discord.utils.get(guild.text_channels, name=f"{self.topic}-ticket-{user.name.lower()}")
        if existing_channel:
            await interaction.response.send_message(f"You already have a ticket open: {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        for role_id in allowed_roles:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True)
        
        category = discord.utils.get(guild.categories, id=category_id) if category_id else None

        ticket_channel = await guild.create_text_channel(
            name=f"{self.topic}-ticket-{user.name.lower()}",
            topic=self.topic,
            overwrites=overwrites,
            category=category
        )

        if roles_to_ping:
            role_mentions = [guild.get_role(role_id).mention for role_id in roles_to_ping if guild.get_role(role_id)]
            await ticket_channel.send(f"{user.mention}, welcome to your ticket! {' '.join(role_mentions)} will assist you shortly.")
        else:
            await ticket_channel.send(f"{user.mention}, welcome to your ticket! Staff will assist you shortly.")

        await interaction.response.send_message(f"Ticket created: {ticket_channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        settings = load_guild_settings(guild_id)
        custom_ids = set()

        guild_ticket_settings = settings.get("tickets", [])
        for idx, ticket in enumerate(guild_ticket_settings):
            custom_id = ticket["custom_id"]
            if custom_id in custom_ids:
                custom_id += f"_{idx}"
            custom_ids.add(custom_id)
            self.add_item(TicketButton(label=ticket["label"], custom_id=custom_id, topic=ticket["topic"]))

# Ticket System Cog with command group
class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Command group for tickets
    tickets = app_commands.Group(name="tickets", description="Ticket system commands")

    @tickets.command(name="open", description="Open the ticket panel")
    async def open_ticket(self, interaction: discord.Interaction):
        view = TicketView(interaction.guild.id)
        await interaction.response.send_message("Select the type of ticket you want to open:", view=view, ephemeral=True)

    @tickets.command(name="add_button", description="Add a new ticket button for this guild")
    @commands.has_permissions(administrator=True)
    async def add_ticket_button(self, interaction: discord.Interaction, label: str, topic: str):
        settings = load_guild_settings(interaction.guild.id)
        if "tickets" not in settings:
            settings["tickets"] = []

        custom_id = f"{label.lower()}_ticket"
        settings["tickets"].append({
            "label": label,
            "custom_id": custom_id,
            "topic": topic
        })
        save_guild_settings(interaction.guild.id, settings)
        await interaction.response.send_message(f"Ticket button '{label}' added for the topic '{topic}'.", ephemeral=True)
    
    @tickets.command(name="set_category", description="Set the category for ticket channels")
    @commands.has_permissions(administrator=True)
    async def set_ticket_category(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        settings = load_guild_settings(interaction.guild.id)
        settings["category_id"] = category.id
        save_guild_settings(interaction.guild.id, settings)
        await interaction.response.send_message(f"Ticket category set to {category.name}.", ephemeral=True)

    @tickets.command(name="set_allowed_roles", description="Set the roles allowed to view ticket channels")
    @commands.has_permissions(administrator=True)
    async def set_allowed_roles(self, interaction: discord.Interaction, roles: str):
        settings = load_guild_settings(interaction.guild.id)
        role_ids = [int(role_id.strip()) for role_id in roles.split(",")]
        settings["allowed_roles"] = role_ids
        save_guild_settings(interaction.guild.id, settings)
        await interaction.response.send_message("Allowed roles for ticket channels have been set.", ephemeral=True)

    @tickets.command(name="set_roles_to_ping", description="Set the roles to ping when a ticket is created")
    @commands.has_permissions(administrator=True)
    async def set_roles_to_ping(self, interaction: discord.Interaction, roles: str):
        settings = load_guild_settings(interaction.guild.id)
        role_ids = [int(role_id.strip()) for role_id in roles.split(',')]
        settings["roles_to_ping"] = role_ids
        save_guild_settings(interaction.guild.id, settings)
        await interaction.response.send_message(f"Roles to ping set: {roles}", ephemeral=True)

    @tickets.command(name="place_buttons", description="Attach ticket buttons to a specific message")
    @commands.has_permissions(administrator=True)
    async def place_ticket_buttons(self, interaction: discord.Interaction, message_id: str):
        try:
            message_id = int(message_id)
            message = await interaction.channel.fetch_message(message_id)
        except (ValueError, discord.NotFound):
            await interaction.response.send_message("Invalid message ID.", ephemeral=True)
            return

        message_content = message.content
        message_attachments = message.attachments
        await message.delete()

        view = TicketView(interaction.guild.id)
        sent_message = await interaction.channel.send(content=message_content, view=view)

        # Save the message ID in the settings
        settings = load_guild_settings(interaction.guild.id)
        settings["ticket_buttons_message_id"] = sent_message.id
        save_guild_settings(interaction.guild.id, settings)

        for attachment in message_attachments:
            await interaction.channel.send(file=await attachment.to_file())

        await interaction.response.send_message(f"Ticket buttons have been placed under the new message with ID {sent_message.id}.", ephemeral=True)

    @tickets.command(name="remove_button", description="Remove an existing ticket button")
    @commands.has_permissions(administrator=True)
    async def remove_ticket_button(self, interaction: discord.Interaction, custom_id: str):
        settings = load_guild_settings(interaction.guild.id)

        # Check if "tickets" key exists
        if "tickets" not in settings or not settings["tickets"]:
            await interaction.response.send_message("No ticket buttons are set up yet.", ephemeral=True)
            return

        # Find the ticket button with the given custom_id
        ticket = next((ticket for ticket in settings["tickets"] if ticket["custom_id"] == custom_id), None)
        
        if not ticket:
            await interaction.response.send_message(f"No ticket button found with the custom ID '{custom_id}'.", ephemeral=True)
            return

        # Remove the ticket button from the settings
        settings["tickets"].remove(ticket)
        save_guild_settings(interaction.guild.id, settings)

        await interaction.response.send_message(f"Ticket button with custom ID '{custom_id}' has been removed.", ephemeral=True)

        # Refresh message that had the button, if needed
        view = TicketView(interaction.guild.id)
        message_id = settings.get("ticket_buttons_message_id")  # Assume this is saved in the settings
        if message_id:
            try:
                message = await interaction.channel.fetch_message(message_id)
                await message.edit(view=view)  # Update the message with the new buttons
            except discord.NotFound:
                await interaction.response.send_message("Could not find the message with the ticket buttons.", ephemeral=True)

    @tickets.command(name="set_archive_category", description="Set the category for archived tickets")
    @commands.has_permissions(administrator=True)
    async def set_archive_category(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        settings = load_guild_settings(interaction.guild.id)
        settings["archive_category_id"] = category.id
        save_guild_settings(interaction.guild.id, settings)
        await interaction.response.send_message(f"Archive category set to {category.name}.", ephemeral=True)

    @tickets.command(name="archive", description="Archive the current ticket")
    @commands.has_permissions(manage_channels=True)
    async def archive_ticket(self, interaction: discord.Interaction):
        if "ticket" not in interaction.channel.name:
            await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)
            return
    
        guild = interaction.guild
        settings = load_guild_settings(guild.id)
        allowed_roles = settings.get("allowed_roles", [])
        archive_category_id = settings.get("archive_category_id")
        
        # Get the user who created the ticket from the channel name
        ticket_creator_name = interaction.channel.name.split('-')[-1]
        ticket_creator = discord.utils.get(guild.members, name=ticket_creator_name)
        
        # New permission overwrites for archived channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        
        # Add permission overwrites for allowed roles (view and read history, but no sending messages)
        for role_id in allowed_roles:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    read_message_history=True,
                    send_messages=False  # Deny sending messages for non-admin allowed roles
                )
        
        # Explicitly deny access to the ticket creator if they're still in the server
        if ticket_creator:
            overwrites[ticket_creator] = discord.PermissionOverwrite(view_channel=False)
        
        # Get archive category if set
        category = None
        if archive_category_id:
            category = discord.utils.get(guild.categories, id=archive_category_id)
        
        # Update channel name to indicate it's archived
        new_channel_name = f"archived-{interaction.channel.name}"
        
        try:
            await interaction.channel.edit(
                name=new_channel_name,
                category=category,
                overwrites=overwrites,
                reason="Ticket archived"
            )
            await interaction.channel.send("This ticket has been archived. Only staff can view it now, and only administrators can send messages.")
            await interaction.response.send_message("Ticket has been archived.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to archive ticket: {str(e)}", ephemeral=True)

    @tickets.command(name="close", description="Close the current ticket")
    async def close_ticket(self, interaction: discord.Interaction):
        if "ticket" not in interaction.channel.name:
            await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)
            return

        # Create a view with buttons for archive and delete
        class CloseOptionsView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
            
            @discord.ui.button(label="Archive", style=discord.ButtonStyle.primary)
            async def archive_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.cog.archive_ticket(interaction)
                self.stop()
                
            @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
            async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.channel.delete(reason="Ticket closed")
                self.stop()

        view = CloseOptionsView()
        view.cog = self  # Pass the cog instance to the view
        await interaction.response.send_message(
            "Choose an option for closing this ticket:",
            view=view,
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(TicketSystem(bot))

import discord
from discord.ext import commands

class AntiHoist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="dehoist", description="Renames users with hoisting nicknames")
    @discord.app_commands.checks.has_permissions(moderate_members=True, manage_nicknames=True)
    async def dehoist(self, interaction: discord.Interaction):
        hoisting_chars = ('!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '.', '/', ':', ';', '<', '=', '>', '?', '@', '[', '\\', ']', '^', '_', '`', '{', '|', '}', '~')
        hoisting_str = ''.join(hoisting_chars)  # Convert tuple to string
        hoisters_found = []
        hoisters_renamed = []
        failed_renames = []

        # Check all members in the guild
        for member in interaction.guild.members:
            # Skip bots and members without hoisting nicknames
            if member.bot or not member.nick:
                continue

            # Check if the nickname starts with a hoisting character
            if member.nick.startswith(hoisting_chars):
                hoisters_found.append(member)

                # Attempt to rename the member by removing leading hoisting characters
                new_nick = member.nick.lstrip(hoisting_str)
                try:
                    await member.edit(nick=new_nick)
                    hoisters_renamed.append(member)
                except discord.Forbidden:
                    failed_renames.append(member)
                except discord.HTTPException:
                    failed_renames.append(member)

        # Format the result with diff formatting
        hoisters_count = len(hoisters_found)
        renamed_count = len(hoisters_renamed)
        failed_count = len(failed_renames)

        result_message = (
            f"--- Hoisters found: {hoisters_count} ---\n"
            f"+ Hoisters renamed: {renamed_count}\n"
            f"- Failed renames: {failed_count}\n"
        )

        # Send the message back to the user using `diff` formatting
        await interaction.response.send_message(f"```diff\n{result_message}```", ephemeral=False)

async def setup(bot):
    await bot.add_cog(AntiHoist(bot))

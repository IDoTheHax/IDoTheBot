import discord
from discord.ext import commands

class ReactionOrderChecker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reaction_sequences = {}  # Store reaction sequences for each message
        # Define blacklisted emoji sequences
        self.blacklisted_orders = [
            ["🇨", "🇺", "🇲"],  # C U M
            ["🇳", "🇮", "🇬", "🇬", "🇪", "🇷"],  # N I G G E R
            ["🇳", "🇮", "🇬", "🇪", "🇷"],  # N I G E R
            ["🖕"],  # Middle finger emoji
            ["🖕🏾"], # different color
        ]

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return  # Ignore bot reactions

        message_id = reaction.message.id

        # If this is the first reaction to this message, create a new sequence tracker
        if message_id not in self.reaction_sequences:
            self.reaction_sequences[message_id] = []

        # Add the emoji to the reaction sequence
        self.reaction_sequences[message_id].append(str(reaction.emoji))

        # Check if the current reaction sequence matches any blacklisted orders
        for blacklist in self.blacklisted_orders:
            if self.reaction_sequences[message_id][-len(blacklist):] == blacklist:
                try:
                    # Send a DM to the user explaining the mute or warning
                    await user.send(
                        f"You have been warned in {reaction.message.guild.name} for inappropriate emojis. "
                        f"Message in question: {reaction.message.content}, emojis: {self.reaction_sequences[message_id]}"
                    )
                except discord.errors.Forbidden:
                    # If DMs are disabled, send a message in the channel instead
                    await reaction.message.channel.send(
                        f"Could not send DM to {user.mention}, but proceeding with the warning.", ephemeral=True
                    )

                # Send a public warning message in the channel
                await reaction.message.channel.send(
                    f"⚠️ Warning: Blacklisted reaction order detected!"
                )

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if user.bot:
            return  # Ignore bot reactions

        message_id = reaction.message.id

        if message_id in self.reaction_sequences:
            # Remove the emoji from the reaction sequence when a reaction is removed
            self.reaction_sequences[message_id].remove(str(reaction.emoji))

# Set up the bot
async def setup(bot):
    # Add the cog to the bot
    await bot.add_cog(ReactionOrderChecker(bot))
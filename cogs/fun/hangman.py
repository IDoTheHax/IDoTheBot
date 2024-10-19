import discord
from discord import app_commands
from discord.ext import commands
import random

class Hangman(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}  # Store games by channel ID

    @app_commands.command(name='hangman', description='Starts a new game of Hangman. Optionally specify a word.')
    async def start_game(self, interaction: discord.Interaction, word: str = None):
        """Starts a new game of Hangman. Optionally specify a word."""
        channel = interaction.channel
        if channel.id in self.games:
            await interaction.response.send_message("A game is already running in this channel!", ephemeral=True)
            return
        
        if word:
            word = word.lower()
        else:
            words = ["python", "discord", "hangman", "bot", "development"]
            word = random.choice(words)

        self.games[channel.id] = {
            "word": word,
            "guesses": [],
            "attempts": 6,  # Number of attempts allowed
            "host": interaction.user  # Track who started the game
        }

        await interaction.response.send_message(f"🎉 A new game of Hangman has started! Word: **{word}** (specified by {interaction.user.mention})\nYou have {self.games[channel.id]['attempts']} attempts.", ephemeral=True)
        await self.display_game_status(channel)

    @app_commands.command(name='guess', description='Make a guess in the Hangman game.')
    async def make_guess(self, interaction: discord.Interaction, letter: str):
        """Make a guess in the Hangman game."""
        channel = interaction.channel

        if channel.id not in self.games:
            await interaction.response.send_message("No game is currently running in this channel! Start a new game with `/hangman`.", ephemeral=True)
            return

        letter = letter.lower()
        game = self.games[channel.id]

        if len(letter) != 1 or not letter.isalpha():
            await interaction.response.send_message("Please guess a single letter.", ephemeral=True)
            return

        if letter in game["guesses"]:
            await interaction.response.send_message("You've already guessed that letter! Try a different one.", ephemeral=True)
            return

        game["guesses"].append(letter)

        if letter not in game["word"]:
            game["attempts"] -= 1
            await interaction.response.send_message(f"❌ Incorrect! You have {game['attempts']} attempts left.", ephemeral=True)

        await self.display_game_status(channel)

        if game["attempts"] <= 0:
            await interaction.followup.send(f"🪦 Game over! The word was: **{game['word']}**. Type `/hangman` to start a new game.", channel=channel)

        if all(letter in game["guesses"] for letter in game["word"]):
            await interaction.followup.send(f"🎉 Congratulations! You've guessed the word: **{game['word']}**! Type `/hangman` to play again.", channel=channel)

    async def display_game_status(self, channel):
        """Displays the current game status."""
        game = self.games[channel.id]
        word_display = ''.join(letter if letter in game["guesses"] else '_' for letter in game["word"])
        await channel.send(f"Current word: **{word_display}**\nGuessed letters: **{', '.join(game['guesses'])}**")

async def setup(bot):
    await bot.add_cog(Hangman(bot))

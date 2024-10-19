import discord
from discord.ext import commands
import random

class Hangman(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}  # Store games by channel ID

    @commands.command(name='hangman')
    async def start_game(self, ctx):
        """Starts a new game of Hangman."""
        words = ["python", "discord", "hangman", "bot", "development"]
        word = random.choice(words)
        self.games[ctx.channel.id] = {
            "word": word,
            "guesses": [],
            "attempts": 6  # Number of attempts allowed
        }

        await ctx.send(f"🎉 A new game of Hangman has started! You have {self.games[ctx.channel.id]['attempts']} attempts.")
        await self.display_game_status(ctx)

    @commands.command(name='guess')
    async def make_guess(self, ctx, letter: str):
        """Make a guess in the Hangman game."""
        if ctx.channel.id not in self.games:
            await ctx.send("No game is currently running in this channel! Start a new game with `!hangman`.")
            return

        letter = letter.lower()
        game = self.games[ctx.channel.id]

        if len(letter) != 1 or not letter.isalpha():
            await ctx.send("Please guess a single letter.")
            return

        if letter in game["guesses"]:
            await ctx.send("You've already guessed that letter! Try a different one.")
            return

        game["guesses"].append(letter)

        if letter not in game["word"]:
            game["attempts"] -= 1
            await ctx.send(f"❌ Incorrect! You have {game['attempts']} attempts left.")

        await self.display_game_status(ctx)

        if game["attempts"] <= 0:
            await ctx.send(f"🪦 Game over! The word was: **{game['word']}**. Type `!hangman` to start a new game.")

        if all(letter in game["guesses"] for letter in game["word"]):
            await ctx.send(f"🎉 Congratulations! You've guessed the word: **{game['word']}**! Type `!hangman` to play again.")

    async def display_game_status(self, ctx):
        """Displays the current game status."""
        game = self.games[ctx.channel.id]
        word_display = ''.join(letter if letter in game["guesses"] else '_' for letter in game["word"])
        await ctx.send(f"Current word: **{word_display}**\nGuessed letters: **{', '.join(game['guesses'])}**")

async def setup(bot):
    await bot.add_cog(Hangman(bot))

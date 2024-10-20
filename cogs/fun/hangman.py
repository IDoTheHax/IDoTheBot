import discord
from discord.ext import commands
from discord import app_commands
import random

HANGMANPICS = [
    '''
  +---+
  |   |
      |
      |
      |
      |
=========''',
    '''
  +---+
  |   |
  O   |
      |
      |
      |
=========''',
    '''
  +---+
  |   |
  O   |
  |   |
      |
      |
=========''',
    '''
  +---+
  |   |
  O   |
 /|   |
      |
      |
=========''',
    '''
  +---+
  |   |
  O   |
 /|\\  |
      |
      |
=========''',
    '''
  +---+
  |   |
  O   |
 /|\\  |
 /    |
      |
=========''',
    '''
  +---+
  |   |
  O   |
 /|\\  |
 / \\  |
      |
========='''
]

class Hangman(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}  # Store games by channel ID

    @app_commands.command(name='hangman', description='Starts a new game of Hangman.')
    async def start_game(self, interaction: discord.Interaction):
        """Starts a new game of Hangman."""
        words = ["python", "discord", "hangman", "bot", "development"]
        word = random.choice(words)
        self.games[interaction.channel.id] = {
            "word": word,
            "guesses": [],
            "attempts": 6  # Number of attempts allowed
        }

        await interaction.response.send_message(f"🎉 A new game of Hangman has started! You have {self.games[interaction.channel.id]['attempts']} attempts.")
        await self.display_game_status(interaction)

    @app_commands.command(name='guess', description='Make a guess in the Hangman game.')
    async def make_guess(self, interaction: discord.Interaction, letter: str):
        """Make a guess in the Hangman game."""
        if interaction.channel.id not in self.games:
            await interaction.response.send_message("No game is currently running in this channel! Start a new game with `/hangman`.")
            return

        letter = letter.lower()
        game = self.games[interaction.channel.id]

        if len(letter) != 1 or not letter.isalpha():
            await interaction.response.send_message("Please guess a single letter.")
            return

        if letter in game["guesses"]:
            await interaction.response.send_message("You've already guessed that letter! Try a different one.")
            return

        game["guesses"].append(letter)
        response_message = ""  # To collect responses

        # Check if the guess was incorrect
        if letter not in game["word"]:
            game["attempts"] -= 1
            response_message += f"❌ Incorrect! You have {game['attempts']} attempts left.\n"
        else:
            response_message += "✅ Correct!\n"

        # Display game status and append it to the response
        response_message += await self.get_game_status(game)

        if game["attempts"] <= 0:
            response_message += f"🪦 Game over! The word was: **{game['word']}**. Type `/hangman` to start a new game."
        elif all(letter in game["guesses"] for letter in game["word"]):
            response_message += f"🎉 Congratulations! You've guessed the word: **{game['word']}**! Type `/hangman` to play again."

        await interaction.response.send_message(response_message)

    @app_commands.command(name='guessword', description='Guess the entire word in the Hangman game.')
    async def guess_word(self, interaction: discord.Interaction, word: str):
        """Make a guess for the entire word in the Hangman game."""
        if interaction.channel.id not in self.games:
            await interaction.response.send_message("No game is currently running in this channel! Start a new game with `/hangman`.")
            return

        game = self.games[interaction.channel.id]

        if word.lower() == game["word"]:
            await interaction.response.send_message(f"🎉 Congratulations! You've guessed the word: **{game['word']}**! Type `/hangman` to play again.")
            del self.games[interaction.channel.id]  # Remove the game from the active games
        else:
            game["attempts"] -= 1
            if game["attempts"] <= 0:
                await interaction.response.send_message(f"🪦 Game over! The word was: **{game['word']}**. Type `/hangman` to start a new game.")
            else:
                await interaction.response.send_message(f"❌ Incorrect guess! You have {game['attempts']} attempts left. Type `/guess` for single letter guesses or `/guessword` to guess the whole word.")

    async def get_game_status(self, game):
        """Returns the current game status as a string."""
        hangman_display = HANGMANPICS[6 - game["attempts"]]
        word_display = ' '.join(letter if letter in game["guesses"] else '_' for letter in game["word"])
        guessed_letters = ', '.join(game["guesses"]) if game["guesses"] else "None"
        
        return f"```\n{hangman_display}\n```\nCurrent word: **{word_display}**\nGuessed letters: **{guessed_letters}**"

    async def display_game_status(self, interaction: discord.Interaction):
        """Displays the current game status, including the hangman and guessed letters."""
        game = self.games[interaction.channel.id]
        hangman_display = HANGMANPICS[6 - game["attempts"]]  # Adjusted to use attempts
        word_display = ' '.join(letter if letter in game["guesses"] else '_' for letter in game["word"])
        guessed_letters = ', '.join(game["guesses"]) if game["guesses"] else "None"
        
        content = f"```\n{hangman_display}\n```\nCurrent word: **{word_display}**\nGuessed letters: **{guessed_letters}**"
        await interaction.followup.send(content)

async def setup(bot):
    await bot.add_cog(Hangman(bot))

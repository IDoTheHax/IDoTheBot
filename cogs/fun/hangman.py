import discord
from discord.ext import commands
from discord import app_commands, ui
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
 /|\  |
      |
      |
=========''',
    '''
  +---+
  |   |
  O   |
 /|\  |
 /    |
      |
=========''',
    '''
  +---+
  |   |
  O   |
 /|\  |
 / \  |
      |
========='''
]

class Hangman(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}  # Store games by channel ID

    @app_commands.command(name='hangman', description='Starts a new game of Hangman.')
    async def start_game(self, interaction: discord.Interaction, mode: str = "default"):
        """Starts a new game of Hangman with an optional custom word."""
        if mode.lower() == "custom":
            # Create and send a button to open the modal for the custom word input
            button = ui.Button(label="Submit Custom Word", style=discord.ButtonStyle.primary)
            button.callback = self.custom_word_button_callback(interaction.user.id)  # Pass the user ID to the callback
            view = ui.View()
            view.add_item(button)
            await interaction.response.send_message("Click the button to submit a custom word for Hangman!", view=view)
        else:
            await interaction.response.send_message("Starting a standard game of Hangman. Use `/hangman custom` for a custom word.")

    def custom_word_button_callback(self, user_id):
        """Show a modal for inputting the custom word, checking if the correct user clicked."""
        async def callback(interaction: discord.Interaction):
            """Handles the button click."""
            if interaction.user.id != user_id:
                await interaction.response.send_message("You cannot submit a custom word. This action is reserved for the user who initiated the game.", ephemeral=True)
                return
            
            # If the correct user clicked the button, show the modal
            modal = CustomWordModal()
            await interaction.response.send_modal(modal)

        return callback

    @app_commands.command(name='guess', description='Make a guess in the Hangman game.')
    async def make_guess(self, interaction: discord.Interaction, letter: str):
        """Make a guess in the Hangman game."""
        if interaction.channel.id not in self.games:
            await interaction.response.send_message("No game is currently running in this channel! Start a new game with `/hangman <word>`.")
            return

        game = self.games[interaction.channel.id]

        # Prevent the host from guessing
        if interaction.user.id == game["host"]:
            await interaction.response.send_message("You cannot guess while hosting the game. Please wait until the game ends.")
            return

        letter = letter.lower()
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
            response_message += f"🪦 Game over! The word was: **{game['word']}**. Type `/hangman <word>` to start a new game."
        elif all(letter in game["guesses"] for letter in game["word"]):
            response_message += f"🎉 Congratulations! You've guessed the word: **{game['word']}**! Type `/hangman <word>` to play again."

        await interaction.response.send_message(response_message)

    @app_commands.command(name='guessword', description='Guess the entire word in the Hangman game.')
    async def guess_word(self, interaction: discord.Interaction, word: str):
        """Make a guess for the entire word in the Hangman game."""
        if interaction.channel.id not in self.games:
            await interaction.response.send_message("No game is currently running in this channel! Start a new game with `/hangman <word>`.")
            return

        game = self.games[interaction.channel.id]

        # Prevent the host from guessing
        if interaction.user.id == game["host"]:
            await interaction.response.send_message("You cannot guess while hosting the game. Please wait until the game ends.")
            return

        if word.lower() == game["word"]:
            await interaction.response.send_message(f"🎉 Congratulations! You've guessed the word: **{game['word']}**! Type `/hangman <word>` to play again.")
            del self.games[interaction.channel.id]  # Remove the game from the active games
        else:
            game["attempts"] -= 1
            if game["attempts"] <= 0:
                await interaction.response.send_message(f"🪦 Game over! The word was: **{game['word']}**. Type `/hangman <word>` to start a new game.")
            else:
                await interaction.response.send_message(f"❌ Incorrect guess! You have {game['attempts']} attempts left. Type `/guess` for single letter guesses or `/guessword` to guess the whole word.")

    async def get_game_status(self, game):
        """Returns the current game status as a string."""
        hangman_display = HANGMANPICS[6 - game["attempts"]]
        word_display = ' '.join(letter if letter in game["guesses"] else '_' for letter in game["word"])
        guessed_letters = ', '.join(game["guesses"]) if game["guesses"] else "None"
        
        return f"```\n{hangman_display}\n```\nCurrent word: **{word_display}**\nGuessed letters: **{guessed_letters}**"

    async def start_game_with_custom_word(self, interaction: discord.Interaction, word: str):
        """Starts a new game of Hangman with a custom word."""
        word = word.lower()
        if not word.isalpha():
            await interaction.response.send_message("Please provide a valid word (letters only).")
            return
        
        self.games[interaction.channel.id] = {
            "word": word,
            "guesses": [],
            "attempts": 6,  # Number of attempts allowed
            "host": interaction.user.id,  # Store the user who started the game
        }

        await interaction.response.send_message(f"🎉 A new game of Hangman has started with the word suggested by {interaction.user.name}. You have {self.games[interaction.channel.id]['attempts']} attempts.")
        await interaction.followup.send(await self.get_game_status(self.games[interaction.channel.id]))

class CustomWordModal(ui.Modal, title="Custom Word for Hangman"):
    """Modal to input a custom word for Hangman."""

    word_input = ui.TextInput(label="Custom Word", placeholder="Enter your custom word", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        """Handles the submission of the custom word."""
        hangman_cog = interaction.client.get_cog("Hangman")
        await hangman_cog.start_game_with_custom_word(interaction, self.word_input.value)

# Setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(Hangman(bot))
import discord
from discord.ext import commands
from discord import app_commands
import random

class TicTacToe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}  # Store games by channel ID

    # Parent command for Tic Tac Toe
    tictactoe_group = app_commands.Group(name='tictactoe', description='Tic Tac Toe game commands')


    @tictactoe_group.command(name='new', description='Starts a new game of Tic Tac Toe.')
    async def start_game(self, interaction: discord.Interaction):
        """Starts a new game of Tic Tac Toe."""
        if interaction.channel.id in self.games:
            await interaction.response.send_message("A game is already in progress in this channel! Finish it first.", ephemeral=True)
            return
        
        self.games[interaction.channel.id] = {
            "board": [' ' for _ in range(9)],
            "turn": "X",  # X starts
            "waiting_for": interaction.user.id,  # Track whose turn it is (player starts)
        }

        await interaction.response.send_message("Tic Tac Toe game started!\nrange from 1-9 for the numbers going from left to right from the top so 1 will be the first of the first row and 4 will be the first of the second\nIt's your turn, X.\n" + self.display_board(self.games[interaction.channel.id]["board"]))
    
    @tictactoe_group.command(name='move', description='Make a move in the Tic Tac Toe game.')
    async def make_move(self, interaction: discord.Interaction, position: int):
        """Make a move in the Tic Tac Toe game."""
        if interaction.channel.id not in self.games:
            await interaction.response.send_message("No game is currently running in this channel! Start a new game with `/tictactoe`.", ephemeral=True)
            return
        
        game = self.games[interaction.channel.id]

        # Check if it's the correct player's turn
        if interaction.user.id != game["waiting_for"]:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        if position < 1 or position > 9:
            await interaction.response.send_message("Please choose a position between 1 and 9.", ephemeral=True)
            return

        if game["board"][position - 1] != ' ':
            await interaction.response.send_message("That position is already taken! Choose another position.", ephemeral=True)
            return

        # Make the player's move
        game["board"][position - 1] = game["turn"]
        
        # Check for a winner
        winner = self.check_winner(game["board"])
        if winner:
            await interaction.response.send_message(f"🎉 {winner} wins! 🎉\n" + self.display_board(game["board"]))
            del self.games[interaction.channel.id]  # Remove the game from active games
            return
        
        # Check for a draw
        if ' ' not in game["board"]:
            await interaction.response.send_message("It's a draw! No more moves left.\n" + self.display_board(game["board"]))
            del self.games[interaction.channel.id]  # Remove the game from active games
            return

        # Switch turns to the computer
        game["turn"] = "O"
        game["waiting_for"] = "Computer"  # Change waiting to computer

        # Computer makes a move
        await self.make_computer_move(interaction, interaction.channel)

    async def make_computer_move(self, interaction: discord.Interaction, channel):
        """Makes a move for the computer."""
        game = self.games[channel.id]

        # Find the first available position
        available_positions = [i for i, value in enumerate(game["board"]) if value == ' ']
        if available_positions:
            position = random.choice(available_positions)  # Random move
            game["board"][position] = game["turn"]

            # Check for a winner
            winner = self.check_winner(game["board"])
            if winner:
                await self.bot.get_channel(channel.id).send(f"🎉 {winner} wins! 🎉\n" + self.display_board(game["board"]))
                del self.games[channel.id]  # Remove the game from active games
                return

            # Check for a draw
            if ' ' not in game["board"]:
                await self.bot.get_channel(channel.id).send("It's a draw! No more moves left.\n" + self.display_board(game["board"]))
                del self.games[channel.id]  # Remove the game from active games
                return

            # Switch turn back to player
            game["turn"] = "X"
            game["waiting_for"] = interaction.user.id  # Change waiting back to the player
            await self.bot.get_channel(channel.id).send(f"It's your turn, X!\n" + self.display_board(game["board"]))
    
    def display_board(self, board):
        """Returns a formatted string of the Tic Tac Toe board."""
        board_display =  f"""
            {board[0]} | {board[1]} | {board[2]}
        ---------
            {board[3]} | {board[4]} | {board[5]}
        ---------
            {board[6]} | {board[7]} | {board[8]}
        """
        return board_display

    def check_winner(self, board):
        """Checks for a winner."""
        win_conditions = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Horizontal
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Vertical
            [0, 4, 8], [2, 4, 6]              # Diagonal
        ]

        for condition in win_conditions:
            if board[condition[0]] == board[condition[1]] == board[condition[2]] != ' ':
                return board[condition[0]]  # Return the winner

        return None  # No winner

# Setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(TicTacToe(bot))

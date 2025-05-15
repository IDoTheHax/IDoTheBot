import discord
from discord import app_commands
from discord.ext import commands
import openai
import os
import requests
from dotenv import load_dotenv
import asyncio
import json
import logging
from cachetools import TTLCache
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")  # Store webhook URL in .env

# Initialize cache (TTL: 1 hour)
cache = TTLCache(maxsize=100, ttl=3600)

# Token limit for conversation history
MAX_TOKENS = 4000
SUMMARIZE_THRESHOLD = 3000

class ChatGPTCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conversation_histories = {}  # User-specific conversation histories
        self.system_prompt = {
            "role": "system",
            "content": (
                "You are The IDoTheHax Glazer, the mascot, a helpful Discord chatbot in the IDoThebasement server. "
                "In this server, IDoTheHax Fans gather and talk about his videos and mods. "
                "Respond in a friendly, engaging tone, and provide concise, relevant answers. "
            )
        }
        self.lock = asyncio.Lock()  # Lock for thread-safe operations

    async def ask_chatgpt(self, user_id, prompt, max_retries=3):
        """Handle OpenAI API calls with exponential backoff and caching."""
        cache_key = f"{user_id}:{prompt[:50]}"  # Create a unique cache key
        if cache_key in cache:
            logger.info(f"Cache hit for user {user_id}")
            return cache[cache_key]

        # Initialize user-specific history if not exists
        if user_id not in self.conversation_histories:
            self.conversation_histories[user_id] = [self.system_prompt]

        # Add user prompt to history
        self.conversation_histories[user_id].append({"role": "user", "content": prompt})

        # Summarize history if it exceeds token threshold
        await self.summarize_history(user_id)

        for attempt in range(max_retries):
            try:
                async with self.lock:
                    response = await asyncio.to_thread(
                        openai.chat.completions.create,
                        model="gpt-4o",  # Use a more efficient model (check OpenAI's latest models)
                        messages=self.conversation_histories[user_id],
                        max_tokens=500,  # Limit response length
                        temperature=0.7
                    )

                assistant_message = response.choices[0].message.content
                self.conversation_histories[user_id].append({"role": "assistant", "content": assistant_message})

                # Cache the response
                cache[cache_key] = assistant_message
                logger.info(f"Response cached for user {user_id}")
                return assistant_message

            except openai.RateLimitError as e:
                wait_time = 2 ** attempt * 10  # Exponential backoff
                logger.warning(f"Rate limit hit, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"Error in OpenAI API call: {e}")
                return f"Error: {e}"

        return "Error: Max retries exceeded due to rate limits."

    async def summarize_history(self, user_id):
        """Summarize conversation history if it exceeds token threshold."""
        history = self.conversation_histories[user_id]
        if len(json.dumps(history)) > SUMMARIZE_THRESHOLD:
            try:
                summary_prompt = (
                    "Summarize the following conversation into a concise paragraph, retaining key context:\n"
                    f"{json.dumps(history[1:])}"  # Exclude system prompt
                )
                summary_response = await asyncio.to_thread(
                    openai.chat.completions.create,
                    model="gpt-4o",
                    messages=[{"role": "user", "content": summary_prompt}],
                    max_tokens=200
                )
                summary = summary_response.choices[0].message.content
                self.conversation_histories[user_id] = [
                    self.system_prompt,
                    {"role": "system", "content": f"Conversation summary: {summary}"}
                ]
                logger.info(f"Conversation history summarized for user {user_id}")
            except Exception as e:
                logger.error(f"Error summarizing history: {e}")

    def send_to_discord(self, message, username="IDoTheHax Glazer"):
        """Send message via webhook."""
        try:
            data = {"content": message, "username": username}
            response = requests.post(WEBHOOK_URL, json=data)
            response.raise_for_status()
            logger.info("Message sent to Discord webhook")
        except requests.RequestException as e:
            logger.error(f"Error sending to webhook: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle incoming messages."""
        if message.author.bot:
            return

        # Check for bot mention or keywords
        keywords = ["chat", "question", "glazer", "IDoTheHax glazer", "bot"]
        if self.bot.user.mentioned_in(message) or any(keyword in message.content.lower() for keyword in keywords):
            async with message.channel.typing():
                response = await self.ask_chatgpt(message.author.id, message.content)
                self.send_to_discord(f"{message.author.mention} {response}")

        await self.bot.process_commands(message)  # Process commands after message handling

    @app_commands.command(name="ask", description="Ask IDoTheHax Glazer a question")
    async def ask_command(self, interaction: discord.Interaction, question: str):
        """Slash command to ask a question."""
        await interaction.response.defer(thinking=True)
        response = await self.ask_chatgpt(interaction.user.id, question)
        self.send_to_discord(f"{interaction.user.mention} {response}")
        await interaction.followup.send("Response sent!", ephemeral=True)

    @app_commands.command(name="reset", description="Reset your conversation history")
    async def reset_command(self, interaction: discord.Interaction):
        """Slash command to reset conversation history."""
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id in self.conversation_histories:
            del self.conversation_histories[interaction.user.id]
            logger.info(f"Conversation history reset for user {interaction.user.id}")
        await interaction.followup.send("Your conversation history has been reset!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ChatGPTCog(bot))
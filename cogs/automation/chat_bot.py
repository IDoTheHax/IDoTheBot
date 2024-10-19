import discord
from discord.ext import commands
import openai
import os
import requests

#load_dotenv()

# Set up OpenAI API key
with open(os.path.expanduser('api.txt'), 'r') as file:
    openai.api_key = file.read().strip()

# Your Discord webhook URL
with open(os.path.expanduser('web.txt'), 'r') as file:
    WEBHOOK_URL = file.read().strip()

class ChatGPTCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conversation_history = [
             {"role": "system", "content": "You are a helpful, Discord chat bot, you live in a server called solar smp where every hour an asteroid falls, this asteroid gives you the ability to get one of the 8 solar system planet fragments that give you abilities related"}
        ]

    async def ask_chatgpt(self, prompt):
        # Add the user's message to the conversation history
        self.conversation_history.append({"role": "user", "content": prompt})

        try:
            # Make an API call to OpenAI using the correct method
            response = openai.chat.completions.create(
                model="gpt-4",  # Ensure this is the correct model name
                messages=self.conversation_history  # Pass the full conversation history directly
            )

            # Extract the assistant's message from the response
            assistant_message = response.choices[0].message.content  # Correct way to access content

            # Add the assistant's message to the conversation history
            self.conversation_history.append({"role": "assistant", "content": assistant_message})

            return assistant_message
        except Exception as e:
            return f"Error: {e}"



    @commands.Cog.listener()
    async def on_message(self, message):
        # Avoid responding to the bot's own messages
        if message.author == self.bot.user:
            return
        
        # Avoid responding if the message does not start with the bot's prefix or mentions the bot
        # Check if the message mentions the bot or contains any specific command
        if self.bot.user.mentioned_in(message) or any(word in message.content for word in ["chat", "question", "glazer", "solar glazer", "bot"]):
            user_input = message.content
       

        # Optionally, respond to regular messages without a command
        ##if len(message.content) > 0:  # Respond to any non-empty message
        ##    user_input = message.content
        ##    
        ##    # Simulate typing
        ##    async with message.channel.typing():
        ##        # Call the OpenAI API
        ##        response = await self.ask_chatgpt(user_input)
##
        ##    # Send the response back to the channel using the webhook
        ##    self.send_to_discord(f"{message.author.mention} {response}")
       

            async with message.channel.typing():  # Use the typing indicator while processing the response
                # Call the OpenAI API
                response = await self.ask_chatgpt(user_input)
        
            # Send the response back to the channel   
            self.send_to_discord(f"{message.author.mention} {response}")

    def send_to_discord(self, message):
        data = {
            "content": message,
            "username": "Solar Glazer"  # Set the username for the webhook message
        }
        requests.post(WEBHOOK_URL, json=data)

# Set up the setup function to add the cog
async def setup(bot):
    await bot.add_cog(ChatGPTCog(bot))

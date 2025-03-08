import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import os
import uuid
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("APIKeyCog")

class APIKeyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.bot_api_key = os.getenv("BOT_API_KEY")
        self.api_url = "http://localhost:5000"

    async def cog_unload(self):
        logger.debug("Closing aiohttp session")
        await self.session.close()

    async def _make_api_request(self, method, endpoint, data=None):
        headers = {"X-API-Key": self.bot_api_key}
        url = f"{self.api_url}/{endpoint}"
        logger.debug(f"Making {method} request to {url} with data: {data}, headers: {headers}")
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)  # Set a timeout to prevent hanging
            async with self.session.request(method, url, headers=headers, json=data, timeout=timeout) as response:
                logger.debug(f"Response status: {response.status}")
                
                # Read the response content regardless of status code
                content = await response.text()
                logger.debug(f"Response content: {content}")
                
                return response
        except aiohttp.ClientError as e:
            logger.error(f"Client error in API request: {str(e)}")
            raise  # Re-raise to be handled by the calling function

    apikey_group = app_commands.Group(name="apikey", description="Manage API keys")

    @apikey_group.command(name="create", description="Create a new API key")
    async def create_key(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        
        # Extract the user's role IDs
        role_ids = [role.id for role in interaction.user.roles]
        
        data = {
            "user_id": user_id,
            "roles": role_ids  # Include the user's roles in the request
        }
        
        logger.debug(f"Starting key creation for user_id: {user_id} with roles: {role_ids}")

        try:
            await interaction.response.defer(ephemeral=True)
            logger.debug("Deferred interaction response")

            response = await self._make_api_request("POST", "api_keys", data=data)
            raw_response = await response.text()
            logger.debug(f"Raw API response: {raw_response}")

            if response.status == 200:
                try:
                    response_data = await response.json()
                    logger.debug(f"Parsed API response: {response_data}")
                    new_key = response_data.get("api_key")
                    if not new_key:
                        new_key = str(uuid.uuid4())
                        logger.warning("API did not return a key; generated locally")
                    await interaction.followup.send(
                        f"Your new API key is: `{new_key}`", ephemeral=True
                    )
                except aiohttp.ContentTypeError as e:
                    logger.error(f"Failed to parse JSON: {str(e)}, raw response: {raw_response}")
                    await interaction.followup.send(
                        "API returned invalid JSON.", ephemeral=True
                    )
            elif response.status == 400:
                try:
                    response_data = await response.json()
                    error_msg = response_data.get("error", "Bad request")
                    logger.debug(f"400 error response: {response_data}")
                    await interaction.followup.send(f"Error: {error_msg}", ephemeral=True)
                except aiohttp.ContentTypeError:
                    logger.error(f"Failed to parse 400 response: {raw_response}")
                    await interaction.followup.send(
                        f"Error: Bad request (invalid response format)", ephemeral=True
                    )
            elif response.status == 404:
                await interaction.followup.send("API endpoint not found.", ephemeral=True)
            elif response.status == 401:
                await interaction.followup.send("Bot’s API key is invalid.", ephemeral=True)
            elif response.status == 500:
                await interaction.followup.send("API server error occurred.", ephemeral=True)
            else:
                await interaction.followup.send(f"API error: {response.status}", ephemeral=True)
        except aiohttp.ClientError as e:
            logger.error(f"Network error: {str(e)}")
            await interaction.followup.send("Network error occurred.", ephemeral=True)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            await interaction.followup.send("An unexpected error occurred.", ephemeral=True)

    @apikey_group.command(name="list", description="List your API keys")
    async def list_keys(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        logger.debug(f"Listing API keys for user_id: {user_id}")

        try:
            await interaction.response.defer(ephemeral=True)
            
            response = await self._make_api_request("GET", f"api_keys/user/{user_id}")
            
            if response.status == 200:
                try:
                    response_data = await response.json()
                    keys = response_data.get("keys", [])
                    
                    if not keys:
                        await interaction.followup.send("You don't have any API keys.", ephemeral=True)
                        return
                    
                    # Modified line to handle missing 'created_at' field
                    keys_text = "\n".join([f"• `{key['key']}` (Created: {key.get('created_at', 'Unknown date')})" for key in keys])
                    await interaction.followup.send(
                        f"Your API keys:\n{keys_text}", ephemeral=True
                    )
                except Exception as e:
                    logger.error(f"Error processing keys: {str(e)}")
                    await interaction.followup.send("Error retrieving your API keys.", ephemeral=True)
            else:
                await interaction.followup.send(f"Error retrieving your API keys. Status: {response.status}", ephemeral=True)
        except Exception as e:
            logger.error(f"Unexpected error in list_keys: {str(e)}", exc_info=True)
            await interaction.followup.send("An unexpected error occurred.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(APIKeyCog(bot))
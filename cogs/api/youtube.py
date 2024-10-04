import os
import requests
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

# Load environment variables from .env file
load_dotenv()

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
YOUTUBE_BASE_URL = 'https://www.googleapis.com/youtube/v3/'

class YouTubeListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_video_id = {}
        self.listening_tasks = {}

    def get_channel_id_from_handle(self, handle):
        """Fetch the channel ID from a YouTube handle"""
        url = f"{YOUTUBE_BASE_URL}search?part=snippet&type=channel&q={handle}&key={YOUTUBE_API_KEY}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            if 'items' in data and len(data['items']) > 0:
                return data['items'][0]['snippet']['channelId']  # Get the channelId from the first search result
        return None

    def fetch_latest_video(self, channel_id):
        """Fetch the latest video from a YouTube channel."""
        url = f"{YOUTUBE_BASE_URL}search?key={YOUTUBE_API_KEY}&channelId={channel_id}&part=snippet&order=date&type=video&maxResults=1"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            if 'items' in data and len(data['items']) > 0:
                latest_video = data['items'][0]
                video_id = latest_video['id']['videoId']
                video_title = latest_video['snippet']['title']
                video_url = f"https://www.youtube.com/watch?v={video_id}"

                # Check if it's a new video
                if channel_id in self.last_video_id and self.last_video_id[channel_id] == video_id:
                    return None  # No new video

                # Update the last seen video ID
                self.last_video_id[channel_id] = video_id
                return {"title": video_title, "url": video_url}

        return None

    @discord.app_commands.command(name="latest_video", description="Get the latest video from a YouTube handle")
    async def latest_video(self, ctx, handle: str):
        """Command to fetch the latest video from a YouTube handle."""
        channel_id = self.get_channel_id_from_handle(handle)
        if channel_id:
            video_data = self.fetch_latest_video(channel_id)

            if video_data:
                await ctx.response.send_message(f"Latest video from the channel: {video_data['title']}\n{video_data['url']}")
            else:
                await ctx.response.send_message(f"No new video found for the channel with handle {handle}.")
        else:
            await ctx.response.send_message(f"Channel with handle {handle} not found.")

    @discord.app_commands.command(name="yt_listener", description="Start listening for new videos on a YouTube channel handle")
    async def yt_listener(self, ctx, handle: str):
        """Command to start listening for new uploads from a YouTube channel handle."""
        channel_id = self.get_channel_id_from_handle(handle)
        if channel_id:
            if channel_id in self.listening_tasks:
                await ctx.response.send_message(f"Already listening for new videos from the channel with handle {handle}.")
            else:
                self.listening_tasks[channel_id] = self.bot.loop.create_task(self.check_for_new_videos(ctx, channel_id))
                await ctx.response.send_message(f"Started listening for new videos from the channel with handle {handle}.")
        else:
            await ctx.response.send_message(f"Channel with handle {handle} not found.")

    async def check_for_new_videos(self, ctx, channel_id):
        """Background task to check for new videos."""
        try:
            while True:
                video_data = self.fetch_latest_video(channel_id)

                if video_data:
                    await ctx.response.send_message(f"New video uploaded! {video_data['title']}\n{video_data['url']}")

                await asyncio.sleep(600)  # Check every 10 minutes
        except Exception as e:
            await ctx.response.send_message(f"Error checking for new videos: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(YouTubeListener(bot))

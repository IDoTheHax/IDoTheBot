import discord
import os
import _osx_support
from discord.ext import commands
import requests
import json

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready(): 
    print(f'We have logged in as {bot.user}')

@bot.before_invoke
async def before_any_command(ctx):
    cmd = ctx.command.name
    if cmd != 'embed' or cmd != 'analyze' or cmd != 'analyse':
        if ctx.command.name == 'delete':
            await ctx.send(f'Deleting Message')
        else:
            await ctx.send(f'Executing command: {ctx.command}')


@bot.command()
async def embed(ctx,  title,  description,  color): 
    embed = discord.Embed(title=title,  description=description,  color=int(color,  16))
    await ctx.send(embed=embed)

@bot.command()
async def github(ctx,  username,  repository): 
    url = f'https://api.github.com/repos/{username}/{repository}'
    response = requests.get(url)
    data = json.loads(response.text)
    
    embed = discord.Embed(title=data['name'],  description=data['description'],  color=0x00ff00)
    embed.add_field(name='Stars',  value=data['stargazers_count'])
    embed.add_field(name='Forks',  value=data['forks_count'])
    embed.add_field(name='Watchers',  value=data['watchers_count'])
    embed.set_footer(text=f'Created at {data["created_at"]}')
    
    await ctx.send(embed=embed)

@bot.command()
async def analyze(ctx, code): 
    crash_report_channels = ['crash-reports', 'errors']  # Add channel names to check
    for channel_name in crash_report_channels:
        channel = discord.utils.get(ctx.guild.channels, name=channel_name)
        if channel:
            async for message in channel.history(limit=100):
                if code in message.content:
                    await ctx.send(f'Found crash report in {channel.mention}:\n{message.jump_url}')
                    return
    await ctx.send('Crash report not found.')

async def analyse(ctx, code): 
    crash_report_channels = ['crash-reports', 'errors']  # Add channel names to check
    for channel_name in crash_report_channels:
        channel = discord.utils.get(ctx.guild.channels, name=channel_name)
        if channel:
            async for message in channel.history(limit=100):
                if code in message.content:
                    await ctx.send(f'Found crash report in {channel.mention}:\n{message.jump_url}')
                    return
    await ctx.send('Crash report not found.')

@bot.command()
async def mappings(ctx, mapping):
    pass

@bot.command()
async def moderate(ctx,  message_id,  action): 
    message = await ctx.fetch_message(message_id)
    if action == 'delete': 
        await message.delete()
    elif action == 'edit': 
        await message.edit(content='This message has been edited.')
    else: 
        await ctx.send('Invalid action.')

with open(os.path.expanduser('token.txt'), 'r') as file:
    TOKEN = file.read().strip()
bot.run(TOKEN) ## define token.txt on the server your running it on
print(TOKEN)
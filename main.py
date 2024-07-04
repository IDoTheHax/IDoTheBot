import discord
from discord.ext import commands

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready(): 
    print(f'We have logged in as {bot.user}')

@bot.command()
async def embed(ctx,  title,  description,  color): 
    embed = discord.Embed(title=title,  description=description,  color=int(color,  16))
    await ctx.send(embed=embed)

@bot.command()
async def github(ctx,  username,  repository): 
    url = f'https: //api.github.com/repos/{username}/{repository}'
    response = requests.get(url)
    data = json.loads(response.text)
    
    embed = discord.Embed(title=data['name'],  description=data['description'],  color=0x00ff00)
    embed.add_field(name='Stars',  value=data['stargazers_count'])
    embed.add_field(name='Forks',  value=data['forks_count'])
    embed.add_field(name='Watchers',  value=data['watchers_count'])
    embed.set_footer(text=f'Created at {data["created_at"]}')
    
    await ctx.send(embed=embed)

@bot.command()
async def analyze(ctx,  code): 
    # Add your crash report analysis code here
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

bot.run('HEHEHEHEH') # Add real token here and find a way to hide it
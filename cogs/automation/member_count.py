import discord
from discord.ext import commands, tasks

class MemberCount(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_member_count.start()  # Start the task that updates member counts
        self.member_count_channels = {}  # Dictionary to store member count channels per guild

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        # Initialize the member count channel if a guild is joined
        await self.update_member_count_for_guild(guild)

    @tasks.loop(minutes=10)  # Update the member count every 10 minutes
    async def update_member_count(self):
        for guild_id, channel_id in self.member_count_channels.items():
            guild = self.bot.get_guild(guild_id)
            if guild:
                channel = guild.get_channel(channel_id)
                if channel:
                    member_count = guild.member_count
                    await channel.edit(name=f"Members: {member_count}")
                    print(f"Updated member count for guild {guild.name} to {member_count}")

    @discord.app_commands.command(name="setmembercount")
    @commands.has_permissions(manage_channels=True)
    async def set_member_count_channel(self, ctx, channel: discord.VoiceChannel):
        """Set the channel where the member count will be displayed."""
        guild_id = ctx.guild.id
        self.member_count_channels[guild_id] = channel.id

        # Update the channel name immediately when setting it up
        member_count = ctx.guild.member_count
        await channel.edit(name=f"Members: {member_count}")

        await ctx.send(f"Member count channel set to: {channel.name}")

    async def update_member_count_for_guild(self, guild):
        """Update the member count channel for a specific guild."""
        if guild.id in self.member_count_channels:
            channel_id = self.member_count_channels[guild.id]
            channel = guild.get_channel(channel_id)
            if channel:
                member_count = guild.member_count
                await channel.edit(name=f"Members: {member_count}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Update the member count when a new member joins
        await self.update_member_count_for_guild(member.guild)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # Update the member count when a member leaves
        await self.update_member_count_for_guild(member.guild)

async def setup(bot):
    await bot.add_cog(MemberCount(bot))

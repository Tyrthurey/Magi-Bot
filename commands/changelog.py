import nextcord
from nextcord.ext import commands
from main import supabase
import asyncio
from datetime import datetime, timezone


class ChangelogCog(commands.Cog):

  def __init__(self, bot):
    self.bot = bot
    self.supabase = supabase

  @commands.command()
  async def changelog(self, ctx, arg=None):
    if arg is None:
      result = await self.get_latest_changelog()
      if result:
        await self.send_changelog_embed(ctx, result)
      else:
        await ctx.send("No changelog found.")
    elif arg.lower() == "list":
      results = await self.get_changelogs()
      if results:
        await self.send_changelog_list(ctx, results)
      else:
        await ctx.send("No changelogs found.")
    elif arg.isdigit():
      result = await self.get_changelog_by_number(int(arg))
      if result:
        await self.send_changelog_embed(ctx, result)
      else:
        await ctx.send(f"No changelog found with number {arg}.")

  async def send_changelog_embed(self, ctx, changelog):
    embed = nextcord.Embed(title=changelog['title'],
                           description=changelog['description'],
                           color=nextcord.Color.blue())
    timestamp = int(
        datetime.fromisoformat(
            changelog['date']).replace(tzinfo=timezone.utc).timestamp())
    embed.add_field(name="", value=f"Date: <t:{timestamp}:f>", inline=False)
    embed.set_footer(text=f"To see all changelogs do `changelog list`")
    await ctx.send(embed=embed)

  async def send_changelog_list(self, ctx, changelogs):
    embed = nextcord.Embed(title="Changelog list", color=nextcord.Color.blue())
    for i, changelog in enumerate(changelogs, start=1):
      timestamp = int(
          datetime.fromisoformat(
              changelog['date']).replace(tzinfo=timezone.utc).timestamp())
      embed.add_field(name="",
                      value=f"`{i}` - <t:{timestamp}:f>",
                      inline=False)
    embed.set_footer(text=f"To view a changelog do 'changelog <number>`")
    await ctx.send(embed=embed)

  async def get_latest_changelog(self):
    response = self.supabase.table('Changelog').select('*').order(
        'date', desc=True).limit(1).execute()
    if response:
      data = response.data
      if data:
        return data[0]
    return None

  async def get_changelogs(self):
    response = self.supabase.table('Changelog').select('*').order(
        'date', desc=True).limit(10).execute()
    if response:
      data = response.data
      if data:
        return data
    return None

  async def get_changelog_by_number(self, number):
    response = self.supabase.table('Changelog').select('*').order(
        'date', desc=True).limit(1).offset(number - 1).execute()
    if response:
      data = response.data
      if data:
        return data[0]
    return None


def setup(bot):
  bot.add_cog(ChangelogCog(bot))

import asyncio
from datetime import datetime
import nextcord
from nextcord.ext import commands
from main import bot, supabase  # Import necessary objects from your project


class Leaderboard(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @commands.command(name="leaderboard",
                    aliases=["lb"],
                    help="Displays the top players by level.")
  async def leaderboard(self, ctx):
    # Fetch top 10 users by level
    results = supabase.table('Players').select('*').eq('is_bot', False).order(
        'level', desc=True).order('adventure_exp',
                                  desc=True).limit(10).execute()

    # Check if the request was successful
    if results.data:
      leaderboard = "\n".join([
          f"{idx + 1}. {user['username']} - Level {user['level']} (EXP: {user['adventure_exp']})"
          for idx, user in enumerate(results.data)
      ])
      await ctx.send(
          f"Top Players by Level and Experience:\n(Top 3 in both Level and EXP of The Beta-Testers will get a reward.)\n**TOP 3 WINNERS ARE**: 1st - `roizah`, 2nd - `Nephilem#4143` and 3rd - `robertblaise`\n{leaderboard}"
      )
    else:
      await ctx.send("Could not retrieve the leaderboard at this time.")


def setup(bot):
  bot.add_cog(Leaderboard(bot))

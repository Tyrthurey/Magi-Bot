import asyncio
from datetime import datetime
import nextcord
from nextcord.ext import commands
from main import bot, supabase  # Import necessary objects from your project
from functions.get_achievement import GetAchievement
import logging


class Leaderboard(commands.Cog):
  current_first_place = None  # Class variable to store current first place

  def __init__(self, bot):
    self.bot = bot
    self.get_achievement = GetAchievement(bot)

  async def update_first_place(self, new_first_place_user_id):
    first_place_achievement_id = 12  # ID for the first place achievement
    print('------------------------------------------------------------')
    print('Current first place user ID:', Leaderboard.current_first_place)
    print('New first place user ID:', new_first_place_user_id)
    print('------------------------------------------------------------')

    if new_first_place_user_id != Leaderboard.current_first_place:
      if Leaderboard.current_first_place:
        former_user_id = Leaderboard.current_first_place
        former_user = await self.bot.fetch_user(former_user_id)
        if former_user:  # Check if the former user is valid
          await self.get_achievement.remove_achievement(former_user_id, 12)
        else:
          logging.error(
              f"Could not fetch former first place user with ID: {former_user_id}"
          )

      Leaderboard.current_first_place = new_first_place_user_id

      new_user = await self.bot.fetch_user(new_first_place_user_id)
      if new_user:  # Check if the new first place user is valid
        await self.get_achievement.get_dm_achievement(new_first_place_user_id,
                                                      12)
      else:
        logging.error(
            f"Could not fetch new first place user with ID: {new_first_place_user_id}"
        )

  @commands.command(name="leaderboard",
                    aliases=["lb"],
                    help="Displays the top players by level.")
  async def leaderboard(self, ctx):
    # Fetch top 10 users by level
    results = supabase.table('Users').select('*').order(
        'level', desc=True).order('adventure_exp',
                                  desc=True).limit(10).execute()

    # Check if the request was successful
    if results.data:
      # Check if the first place has changed
      await self.update_first_place(results.data[0]['discord_id'])

      leaderboard = "\n".join([
          f"{idx + 1}. {user['username']} - Level {user['level']} (EXP: {user['adventure_exp']})"
          for idx, user in enumerate(results.data)
      ])
      await ctx.send(
          f"Top Players by Level and Experience:\n(Top 3 in both Level and EXP of The Beta-Testers will get a reward.)\n**TOP 3 WINNERS (FROM PREVIOUS COMP) ARE**: 1st - `roizah`, 2nd - `Nephilem#4143` and 3rd - `robertblaise`\n{leaderboard}"
      )
    else:
      await ctx.send("Could not retrieve the leaderboard at this time.")


def setup(bot):
  bot.add_cog(Leaderboard(bot))

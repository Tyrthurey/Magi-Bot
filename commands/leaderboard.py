import asyncio
from datetime import datetime
import nextcord
from nextcord.ext import tasks
from nextcord.ext import commands
from main import bot, supabase  # Import necessary objects from your project
from functions.get_achievement import GetAchievement
import logging


class Leaderboard(commands.Cog):
  current_first_place = None  # Class variable to store current first place

  def __init__(self, bot):
    self.bot = bot
    self.get_achievement = GetAchievement(bot)
    self.update_leaderboard.start()

  def cog_unload(self):
    self.update_leaderboard.cancel()

  @tasks.loop(minutes=5.0)
  async def update_leaderboard(self):
    # Query the database
    results = supabase.table('Users').select('*').execute()

    if results.data:
      # Sort the players first by level in descending order, then by adventure_exp in descending order
      sorted_data = sorted(results.data,
                           key=lambda x: (-x['level'], -x['adventure_exp']))
      sorted_data[:10]  # Return only the top 10 players

    new_first_place_user_id = sorted_data[0]['discord_id']

    await self.update_first_place(new_first_place_user_id)

  @update_leaderboard.before_loop
  async def before_update_leaderboard_task(self):
    print('Waiting...')
    await self.bot.wait_until_ready()

  async def update_first_place(self, new_first_place_user_id):
    # first_place_achievement_id = 12  # ID for the first place achievement
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
      else:
        print("No first place. Probably a restart.")
      Leaderboard.current_first_place = new_first_place_user_id

      new_user = await self.bot.fetch_user(new_first_place_user_id)
      if new_user and (former_user_id is not None):
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
    # Query the database
    results = supabase.table('Users').select('*').execute()

    if results.data:
      # Sort the players first by level in descending order, then by adventure_exp in descending order
      sorted_data = sorted(results.data,
                           key=lambda x: (-x['level'], -x['adventure_exp']))
      results = sorted_data[:10]  # Return only the top 10 players

      new_first_place_user_id = results[0]['discord_id']

      await self.update_first_place(new_first_place_user_id)

      leaderboard = "\n".join([
          f"{idx + 1}. {user['username']} - Level {user['level']} (EXP: {user['adventure_exp']})"
          for idx, user in enumerate(results)
      ])
      await ctx.send(
          f"Top Players by Level and Experience:\n(Top 3 in both Level and EXP of The Beta-Testers will get a reward.)\n**TOP 3 WINNERS (FROM PREVIOUS COMP) ARE**: 1st - `roizah`, 2nd - `Nephilem#4143` and 3rd - `robertblaise`\n{leaderboard}"
      )
    else:
      await ctx.send("Could not retrieve the leaderboard at this time.")

  @bot.slash_command(name="leaderboard",
                     description="Displays the top players by level.")
  async def leaderboard_slash(self, interaction: nextcord.Interaction):
    # Query the database
    results = supabase.table('Users').select('*').execute()

    if results.data:
      # Sort the players first by level in descending order, then by adventure_exp in descending order
      sorted_data = sorted(results.data,
                           key=lambda x: (-x['level'], -x['adventure_exp']))
      results = sorted_data[:10]  # Return only the top 10 players

      new_first_place_user_id = results[0]['discord_id']

      await self.update_first_place(new_first_place_user_id)

      leaderboard = "\n".join([
          f"{idx + 1}. {user['username']} - Level {user['level']} (EXP: {user['adventure_exp']})"
          for idx, user in enumerate(results)
      ])
      await interaction.response.send_message(
          f"Top Players by Level and Experience:\n(Top 3 in both Level and EXP of The Beta-Testers will get a reward.)\n**TOP 3 WINNERS (FROM PREVIOUS COMP) ARE**: 1st - `roizah`, 2nd - `Nephilem#4143` and 3rd - `robertblaise`\n{leaderboard}"
      )
    else:
      await interaction.response.send_message(
          "Could not retrieve the leaderboard at this time.")


def setup(bot):
  bot.add_cog(Leaderboard(bot))

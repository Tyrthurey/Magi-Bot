from nextcord.ext import commands
from nextcord import Embed, Reaction, User

import asyncio
import nextcord
from nextcord.ext import commands
from supabase import Client, create_client
from dotenv import load_dotenv
from functions.load_settings import command_prefix, get_embed_color
import os
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


class Achievements(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @commands.group(invoke_without_command=True,
                  aliases=["ach", "achievement"],
                  help="Display your achievements.")
  async def achievements(self, ctx):
    user_id = ctx.author.id

    # Fetch all achievements from the Achievements table
    all_achievements_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Achievements').select(
            'id, achievement_name, achievement_description, achievement_requirement, hidden'
        ).execute())

    if not all_achievements_response.data:
      await ctx.send("There are no achievements available.")
      return

    all_achievements = all_achievements_response.data

    # Fetch the inventory data for the user
    inventory_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Inventory').select('achievements').eq(
            'discord_id', user_id).execute())

    inventory_data = inventory_response.data[
        0] if inventory_response.data else None
    user_achievements = inventory_data.get('achievements',
                                           []) if inventory_data else []

    # Convert user achievements to a dict for easy lookup
    user_achievements_dict = {ach['id']: ach for ach in user_achievements}

    # Create an embed for the achievements
    embed_color = await get_embed_color(
        None if ctx.guild is None else ctx.guild.id)
    embed = Embed(color=embed_color)
    avatar_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
    embed.set_author(name=ctx.author.display_name, icon_url=avatar_url)

    page = 0
    per_page = 4

    # Calculate visible achievements
    visible_achievements = [
        ach for ach in all_achievements if not ach['hidden']
    ]

    # Calculate completed achievements
    completed_achievements = len(
        [ach for ach in user_achievements if ach['awarded']])

    # Calculate max_pages based on visible achievements
    max_pages = (len(visible_achievements) - 1) // per_page

    total_achievements = len(all_achievements)
    hidden_achievements = total_achievements - len(visible_achievements)

    async def update_embed():
      start = page * per_page
      end = start + per_page
      embed.clear_fields()
      embed.title = f"Your Achievements"
      embed.add_field(name=f"-----------------------------------------",
                      value="",
                      inline=False)

      for i in range(start, min(end, len(visible_achievements))):
        achievement_data = visible_achievements[i]
        achievement_id = achievement_data['id']
        user_achievement = user_achievements_dict.get(achievement_id, None)

        if user_achievement and user_achievement['awarded']:
          embed.add_field(
              name=f"{achievement_data['achievement_name']}",
              value=f"📜 {achievement_data['achievement_description']}",
              inline=False)
        else:
          embed.add_field(
              name=f"🔒 ~~{achievement_data['achievement_name']}~~ 🔒",
              value=f"📜 {achievement_data['achievement_requirement']}",
              inline=False)
        embed.add_field(name=f"-----------------------------------------",
                        value="",
                        inline=False)
      embed.add_field(
          name="",
          value=
          f"**Completed:** {completed_achievements}/{total_achievements}<:literallynothing:1175951091800740000> | <:literallynothing:1175951091800740000>**Hidden:** {hidden_achievements}",
          inline=False)
      embed.add_field(name=f"Page {page + 1}/{max_pages + 1}",
                      value="",
                      inline=False)

    def check(reaction: Reaction, user: User):
      return user.id == ctx.author.id and str(reaction.emoji) in ["⬅️", "➡️"]

    await update_embed()
    message = await ctx.send(embed=embed)
    await message.add_reaction("⬅️")
    await message.add_reaction("➡️")

    while True:
      try:
        reaction, user = await self.bot.wait_for("reaction_add",
                                                 timeout=60,
                                                 check=check)
        if str(reaction.emoji) == "➡️" and page < max_pages:
          page += 1
        elif str(reaction.emoji) == "⬅️" and page > 0:
          page -= 1
        else:
          continue
        await message.remove_reaction(reaction, user)
        await update_embed()
        await message.edit(embed=embed)
      except asyncio.TimeoutError:
        await message.clear_reactions()
        break


def setup(bot):
  bot.add_cog(Achievements(bot))

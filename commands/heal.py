import asyncio
from nextcord.ext import commands
from functions.check_inventory import check_inventory
from functions.item_write import item_write
from functions.load_settings import command_prefix
import random

import logging
import os

from dotenv import load_dotenv
from supabase import Client, create_client

from classes.Player import Player

load_dotenv()
logging.basicConfig(level=logging.INFO)
url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


class Heal(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @commands.command(name="heal", help="Heals you using a Healing Potion.")
  async def heal(self, ctx):
    user_data_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Users').select('*').eq(
            'discord_id', ctx.author.id).execute())
    if not user_data_response.data:
      await ctx.send(
          f"{ctx.author} does not have a profile yet.\nPlease type `::start`.")
      return
    user_data = user_data_response.data[0]
    using_command = user_data['using_command']
    if using_command:
      await ctx.send(
          "You're already in a command. Finish it before starting another.")
      return
    # Call the `healing` function
    heal_message = await self.healing(ctx)
    await ctx.send(heal_message)

  async def healing(self, ctx):
    command_prefix_str = await command_prefix(self.bot, ctx.message)
    ITEM_ID = 1  # Assuming ITEM_ID 1 is always the health potion

    # Get the user's health and max_health
    player_response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: supabase.table('Users').select('health', 'max_health').eq(
            'discord_id', ctx.author.id).execute())

    if player_response.data:
      player_data = player_response.data[0]
      current_health = player_data['health']
      max_health = player_data['max_health']
      player = Player(ctx.author)

      if current_health < max_health:
        # Check if the user has a health potion in inventory using check_inventory
        potion_quantity_lesser = await check_inventory(ctx.author.id, ITEM_ID,
                                                       'item')
        potion_quantity_minor = await check_inventory(ctx.author.id, 2, 'item')
        if potion_quantity_lesser > 0:
          # Decrease the potion count by one using item_write
          await item_write(ctx.author.id, ITEM_ID, -1)

          heal_amount = random.randint(15, 25)
          player.health += heal_amount
          if player.health >= player.max_health:
            player.health = player.max_health
          player.update_health()

          return f"**{ctx.author}** has used a <:healthpotion:1175114505013968948> **(Lesser) Health Potion** \n+`{heal_amount}` HP! Current HP: `{player.health}`/`{player.max_health}`"
        elif potion_quantity_minor > 0:
          # Decrease the potion count by one using item_write
          await item_write(ctx.author.id, 2, -1)

          heal_amount = random.randint(30, 50)
          player.health += heal_amount
          if player.health >= player.max_health:
            player.health = player.max_health
          player.update_health()

          return f"**{ctx.author}** has used a <:healthpotion:1175114505013968948> **(Minor) Health Potion** \n+`{heal_amount}` HP! Current HP: `{player.health}`/`{player.max_health}`"
        else:
          return f"**{ctx.author}**, you don't have any health potions. \nUse `{command_prefix_str}buy health potion` to get one!"
      else:
        return f"**{ctx.author}**, your health is already full."
    else:
      return "You do not have a profile yet. Is this a bug? Type `::bug <description>` to report it!"


def setup(bot):
  bot.add_cog(Heal(bot))

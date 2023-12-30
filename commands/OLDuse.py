# use.py
import asyncio
import logging
import os

from dotenv import load_dotenv
from supabase import Client, create_client
import nextcord
from nextcord.ext import commands

import random

from functions.check_inventory import check_inventory
from functions.item_write import item_write
from functions.load_settings import command_prefix
from functions.cooldown_manager import cooldown_manager_instance

from classes.Player import Player

load_dotenv()
logging.basicConfig(level=logging.INFO)
url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)

intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True  # Enables the member intent

# When you instantiate your bot, use the following lambda for the command_prefix
bot = commands.Bot(command_prefix=command_prefix,
                   intents=intents,
                   help_command=None,
                   case_insensitive=True)


async def using(ctx, *args):
  # Check if at least the item name is provided
  if not args:
    await ctx.send("Usage: `apo use [item name]` (without [])")
    return

  # Check if the last argument is an integer (the amount), and if not, default the amount to 1
  try:
    amount = int(args[-1])
    if amount <= 0:
      raise ValueError
    item_display_name = " ".join(args[:-1]).lower()
  except ValueError:  # Last argument is not an integer, so we assume it's part of the item name
    amount = 1
    item_display_name = " ".join(args).lower()

  # Lookup item ID, price, and other necessary details from the Items table
  item_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Items').select('*').ilike(
          'item_displayname', f'%{item_display_name}%').execute())

  item_data = item_response.data[0]
  useable = item_data['useable']

  if not useable or not item_response.data:
    await ctx.send("Item not found or amount invalid.")
    return

  item_data = item_response.data[0]
  ITEM_ID = item_data['item_id']
  user_id = ctx.author.id
  player = Player(ctx.author)

  # Check if the user has a health potion in inventory
  inventory_response = await check_inventory(user_id, ITEM_ID, 'item')

  if ITEM_ID == 12:
    if inventory_response > 0:
      # Decrease the pill count by one
      await item_write(user_id, ITEM_ID, -1)

      # Update the player's cooldowns
      cooldown_manager_instance.reduce_all_cooldowns(user_id, 55)

      await ctx.send(
          f"**{ctx.author}** is SUPERCHARGED! That :coffee: `coffee` is probably bad for their health though!"
      )
    else:
      await ctx.send("You don't have any coffee left. Sadge.")

  elif ITEM_ID == 1:
    if inventory_response > 0:
      # Decrease the pill count by one
      await item_write(user_id, ITEM_ID, -1)
      heal_amount = random.randint(15, 25)
      player.health += heal_amount
      if player.health >= player.max_health:
        player.health = player.max_health
      player.update_health()
      await ctx.send(
          f"**{ctx.author}** has used a <:healthpotion:1175114505013968948> **Health Potion (Lesser)**\n+`{heal_amount}` HP! Current HP: `{player.health}`/`{player.max_health}`"
      )
    else:
      await ctx.send(
          "You don't have any Lesser Health Potions. Sadge.\nUse `apo buy health potion` to buy some!"
      )
  elif ITEM_ID == 2:
    if inventory_response > 0:
      # Decrease the pill count by one
      await item_write(user_id, ITEM_ID, -1)
      heal_amount = random.randint(30, 50)
      player.health += heal_amount
      if player.health >= player.max_health:
        player.health = player.max_health
      player.update_health()
      await ctx.send(
          f"**{ctx.author}** has used a <:healthpotion:1175114505013968948> **Health Potion (Minor)**\n+`{heal_amount}` HP! Current HP: `{player.health}`/`{player.max_health}`"
      )
    else:
      await ctx.send(
          "You don't have any Minor Health Potions. Sadge.\nUse `apo buy health potion` to buy some!"
      )
  elif ITEM_ID == 17:
    if inventory_response > 0:
      # Decrease the pill count by one
      await item_write(user_id, ITEM_ID, -1)
      heal_amount = random.randint(100, 300)
      player.health += heal_amount
      if player.health >= player.max_health:
        player.health = player.max_health
      player.update_health()
      await ctx.send(
          f"**{ctx.author}** has used a <:healthpotion:1175114505013968948> **Health Potion (Major)**\n+`{heal_amount}` HP! Current HP: `{player.health}`/`{player.max_health}`"
      )
    else:
      await ctx.send(
          "You don't have any Major Health Potions. Sadge.\nUse `apo buy health potion` to buy some!"
      )
  else:
    await ctx.send("This item cannot be used. Duh.\nCheck your spelling.")


@commands.command(name="use", aliases=["eat", "drink"], help="Uses an item.")
async def use(ctx, *args):
  user_data_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Users').select('using_command').eq(
          'discord_id', ctx.author.id).execute())
  if not user_data_response.data:
    await ctx.send("You do not have a profile yet.")
    return

  user_data = user_data_response.data[0]
  using_command = user_data['using_command']
  # Check if the player is already in a command
  if using_command:
    await ctx.send(
        "You're already in a command. Finish it before starting another.")
    return
  await using(ctx, *args)


# Export the command function to be imported in main.py
def setup(bot):
  global bot_info
  bot.add_command(use)

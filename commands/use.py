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

  # Check if the last argument is "all" (to sell all items), or an integer (the amount),
  # and if neither, default the amount to 1
  if args[-1].lower() == 'all':
    item_display_name = " ".join(args[:-1]).lower()
    all_items = True
    amount = 1  # Assign a default value to amount
  else:
    all_items = False
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
  ITEM_NAME = item_data['item_displayname']
  EFFECT_ID = item_data['effect_id']
  print(EFFECT_ID)
  user_id = ctx.author.id
  player = Player(ctx.author)

  # Lookup item ID, price, and other necessary details from the Items table
  effect_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('ItemEffects').select('*').eq(
          'id', EFFECT_ID).execute())
  effect_data = effect_response.data[0]
  effect_name = effect_data['effect_name']
  print(effect_name)
  effect_category = effect_data['category']
  effect_modifier = effect_data['modifier']
  print(effect_category)
  print(effect_modifier)
  low_mod = 0
  high_mod = 0
  modifier = 0

  low_mod, high_mod = map(int, effect_modifier)

  print(f"LOW MOD: {low_mod}, HIGH MOD: {high_mod}")

  if low_mod == high_mod:
    modifier = low_mod

  # Check if the user has a health potion in inventory
  inventory_response = await check_inventory(user_id, ITEM_ID, 'item')

  if effect_category == 'healing':
    if inventory_response >= amount:
      amount_used = 0
      heal_amount = 0
      total_heal_amount = 0

      if all_items:
        amount = inventory_response

      while player.health < player.max_health and amount > 0:
        heal_amount = random.randint(low_mod, high_mod)
        player.health += heal_amount
        total_heal_amount += heal_amount
        amount -= 1
        amount_used += 1

      if player.health >= player.max_health:
        player.health = player.max_health

      if total_heal_amount == 0:
        message = f"**{ctx.author}** tried to use a health potion but they are already fully healed."
      else:
        message = f"**{ctx.author}** has used `{amount_used}` **{ITEM_NAME}(s)**\n+`{total_heal_amount}` HP! Current HP: `{player.health}`/`{player.max_health}`"

      await item_write(user_id, ITEM_ID, -amount_used)
      player.update_health()
      await ctx.send(message)
    else:
      await ctx.send(
          f"You don't have enough {ITEM_NAME}. Sadge.\nUse `apo buy health potion` to buy some!"
      )
  elif effect_category == 'time_travel':
    if inventory_response >= amount:
      amount_used = 0
      time_skip_amount = 0
      total_time_skip_amount = 0

      if all_items:
        amount = inventory_response

      while amount > 0:
        time_skip_amount += random.randint(low_mod, high_mod)
        total_time_skip_amount += time_skip_amount
        amount -= 1
        amount_used += 1

      await item_write(user_id, ITEM_ID, -amount_used)
      # Update the player's cooldowns
      cooldown_manager_instance.reduce_all_cooldowns(user_id,
                                                     total_time_skip_amount)

      minutes, seconds = divmod(int(total_time_skip_amount), 60)
      hours, minutes = divmod(minutes, 60)
      days, hours = divmod(hours, 24)

      if days > 0:
        timeskip_message = f"{days}d {hours}h {minutes}m {seconds}s"
      elif hours > 0:
        timeskip_message = f"{hours}h {minutes}m {seconds}s"
      elif minutes > 0:
        timeskip_message = f"{minutes}m {seconds}s"
      else:
        timeskip_message = f"{seconds}s"

      await ctx.send(
          f"**{ctx.author}** is SUPERCHARGED after drinking `{amount_used}` **{ITEM_NAME}(s)**!!\n+`{timeskip_message}` cooldown reduction!"
      )
    else:
      await ctx.send(f"You don't have enough **{ITEM_NAME}** left. Sadge.")

  else:
    await ctx.send("This item cannot be used. Duh.\nCheck your spelling.")


@commands.command(name="use", aliases=["eat", "drink"], help="Uses an item.")
async def use(ctx, *args):
  user_data_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Users').select('using_command').eq(
          'discord_id', ctx.author.id).execute())
  if not user_data_response.data:
    await ctx.send("You do not have a profile yet.\nPlease use `apo start`.")
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

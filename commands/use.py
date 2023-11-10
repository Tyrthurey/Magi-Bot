# use.py
import asyncio
import logging
import os

from dotenv import load_dotenv
from supabase import Client, create_client
import nextcord
from nextcord.ext import commands

from functions.check_inventory import check_inventory
from functions.item_write import item_write
from functions.load_settings import command_prefix
from functions.cooldown_manager import cooldown_manager_instance

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
    await ctx.send("Usage: ::use [item name]")
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

  # Check if the user has a health potion in inventory
  inventory_response = await check_inventory(user_id, ITEM_ID, 'item')

  if ITEM_ID == 12:
    if inventory_response > 0:
      # Decrease the pill count by one
      await item_write(user_id, ITEM_ID, -1)

      # Update the player's cooldowns
      cooldown_manager_instance.reduce_all_cooldowns(user_id, 50)

      await ctx.send(
          f"**{ctx.author}** is SUPERCHARGED! That :coffee: `coffee` is probably bad for their health though!"
      )
    else:
      await ctx.send("You don't have any coffee left. Sadge.")
  else:
    await ctx.send("This item cannot be used. Duh.\nCheck your spelling.")


@commands.command(name="use", help="Uses an item.")
async def use(ctx, *args):
  await using(ctx, *args)


# Export the command function to be imported in main.py
def setup(bot):
  global bot_info
  bot.add_command(use)

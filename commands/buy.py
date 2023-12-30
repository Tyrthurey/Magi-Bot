"""===============================
Has not been integrated into main.py or the rest of the bot
==============================="""

import asyncio
import logging
import os
import nextcord
from nextcord.ext import commands
from supabase import Client, create_client
from dotenv import load_dotenv

from functions.item_write import item_write

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


async def buying(ctx, *args):
  # Check if at least the item name is provided
  if not args:
    await ctx.send("Usage: `apo buy [item name] [amount]` (without the [])")
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
  buyable = item_data['buyable']

  if not buyable or not item_response.data:
    await ctx.send("Item not found or amount invalid.")
    return

  item_data = item_response.data[0]
  ITEM_ID = item_data['item_id']
  ITEM_COST = item_data[
      'price'] * amount  # Now we use the price from the Items table

  user_id = ctx.author.id
  # Check user's balance
  balance_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Users').select('bal').eq(
          'discord_id', user_id).execute())

  if balance_response.data:
    balance = balance_response.data[0]['bal']
    if balance < ITEM_COST:
      await ctx.send(
          f"You don't have enough gold to buy this, noob.\n It costs `{ITEM_COST}` Gold."
      )
    else:
      # Deduct cost from balance
      new_balance = balance - ITEM_COST
      # Update the player's balance
      await asyncio.get_event_loop().run_in_executor(
          None, lambda: supabase.table('Users').update({
              'bal': new_balance
          }).eq('discord_id', user_id).execute())

      # Update inventory using the item_write function
      await item_write(user_id, ITEM_ID, amount)

      await ctx.send(
          f"**{ctx.author}** successfully bought `{amount}` **{item_data['item_displayname']}**(s) for `{ITEM_COST}` Gold."
      )
  else:
    await ctx.send("You do not have a profile yet.")


# Command function
@commands.command(name="buy", aliases=["b"], help="Buy an item!")
@commands.cooldown(1, 5, commands.BucketType.user
                   )  # Cooldown: 1 time per 5 seconds per user
async def buy(ctx, *args):
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
  await buying(ctx, *args)


# Error handler
async def buying_error(ctx, error):
  if isinstance(error, commands.CommandOnCooldown):
    await ctx.send(
        f"This command is on cooldown. You can use it again in `{error.retry_after:.2f}` seconds. \nPlease use `buy <item> <amount>` to prevent spam!"
    )
  elif IndexError:
    await ctx.send(
        "Invalid item name. Please use `buy <item> <amount>` to buy an item.\nLookup items using `shop`"
    )
  else:
    await ctx.send(f"An error occurred: {error}")


# Assign the error handler to the command
buy.error(buying_error)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(buy)

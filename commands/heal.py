import asyncio
import logging
import os

from dotenv import load_dotenv
from supabase import Client, create_client

from functions.check_inventory import check_inventory
from functions.item_write import item_write
from functions.load_settings import command_prefix

load_dotenv()
logging.basicConfig(level=logging.INFO)
url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


async def healing(ctx, bot):
  command_prefix_str = await command_prefix(bot, ctx.message)
  ITEM_ID = 1  # Assuming ITEM_ID 1 is always the health potion

  # Get the user's health and max_health
  player_response = await asyncio.get_event_loop().run_in_executor(
      None,
      lambda: supabase.table('Players').select('health', 'max_health').eq(
          'discord_id', ctx.author.id).execute())

  if player_response.data:
    player_data = player_response.data[0]
    current_health = player_data['health']
    max_health = player_data['max_health']

    if current_health < max_health:
      # Check if the user has a health potion in inventory using check_inventory
      potion_quantity = await check_inventory(ctx.author.id, ITEM_ID, 'item')

      if potion_quantity > 0:
        # Decrease the potion count by one using item_write
        await item_write(ctx.author.id, ITEM_ID,
                         -1)  # Assuming item_write can handle decrement

        # Update the player's health to max_health
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table('Players').update({
                'health': max_health
            }).eq('discord_id', ctx.author.id).execute())

        return f"**{ctx.author}** has healed to full HP!"
      else:
        return f"**{ctx.author}**, you don't have any health potions. \nUse `{command_prefix_str}buy health potion` to get one!"
    else:
      return f"**{ctx.author}**, your health is already full."
  else:
    return "You do not have a profile yet."

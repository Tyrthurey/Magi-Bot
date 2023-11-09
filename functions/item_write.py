from dotenv import load_dotenv
import logging
from supabase import create_client, Client
import os
import asyncio
from datetime import datetime, timedelta, timezone

load_dotenv()

logging.basicConfig(level=logging.INFO)

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


async def item_write(discord_id: int, item_id: int, amount: int):
  # Check if the user already has an inventory
  inventory_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Inventory').select('items').eq(
          'discord_id', discord_id).execute())

  inventory_data = inventory_response.data

  # Initialize an empty list for items if the user does not have an inventory
  # or if the 'items' field is None
  inventory_items = []

  # If the user has an inventory and the 'items' field is not None, get the items list
  if inventory_data and inventory_data[0]['items'] is not None:
    inventory_items = inventory_data[0]['items']['items']

  # Check if the item already exists in the inventory
  item_exists = next(
      (item for item in inventory_items if item['item_id'] == item_id), None)

  if item_exists:
    # Update the quantity of the existing item
    item_exists['quantity'] += amount
  else:
    # Add the new item to the inventory
    new_item = {
        'item_id': item_id,
        'quantity': amount,
        'cooldown': datetime.utcnow().isoformat()
    }
    inventory_items.append(new_item)

  # Prepare the updated inventory data
  updated_inventory_data = {'items': {'items': inventory_items}}

  # Write the updated items back to the inventory
  await asyncio.get_event_loop().run_in_executor(
      None,
      lambda: supabase.table('Inventory').update(updated_inventory_data).eq(
          'discord_id', discord_id).execute())

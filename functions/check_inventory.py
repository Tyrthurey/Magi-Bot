from dotenv import load_dotenv
import logging
from supabase import create_client, Client
import os
import asyncio

load_dotenv()

logging.basicConfig(level=logging.INFO)

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


async def check_inventory(discord_id: int, search_id: int, search_type: str):
  # Fetch the user's inventory data from the database
  response = await asyncio.get_event_loop().run_in_executor(
      None,
      lambda: supabase.table('Inventory').select('items', 'equipments').eq(
          'discord_id', discord_id).execute())

  # Check if the inventory exists and has the items or equipments key
  if response.data:
    inventory_data = response.data[0]

    # Depending on the search_type, look within 'items' or 'equipments'
    if search_type == 'item':
      inventory_list = inventory_data.get('items', {}).get('items', [])
    elif search_type == 'equipment':
      inventory_list = inventory_data.get('equipments',
                                          {}).get('equipments', [])
    else:
      raise ValueError("search_type must be 'item' or 'equipment'.")

    # Search the list for the item_id or equipment_id
    inventory_entry = next((entry for entry in inventory_list
                            if entry.get(f'{search_type}_id') == search_id),
                           None)

    # If the item or equipment is found and the quantity is more than 0, return the quantity
    if inventory_entry and inventory_entry['quantity'] > 0:
      return inventory_entry['quantity']
  else:
    # No inventory exists, so create one
    new_inventory_data = {
        'discord_id': discord_id,
        'items': {
            'items': []
        } if search_type == 'item' else {},
        'equipments': {
            'equipments': []
        } if search_type == 'equipment' else {}
    }
    await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: supabase.table('Inventory').insert(new_inventory_data).execute(
        ))
    # Return 0 as the inventory has just been created and will not have the item/equipment
    return 0

  # If the item or equipment is not found, or the inventory does not exist, return 0
  return 0

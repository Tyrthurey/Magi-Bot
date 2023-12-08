import nextcord
import logging
import os
from supabase import Client, create_client
from dotenv import load_dotenv

from functions.settings_manager import get_settings_cache

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


# Function to load settings including channel ID
async def load_settings(server_id: int):
  response = supabase.table('ServerSettings').select('settings').eq(
      'server_id', server_id).execute()
  if response.data:
    return response.data[0]['settings']
  else:
    # Include a 'channel_id' setting with a default value of None
    return {'embed_color': 'green', 'prefix': '::', 'channel_id': None}


async def command_prefix(bot, message):
  # Get the server ID from the message
  guild_id = message.guild.id if message.guild else None  # DMs do not have a guild

  if guild_id:
    settings = get_settings_cache(guild_id)
    if settings:
      prefix = settings.get('prefix', '::')
      return prefix
    else:
      # Query the prefix setting from the Supabase for the specific guild
      response = supabase.table('ServerSettings').select('settings').eq(
          'server_id', guild_id).execute()
      if response.data:
        settings = response.data[0]['settings']
        return settings.get('prefix', '::')  # Default to '::' if not found
  return '::'  # Default to '::' if we are in DMs or if the guild_id is not found


async def get_prefix(bot, message):
  # This is your previously defined async function to get the prefix
  prefix = await command_prefix(bot, message)
  return prefix


async def get_embed_color(guild_id: int):
  # Default color
  color_name = 'green'

  # Fetch settings from cache or database
  if guild_id:
    settings = get_settings_cache(guild_id)
    if settings:
      color_name = settings.get('embed_color', color_name)
    else:
      # Query the embed_color setting from the Supabase for the specific guild
      response = supabase.table('ServerSettings').select('settings').eq(
          'server_id', guild_id).execute()
      if response.data:
        settings = response.data[0]['settings']
        color_name = settings.get('embed_color', color_name)

  # Check if the color name is valid for nextcord.Color
  if hasattr(nextcord.Color, color_name.lower()):
    # Use getattr to get the nextcord.Color method corresponding to the color_name
    color_method = getattr(nextcord.Color, color_name.lower())
    # Call the method to get the color object
    return color_method()
  else:
    # Fallback to a default color if the provided color name is not valid
    return nextcord.Color.green()


bot_settings = {}

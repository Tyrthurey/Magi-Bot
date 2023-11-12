"""Everything related to handling XP and leveling up should go here"""

"""===============================
Has not been integrated into main.py or the rest of the bot
==============================="""

import asyncio
import logging
import nextcord
import os
import random
from dotenv import load_dotenv
from supabase import Client, create_client

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)

"""
  Create an "add_xp(discord_ID, exp gained)" function.
    Within that function, pull the player's profile,
    add the exp, check if it exceeds the next level mile stone,
    call a level_up() if appropriate, and returns the profile to the database.
"""

async def add_xp(ctx, user_id, exp_gain):

  user_data = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Players').select('*').eq(
          'discord_id', user_id).execute())

  
  if user_data:
    level_up_exp = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('LevelProgression').select(
            'total_level_exp').eq('level',user_data['level']).execute())
    
    if level_up_exp:
      user_data['adventure_exp'] += exp_gain
      
      if user_data['adventure_exp'] >= level_up_exp['total_level_exp']:
        user_data['adventure_exp'] -= level_up_exp['total_level_exp']
        level_up(user_data)
        user_data['level'] += 1
    else
      print("Error: Unable to retrieve level_up value from Database")
    
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Players').update(user_data, ['
  else
    print("Error: Unable to retrieve user_data from Database")



""" Seperate leveling up and xp handling into it's own functions.
    The level_up() function pulls the player's profile,
    double checks which level up they are getting,
    gives the player whatever choices for how they want to spend
    their level up points (or however you handle leveling up),
    and writes those changes back to the DB.
"""
    
async def level_up(user_data):
  user_data['level'] += 1
  # Static until we add choices/classes/other options
  additional_atk = 1
  additional_def = 1
  additional_magic = 1
  additional_magic_def = 1
  additional_max_health = 5
  new_max_health = max_health + additional_max_health

  # Update the player's health, adventure_exp, in the database
  supabase.table('Players').update({
    'health':
    max(1, new_health),  # Ensure health does not go below 1
    'level':
    new_level if level_up else user_level,

    # Only update these if there's a level up
    **({
        'atk': user_data['atk'] + additional_atk,
        'def': user_data['def'] + additional_def,
        'magic': user_data['magic'] + additional_magic,
        'magic_def': user_data['magic_def'] + additional_magic_def,
        'max_health': new_max_health
    } if level_up else {})
  }).eq('discord_id', user_id).execute()


"""===============================
Has not been integrated into main.py or the rest of the bot
==============================="""

import asyncio
import logging
import os
import random

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

logging.basicConfig(level=logging.INFO)

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


async def hunting(user_id):

  # Retrieve the current user data
  user_data_response = await asyncio.get_event_loop().run_in_executor(
      None,
      lambda: supabase.table('Players').select('*').eq('discord_id', user_id).execute()
  )
  if not user_data_response.data:
    await ctx.send("You do not have a profile yet.")
    return

  user_data = user_data_response.data[0]
  current_health = user_data['health']
  max_health = user_data['max_health']
  current_exp = user_data['adventure_exp']
  user_level = user_data['level']
  user_gold = user_data['bal']

  # Calculate the health reduction and gold reward
  health_loss_percentage = random.randint(40, 80)
  health_loss = math.floor(health_loss_percentage / 100 * max_health)
  gold_reward = random.randint(10, 40)
  new_health = current_health - health_loss

  # Check if the user "dies"
  if new_health <= 0:
    new_health = max_health  # Reset health to max if died
    lost_atk = max(1, user_data['atk'] - 1)
    lost_def = max(1, user_data['def'] - 1)
    lost_magic = max(1, user_data['magic'] - 1)
    lost_magic_def = max(1, user_data['magic_def'] - 1)
    lost_max_health = max(100, max_health - 5)

    # Update the player's health, level, adventure_exp, and gold in the database
    supabase.table('Players').update({
        'health': new_health,
           # Ensure level does not go below 1
        'level': max(1, user_level - 1),  
        'adventure_exp': 0,
           # Ensure gold does not go below 0
        'bal': max(0, user_gold - math.floor(10 / 100 * user_gold)),
        'atk': lost_atk,
        'def': lost_def,
        'magic': lost_magic,
        'magic_def': lost_magic_def,
        'max_health': lost_max_health
    }).eq('discord_id', user_id).execute()

    # Inform the user that they "died"
    await ctx.send(
        f"You have died during the hunt, when you got hit for `{health_loss}` HP.\n"
        f"You lost all rewards, including `1` level and `10`% of your gold."
    )
    return

  # Player Wins
  else:
    # Calculate the experience gained
    additional_exp = random.randint(10, 20) + (user_level - 1) * random.randint(3, 8)
    new_exp = current_exp + additional_exp

    # Check for level up
    if new_exp >= get_needed_exp_for_next_level(user_level + 1): 
############ Move exp level values to new table in supabase
      await handle_level_up(user_id, user_data, additional_exp)

    # Update the player's health, adventure_exp, and gold in the database
    supabase.table('Players').update({
           # Ensure health does not go below 1
        'health': max(1, new_health),  
        'adventure_exp': new_exp,
        'bal': user_gold + gold_reward
    }).eq('discord_id', user_id).execute()

    # Inform the user of the outcome of the hunt
    await ctx.send(
        f"**{ctx.author}** killed some :skull: **SKELETONS**! \n"
        f"Gained `{additional_exp}` EXP, and `{gold_reward}` gold! \n"
        f"Lost `{health_loss}` HP. Current Health: `{max(1, new_health)}/{max_health}` HP."
    )


# Function to handle level up logic
async def handle_level_up(user_id, user_data, additional_exp):
  user_level = user_data['level']
  user_data['bal']
  additional_atk = 1
  additional_def = 1
  additional_magic = 1
  additional_magic_def = 1
  additional_max_health = 5
  new_level = user_level + 1
  new_max_health = user_data['max_health'] + additional_max_health

  # Update the player's stats and level in the database
  supabase.table('Players').update({
      'level': new_level,
      'atk': user_data['atk'] + additional_atk,
      'def': user_data['def'] + additional_def,
      'magic': user_data['magic'] + additional_magic,
      'magic_def': user_data['magic_def'] + additional_magic_def,
      'max_health': new_max_health
  }).eq('discord_id', user_id).execute()

  # Inform the user about the level up
  await ctx.send(
      f"**{ctx.author}** killed some :skull: **SKELETONS**! \n"
      f"Gained `{additional_exp}` EXP, and leveled up to level `{new_level}`! \n"
      f"Stats increased: ATK: `{user_data['atk'] + additional_atk}`, "
      f"DEF: `{user_data['def'] + additional_def}`, "
      f"MAGIC: `{user_data['magic'] + additional_magic}`, "
      f"MAGIC DEF: `{user_data['magic_def'] + additional_magic_def}`"
      f"Health: `{new_max_health}` HP!"
  )

import asyncio
import logging
import os
import random
import math
from nextcord.ext import commands
from supabase import Client, create_client
from dotenv import load_dotenv
from functions.item_write import item_write
from functions.cooldown_manager import cooldown_manager_instance as cooldowns

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


async def hunting(ctx):
  user_id = ctx.author.id
  command_name = ctx.command.name
  cooldown_remaining = cooldowns.get_cooldown(user_id, command_name)

  if cooldown_remaining > 0:
    await ctx.send(
        f"This command is on cooldown. You can use it again in `{cooldown_remaining:.2f}` seconds."
    )
    return

  # Set the cooldown for the hunt command
  cooldowns.set_cooldown(user_id, command_name, 60)

  # Retrieve the current user data
  user_data_response = await asyncio.get_event_loop().run_in_executor(
    None, lambda: supabase.table('Players').select('*').eq(
        'discord_id', user_id).execute())
  if not user_data_response.data:
    await ctx.send("You do not have a profile yet.")
    return

  user_data = user_data_response.data[0]
  current_health = user_data['health']
  max_health = user_data['max_health']
  current_exp = user_data['adventure_exp']
  user_level = user_data['level']
  user_gold = user_data['bal']
  user_floor = user_data['floor']
  max_user_floor = user_data['max_floor']

  # Get the player's current floor
  player_floor = user_data['floor']

  # Load mobs list for the current floor and select a random mob
  mob_data_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Mobs').select('*').eq(
          'floor', player_floor).execute())

  mobs_list = mob_data_response.data if mob_data_response.data else []
  if not mobs_list:
    await ctx.send(f"No creatures to hunt on floor {player_floor}.")
    return

  selected_mob = random.choice(
      mobs_list)  # Randomly select a mob from the correct floor

  mob_name = f"{selected_mob['mob_displayname']}"

  # Retrieve the mob stats
  mob_atk = selected_mob['atk']
  mob_def = selected_mob['def']
  mob_magic = selected_mob['magic']
  mob_magic_def = selected_mob['magic_def']
  total_mob_stats = mob_atk + mob_def + mob_magic + mob_magic_def

  # Retrieve the player stats
  player_atk = user_data['atk']
  player_def = user_data['def']
  player_magic = user_data['magic']
  player_magic_def = user_data['magic_def']
  total_player_stats = player_atk + player_def + player_magic + player_magic_def

  # Scale damage taken based on the ratio between player's stats and mob's stats
  stat_ratio = total_player_stats / total_mob_stats

  if stat_ratio >= 3:
    # Player's stats are triple or more than the mob's stats, so no damage is taken
    health_loss = 0
  elif stat_ratio > 1:
    # If player's stats are greater than the mob's but less than triple
    # Scale damage from 0% at triple player's stats to 50% at equal stats
    health_loss = math.floor((2 - (stat_ratio / 3)) * 0.5 * max_health)
  elif stat_ratio == 1:
    # If player's stats are equal to the mob's stats
    health_loss = math.floor(0.5 * max_health)
  elif stat_ratio > 1 / 3:
    # If mob's stats are greater than the player's but less than triple
    # Scale damage from 50% at equal stats to 100% at triple mob's stats
    health_loss = math.floor((1 + (1 - (stat_ratio * 3)) * 0.5) * max_health)
  else:
    # Mob's stats are triple or more than the player's stats, player takes full health as damage
    health_loss = max_health

  # Calculate the health reduction and gold reward
  if user_floor < max_user_floor:
    health_loss = math.floor(health_loss * (user_floor + 1))
    gold_reward = random.randint(10, 40) - 10 * (user_floor)
    if gold_reward < 0:
      gold_reward = 0
  else:
    gold_reward = random.randint(10, 40)
  new_health = current_health - health_loss

  # Check if the user "dies"
  if new_health <= 0:
    new_health = max_health  # Reset health to max if died
    new_level = max(1, user_level - 1)  # Ensure level does not go below 1

    level_change = 0 if new_level == 1 else 1

    new_exp = 0
    gold_loss = random.randint(10, 30)
    user_gold = max(0, user_gold - math.floor(
        gold_loss / 100 * user_gold))  # Ensure gold does not go below 0
    lost_atk = max(1, user_data['atk'] - 1)
    lost_def = max(1, user_data['def'] - 1)
    lost_magic = max(1, user_data['magic'] - 1)
    lost_magic_def = max(1, user_data['magic_def'] - 1)
    lost_max_health = max(10, max_health - 5)

    # Update the player's health, level, adventure_exp, and gold in the database
    supabase.table('Players').update({
        'health': new_health,
        'level': new_level,
        'adventure_exp': new_exp,
        'bal': user_gold,
        'atk': lost_atk,
        'def': lost_def,
        'magic': lost_magic,
        'magic_def': lost_magic_def,
        'max_health': lost_max_health
    }).eq('discord_id', user_id).execute()

    diedmessage1 = (
        f"**{ctx.author.display_name}** WAS ABSOLUTELY DESTROYED by a {mob_name} that had TRIPLE THEIR STATS!!!\n"
        if stat_ratio <= 1 / 3 else "")

    diedmessage2 = (f"**{ctx.author}** couldn\'t handle a {mob_name}. "
                    if stat_ratio > 1 / 3 else "")

    # Inform the user that they "died"
    await ctx.send(
        f"**{ctx.author}'s** Total Stats: `{total_player_stats}`\n"
        f"{mob_name}'s Total Stats: `{total_mob_stats}`\n"
        f"{diedmessage1}"
        f"{diedmessage2}"
        f"They got hit for `{health_loss}` HP and died.\n"
        f"**{ctx.author}** lost all rewards, including `{level_change}` level and `{gold_loss}`% of their gold."
    )
    return
  else:
    # Calculate the experience gained
    additional_exp = random.randint(2, 15)
    new_exp = current_exp + additional_exp

    # Initialize stat increases to 0
    additional_atk = 0
    additional_def = 0
    additional_magic = 0
    additional_max_health = 0

    # Fetch level progression data from Supabase
    level_progression_response = await asyncio.get_event_loop(
    ).run_in_executor(
        None, lambda: supabase.table('LevelProgression').select('*').execute())

    level_progression_data = {
        str(level['level']): level
        for level in level_progression_response.data
    }

    # Check for level up
    needed_exp_for_next_level = level_progression_data.get(
        str(user_level + 1), {}).get('total_level_exp', float('inf'))
    level_up = new_exp >= needed_exp_for_next_level

    # Determine if an item is dropped
    drop_chance = selected_mob['drop_chance']
    drop_roll = random.randint(1, 100)  # Roll a number between 1 and 100
    item_dropped = drop_roll <= drop_chance  # Determine if the roll is within the drop chance

    # If an item is dropped, add it to the player's inventory
    if item_dropped:
      dropped_item_id = selected_mob['drop_item_id']
      await item_write(user_id, dropped_item_id,
                       1)  # Amount is 1 for the dropped item

    if level_up:
      new_level = user_level + 1
      new_exp -= needed_exp_for_next_level  # Reset exp to 0 for next level
      # Increase stats
      additional_atk = 1
      additional_def = 1
      additional_magic = 1
      additional_magic_def = 1
      additional_max_health = 5
      new_max_health = max_health + additional_max_health

    # Update the player's health, adventure_exp, and gold in the database
    supabase.table('Players').update({
        'health':
        max(1, new_health),  # Ensure health does not go below 1
        'adventure_exp':
        new_exp,
        'level':
        new_level if level_up else user_level,
        'bal':
        user_gold + gold_reward,
        # Only update these if there's a level up
        **({
            'atk': user_data['atk'] + additional_atk,
            'def': user_data['def'] + additional_def,
            'magic': user_data['magic'] + additional_magic,
            'magic_def': user_data['magic_def'] + additional_magic_def,
            'max_health': new_max_health
        } if level_up else {})
    }).eq('discord_id', user_id).execute()

    # Now send a message to the user with the outcome of the hunt
    # Including whether an item was dropped and which mob was encountered
    item_name = "nothing"
    if item_dropped:
      # Fetch the item's display name from Items table
      item_response = await asyncio.get_event_loop().run_in_executor(
          None, lambda: supabase.table('Items').select('item_displayname').eq(
              'item_id', dropped_item_id).execute())
      if item_response.data:
        item_name = item_response.data[0]['item_displayname'].lower()

    message1 = (
        f"**{ctx.author}** DOES UNSPEAKABLE THINGS to the poor {mob_name} simply by having ***PENTUPLE*** the stats!!!! \n"
        if stat_ratio >= 5 else
        f"**{ctx.author}** RAGE STOMPED a {mob_name} INTO THE GROUND having QUADRUPLE the stats!?! \n"
        if stat_ratio >= 4 else
        f"**{ctx.author}** ABSOLUTELY DECIMATED a {mob_name} by having TRIPLE stats!?! \n"
        if stat_ratio >= 3 else f"**{ctx.author}** killed a {mob_name}! \n")

    message2 = (
        f"**{ctx.author}** DOES UNSPEAKABLE THINGS to the poor {mob_name} simply by having ***PENTUPLE*** the stats!!!! \n"
        if stat_ratio >= 5 else
        f"**{ctx.author}** RAGE STOMPED a {mob_name} INTO THE GROUND having **QUADRUPLE** the stats!?! \n"
        if stat_ratio >= 4 else
        f"**{ctx.author}** ABSOLUTELY DECIMATED a {mob_name} by having *TRIPLE* stats!?! \n"
        if stat_ratio >= 3 else f"**{ctx.author}** killed a {mob_name}! \n")

    # Inform the user of the outcome of the hunt
    if level_up:
      await ctx.send(
          f"**{ctx.author}'s ** Total Stats: `{total_player_stats}`\n"
          f"{mob_name}'s Total Stats: `{total_mob_stats}`\n"
          f'{message1}'
          f"Gained `{additional_exp}`EXP, and `{gold_reward}` gold! \n"
          f"Lost `{health_loss}`HP. Current Health: `{max(1, new_health)}/{new_max_health}`HP. \n"
          f":arrow_up: Level Up to lvl `{new_level}`! New Stats: ATK: `{user_data['atk'] + additional_atk}`, "
          f"DEF: `{user_data['def'] + additional_def}`, MAGIC: `{user_data['magic'] + additional_magic}`, "
          f"MAGIC DEF: `{user_data['magic_def'] + additional_magic_def}`, "
          f"Health: `{new_max_health}`HP!\n"
          f"{f'**{ctx.author}** got `1` {item_name}' if item_name!='nothing' else ''}"
      )
    else:
      await ctx.send(
          f"**{ctx.author}'s ** Total Stats: `{total_player_stats}`\n"
          f"{mob_name}'s Total Stats: `{total_mob_stats}`\n"
          f"{message2}"
          f"Gained `{additional_exp}`EXP, and `{gold_reward}` gold! \n"
          f"Lost `{health_loss}`HP. Current Health: `{max(1, new_health)}/{max_health}`HP.\n"
          f"{f'**{ctx.author}** got `1` {item_name}' if item_name!='nothing' else ''}"
      )


# Command function
@commands.command(name="hunt",
                  aliases=["h", "hunting"],
                  help="Go on a hunting adventure and gain experience.")
async def hunt(ctx):
  await hunting(ctx)


# Error handler
async def hunting_error(ctx, error):
  if isinstance(error, commands.CommandOnCooldown):
    await ctx.send(
        f"This command is on cooldown. You can use it again in `{error.retry_after:.2f}` seconds."
    )
  else:
    await ctx.send(f"An error occurred: {error}")


# Assign the error handler to the command
hunt.error(hunting_error)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(hunt)

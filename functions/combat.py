"""This file should hold all of the internal combat functions
that are used within alll combat commands (Hunt, Adv, Dungeon, etc.)"""
"""===============================
Has not been integrated into main.py or the rest of the bot
==============================="""

import asyncio
import logging
import nextcord
import os
from dotenv import load_dotenv
from supabase import Client, create_client
import nextcord
from nextcord.ext import commands
import random

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


# Calculate the damage dealt
def calc_damage(atk, def_, dmg_type, weakness):
  damage = atk - def_
  if dmg_type == weakness:
    damage *= 2
  return damage


def get_health_status(percentage):
  if percentage >= 80:
    return "Healthy"
  elif percentage >= 60:
    return "Scraped a knee"
  elif percentage >= 40:
    return "Minorly Injured"
  elif percentage >= 20:
    return "Injured"
  elif percentage > 0:
    return "Fatally Injured"
  else:
    return "Dead"


# Generic combat function
async def combat(ctx, user_id, selected_mob, dmg_type, weakness):
  user_id = ctx.author.id
  user_name = ctx.author

  user_data = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Players').select('*').eq(
          'discord_id', user_id).execute())

  mob_data_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Mobs').select('*').eq(
          'floor', user_data['floor']).execute())

  mobs_list = mob_data_response.data if mob_data_response.data else []
  if not mobs_list:
    await ctx.send(f"No creatures to hunt on floor {user_data['floor']}.")
    return

  selected_mob = random.choice(
      mobs_list)  # Randomly select a mob from the correct floor

  mob_name = f"{selected_mob['mob_displayname']}"

  # Retrieve the player stats
  current_health = user_data['health']
  max_health = user_data['max_health']
  current_mana = user_data['mana']
  max_mana = user_data['max_mana']
  player_atk = user_data['atk']
  player_def = user_data['def']
  player_magic = user_data['magic']
  player_magic_def = user_data['magic_def']
  player_dmgtype = "physical"
  player_weakness = "none"

  # Retrieve the mob stats
  mob_name = selected_mob['mob_displayname']
  mob_maxhealth = selected_mob['health']
  mob_maxmana = selected_mob['mana']
  mob_curhealth = mob_maxhealth
  mob_curmana = mob_maxmana
  mob_atk = selected_mob['atk']
  mob_def = selected_mob['def']
  mob_magic = selected_mob['magic']
  mob_magic_def = selected_mob['magic_def']
  mob_dmgtype = "physical"
  mob_weakness = selected_mob['weakness']

  # Player goes first for now, but add an initiative calculator later.
  # Player goes first for now, but add an initiative calculator later.
  player_turn = True

  while current_health > 0 and mob_curhealth > 0:
    if player_turn:
      # Player attacks mob
      dmg = calc_damage(player_atk, mob_def, player_dmgtype, mob_weakness)
      # Calculate the mob's new health
      mob_curhealth -= dmg
      turn_description = f"**{user_name}** dealt `{dmg}` damage to the {mob_name}"
    else:
      # Mob attacks player
      dmg = calc_damage(mob_atk, player_def, mob_dmgtype, player_weakness)
      # Calculate the player's new health
      current_health -= dmg
      turn_description = f"{mob_name} dealt `{dmg}` damage to **{user_name}**"

    mob_health_percentage = (mob_curhealth / mob_maxhealth) * 100
    mob_health_status = get_health_status(mob_health_percentage)
    player_status = f"HP: {current_health}/{max_health}\nMP: {current_mana}/{max_mana}"

    embed = nextcord.Embed(
        title="Fight Overview",
        description=
        f"You have encountered a {mob_name}.\nYou are now fighting!",
        color=nextcord.Color.blue())
    embed.set_author(name=f"{ctx.author.display_name}'s adventure",
                     icon_url=ctx.author.avatar.url)
    embed.add_field(name="__Current Turn__",
                    value=turn_description,
                    inline=False)
    embed.add_field(name="__Mob Status__",
                    value=f"HP: {mob_health_status}",
                    inline=True)
    embed.add_field(name="__Player Status__", value=player_status, inline=True)
    embed.add_field(
        name="__Stats:__",
        value=
        f"ATK: {player_atk}\nDEF: {player_def}\nMAGIC: {player_magic}\nMAGIC DEF: {player_magic_def}\nDMG TYPE: {player_dmgtype}\nWEAKNESS: {player_weakness}",
        inline=False)
    embed.set_thumbnail(
        url=
        "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Crossed_swords.svg/240px-Crossed_swords.svg.png"
    )
    embed.set_footer(
        text=f"{ctx.bot.user.name} - https://magi-bot.tyrthurey.repl.co/",
        icon_url=ctx.bot.user.avatar.url)

    await ctx.send(embed=embed)
    player_turn = not player_turn

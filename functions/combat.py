"""This file should hold all of the internal combat functions
that are used within alll combat commands (Hunt, Adv, Dungeon, etc.)"""

"""===============================
Has not been integrated into main.py or the rest of the bot
==============================="""
import asyncio
from dotenv import load_dotenv
import os
from supabase import Client, create_client

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

# Generic combat function
def combat(user_data, selected_mob, dmg_type, weakness):
  user_data = await asyncio.get_event_loop().run_in_executor(
              None, lambda: supabase.table('Players').select('*').eq(
              'discord_id', user_id).execute()

  selected_mob = await asyncio.get_event_loop().run_in_executor(
                None, lambda: supabase.table('Mobs').select('*').eq(
                'floor', player_floor).execute())
  
  
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
  player_turn = True

  while current_health > 0 and mob_curhealth > 0:
    if player_turn:
        # Player attacks mob
      dmg = calc_damage(player_atk, mob_def, player_dmgtype, mob_weakness)
      # Display damage done to the mob
      embed = nextcord.Embed(title="Damage Done", color=0xFF5733)
      embed.add_field(name="Player Attack", value=f"Dealt {dmg} damage to the mob", inline=False)
      # Calculate the mob's new health
      mob_curhealth -= dmg
    
    else:
        # Mob attacks player
      dmg = calc_damage(mob_atk, player_def, mob_dmgtype, player_weakness)
      # Display damage done to player
      embed = nextcord.Embed(title="Damage Dealt", color=0xFF5733)
      embed.add_field(name="Damage Dealt to Player", value="Dealt 20 damage to the player", inline=False)
      # Calculate the player's new health
      current_health -= dmg
    player_turn = not player_turn

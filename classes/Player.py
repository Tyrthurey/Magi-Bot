"""
The player class, inherets from combat_entity.
Pulls once from the player DB and holds all relevant data for the player until dismissed.
"""

from classes.Combat_Entity import Combat_Entity
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
import random
import math
import os

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


class Player(Combat_Entity):

  def __init__(self, discord_user):
    self.discord_user = discord_user
    self.load_data()

  def __del__(self):
    self.save_data()

  def load_data(self):
    # Fetch player data from the 'Players' table using the supabase client
    response = supabase.table('Players').select('*').eq(
        'discord_id', self.discord_user.id).execute()
    data = response.data[0] if response.data else {}

    # Set player attributes
    self.name = self.discord_user.display_name
    self.health = data.get('health', 10)
    self.max_health = data.get('max_health', 10)
    self.atk = data.get('atk', 1)
    self.defense = data.get('def', 1)
    self.magic = data.get('magic', 1)
    self.magic_def = data.get('magic_def', 1)
    self.level = data.get('level', 1)
    self.exp = data.get('adventure_exp', 0)
    self.gold = data.get('bal', 0)
    self.floor = data.get('floor', 1)
    self.using_command = data.get('using_command', False)
    self.dung_tutorial = data.get('dung_tutorial', True)
    self.adv_tuturial = data.get('adv_tutorial', True)
    # ... and other attributes as needed

  def save_data(self):
    # Save player data to the 'Players' table using the supabase client
    supabase.table('Players').update({
        'health': self.health,
        'max_health': self.max_health,
        'atk': self.atk,
        'def': self.defense,
        'magic': self.magic,
        'magic_def': self.magic_def,
        'level': self.level,
        'adventure_exp': self.exp,
        'bal': self.gold,
        'using_command': False,
        'dung_tutorial': False
    }).eq('discord_id', self.discord_user.id).execute()

  def set_using_command(self, using_command):
    # Update the using_command field in the database
    response = supabase.table('Players').update({
        'using_command': using_command
    }).eq('discord_id', self.discord_user.id).execute()
    if not response:
      raise Exception('Failed to update player state.')

  def cast_spell(self, enemy):
    # Simplified spell logic
    multiplier = 1.5
    base_damage = math.floor(self.magic * multiplier - enemy.defense)
    damage = max(1, base_damage)  # Ensure at least 1 damage
    enemy.health -= damage
    return damage

  def melee_attack(self, enemy):
    # Simplified attack logic
    multiplier = 1.5
    base_damage = math.floor(self.atk * multiplier - enemy.defense)
    damage = max(1, base_damage)  # Ensure at least 1 damage
    enemy.health -= damage
    return damage

  def defend(self):
    # Increase defense stat temporarily for the next enemy attack
    self.is_defending = True

  def flee(self):
    # Flee attempt logic with some chance of success
    return random.random() < 0.1  # 50% chance to flee

  def __str__(self):
    # String representation of the player's stats
    return (
        f"**Health:** {self.health}/{self.max_health}\n"
        f"**Mana:** 0/0\n"
        f"**ATK:** {self.atk} | | **MAGIC:** {self.magic}\n**DEF:** {self.defense} | | **MAGIC DEF:** {self.magic_def}\n"
    )

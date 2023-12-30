"""
Enemy shouldn't have any interaction directly with the player database.
Instead, it should be given specific data elements from the containing function
and handle itself.

"""

from classes.Combat_Entity import Combat_Entity
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
import math
import os
import random

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


class Enemy(Combat_Entity):

  def __init__(self, mob_id):
    self.load_data(mob_id)

  def load_data(self, mob_id):
    # Fetch enemy data from the 'Mobs' table using the supabase client
    response = supabase.table('Mobs').select('*').eq('id', mob_id).execute()
    data = response.data[0] if response.data else {}

    # Set enemy attributes
    self.name = data.get('mob_displayname', "Default Mob - use `apo bug <desc>`")
    self.health = data.get('health', 10)
    self.max_health = self.health
    self.mana = data.get('mana', 0)
    self.max_mana = self.mana
    self.atk = data.get('atk', 5)
    self.defense = data.get('def', 5)
    self.magic = data.get('magic', 5)
    self.magic_def = data.get('magic_def', 5)
    self.drop_chance = data.get('drop_chance', 0)
    self.exp_drop = data.get('exp_drop', 40)
    self.drop_item_id = data.get('drop_item_id', 0)
    self.weakness = data.get('weakness', 'none')
    self.is_preparing = False
    self.is_stunned = False
    self.is_downed = False
    self.is_bound = False
    self.health_status_text = 'Healthy'
    self.previous_health_status_text = ''

    self.special_multiplier = 1
    self.special_name = 'None'

  def attack(self, player):
    # Simplified attack logic
    if player.is_defending:
      damage = max(0, math.floor((self.atk * 0.5) - player.defense))
      player.is_defending = False
    else:
      base_damage = math.floor(self.atk - player.defense)
      damage = max(1, base_damage)  # Ensure at least 1 damage
    player.health -= damage
    return damage

  def special_attack(self, player):
    # Special Attack
    damage = self.calculate_damage(player, self.atk * self.special_multiplier)
    player.health -= damage
    return damage

  def strong_attack(self, player):
    # Strong Attack
    damage = self.calculate_damage(player, self.atk * 2.0)
    player.health -= damage
    self.is_preparing = False  # Reset
    return damage

  def prepare(self, player=None):
    # Prepare for a strong attack
    self.is_preparing = True
    return 0  # No damage is dealt

  def quick_attack(self, player):
    # Quick Attack
    damage = self.calculate_damage(player, self.magic * 0.5)
    player.health -= damage
    return damage

  def calculate_damage(self, player, base_damage):
    # Extracted damage calculation logic to reuse
    if player.is_defending:
      return max(0, math.floor(base_damage * 0.5 - player.defense))
    else:
      return max(1, math.floor(base_damage -
                               player.defense))  # Ensure at least 1 damage

  def __str__(self):
    # String representation of the enemy's stats
    return (f"**Health:** {self.health_status()}")

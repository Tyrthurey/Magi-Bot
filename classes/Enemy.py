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
    self.name = data.get('mob_displayname', "Default Mob - use ::bug <desc>")
    self.health = data.get('health', 10)
    self.max_health = self.health
    self.atk = data.get('atk', 1)
    self.defense = data.get('def', 1)
    self.magic = data.get('magic', 1)
    self.magic_def = data.get('magic_def', 1)

  def attack(self, player):
    # Simplified attack logic
    base_damage = math.floor(self.atk - player.defense)
    damage = max(1, base_damage)  # Ensure at least 1 damage
    player.health -= damage
    return damage

  def __str__(self):
    # String representation of the enemy's stats
    return (f"**Health:** {self.health_status()}")

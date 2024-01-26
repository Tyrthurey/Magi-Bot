"""
Parent class for all combat entities (enemy and player)

"""
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
import os

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


class Combat_Entity:

  def __init__(self, name, health, max_health, atk, defense, magic, magic_def):
    self.name = name
    self.health = health
    self.max_health = max_health
    self.atk = atk
    self.defense = defense
    self.magic = magic
    self.magic_def = magic_def

  # Apply damage to self, and return true if still alive, or false if dead.
  def take_damage(self, damage):
    self.health -= damage
    if self.health <= 0:
      self.health = 0
      return False
    else:
      return True

  def atk_value(self):
    return self.atk

  def def_value(self):
    return self.defense

  def magic_value(self):
    return self.magic

  def magic_def_value(self):
    return self.magic_def

  def health_status(self):
    health_percentage = (self.health / self.max_health) * 100
    if health_percentage > 80:
      return "Healthy"
    elif health_percentage > 60:
      return "Scratched"
    elif health_percentage > 40:
      return "Minorly Injured"
    elif health_percentage > 20:
      return "Injured"
    elif health_percentage > 0:
      return "Fatally Injured"
    else:
      return "Dead"

  def determine_threat_level(self, opponent_stats_total):
    stat_ratio = opponent_stats_total / (self.atk + self.defense + self.magic +
                                         self.magic_def)
    if stat_ratio >= 5:
      return "Laughably Easy"
    elif stat_ratio >= 3:
      return "Easy"
    elif stat_ratio >= 2:
      return "Normal"
    elif stat_ratio >= 1:
      return "Hard"
    elif stat_ratio >= 1 / 2:
      return "Extreme"
    elif stat_ratio >= 1 / 3:
      return "Hell"
    else:
      return "Impossible"

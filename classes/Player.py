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

  # The timing of the destructor call in Python can be unpredictable,
  # because it depends on the Python garbage collector which deallocates the object.
  # def __del__(self):
  #   self.save_data()

  def load_data(self):
    # Fetch player data from the 'Users' table using the supabase client
    response = supabase.table('Users').select('*').eq(
        'discord_id', self.discord_user.id).execute()
    data = response.data[0] if response.data else {}

    # Set player attributes with the new stats
    self.exists = data.get('exists', False)
    self.displayname = data.get('displayname', 'Default')
    self.name = self.displayname if self.displayname != 'Default' else self.discord_user.name
    self.deaths = data.get('deaths', 0)
    self.times_fled = data.get('times_fled', 0)
    #self.name = self.discord_user.display_name
    self.user_id = self.discord_user.id
    self.location = data.get('location', 1)
    self.bal = data.get('bal', 0)
    self.gems = data.get('gems', 10)
    self.adventure_exp = data.get('adventure_exp', 0)
    self.free_points = data.get('free_points', 0)
    self.health = data.get('health', 25)
    self.max_health = data.get('max_health', 25)
    self.energy = data.get('energy', 13)
    self.max_energy = data.get('max_energy', 13)
    self.base_strength = data.get('strength', 5)
    self.base_dexterity = data.get('dexterity', 5)
    self.base_vitality = data.get('vitality', 5)
    self.base_cunning = data.get('cunning', 5)
    self.base_magic = data.get('magic', 5)
    self.luck = data.get('luck', 5)
    self.level = data.get('level', 1)
    self.adventure_exp = data.get('adventure_exp', 0)
    self.floor = data.get('floor', 1)
    self.max_floor = data.get('max_floor', 1)
    self.using_command = data.get('using_command', False)
    self.dung_tutorial = data.get('dung_tutorial', False)
    self.adv_tuturial = data.get('adv_tutorial', False)
    self.floor_tutorial = data.get('floor_tutorial', True)
    self.is_defending = False
    self.combat_log = []
    self.titles_list = []

    # self.endurance = data.get('endurance', 5)
    # self.intelligence = data.get('intelligence', 5)
    # self.agility = data.get('agility', 5)
    self.base_weapon_damage = data.get('base_weapon_damage', 0)
    self.base_armor_defense = data.get('base_armor_defense', 0)
    # self.endurance_to_hp_ratio = data.get(
    #     'endurance_to_hp_ratio', 0)  # ratio to convert endurance to hp
    # self.level_hp_bonus = data.get('level_hp_bonus', 0)  # bonus hp per level
    # self.intelligence_to_mp_ratio = data.get(
    #     'intelligence_to_mp_ratio', 0)  # ratio to convert intelligence to mp
    # self.level_mp_bonus = data.get('level_mp_bonus', 0)  # bonus mp per level
    # self.endurance_modifier = data.get(
    #     'endurance_modifier', 1)  # ratio to convert endurance to defense
    # ... and other attributes as needed

    player_class = data.get('class', 0)
    # Fetch class data from the 'Class' table using the supabase client
    class_response = supabase.table('Classes').select('*').eq(
        'class_id', player_class).execute()
    class_data = class_response.data[0] if class_response.data else {}

    # Set player attributes with the new stats
    self.class_displayname = class_data.get('class_displayname', 'Unclassed')
    self.class_id = class_data.get('class_id', 0)
    self.class_name = class_data.get('class_name', 'error')
    self.str_modifier = class_data.get('str_modifier', 100)
    self.dex_modifier = class_data.get('dex_modifier', 100)
    self.vit_modifier = class_data.get('vit_modifier', 100)
    self.cun_modifier = class_data.get('cun_modifier', 100)
    self.mag_modifier = class_data.get('mag_modifier', 100)
    self.health_modifier = class_data.get('health_modifier', 100)
    self.energy_modifier = class_data.get('energy_modifier', 100)
    self.recovery_speed_modifier = class_data.get('recovery_speed_modifier',
                                                  100)
    self.crit_modifier = class_data.get('crit_modifier', 0)
    self.dodge_modifier = class_data.get('dodge_modifier', 0)
    self.escape_modifier = class_data.get('escape_modifier', 0)
    self.accuracy_modifier = class_data.get('accuracy_modifier', 0)
    self.level_disparity_ignore = class_data.get('level_disparity_ignore', 0)

    self.strength = math.floor(self.base_strength * (self.str_modifier / 100))
    self.dexterity = math.floor(self.base_dexterity *
                                (self.dex_modifier / 100))
    self.vitality = math.floor(self.base_vitality * (self.vit_modifier / 100))
    self.cunning = math.floor(self.base_cunning * (self.cun_modifier / 100))
    self.magic = math.floor(self.base_magic * (self.mag_modifier / 100))

    self.stat_score = self.strength + self.dexterity + self.vitality + self.cunning + self.magic

    # self.health = math.floor(self.health * (self.health_modifier / 100))
    self.max_health = math.floor(self.stat_score *
                                 (self.health_modifier / 100))
    # self.energy = math.floor(self.energy * (self.energy_modifier / 100))
    self.max_energy = math.floor(
        round(self.stat_score / 2) * (self.energy_modifier / 100))
    self.recovery_speed = math.floor(((self.vitality + self.dexterity) / 2) *
                                     (self.recovery_speed_modifier / 100))

    self.damage = round((max(self.strength, self.cunning, self.magic) * 2) +
                        (min(self.strength, self.cunning, self.magic) * 0.4))
    self.defense = round((max(self.dexterity, self.vitality) * 2) +
                         (min(self.dexterity, self.vitality) * 0.4))

    supabase.table('Users').update({
        'max_health': self.max_health
    }).eq('discord_id', self.discord_user.id).execute()

  def save_data(self):
    response = supabase.table('Users').update({
        'discord_str_id': f'{self.user_id}',
        'free_points': self.free_points,
        'location': self.location,
        'health': self.health,
        'max_health': self.max_health,
        'energy': self.energy,
        'max_energy': self.max_energy,
        'strength': self.base_strength,
        'dexterity': self.base_dexterity,
        'vitality': self.base_vitality,
        'cunning': self.base_cunning,
        'magic': self.base_magic,
        'luck': self.luck,
        'level': self.level,
        'deaths': self.deaths,
        'times_fled': self.times_fled,
        'adventure_exp': self.adventure_exp,
        'bal': self.bal,
        # 'dung_tutorial': self.dung_tutorial,
        'adv_tutorial': self.adv_tuturial
    }).eq('discord_id', self.discord_user.id).execute()
    if not response:
      raise Exception('Failed to update player save_data.')

  def update_health(self):
    supabase.table('Users').update({
        'health': self.health
    }).eq('discord_id', self.discord_user.id).execute()

  def save_strength_choice(self):
    supabase.table('Users').update({
        'free_points': self.free_points,
        'strength': self.base_strength
    }).eq('discord_id', self.discord_user.id).execute()

  def save_dexterity_choice(self):
    supabase.table('Users').update({
        'free_points': self.free_points,
        'dexterity': self.base_dexterity
    }).eq('discord_id', self.discord_user.id).execute()

  def save_vitality_choice(self):
    supabase.table('Users').update({
        'free_points': self.free_points,
        'vitality': self.base_vitality
    }).eq('discord_id', self.discord_user.id).execute()

  def save_cunning_choice(self):
    supabase.table('Users').update({
        'free_points': self.free_points,
        'cunning': self.base_cunning
    }).eq('discord_id', self.discord_user.id).execute()

  def save_magic_choice(self):
    supabase.table('Users').update({
        'free_points': self.free_points,
        'magic': self.base_magic
    }).eq('discord_id', self.discord_user.id).execute()

  def set_using_command(self, using_command):
    # Update the using_command field in the database
    response = supabase.table('Users').update({
        'using_command': using_command
    }).eq('discord_id', self.discord_user.id).execute()
    if not response:
      raise Exception('Failed to update player state.')

  def download_player_settings(self, user_id):
    response = supabase.table('Inventory').select('settings').eq(
        'discord_id', user_id).execute()
    if not response:
      raise Exception('Failed to download player settings.')
    return response

  def download_player_unlocks(self, user_id):
    response = supabase.table('Inventory').select('unlocked_cosmetics').eq(
        'discord_id', user_id).execute()
    if not response:
      raise Exception('Failed to download player unlocked cosmetics.')
    return response

  def cast_spell(self, enemy):
    self.is_defending = False
    # Simplified spell logic
    multiplier = 1.5
    base_damage = math.floor(self.magic * multiplier - enemy.defense)
    damage = max(1, base_damage)  # Ensure at least 1 damage
    enemy.health -= damage
    return damage

  def melee_attack(self, enemy):
    self.is_defending = False
    # Applying the formula from the CSV to calculate attack damage
    attack_damage = math.floor(self.base_weapon_damage + self.damage)
    damage = max(1, attack_damage - enemy.defense)
    enemy.health -= damage
    return damage

  def defend(self):
    # Increase defense stat temporarily for the next enemy attack
    # currently does nothing
    # Applying the formula to calculate defense
    # defense = round(
    #     max(self.dexterity, self.vitality) * 2 +
    #     min(self.dexterity, self.vitality) * 0.4)
    # self.defense = defense
    self.is_defending = True

  def flee(self):
    self.is_defending = False
    # Flee attempt logic with some chance of success
    return random.random() < 0.5  # 50% chance to flee

  def __str__(self):
    # String representation of the player's stats
    return (f"**HP:** {self.health}/{self.max_health}\n"
            f"**Energy:** 0/0\n")
    # f"**STR:** {self.strength} | | **VIT:** {self.vitality}\n"
    # f"**DEX:** {self.dexterity} | | **SAV:** {self.cunning}\n"
    # f"**MAG:** {self.magic}\n")

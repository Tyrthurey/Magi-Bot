import nextcord
from nextcord.ext import commands
from nextcord.ext.commands import has_permissions
from nextcord.ui import Button, View
from typing import List
from supabase import create_client, Client
from dotenv import load_dotenv
from functions.load_settings import command_prefix, get_embed_color
import logging
import random
import os

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


class CombatView(View):

  def __init__(self, ctx, player, enemy):
    super().__init__(timeout=None)
    self.ctx = ctx
    self.player = player
    self.enemy = enemy
    self.combat_log = []

  async def interaction_check(self, interaction):
    # Only the user who started the hunt can interact with the buttons
    return interaction.user == self.ctx.author

  async def on_timeout(self):
    # Handle what happens when the view times out
    await self.ctx.send(f"Combat with {self.enemy.name} has timed out.")

  async def update_embed(self, interaction):
    embed = nextcord.Embed(title=f"Dungeon Floor {self.player.floor}")
    embed.set_thumbnail(url=self.ctx.author.avatar.url)
    embed.add_field(name=f"{self.enemy.name}'s Stats",
                    value=str(self.enemy),
                    inline=False)
    embed.add_field(name="Your Stats", value=str(self.player), inline=False)
    embed.add_field(name="Combat Log",
                    value="\n".join(self.combat_log[-4:]),
                    inline=False)  # Only show the last 4 actions

    await interaction.message.edit(embed=embed, view=self)

  # In the CombatView class...
  @nextcord.ui.button(label="Cast Spell", style=nextcord.ButtonStyle.blurple)
  async def cast_spell(self, button: Button,
                       interaction: nextcord.Interaction):
    # Assume the player has a spell called "Fireball"
    damage = self.player.cast_spell(self.enemy, "Fireball")
    self.combat_log.append(
        f"{self.player.name} casts Fireball for {damage} damage!")
    await self.update_embed(interaction)

  @nextcord.ui.button(label="Melee Attack", style=nextcord.ButtonStyle.green)
  async def melee_attack(self, button: Button,
                         interaction: nextcord.Interaction):
    # Melee attack logic
    self.player.melee_attack(self.enemy)
    self.combat_log.append(f"{self.player.name} attacks with melee!")
    await self.update_embed(interaction)
    # Check for end of combat

  @nextcord.ui.button(label="Defend", style=nextcord.ButtonStyle.gray)
  async def defend(self, button: Button, interaction: nextcord.Interaction):
    # Defense logic
    self.player.defend()
    self.combat_log.append(f"{self.player.name} defends!")
    await self.update_embed(interaction)
    # Check for end of combat

  @nextcord.ui.button(label="Use Item", style=nextcord.ButtonStyle.blurple)
  async def use_item(self, button: Button, interaction: nextcord.Interaction):
    # Item usage logic
    # Would need to show item selection and then update the combat state
    self.player.use_item('Health Potion')  # Example item
    self.combat_log.append(f"{self.player.name} uses a Health Potion!")
    await self.update_embed(interaction)
    # Check for end of combat

  @nextcord.ui.button(label="Flee", style=nextcord.ButtonStyle.red)
  async def flee(self, button: Button, interaction: nextcord.Interaction):
    # Flee logic
    fled_success = self.player.flee(
    )  # This would have a chance to succeed or fail
    if fled_success:
      self.combat_log.append(f"{self.player.name} has fled the battle!")
      await interaction.message.edit(content="You fled the battle!",
                                     embed=None,
                                     view=None)
      self.player.set_using_command(False)  # Reset the using_command field
      self.stop()  # Stop the view to clean up
    else:
      self.combat_log.append(f"{self.player.name} failed to flee!")
      await self.update_embed(interaction)

  async def handle_death(self, interaction: nextcord.Interaction):
    # Call this method when the player's health reaches 0
    self.combat_log.append(f"{self.player.name} has been defeated!")
    await interaction.message.edit(content="You have been defeated!",
                                   embed=None,
                                   view=None)
    self.player.set_using_command(False)  # Reset the using_command field
    self.stop()  # Stop the view to clean up


class Player:

  def __init__(self, discord_user):
    self.discord_user = discord_user
    self.load_data()

  def load_data(self):
    # Fetch player data from the 'Players' table using the supabase client
    response = supabase.table('Players').select('*').eq(
        'discord_id', self.discord_user.id).execute()
    data = response.data[0] if response.data else {}

    # Set player attributes
    self.name = self.discord_user.display_name
    self.health = data.get('health', 100)
    self.max_health = data.get('max_health', 100)
    self.atk = data.get('atk', 10)
    self.defense = data.get('def', 10)
    self.magic = data.get('magic', 10)
    self.magic_def = data.get('magic_def', 10)
    self.level = data.get('level', 1)
    self.exp = data.get('adventure_exp', 0)
    self.gold = data.get('bal', 0)
    self.floor = data.get('floor', 1)
    self.using_command = data.get('using_command', False)
    # ... and other attributes as needed

  def set_using_command(self, using_command):
    # Update the using_command field in the database
    response = supabase.table('Players').update({
        'using_command': using_command
    }).eq('discord_id', self.discord_user.id).execute()
    if not response:
      raise Exception('Failed to update player state.')

  def cast_spell(self, enemy, spell_name):
    # Simplified spell logic
    spell_power = self.magic * 1.5  # Example spell power calculation
    enemy.health -= spell_power
    return spell_power

  def melee_attack(self, enemy):
    # Simplified melee attack logic
    damage = self.atk - enemy.defense
    enemy.health -= max(0, damage)  # Prevent negative damage
    return damage

  def defend(self):
    # Increase defense stat temporarily for next enemy attack
    self.is_defending = True

  def use_item(self, item_name):
    # Use an item from the inventory
    if item_name == 'Health Potion':
      restored_health = min(50, self.max_health - self.health)
      self.health += restored_health
      return restored_health

  def flee(self):
    # Flee attempt logic with some chance of success
    return random.random() < 0.5  # 50% chance to flee

  def __str__(self):
    # String representation of the player's stats
    return (f"Health: {self.health}/{self.max_health} "
            f"ATK: {self.atk} DEF: {self.defense} "
            f"MAGIC: {self.magic} MAGIC DEF: {self.magic_def}")


class Enemy:

  def __init__(self, name, floor, player_stats_total):
    self.name = name
    self.floor = floor
    self.load_data()
    self.threat_level = self.determine_threat_level(player_stats_total)

  def load_data(self):
    # Fetch enemy data from the 'Mobs' table using the supabase client
    response = supabase.table('Mobs').select('*').eq(
        'mob_displayname', self.name).eq('floor', self.floor).execute()
    data = response.data[0] if response.data else {}

    # Set enemy attributes
    self.health = data.get('health', 100)
    self.atk = data.get('atk', 10)
    self.defense = data.get('def', 10)
    self.magic = data.get('magic', 10)
    self.magic_def = data.get('magic_def', 10)
    # ... and other attributes as needed

  def determine_threat_level(self, player_stats_total):
    stat_ratio = player_stats_total / (self.atk + self.defense + self.magic +
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

  def __str__(self):
    # String representation of the enemy's stats
    return (f"Health: {self.health} "
            f"ATK: {self.atk} DEF: {self.defense} "
            f"MAGIC: {self.magic} MAGIC DEF: {self.magic_def}")


# In the dungeon command...
@commands.command(name="dungeon")
@has_permissions(administrator=True)
async def dungeon(ctx):
  player = Player(ctx.author)
  # Check if the player is already in a command
  if player.using_command:
    await ctx.send(
        "You're already in a command. Finish it before starting another.")
    return
  player.set_using_command(True)
  player_stats_total = player.atk + player.defense + player.magic + player.magic_def

  # Now we can instantiate Enemy with the player's total stats
  enemy = Enemy("Skeleton",
                floor=player.floor,
                player_stats_total=player_stats_total)

  # Create the initial embed with player and enemy information
  embed = nextcord.Embed(title=f"Dungeon Floor {player.floor}",
                         description="A wild creature appears!")
  embed.set_thumbnail(url=ctx.author.avatar.url)
  embed.add_field(name="Your Stats", value=str(player), inline=False)
  embed.add_field(name=f"{enemy.name}'s Stats (Threat: {enemy.threat_level})",
                  value=str(enemy),
                  inline=False)
  embed.add_field(name="Combat Log",
                  value="The battle is about to begin!",
                  inline=False)

  # Start combat with the initial embed
  view = CombatView(ctx, player, enemy)
  await ctx.send(embed=embed, view=view)


# The embed is initially created within the CombatView constructor


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(dungeon)

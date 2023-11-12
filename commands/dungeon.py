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
import asyncio
import time
import math

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


class TutorialView(nextcord.ui.View):

  def __init__(self, ctx, tutorial_messages):
    super().__init__(timeout=None)
    self.ctx = ctx
    self.tutorial_messages = tutorial_messages
    self.current_index = 0
    self.tutorial_done = asyncio.Event()

  async def interaction_check(self, interaction):
    return interaction.user == self.ctx.author

  @nextcord.ui.button(label="Continue", style=nextcord.ButtonStyle.green)
  async def continue_button(self, button: nextcord.ui.Button,
                            interaction: nextcord.Interaction):
    # Move to the next tutorial message
    self.current_index += 1
    if self.current_index < len(self.tutorial_messages):
      await interaction.message.edit(
          content=self.tutorial_messages[self.current_index], view=self)
    else:
      # End of tutorial, remove buttons
      await interaction.message.edit(
          content="Tutorial completed. Starting your dungeon adventure!",
          view=None)
      self.tutorial_done.set()  # Signal that the tutorial is done
      # Here you can call your dungeon logic or any other post-tutorial logic

  @nextcord.ui.button(label="Skip", style=nextcord.ButtonStyle.red)
  async def skip_button(self, button: nextcord.ui.Button,
                        interaction: nextcord.Interaction):
    await interaction.message.edit(
        content="Tutorial skipped. Starting your dungeon adventure!",
        view=None)
    self.tutorial_done.set()  # Signal that the tutorial is skipped
    # Here you can call your dungeon logic or any other post-tutorial logic


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
    avatar_url = self.ctx.author.avatar.url if self.ctx.author.avatar else self.ctx.author.default_avatar.url
    embed = nextcord.Embed(title=f"Dungeon Floor {self.player.floor}")
    embed.set_thumbnail(
        url=
        'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Crossed_swords.svg/240px-Crossed_swords.svg.png'
    )
    embed.add_field(
        name=f"**BOSS** {self.enemy.name}'s Stats",
        value=f"**Threat Level:** {self.enemy.threat_level}\n{str(self.enemy)}",
        inline=False)
    embed.add_field(name="__Your Stats__",
                    value=str(self.player),
                    inline=False)
    embed.add_field(name="------------------------------",
                    value="\n".join(self.combat_log[-4:]),
                    inline=False)  # Only show the last 4 actions
    embed.add_field(name="------------------------------",
                    value="",
                    inline=False)

    embed.add_field(
        name="",
        value="⚔️ --> Melee Attack \n🛡️ --> Defend \n✨ --> Cast Spell",
        inline=True)

    embed.add_field(name="", value="🔨 --> Use Item \n💨 --> Flee", inline=True)

    await interaction.message.edit(embed=embed, view=self)

  # In the CombatView class.
  @nextcord.ui.button(label="⚔️", style=nextcord.ButtonStyle.green)
  async def melee_attack_button(self, button: Button,
                                interaction: nextcord.Interaction):
    await self.handle_combat_turn(interaction, "melee")
    # Check for end of combat

  @nextcord.ui.button(label="🛡️", style=nextcord.ButtonStyle.gray)
  async def defend(self, button: Button, interaction: nextcord.Interaction):
    # Defense logic
    self.player.defend()
    await self.handle_combat_turn(interaction, "defend")
    # Check for end of combat

  @nextcord.ui.button(label="✨",
                      style=nextcord.ButtonStyle.blurple,
                      disabled=True)
  async def cast_spell_button(self, button: Button,
                              interaction: nextcord.Interaction):
    await self.handle_combat_turn(interaction, "spell")

  @nextcord.ui.button(label="🔨",
                      style=nextcord.ButtonStyle.blurple,
                      disabled=True)
  async def use_item(self, button: Button, interaction: nextcord.Interaction):
    # Item usage logic
    # Would need to show item selection and then update the combat state
    self.player.use_item('Health Potion')  # Example item
    self.combat_log.append(f"**{self.player.name}** uses a Health Potion!")
    await self.update_embed(interaction)
    # Check for end of combat

  @nextcord.ui.button(label="💨", style=nextcord.ButtonStyle.red)
  async def flee(self, button: Button, interaction: nextcord.Interaction):
    # Flee logic
    fled_success = self.player.flee(
    )  # This would have a chance to succeed or fail
    if fled_success:
      self.combat_log.append(f"{self.player.name} has fled the battle!")
      await interaction.message.edit(
          content=f"**{self.player.name}** has fled from the battle! Coward.",
          embed=None,
          view=None)
      self.player.set_using_command(False)  # Reset the using_command field
      self.stop()  # Stop the view to clean up
    else:
      await self.handle_combat_turn(interaction, "flee")

  async def handle_death(self, interaction: nextcord.Interaction):
    # Call this method when the player's health reaches 0
    self.combat_log.append(f"{self.player.name} has been defeated!")
    await interaction.message.edit(
        content=
        f"**{self.player.name}** could not handle a {self.enemy.name}! Noob.",
        embed=None,
        view=None)
    self.player.set_using_command(False)  # Reset the using_command field
    self.stop()  # Stop the view to clean up

  # handle combat turns
  async def handle_combat_turn(self, interaction: nextcord.Interaction,
                               action: str):
    player_damage = 0
    enemy_damage = 0

    if action == "spell":
      player_damage = self.player.cast_spell(self.enemy)
    elif action == "melee":
      player_damage = self.player.melee_attack(self.enemy)
    elif action == "defend":
      self.player.defend()
    elif action == "item":
      # Implement item usage logic here
      pass
    elif action == "flee":
      fled_success = self.player.flee()
      if fled_success:
        await self.handle_flee(interaction)
        return

    if action == "flee":
      # Update combat log
      enemy_damage = self.enemy.attack(self.player)
      self.combat_log.append(f"**{self.player.name}** failed to flee!")

      # Update the embed to show the player's action
      await self.update_embed(interaction)

      # Add a delay before showing the mob's action
      await asyncio.sleep(0.5)

      self.combat_log.append(
          f"{self.enemy.name} attacks for {enemy_damage} damage!")

    elif action == "defend":
      # Update combat log
      enemy_damage = math.floor(enemy_damage * 0.5)
      self.combat_log.append(f"**{self.player.name}** defends!")

      # Update the embed to show the player's action
      await self.update_embed(interaction)

      # Add a delay before showing the mob's action
      await asyncio.sleep(0.5)

      self.combat_log.append(
          f"{self.enemy.name} attacks for {enemy_damage} damage!")
    else:
      enemy_damage = self.enemy.attack(self.player)
      # Update combat log
      self.combat_log.append(
          f"**{self.player.name}** {action} for `{player_damage}` damage!")

      # Update the embed to show the player's action
      await self.update_embed(interaction)

      # Add a delay before showing the mob's action
      await asyncio.sleep(0.5)

      self.combat_log.append(
          f"{self.enemy.name} attacks for `{enemy_damage}` damage!")

    # Check for end of combat
    if self.player.health <= 0:
      await self.handle_death(interaction)
    elif self.enemy.health <= 0:
      await self.handle_enemy_defeat(interaction)
    else:
      await self.update_embed(interaction)

  async def handle_flee(self, interaction: nextcord.Interaction):
    # Logic for handling flee
    pass

  async def handle_enemy_defeat(self, interaction: nextcord.Interaction):
    self.combat_log.append(
        f"{self.player.name} has defeated the **BOSS** {self.enemy.name}!")
    await elf.ctx.send(
        f"**{self.player.name}** has fled from the battle! Coward.")
    self.player.set_using_command(False)  # Reset the using_command field
    self.stop()
    pass


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
    # ... and other attributes as needed

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


class Enemy:

  def __init__(self, name, floor, player_stats_total, user_id):
    self.name = name
    self.floor = floor
    self.load_data(user_id)
    self.threat_level = self.determine_threat_level(player_stats_total)

  def load_data(self, user_id):
    # Fetch enemy data from the 'Mobs' table using the supabase client
    response = supabase.table('Mobs').select('*').eq(
        'mob_displayname', self.name).eq('floor', self.floor).execute()
    data = response.data[0] if response.data else {}

    response = supabase.table('Players').select('level').eq(
        'discord_id', user_id).execute()
    player = response.data[0] if response.data else {}

    # Set enemy attributes
    self.health = data.get('health', 10) * player['level']
    self.max_health = self.health
    self.atk = data.get('atk', 1) + player['level'] / 2
    self.defense = data.get('def', 1) + player['level'] / 2
    self.magic = data.get('magic', 1) + player['level'] / 2
    self.magic_def = data.get('magic_def', 1) + player['level'] / 2
    # ... and other attributes as needed

  def attack(self, player):
    # Simplified attack logic
    base_damage = math.floor(self.atk - player.defense)
    damage = max(1, base_damage)  # Ensure at least 1 damage
    player.health -= damage
    return damage

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

  def health_status(self):
    health_percentage = (self.health / self.max_health) * 100
    if health_percentage > 80:
      return "Healthy"
    elif health_percentage > 60:
      return "Scraped a knee"
    elif health_percentage > 40:
      return "Minorly Injured"
    elif health_percentage > 20:
      return "Injured"
    elif health_percentage > 0:
      return "Fatally Injured"
    else:
      return "Dead"

  def __str__(self):
    # String representation of the enemy's stats
    return (f"**Health:** {self.health_status()}")


# In the dungeon command...
@commands.command(name="dungeon")
async def dungeon(ctx):
  player = Player(ctx.author)
  # Check if the player is already in a command
  if player.using_command:
    await ctx.send(
        "You're already in a command. Finish it before starting another.")
    return
  player.set_using_command(True)

  # Define your tutorial messages here
  tutorial_messages = [
      "Welcome to the dungeon! ...",  # Tutorial part 1
      "Dungeon Monsters ...",  # Tutorial part 2
      "Stats ...",  # Tutorial part 3
      # Add all the tutorial parts here...
  ]

  # Check if the user is new and should see the tutorial
  if player.dung_tutorial:
    # Show the tutorial
    tutorial_view = TutorialView(ctx, tutorial_messages)
    await ctx.send(content=tutorial_messages[0], view=tutorial_view)
    await tutorial_view.tutorial_done.wait(
    )  # Wait for the tutorial to be done

  player_stats_total = player.atk + player.defense + player.magic + player.magic_def

  # Load mobs list for the current floor and select a random mob
  mob_data_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Mobs').select('*').eq(
          'floor', player.floor).execute())

  mobs_list = mob_data_response.data if mob_data_response.data else []
  if not mobs_list:
    await ctx.send(f"No creatures to hunt on floor {player.floor}.")
    return

  selected_mob = random.choice(
      mobs_list)  # Randomly select a mob from the correct floor

  mob_name = f"{selected_mob['mob_displayname']}"

  # Now we can instantiate Enemy with the player's total stats
  enemy = Enemy(mob_name,
                floor=player.floor,
                player_stats_total=player_stats_total,
                user_id=ctx.author.id)

  # Create the initial embed with player and enemy information
  embed = nextcord.Embed(title=f"Dungeon Floor {player.floor}")
  embed.set_thumbnail(
      url=
      'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Crossed_swords.svg/240px-Crossed_swords.svg.png'
  )
  embed.add_field(
      name=f"A wild **BOSS** {enemy.name} appears!",
      value=f"**Threat Level:** {enemy.threat_level}\n{str(enemy)}",
      inline=False)

  embed.add_field(name="__Your Stats__", value=str(player), inline=False)

  embed.add_field(name="------------------------------",
                  value="The battle is about to begin!",
                  inline=False)

  embed.add_field(name="------------------------------",
                  value="",
                  inline=False)

  embed.add_field(
      name="",
      value="⚔️ --> Melee Attack \n🛡️ --> Defend \n✨ --> Cast Spell",
      inline=True)

  embed.add_field(name="", value="🔨 --> Use Item \n💨 --> Flee", inline=True)

  # Start combat with the initial embed
  view = CombatView(ctx, player, enemy)
  await ctx.send(embed=embed, view=view)


# The embed is initially created within the CombatView constructor


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(dungeon)

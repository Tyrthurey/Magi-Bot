import nextcord
from nextcord.ui import Button, View
import asyncio
import math

from classes.Player import Player
from classes.Enemy import Enemy
import random

import logging

from supabase import create_client, Client
from dotenv import load_dotenv
import logging
import os
import time

from functions.item_write import item_write

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


class CombatView(View):

  def __init__(self, ctx, player: Player, enemy: Enemy):
    super().__init__(timeout=300)
    self.ctx = ctx
    self.player = player
    self.enemy = enemy
    self.combat_log = []
    self.cooldowns = {}
    self.is_players_turn = True
    self.threat_level = enemy.determine_threat_level(player.strength +
                                                     player.dexterity +
                                                     player.vitality +
                                                     player.cunning +
                                                     player.magic)

  def update_button_states(self):
    """Enable or disable buttons based on the player's turn."""
    for item in self.children:
      if isinstance(item, nextcord.ui.Button):
        item.disabled = not self.is_players_turn

  async def change_turn(self):
    self.is_players_turn = not self.is_players_turn
    self.update_button_states()

  # ------------------------------------------------------------------------------------
  # Timeout function
  # ------------------------------------------------------------------------------------

  async def on_timeout(self):
    # Code to handle the timeout scenario
    # For example, send a message to the channel indicating the timeout
    # Update the embed to show the player's action
    self.player.deaths = self.player.deaths + 1
    await self.ctx.send(
        f"**{self.player.name}** fell asleep while fighting {self.enemy.name} and died! \nYour problems don't go away if you ignore them.\n"
        f"Deaths: `{self.player.deaths}`")

    # Reset the using_command field
    self.player.set_using_command(False)
    self.player.save_data()

    # ---------------------------------------------------------------------------------
    # Consequences
    # ---------------------------------------------------------------------------------

    self.player.health = self.player.max_health
    self.player.adventure_exp = 0
    self.player.bal = max(10,
                          self.player.bal - math.floor(self.player.bal * 0.1))

    self.player.save_data()

    # ----------------------------------------------------------------------------------
    # Stops the view from listening to more input
    # ----------------------------------------------------------------------------------
    self.stop()

  # ------------------------------------------------------------------------------------
  # Updates the embed. Default template that is replaced by something
  # more specialized from another class.
  # ------------------------------------------------------------------------------------

  async def update_embed(self, interaction):
    avatar_url = self.ctx.author.avatar.url if self.ctx.author.avatar else self.ctx.author.default_avatar.url
    embed = nextcord.Embed(title="Default Embed")
    embed.set_thumbnail(url='')
    embed.add_field(name="", value="", inline=False)

    await interaction.message.edit(embed=embed, view=self)

  # ------------------------------------------------------------------------------------
  # Death handler
  # ------------------------------------------------------------------------------------

  # async def handle_death(self, interaction: nextcord.Interaction):
  #   # Call this method when the player's health reaches 0
  #   self.combat_log.append(f"{self.player.name} has been defeated!")
  #   await self.ctx.send(
  #       f"**{self.player.name}** could not handle a {self.enemy.name}! Noob.")

  #   # Update the embed to show the player's action
  #   await self.update_embed(interaction)
  #   self.player.set_using_command(False)  # Reset the using_command field
  #   self.player.save_data()
  #   self.stop()  # Stop the view to clean up

  # ------------------------------------------------------------------------------------
  # Combat turn handler
  # ------------------------------------------------------------------------------------

  async def handle_combat_turn(self, interaction: nextcord.Interaction,
                               action: str):
    player_damage = 0
    enemy_damage = 0
    is_defending = False

    # ----------------------------------------------------------------------------------
    # Cast spell
    # ----------------------------------------------------------------------------------

    if action == "spell":
      self.player.is_defending = False
      await self.change_turn()
      player_damage = self.player.cast_spell(self.enemy)

      # Update combat log
      self.combat_log.append(
          f"**{self.player.name}** casts [spell] for `{player_damage}` damage!"
      )

    # ----------------------------------------------------------------------------------
    # Melee attack
    # ----------------------------------------------------------------------------------

    elif action == "melee":
      self.player.is_defending = False
      await self.change_turn()
      player_damage = self.player.melee_attack(self.enemy)

      # Update combat log
      self.combat_log.append(
          f"**{self.player.name}** attacks for `{player_damage}` damage!")

    # ----------------------------------------------------------------------------------
    # Defend action
    # Could be used by some class or something
    # ----------------------------------------------------------------------------------

    elif action == "defend":
      self.player.defend()
      await self.change_turn()

      # Update combat log
      self.combat_log.append(f"**{self.player.name}** defends!")

    # ----------------------------------------------------------------------------------
    # Use item
    # ----------------------------------------------------------------------------------

    elif action == "item":
      self.player.is_defending = False
      await self.change_turn()
      # Implement item usage logic here
      pass

    # ----------------------------------------------------------------------------------
    # Flee action
    # ----------------------------------------------------------------------------------

    elif action == "flee":
      self.player.is_defending = False
      await self.change_turn()
      if self.player.flee():
        await self.handle_flee(interaction)
        return
      else:
        self.combat_log.append(f"**{self.player.name}** failed to flee!")

    # ----------------------------------------------------------------------------------
    # Update the embed to show the player's action
    # ----------------------------------------------------------------------------------
    health_percentage = (self.enemy.health / self.enemy.max_health) * 100
    # Update the health_status_text based on health_percentage
    previous_health_status = self.enemy.health_status_text
    if health_percentage > 80:
      self.enemy.health_status_text = 'Healthy'
    elif health_percentage > 60:
      self.enemy.health_status_text = "Scraped a knee"
    elif health_percentage > 40:
      self.enemy.health_status_text = "Minorly Injured"
    elif health_percentage > 20:
      self.enemy.health_status_text = "Injured"
    elif health_percentage > 0:
      self.enemy.health_status_text = "Fatally Injured"
    else:
      self.enemy.health_status_text = "Dead"

    # Only send a message if the health status has changed
    if self.enemy.health_status_text != previous_health_status:
      self.combat_log.append(
          f"{self.enemy.name} is now {self.enemy.health_status_text}!")
      self.enemy.previous_health_status_text = self.enemy.health_status_text

    await self.update_embed(interaction)

    # ----------------------------------------------------------------------------------
    # Add a delay before showing the mob's action
    # ----------------------------------------------------------------------------------

    await asyncio.sleep(0.5)

    # ----------------------------------------------------------------------------------
    # If the enemy is dead, end combat
    # ----------------------------------------------------------------------------------

    if self.enemy.health <= 0:
      await self.handle_enemy_defeat(interaction)
    else:
      # Randomly select an action for the enemy
      enemy_actions = [self.enemy.attack, self.enemy.prepare]

      if self.enemy.special_name != 'None':  # Only add special_attack if special_name is not None
        enemy_actions.append(self.enemy.special_attack)

      if self.enemy.is_preparing:
        enemy_action = self.enemy.strong_attack
        self.enemy.is_preparing = False
      else:
        enemy_action = random.choice(enemy_actions)

      enemy_damage = enemy_action(self.player)

      # Update the combat log based on the enemy's action
      if enemy_action == self.enemy.prepare:
        self.combat_log.append(
            f"{self.enemy.name} is preparing for a strong attack!")
      elif enemy_action == self.enemy.special_attack:
        self.combat_log.append(
            f"{self.enemy.name} uses {self.enemy.special_name} for `{enemy_damage}` damage!"
        )
      elif enemy_action == self.enemy.strong_attack:
        self.combat_log.append(
            f"{self.enemy.name} uses a strong attack for `{enemy_damage}` damage!"
        )
      else:
        self.combat_log.append(
            f"{self.enemy.name} attacks for `{enemy_damage}` damage!")

      if random.random() < 0.1:  #10% chance for an extra quick attack
        enemy_action = self.enemy.quick_attack
        enemy_damage = enemy_action(self.player)
        self.combat_log.append(
            f"{self.enemy.name} uses a quick attack for `{enemy_damage}` damage!"
        )

      await self.update_embed(interaction)
      await self.change_turn()

    if self.player.health <= 0:
      is_dead = True
      await self.change_turn()
      await self.handle_death(interaction)
    else:
      # ----------------------------------------------------------------------------------
      # Update the embed to show the mobs's action
      # ----------------------------------------------------------------------------------

      await self.update_embed(interaction)

    # ----------------------------------------------------------------------------------
    # Check for end of combat
    # ----------------------------------------------------------------------------------

    if self.player.health <= 0 and is_dead == False:
      await self.change_turn()
      await self.handle_death(interaction)
    else:
      await self.update_embed(interaction)

  # ------------------------------------------------------------------------------------
  # Handle combat end due to flee action
  # ------------------------------------------------------------------------------------

  async def handle_flee(self, interaction: nextcord.Interaction):
    # Logic for handling flee
    self.player.times_fled = self.player.times_fled + 1
    await self.ctx.send(
        f"**{self.player.name}** has fled from the battle! Coward."
        f"\n**Times fled:** `{self.player.times_fled}`")
    self.player.set_using_command(False)  # Reset the using_command field
    self.player.save_data()
    self.stop()  # Stop the view to clean up
    pass

  # ------------------------------------------------------------------------------------
  # Handle combat end due to enemy defeat
  # ------------------------------------------------------------------------------------

  # async def handle_enemy_defeat(self, interaction: nextcord.Interaction):
  #   self.combat_log.append(f"{self.enemy.name} has been defeated!")

  #   # Determine if an item is dropped
  #   drop_chance = self.enemy.drop_chance
  #   drop_roll = random.randint(1, 100)  # Roll a number between 1 and 100
  #   item_dropped = drop_roll <= drop_chance  # Determine if the roll is within the drop chance

  #   print(
  #       "----------------------------------------------------------------------------------"
  #   )
  #   print("Drop chance: ")
  #   print(drop_chance)
  #   print(
  #       "----------------------------------------------------------------------------------"
  #   )
  #   print("Drop roll: ")
  #   print(drop_roll)
  #   print(
  #       "----------------------------------------------------------------------------------"
  #   )
  #   print("Item dropped: ")
  #   print(item_dropped)

  #   # If an item is dropped, add it to the player's inventory
  #   if item_dropped:
  #     dropped_item_id = self.enemy.drop_item_id
  #     await item_write(self.ctx.author.id, dropped_item_id, 1)  # Amount is 1

  #   # Now send a message to the user with the outcome of the hunt
  #   # Including whether an item was dropped and which mob was encountered
  #   item_name = "nothing"
  #   if item_dropped:
  #     # Fetch the item's display name from Items table
  #     item_response = await asyncio.get_event_loop().run_in_executor(
  #         None, lambda: supabase.table('Items').select('item_displayname').eq(
  #             'item_id', dropped_item_id).execute())
  #     if item_response.data:
  #       item_name = item_response.data[0]['item_displayname'].lower()

  #   print(
  #       "----------------------------------------------------------------------------------"
  #   )
  #   print("Item name: ")
  #   print(item_name)

  #   await self.ctx.send(
  #       f"**{self.player.name}** has defeated the {self.enemy.name}!"
  #       f"{f'**{self.player.name}** got `1` {item_name}' if item_name!='nothing' else ''}"
  #   )

  #   # Update the embed to show the player's action
  #   await self.update_embed(interaction)
  #   self.player.set_using_command(False)  # Reset the using_command field
  #   self.stop()  # Stop the view to clean up
  #   pass

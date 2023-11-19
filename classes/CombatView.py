import nextcord
from nextcord.ui import Button, View
import asyncio
import math

from classes.Player import Player
from classes.Enemy import Enemy


class CombatView(View):

  def __init__(self, ctx, player: Player, enemy: Enemy):
    super().__init__(timeout=300)
    self.ctx = ctx
    self.player = player
    self.enemy = enemy
    self.combat_log = []
    self.threat_level = enemy.determine_threat_level(player.atk +
                                                     player.defense +
                                                     player.magic +
                                                     player.magic_def)

  # ------------------------------------------------------------------------------------
  # Timeout function
  # ------------------------------------------------------------------------------------

  async def on_timeout(self):
    # Code to handle the timeout scenario
    # For example, send a message to the channel indicating the timeout
    # Update the embed to show the player's action

    await self.ctx.send(
        f"**{self.player.name}** fell asleep while fighting {self.enemy.name} and died! Noob.\nYour problems don't go away if you ignore them lol."
    )

    # Reset the using_command field
    self.player.set_using_command(False)
    self.player.save_data()

    # ---------------------------------------------------------------------------------
    # Consequences
    # ---------------------------------------------------------------------------------

    self.player.health = 0
    self.player.exp = 0
    self.player.level = max(1, self.player.level - 1)
    self.player.gold = max(
        0, self.player.gold - math.floor(self.player.gold * 0.1))
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

  async def handle_death(self, interaction: nextcord.Interaction):
    # Call this method when the player's health reaches 0
    self.combat_log.append(f"{self.player.name} has been defeated!")
    await interaction.message.edit(
        content=
        f"**{self.player.name}** could not handle a {self.enemy.name}! Noob.",
        embed=None,
        view=None)

    # Update the embed to show the player's action
    await self.update_embed(interaction)
    self.player.set_using_command(False)  # Reset the using_command field
    self.player.save_data()
    self.stop()  # Stop the view to clean up

  # ------------------------------------------------------------------------------------
  # Combat turn handler
  # ------------------------------------------------------------------------------------

  async def handle_combat_turn(self, interaction: nextcord.Interaction,
                               action: str):
    player_damage = 0
    enemy_damage = 0

    # ----------------------------------------------------------------------------------
    # Cast spell
    # ----------------------------------------------------------------------------------

    if action == "spell":
      player_damage = self.player.cast_spell(self.enemy)

      # Update combat log
      self.combat_log.append(
          f"**{self.player.name}** casts [spell] for `{player_damage}` damage!"
      )

    # ----------------------------------------------------------------------------------
    # Melee attack
    # ----------------------------------------------------------------------------------

    elif action == "melee":
      player_damage = self.player.melee_attack(self.enemy)

      # Update combat log
      self.combat_log.append(
          f"**{self.player.name}** attacks for `{player_damage}` damage!")

    # ----------------------------------------------------------------------------------
    # Defend action
    # Activates player.is_defending = True
    # Could be used by some class or something
    # ----------------------------------------------------------------------------------

    elif action == "defend":
      self.player.defend()  #??
      enemy_damage = math.floor(enemy_damage * 0.5)

      # Update combat log
      self.combat_log.append(f"**{self.player.name}** defends!")

    # ----------------------------------------------------------------------------------
    # Use item
    # ----------------------------------------------------------------------------------

    elif action == "item":
      # Implement item usage logic here
      pass

    # ----------------------------------------------------------------------------------
    # Flee action
    # ----------------------------------------------------------------------------------

    elif action == "flee":
      if self.player.flee():
        await self.handle_flee(interaction)
        return
      else:
        self.combat_log.append(f"**{self.player.name}** failed to flee!")

    # ----------------------------------------------------------------------------------
    # Update the embed to show the player's action
    # ----------------------------------------------------------------------------------

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

      # ----------------------------------------------------------------------------------
      # Show the mob's action
      # ----------------------------------------------------------------------------------

      enemy_damage = self.enemy.attack(self.player)

      self.combat_log.append(
          f"{self.enemy.name} attacks for {enemy_damage} damage!")

      # ----------------------------------------------------------------------------------
      # Update the embed to show the mobs's action
      # ----------------------------------------------------------------------------------

      await self.update_embed(interaction)

    # ----------------------------------------------------------------------------------
    # Check for end of combat
    # ----------------------------------------------------------------------------------

    if self.player.health <= 0:
      await self.handle_death(interaction)
    else:
      await self.update_embed(interaction)

  # ------------------------------------------------------------------------------------
  # Handle combat end due to flee action
  # ------------------------------------------------------------------------------------

  async def handle_flee(self, interaction: nextcord.Interaction):
    # Logic for handling flee
    await self.ctx.send(
        f"**{self.player.name}** has fled from the battle! Coward.")
    self.player.set_using_command(False)  # Reset the using_command field
    self.stop()  # Stop the view to clean up
    pass

  # ------------------------------------------------------------------------------------
  # Handle combat end due to enemy defeat
  # ------------------------------------------------------------------------------------

  async def handle_enemy_defeat(self, interaction: nextcord.Interaction):
    self.combat_log.append(f"{self.enemy.name} has been defeated!")
    await self.ctx.send(
        f"**{self.player.name}** has defeated the {self.enemy.name}!")
    # Update the embed to show the player's action
    await self.update_embed(interaction)
    self.player.set_using_command(False)  # Reset the using_command field
    self.stop()  # Stop the view to clean up
    pass

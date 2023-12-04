import nextcord
from nextcord.ui import Button, View
import asyncio
import math
from classes.Player import Player
from classes.Enemy import Enemy
from functions.load_settings import get_embed_color


class MultiplayerCombatView(View):

  def __init__(self, ctx, players, enemies):
    super().__init__(timeout=None)
    self.players = players
    self.enemies = enemies
    self.current_turn = 0
    self.embed_color = None
    self.ctx = ctx
    self.combat_log = []
    self.create_buttons()

  def create_buttons(self):
    for i, player in enumerate(self.players):
      self.add_player_buttons(player, i)

  def add_player_buttons(self, player, index):
    label = f"{player.name}'s Turn"
    button = Button(label=label,
                    style=nextcord.ButtonStyle.green,
                    custom_id=f"player_turn_{index}")
    self.add_item(button)

  async def interaction_check(self, interaction):
    # Check if it's the turn of the interacting player
    index = int(interaction.custom_id.split("_")[-1])
    return index == self.current_turn

  async def on_timeout(self):
    await self.ctx.send("Combat timeout. The battle is over.")
    self.stop()

  async def update_embed(self, interaction):
    self.embed_color = await get_embed_color(
        None if ctx.guild is None else ctx.guild.id)
    embed = nextcord.Embed(title="Multiplayer Combat", color=self.embed_color)
    embed.set_thumbnail(url='')

    for player in self.players:
      embed.add_field(
          name=f"**{player.name}'s Stats**",
          value=
          f"**HP:** {player.health}/{player.max_health}\n**Energy:** {player.energy}/{player.max_energy}",
          inline=True)

    for enemy in self.enemies:
      embed.add_field(name=f"**{enemy.name}'s Stats**",
                      value=f"**HP:** {enemy.health}/{enemy.max_health}",
                      inline=True)

    embed.add_field(name="**Combat Log**",
                    value="\n".join(self.combat_log[-6:]),
                    inline=False)

    await interaction.message.edit(embed=embed, view=self)

  async def handle_player_turn(self, interaction, player):
    # Logic for handling player's turn
    await self.ctx.send(f"**{player.name}'s Turn**")
    await self.update_embed(interaction)
    # Implement player actions here
    # You can use buttons to handle different actions like attack, defend, spell, etc.
    # Update the combat log and enemy's health accordingly
    # You can use player.melee_attack(enemy), player.cast_spell(enemy), etc.

    # After the player's turn, check if any enemies are defeated
    defeated_enemies = [enemy for enemy in self.enemies if enemy.health <= 0]
    if defeated_enemies:
      for enemy in defeated_enemies:
        self.enemies.remove(enemy)
        self.combat_log.append(f"{enemy.name} is defeated!")

    # Check if all enemies are defeated
    if not self.enemies:
      await self.ctx.send("All enemies are defeated. You win!")
      self.stop()
      return

    # Switch to the next player's turn
    self.current_turn = (self.current_turn + 1) % len(self.players)
    await self.update_embed(interaction)

  async def handle_enemy_turn(self, interaction, enemy):
    # Logic for handling enemy's turn
    await asyncio.sleep(1)  # Add a delay before enemy's action
    await self.ctx.send(f"**{enemy.name}'s Turn**")
    await self.update_embed(interaction)
    # Implement enemy actions here
    # You can use logic similar to player actions to determine enemy's actions
    # Update the combat log and player's health accordingly

    # After the enemy's turn, check if any players are defeated
    defeated_players = [
        player for player in self.players if player.health <= 0
    ]
    if defeated_players:
      for player in defeated_players:
        self.players.remove(player)
        self.combat_log.append(f"{player.name} is defeated!")

    # Check if all players are defeated
    if not self.players:
      await self.ctx.send("All players are defeated. You lose!")
      self.stop()
      return

    # Switch to the next player's turn
    self.current_turn = (self.current_turn + 1) % len(self.players)
    await self.update_embed(interaction)

  async def on_button_click(self, interaction):
    if interaction.custom_id.startswith("player_turn"):
      index = int(interaction.custom_id.split("_")[-1])
      player = self.players[index]
      await self.handle_player_turn(interaction, player)
    elif interaction.custom_id.startswith("enemy_turn"):
      index = int(interaction.custom_id.split("_")[-1])
      enemy = self.enemies[index]
      await self.handle_enemy_turn(interaction, enemy)


# Usage Example:
# Create a list of players and a list of enemies
# players = [Player(ctx.author), Player(other_user)]
# enemies = [Enemy(enemy_id_1), Enemy(enemy_id_2)]
# combat_view = MultiplayerCombatView(ctx, players, enemies)
# await ctx.send("A battle begins!")
# await combat_view.start()

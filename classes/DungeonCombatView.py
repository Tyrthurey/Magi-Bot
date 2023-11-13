import nextcord
from nextcord.ui import Button, View
from classes.CombatView import CombatView
import asyncio
import math


class DungeonCombatView(CombatView):

  def __init__(self, ctx, player, enemy):
    super().__init__(ctx, player, enemy)
    self.ctx = ctx
    self.player = player
    self.enemy = enemy
    self.combat_log = []
    self.threat_level = enemy.determine_threat_level(player.atk +
                                                     player.defense +
                                                     player.magic +
                                                     player.magic_def)

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
        value=f"**Threat Level:** {self.threat_level}\n{str(self.enemy)}",
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
      # Update the embed to show the player's action
      await self.update_embed(interaction)
    else:
      await self.handle_combat_turn(interaction, "flee")

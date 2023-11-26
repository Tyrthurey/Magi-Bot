import nextcord
from nextcord.ext import commands
from nextcord.ext.commands import has_permissions
from nextcord.ui import Button, View
import asyncio


class TutorialView(nextcord.ui.View):

  def __init__(self, ctx, tutorial_embeds):
    super().__init__(timeout=None)
    self.ctx = ctx
    self.tutorial_embeds = tutorial_embeds
    self.current_index = 0
    self.tutorial_done = asyncio.Event()

  async def interaction_check(self, interaction):
    return interaction.user == self.ctx.author

  @nextcord.ui.button(label="Continue", style=nextcord.ButtonStyle.green)
  async def continue_button(self, button: nextcord.ui.Button,
                            interaction: nextcord.Interaction):
    # Move to the next tutorial message
    self.current_index += 1
    if self.current_index < len(self.tutorial_embeds):
      await interaction.message.edit(
          embed=self.tutorial_embeds[self.current_index], view=self)
    else:
      # End of tutorial, remove buttons
      await interaction.message.edit(
          content=":tada: Tutorial completed! :tada: ", view=None)
      self.tutorial_done.set()  # Signal that the tutorial is done
      # Here you can call your dungeon logic or any other post-tutorial logic

  @nextcord.ui.button(label="Skip", style=nextcord.ButtonStyle.red)
  async def skip_button(self, button: nextcord.ui.Button,
                        interaction: nextcord.Interaction):
    await interaction.message.edit(content="Tutorial skipped. :<", view=None)
    self.tutorial_done.set()  # Signal that the tutorial is skipped
    # Here you can call your dungeon logic or any other post-tutorial logic

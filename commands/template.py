import asyncio
from nextcord.ext import commands
from nextcord import slash_command, SlashOption
import nextcord
from nextcord import Embed, ButtonStyle, ui
from nextcord.ui import Button, View
from main import bot, supabase
from functions.load_settings import get_embed_color
from classes.Player import Player
from functions.using_command_failsafe import using_command_failsafe_instance as failsafes
from functions.cooldown_manager import cooldown_manager_instance as cooldowns
import os
from PIL import Image, ImageSequence
import io
import functools


class Area(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @slash_command(name="command", description="Command information.")
  async def command_slash(self, interaction: nextcord.Interaction):
    await self.command(interaction)

  @commands.command(name="command",
                    aliases=["commands"],
                    help="Command information.")
  async def command_text(self, ctx):
    await self.command(ctx)

  async def command(self, interaction):
    send_message = interaction.response.send_message
    author = "Unknown"
    user_id = 0
    # If it's a text command, get the author from the context
    if isinstance(interaction, commands.Context):
      user_id = interaction.author.id
      author = interaction.author
      channel = interaction.channel
      send_message = interaction.send
    # If it's a slash command, get the author from the interaction
    elif isinstance(interaction, nextcord.Interaction):
      user_id = interaction.user.id
      author = interaction.user
      channel = interaction.channel
      send_message = interaction.response.send_message

    self.player = Player(author)

    embed_color = await get_embed_color(
        None if interaction.guild is None else interaction.guild.id)

    # Check if the player is already in a command
    if self.player.using_command:
      using_command_failsafe = failsafes.get_last_used_command_time(
          user_id, "general_failsafe")
      if not using_command_failsafe > 0:
        await send_message("Failsafe activated! Commencing with command!")
        self.player.using_command = False
      else:
        await send_message(
            "You're already in a command. Finish it before starting another.\n"
            f"Failsafe will activate in `{using_command_failsafe:.2f}` seconds if you're stuck."
        )
        return

    failsafes.set_last_used_command_time(self.player.user_id, "hunt", 60)
    failsafes.set_last_used_command_time(self.player.user_id,
                                         "general_failsafe", 70)

    action_id = 1

    command_data_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Actions').select('*').eq(
            'id', action_id).execute())

    if not command_data_response.data:
      await send_message("This command does not exist.")
      return

    command_data = command_data_response.data[0]
    command_name = command_data['name']
    command_cd = command_data['normal_cd']
    # command_patreon_cd = command_data['patreon_cd']

    # command_name = ctx.command.name
    cooldown_remaining = cooldowns.get_cooldown(user_id, command_name)

    if cooldown_remaining > 0:
      embed = nextcord.Embed(
          title=f"Command on Cooldown. Wait {cooldown_remaining:.2f}s...",
          color=embed_color)

      embed.add_field(
          name="",
          value=
          f"Tired of waiting? You can help us out by subscribing to our [Patreon](https://www.patreon.com/RCJoshua) for a reduced cooldown!\n(COMING SOON - NOT YET IMPLEMENTED)"
      )

      await send_message(embed=embed)
      return

    cooldown = command_cd

    # Set the cooldown for the hunt command
    cooldowns.set_cooldown(user_id, command_name, cooldown)

    # Instead of `ctx.send`, use `send_message`
    # Instead of `ctx.author`, use the `author` variable

    # When sending responses for slash commands, use `await interaction.response.send_message` aka "send_message()"
    # For follow-up messages, use `await interaction.followup.send`

    # Example:
    # await send_message("This is a response that works for both text and slash commands.")


def setup(bot):
  bot.add_cog(Area(bot))

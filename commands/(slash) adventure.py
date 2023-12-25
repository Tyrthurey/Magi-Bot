import nextcord
from nextcord.ext import commands
from nextcord.ext.commands import has_permissions
from nextcord.ui import Button, View
from typing import List
from supabase import create_client, Client
from dotenv import load_dotenv
from functions.load_settings import command_prefix, get_embed_color
from nextcord.ext.commands import has_permissions
import logging
import random
import os
import asyncio
import time
import math

from classes.SlashAdvCombatView import SlashAdvCombatView
from classes.TutorialView import TutorialView
from classes.Enemy import Enemy
from classes.Player import Player
from functions.cooldown_manager import cooldown_manager_instance as cooldowns
from functions.using_command_failsafe import using_command_failsafe_instance as failsafes

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


# New function to get location name
async def get_location_name(location_id):
  location_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Areas').select('name').eq(
          'id', location_id).execute())
  return location_response.data[0][
      'name'] if location_response.data else 'Unknown'


class AdventureCog(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @nextcord.slash_command(name="adventure",
                          description="Go on an awesome adventure!")
  async def adventure_slash(self, interaction: nextcord.Interaction):
    player = Player(interaction.user)
    # Check if the player is already in a command
    if player.using_command:
      using_command_failsafe = failsafes.get_last_used_command_time(
          player.user_id, "adventure")
      if not using_command_failsafe > 0:
        await interaction.response.send_message(
            "Failsafe activated! Commencing with command!")
      else:
        await interaction.response.send_message(
            "You're already in a command. Finish it before starting another.\n"
            f"Failsafe will activate in `{using_command_failsafe:.2f}` seconds if you're stuck."
        )
        return

    failsafes.set_last_used_command_time(player.user_id, "adventure", 320)
    failsafes.set_last_used_command_time(player.user_id, "general_failsafe",
                                         500)

    action_id = 4

    command_data_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Actions').select('*').eq(
            'id', action_id).execute())

    command_data = command_data_response.data[0]
    command_name = command_data['name']
    command_cd = command_data['normal_cd']
    # command_patreon_cd = command_data['patreon_cd']

    user_id = player.user_id
    # command_name = ctx.command.name
    cooldown_remaining = cooldowns.get_cooldown(user_id, command_name)

    if cooldown_remaining > 0:
      await interaction.response.send_message(
          f"This command is on cooldown. You can use it again in `{cooldown_remaining:.2f}` seconds."
      )
      return

    cooldown = command_cd

    # Set the cooldown for the hunt command
    cooldowns.set_cooldown(user_id, command_name, cooldown)

    player.set_using_command(True)

    # # Define your tutorial messages here
    # tutorial_messages = [
    #     "Welcome to adventurin!",  # Tutorial part 1
    #     "Monsters are random",  # Tutorial part 2
    #     "Stats affect you!",  # Tutorial part 3
    #     # Add all the tutorial parts here...
    # ]

    # # Check if the user is new and should see the tutorial
    # if player.dung_tutorial:
    #   # Show the tutorial
    #   tutorial_view = TutorialView(ctx, tutorial_messages)
    #   await ctx.send(content=tutorial_messages[0], view=tutorial_view)
    #   await tutorial_view.tutorial_done.wait(
    #   )  # Wait for the tutorial to be done

    player_stats_total = player.strength + player.dexterity + player.vitality + player.cunning + player.magic

    location = player.location
    location_name = await get_location_name(location)

    # Load mobs list for the current floor and select a random mob
    mob_data_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Mobs').select('*').eq(
            'area', player.location).execute())

    mobs_list = mob_data_response.data if mob_data_response.data else []
    if not mobs_list:
      await interaction.response.send_message(
          f"No creatures to hunt in {location_name}.")
      player.set_using_command(False)
      return

    selected_mob = random.choice(
        mobs_list)  # Randomly select a mob from the correct floor

    mob_id = selected_mob['id']

    # Now we can instantiate Enemy with the player's total stats
    enemy = Enemy(mob_id)
    threat_level = enemy.determine_threat_level(player_stats_total)

    # Create the initial embed with player and enemy information
    embed = nextcord.Embed(title=f"{player.name}'s adventure")
    embed.set_thumbnail(url='')
    embed.add_field(name=f"A wild {enemy.name} appears!",
                    value=f"**Threat Level:** {threat_level}\n{str(enemy)}",
                    inline=False)

    embed.add_field(name="__Your Stats__", value=str(player), inline=False)

    embed.add_field(name="------------------------------",
                    value="The battle is about to begin!",
                    inline=False)

    embed.add_field(name="------------------------------",
                    value="",
                    inline=False)

    embed.add_field(name="",
                    value="⚔️ --> Melee Attack \n🛡️ --> Defend",
                    inline=True)

    embed.add_field(name="", value="🔨 --> Use Item \n💨 --> Flee", inline=True)

    # Start combat with the initial embed
    view = SlashAdvCombatView(interaction, player, enemy)

    # At the end, instead of ctx.send, you'll use interaction response
    await interaction.response.send_message(embed=embed, view=view)


def setup(bot):
  bot.add_cog(AdventureCog(bot))

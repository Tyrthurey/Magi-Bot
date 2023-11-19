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

from classes.AdvCombatView import AdvCombatView
from classes.TutorialView import TutorialView
from classes.Enemy import Enemy
from classes.Player import Player

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


# Adventure command...
@commands.command(name="adventure")
@has_permissions(administrator=True)
async def adventure(ctx):

  player = Player(ctx.author)
  # Check if the player is already in a command
  if player.using_command:
    await ctx.send(
        "You're already in a command. Finish it before starting another.")
    return
  player.set_using_command(True)

  # Define your tutorial messages here
  tutorial_messages = [
      "Welcome to adventurin!",  # Tutorial part 1
      "Monsters are random",  # Tutorial part 2
      "Stats affect you!",  # Tutorial part 3
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

  mob_id = selected_mob['id']

  # Now we can instantiate Enemy with the player's total stats
  enemy = Enemy(mob_id)
  threat_level = enemy.determine_threat_level(player_stats_total)

  # Create the initial embed with player and enemy information
  embed = nextcord.Embed(title=f"{player.name}'s adventure")
  embed.set_thumbnail(
      url=
      'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Crossed_swords.svg/240px-Crossed_swords.svg.png'
  )
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
  view = AdvCombatView(ctx, player, enemy)
  await ctx.send(embed=embed, view=view)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(adventure)

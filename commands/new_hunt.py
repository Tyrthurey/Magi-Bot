import asyncio
import logging
import os
import random
import math
from nextcord.ext import commands
from supabase import Client, create_client
from dotenv import load_dotenv
from functions.item_write import item_write
from functions.cooldown_manager import cooldown_manager_instance as cooldowns
from classes.Player import Player
from classes.Enemy import Enemy

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


async def hunting(ctx, action_id):
  player = Player(ctx.author)

  mob_data_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Mobs').select('*').eq(
          'floor', player.floor).execute())

  mobs_list = mob_data_response.data if mob_data_response.data else []
  if not mobs_list:
    await ctx.send(f"No creatures to hunt on floor {player.location}.")
    return

  selected_mob = random.choice(
      mobs_list)  # Randomly select a mob from the correct floor
  mob_id = selected_mob['id']

  # Initialize Enemy with mob_id and other required parameters (you may need to adjust this per your Enemy class)
  enemy = Enemy(mob_id)

  # Now you have both player and enemy instance, you can start the fight or do anything you want
  # For example, let's send a message about the encounter
  await ctx.send(
      f"{player.name} encountered a {enemy.name}!\nTHIS IS A DEBUG COMMAND IT HAS NO OTHER USE"
  )


# Command function
@commands.command(name="new_hunt",
                  aliases=["nh"],
                  help="Debug hunt command. Useless.")
async def new_hunt(ctx):
  # Retrieve the current user data
  user_data_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Players').select('using_command').eq(
          'discord_id', ctx.author.id).execute())
  if not user_data_response.data:
    await ctx.send("You do not have a profile yet.")
    return

  user_data = user_data_response.data[0]
  using_command = user_data['using_command']
  # Check if the player is already in a command
  if using_command:
    await ctx.send(
        "You're already in a command. Finish it before starting another.")
    return

  await hunting(ctx, 1)


# # Command function
# @commands.command(name="scout",
#                   aliases=["s", "scouting"],
#                   help="Go on a scouting adventure and gain experience.")
# async def battle(ctx, 3):
#   await battle(ctx, 3)


# Error handler
async def hunting_error(ctx, error):
  if isinstance(error, commands.CommandOnCooldown):
    await ctx.send(
        f"This command is on cooldown. You can use it again in `{error.retry_after:.2f}` seconds."
    )
  else:
    await ctx.send(
        f"An error occurred: {error}\nWas this a mistake? Type `::bug <description>` to report it!"
    )


# Assign the error handler to the command
new_hunt.error(hunting_error)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(new_hunt)

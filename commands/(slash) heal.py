import asyncio
from nextcord.ext import commands
from functions.check_inventory import check_inventory
from functions.item_write import item_write
from functions.load_settings import command_prefix
import random
import nextcord

import logging
import os

from dotenv import load_dotenv
from supabase import Client, create_client

from classes.Player import Player

load_dotenv()
logging.basicConfig(level=logging.INFO)
url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


class SlashHeal(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @nextcord.slash_command(name="heal",
                          description="Heals you using a Healing Potion.")
  async def heal(self, interaction: nextcord.Interaction, quantity: str = "1"):
    user_data_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Users').select('*').eq(
            'discord_id', interaction.user.id).execute())
    if not user_data_response.data:
      await interaction.response.send_message(
          f"{interaction.user} does not have a profile yet.\nPlease type `apo start`."
      )
      return
    user_data = user_data_response.data[0]
    using_command = user_data['using_command']
    if using_command:
      await interaction.response.send_message(
          "You're already in a command. Finish it before starting another.")
      return
    # Call the `healing` function
    if quantity.isdigit():
      heal_message = await self.healing(interaction, int(quantity))
    # elif quantity.lower() == "all":
    #     heal_message = await self.heal_to_full(ctx)
    else:
      heal_message = "Invalid command usage. Type `apo heal <number>` or `apo heal all`."
    await interaction.response.send_message(heal_message)

  async def healing(self, interaction: nextcord.Interaction, quantity):

    # Get the user's health and max_health
    player_response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: supabase.table('Users').select('health', 'max_health').eq(
            'discord_id', interaction.user.id).execute())

    if player_response.data:
      player_data = player_response.data[0]
      current_health = player_data['health']
      max_health = player_data['max_health']
      player = Player(interaction.user)

      if current_health < max_health:
        # Check if the user has a health potion in inventory using check_inventory
        potion_quantity_lesser = await check_inventory(interaction.user.id,
                                                       1000, 'item')
        potion_quantity_minor = await check_inventory(interaction.user.id,
                                                      1001, 'item')

        potion_quantity_major = await check_inventory(interaction.user.id,
                                                      1002, 'item')

        if potion_quantity_lesser >= quantity:
          # Decrease the potion count by one using item_write
          await item_write(interaction.user.id, 1000, -quantity)

          heal_amount = 0
          for _ in range(quantity):
            heal_amount += random.randint(15, 25)
          player.health += heal_amount
          if player.health >= player.max_health:
            player.health = player.max_health
          player.update_health()

          return f"**{interaction.user}** has used `{quantity}` <:healthpotion:1175114505013968948> **(Lesser) Health Potion(s)** \n+`{heal_amount}` HP! Current HP: `{player.health}`/`{player.max_health}`"
        elif potion_quantity_minor >= quantity:
          # Decrease the potion count by one using item_write
          await item_write(interaction.user.id, 1001, -quantity)

          heal_amount = 0
          for _ in range(quantity):
            heal_amount += random.randint(30, 50)

          player.health += heal_amount
          if player.health >= player.max_health:
            player.health = player.max_health
          player.update_health()

          return f"**{interaction.user}** has used `{quantity}` <:healthpotion:1175114505013968948> **(Minor) Health Potion(s)** \n+`{heal_amount}` HP! Current HP: `{player.health}`/`{player.max_health}`"

        elif potion_quantity_major >= quantity:
          # Decrease the potion count by one using item_write
          await item_write(interaction.user.id, 1002, -quantity)

          heal_amount = 0
          for _ in range(quantity):
            heal_amount += random.randint(100, 300)
          player.health += heal_amount
          if player.health >= player.max_health:
            player.health = player.max_health
          player.update_health()

          return f"**{interaction.user}** has used `{quantity}` <:healthpotion:1175114505013968948> **(Major) Health Potion(s)** \n+`{heal_amount}` HP! Current HP: `{player.health}`/`{player.max_health}`"
        else:
          return f"**{interaction.user}**, you don't have any health potions. \nUse `buy health potion` to get one!"
      else:
        return f"**{interaction.user}**, your health is already full."
    else:
      return "You do not have a profile yet. Is this a bug? Type `apo bug <description>` to report it!"


def setup(bot):
  bot.add_cog(SlashHeal(bot))

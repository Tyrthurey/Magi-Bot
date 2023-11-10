import asyncio
import os
import requests
import json
import random
from dotenv import load_dotenv
import nextcord
from nextcord.ext import commands, tasks
from nextcord.ext.commands import has_permissions
from nextcord import SelectOption, message
from nextcord.ui import Select, Button, View
from nextcord import Interaction
from nextcord import ActionRow
from nextcord.ext.commands import UserConverter
import aiofiles
import aiohttp
import logging
from supabase import create_client, Client
from nextcord.ext.commands import BucketType
from datetime import datetime, timedelta, timezone
from keep_alive import keep_alive
import math
import sys
from pathlib import Path

# Add the directory containing the 'commands' package to sys.path
commands_dir = Path(__file__).parent.resolve()
sys.path.append(str(commands_dir))

from commands.heal import healing
from functions.check_inventory import check_inventory
from functions.item_write import item_write
from functions.load_settings import load_settings, command_prefix, get_prefix, get_embed_color
from functions.cooldown_manager import cooldown_manager_instance

from commands.website import setup as web_setup
from commands.admin import setup as admin_setup
from commands.help import setup as help_setup
from commands.hunt import setup as hunt_setup
from commands.shop import setup as shop_setup
from commands.buy import setup as buy_setup
from commands.dog import setup as dog_setup
from commands.cat import setup as cat_setup
from commands.use import setup as use_setup
from commands.hi import setup as hi_setup
from commands.sell import setup as sell_setup

load_dotenv()

logging.basicConfig(level=logging.INFO)

intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True  # Enables the member intent

# When you instantiate your bot, use the following lambda for the command_prefix
bot = commands.Bot(command_prefix=command_prefix,
                   intents=intents,
                   help_command=None,
                   case_insensitive=True)


async def save_settings(guild_id: int, new_settings):
  try:
    # Retrieve existing settings for the guild, if any
    existing = supabase.table('ServerSettings').select('settings').eq(
        'server_id', guild_id).execute()

    # Check if the settings already exist
    if existing.data:
      # Merge new settings with existing settings
      current_settings = existing.data[0]['settings']
      updated_settings = {**current_settings, **new_settings}
      # Update the existing record with the merged settings
      supabase.table('ServerSettings').update({
          'settings': updated_settings
      }).eq('server_id', guild_id).execute()
    else:
      # If there are no settings for this server, use default values and include the new settings
      default_settings = {"embed_color": "green", "prefix": "::"}
      updated_settings = {**default_settings, **new_settings}
      # Insert the new record with the default settings merged with the new settings
      supabase.table('ServerSettings').insert({
          'server_id': guild_id,
          'settings': updated_settings
      }).execute()

    logging.info(
        "Settings saved successfully for guild ID {}".format(guild_id))
  except Exception as e:
    logging.exception(
        "Failed to save settings for guild ID {}: ".format(guild_id),
        exc_info=e)


async def get_items(discord_id: int):
  # Fetch the user's inventory data from the database
  response = await bot.loop.run_in_executor(
      None, lambda: supabase.table('Inventory').select('items').eq(
          'discord_id', discord_id).execute())

  # Check if the user has items in inventory
  if response.data and response.data[0]['items']:
    return response.data[0]['items'][
        'items']  # This assumes the JSON structure as described
  else:
    return []  # Return an empty list if there are no items


bot_settings = {}


# Bot event for when the bot is ready
@bot.event
async def on_ready():
  global bot_settings
  global level_progression_data

  print(f'Logged in as {bot.user.name}')
  # Loop through all the guilds the bot is a member of
  for guild in bot.guilds:
    # Check if there is an entry for the guild in the database
    existing = supabase.table('ServerSettings').select('settings').eq(
        'server_id', guild.id).execute()

    # If there is no entry, insert the default settings
    if not existing.data:
      default_settings = {"embed_color": "green", "prefix": "::"}
      supabase.table('ServerSettings').insert({
          'server_id': guild.id,
          'settings': default_settings
      }).execute()
      print(f"Inserted default settings for guild ID {guild.id}")
    server_id = guild.id
    bot_settings[server_id] = await load_settings(server_id)
  print("All guild settings are checked and updated/inserted if necessary.")

  print(f'Logged in as {bot.user.name}')


@bot.event
async def on_message(message):
  # Avoid responding to the bot's own messages
  if message.author == bot.user:
    return

  # Get user information
  user_id = message.author.id
  username = str(message.author)

  # Check if the user is already in the database
  def check_user():
    return supabase.table('Players').select('total_server_exp').eq(
        'discord_id', user_id).execute()

  def update_user_exp(new_total_exp):
    return supabase.table('Players').update({
        'total_server_exp': new_total_exp
    }).eq('discord_id', user_id).execute()

  def insert_new_user():
    initial_data = {
        'discord_id': user_id,
        'username': username,
        'health': 10,
        'max_health': 10,
        'level': 1,
        'server_exp': 0,
        'total_server_exp': 0,
        'adventure_rank': 0,
        'adventure_exp': 0,
        'adventure_total_exp': 0,
        'atk': 1,
        'def': 1,
        'magic': 1,
        'magic_def': 1,
        'bal': 100,
        'floor': 1,
        'max_floor': 1,
        'free_points': 0
    }
    return supabase.table('Players').insert(initial_data).execute()

  response = await bot.loop.run_in_executor(None, check_user)

  if response.data:
    # The user exists, so increment their total_exp by 1
    user_data = response.data[0]
    new_total_exp = user_data['total_server_exp'] + 1
    # Update the user's total_exp in the database
    await bot.loop.run_in_executor(None, update_user_exp, new_total_exp)
  else:
    # The user doesn't exist, so add them to the database with initial values
    await bot.loop.run_in_executor(None, insert_new_user)

  # Process commands (if any)
  await bot.process_commands(message)


# Bot command to send a random gif
@bot.command(name="gif",
             aliases=["feed", "play", "sleep"],
             help="Sends a random dog gif.")
async def gif(ctx):
  with open("gifs.json") as f:
    links = json.load(f)
  await ctx.send(random.choice(links[ctx.invoked_with]))


class CustomIdModal(nextcord.ui.Modal):

  def __init__(self, title, guild_id):
    super().__init__(title=title)
    self.guild_id = guild_id
    self.add_item(
        nextcord.ui.TextInput(label="New Value",
                              placeholder="Enter a new value here..."))

  async def callback(self, interaction: nextcord.Interaction):
    new_value = self.children[0].value
    settings = {}
    if self.title == "Change Prefix":
      settings["prefix"] = new_value
    elif self.title == "Change Embed Color":
      settings["embed_color"] = new_value

    logging.info(f"New settings for guild {self.guild_id}: {settings}")
    await save_settings(self.guild_id, settings)
    logging.info("Save settings called.")

    await interaction.response.send_message(
        f"{self.title.split()[-1]} changed to `{new_value}`", ephemeral=True)


@bot.command(name="settings",
             help="Shows or updates current settings with interactive buttons."
             )
@has_permissions(administrator=True)
async def settings_command(ctx):
  bot_settings = await load_settings(ctx.guild.id)
  embed_color = await get_embed_color(ctx.guild.id
                                      )  # Use the color from settings
  embed = nextcord.Embed(title='Bot Settings',
                         description='Configure the bot settings below.',
                         color=embed_color)
  embed.add_field(
      name="Embed Color",
      value=
      f"Current embed color is `{bot_settings.get('embed_color', 'green')}`.\n---\n*Available Colors:* \ndefault, teal dark_teal, green, dark_green,\n blue, dark_blue, purple, dark_purple, magenta,\n dark_magenta, gold, dark_gold, orange,\n dark_orange, red, dark_red, lighter_grey,\n dark_grey, light_grey, darker_grey,\n blurple, greyple, dark_theme",
      inline=True)
  embed.add_field(
      name="Prefix",
      value=f"Current prefix is `{bot_settings.get('prefix', '!')}`",
      inline=True)
  embed.add_field(name="Click the buttons below to change the settings.",
                  value="",
                  inline=False)
  view = View(timeout=60)

  async def change_prefix_callback(interaction: nextcord.Interaction):
    if interaction.user != ctx.author:
      await interaction.response.send_message(
          "You are not authorized to change the settings.", ephemeral=True)
      return
    modal = CustomIdModal(title="Change Prefix", guild_id=ctx.guild.id)
    await interaction.response.send_modal(modal)

  async def change_color_callback(interaction: nextcord.Interaction):
    if interaction.user != ctx.author:
      await interaction.response.send_message(
          "You are not authorized to change the settings.", ephemeral=True)
      return
    modal = CustomIdModal(title="Change Embed Color", guild_id=ctx.guild.id)
    await interaction.response.send_modal(modal)

  prefix_button = Button(style=nextcord.ButtonStyle.primary,
                         label="Change Prefix",
                         custom_id="change_prefix")
  color_button = Button(style=nextcord.ButtonStyle.primary,
                        label="Change Embed Color",
                        custom_id="change_color")

  prefix_button.callback = change_prefix_callback
  color_button.callback = change_color_callback

  view.add_item(prefix_button)
  view.add_item(color_button)

  await ctx.send(embed=embed, view=view)


# Error handling for the settings command
@settings_command.error
async def settings_command_error(ctx, error):
  if isinstance(error, commands.MissingPermissions):
    await ctx.send("You need administrator permissions to change the settings."
                   )


@bot.command(name="profile",
             aliases=["p", "prof"],
             help="Displays the user's or another user's game profile.")
async def profile(ctx, *, user: nextcord.User = None):
  embed_color = await get_embed_color(ctx.guild.id)
  # If no user is specified, show the profile of the author of the message
  if user is None:
    user = ctx.author

  user_id = user.id
  username = user.display_name
  avatar_url = user.avatar.url if user.avatar else user.default_avatar.url

  # Fetch the latest user data from the database
  response = await bot.loop.run_in_executor(
      None, lambda: supabase.table('Players').select('*').eq(
          'discord_id', user_id).execute())

  # Fetch the latest user data from the database
  user_data_response = await bot.loop.run_in_executor(
      None, lambda: supabase.table('Players').select('*').eq(
          'discord_id', user_id).execute())

  # Check if the user has a profile
  if not user_data_response.data:
    await ctx.send(f"{username} does not have a profile yet.")
    return

  user_data = user_data_response.data[0]  # User data from the database

  # Fetch level progression data for the user's next level
  level_progression_response = await bot.loop.run_in_executor(
      None, lambda: supabase.table('LevelProgression').select('*').eq(
          'level', user_data['level'] + 1).execute())

  if level_progression_response.data:
    needed_adv_level_exp = level_progression_response.data[0][
        'total_level_exp']
  else:
    needed_adv_level_exp = "N/A"

  # Create the embed with the updated user data
  embed = nextcord.Embed(title="Rookie Adventurer", color=embed_color)
  embed.set_author(name=f"{username}'s Profile", icon_url=avatar_url)

  total_stats = user_data['atk'] + user_data['def'] + user_data[
      'magic'] + user_data['magic_def']

  embed.add_field(
      name="__Status:__",
      value=f"**Level:** {user_data['level']}\n"
      f"**EXP:** {user_data['adventure_exp']}/{needed_adv_level_exp}\n"
      f"**Gold:** {user_data['bal']}\n"
      f"**Floor:** {user_data['floor']}\n"
      f"**HP:** {user_data['health']}/{user_data['max_health']}\n"
      f"**MP:** 0/0",
      inline=True)

  embed.add_field(name="__Stats:__",
                  value=f"**ATK:** {user_data['atk']}\n"
                  f"**DEF:** {user_data['def']}\n"
                  f"**MAGIC:** {user_data['magic']}\n"
                  f"**MAGIC DEF:** {user_data['magic_def']}\n"
                  f"**STAT SCORE:** {total_stats}\n"
                  f"**FREE POINTS:** (In-Dev)\n",
                  inline=True)

  embed.add_field(name="__Equipment:__", value="N/A", inline=False)

  # Set the thumbnail to the user's Discord avatar
  embed.set_thumbnail(url=avatar_url)

  # Set the footer to the bot's name and icon
  embed.set_footer(text=bot.user.name, icon_url=bot.user.avatar.url)

  # Send the embed
  await ctx.send(embed=embed)


# Converters to handle the user argument
@profile.error
async def profile_error(ctx, error):
  if isinstance(error, nextcord.ext.commands.errors.BadArgument):
    await ctx.send("Couldn't find that user.")


@bot.command(name="leaderboard", help="Displays the top players by level.")
async def leaderboard(ctx):
  # Fetch top 10 users by level
  results = supabase.table('Players').select('*').eq('is_bot', False).order(
      'level', desc=True).limit(10).execute()

  # Check if the request was successful
  if results.data:
    leaderboard = "\n".join([
        f"{idx + 1}. {user['username']} - Level {user['level']}"
        for idx, user in enumerate(results.data)
    ])
    await ctx.send(f"Top Players by Level:\n{leaderboard}")
  else:
    await ctx.send("Could not retrieve the leaderboard at this time.")


@bot.command(name="cooldowns",
             aliases=["cd"],
             help="Displays your current command cooldowns.")
async def cooldowns(ctx, *, user: nextcord.User = None):
  embed_color = await get_embed_color(ctx.guild.id)
  # If no user is specified, show the profile of the author of the message
  if user is None:
    user = ctx.author

  user_id = user.id
  username = user.display_name
  avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
  guild_settings = await load_settings(ctx.guild.id)
  guild_prefix = guild_settings.get(
      'prefix', '::')  # Use the default prefix if not found in the settings

  embed = nextcord.Embed(title='Cooldowns', color=embed_color)
  embed.set_author(name=username, icon_url=avatar_url)

  # Loop through all commands and get cooldowns from the CooldownManager
  for command in bot.commands:
    # Skip if the command is hidden
    if command.hidden:
      continue

    # Get the remaining cooldown for this command and user
    cooldown_remaining = cooldown_manager_instance.get_cooldown(
        user_id, command.name)

    if cooldown_remaining > 0:
      # Command is on cooldown
      minutes, seconds = divmod(int(cooldown_remaining), 60)
      hours, minutes = divmod(minutes, 60)
      cooldown_message = f":x: {hours}h {minutes}m {seconds}s remaining"
      # Add the command and its cooldown status to the embed
      embed.add_field(name=f"{guild_prefix}{command.name}",
                      value=cooldown_message,
                      inline=False)

  # If the embed has no fields, it means no commands are on cooldown
  if len(embed.fields) == 0:
    embed.description = "No commands on cooldown!"

  # Send the embed
  await ctx.send(embed=embed)


@bot.command(name="inventory",
             aliases=["inv"],
             help="Displays the user's inventory.")
async def inventory(ctx, *, user: nextcord.User = None):
  embed_color = await get_embed_color(ctx.guild.id)
  # If no user is specified, show the profile of the author of the message
  if user is None:
    user = ctx.author

  user_id = user.id
  username = user.display_name
  avatar_url = user.avatar.url if user.avatar else user.default_avatar.url

  # Use the new get_items function to fetch the user's items
  items = await get_items(user_id)

  # Create the embed with the inventory data
  embed = nextcord.Embed(color=embed_color)
  embed.set_author(name=f"{username}'s Inventory", icon_url=avatar_url)

  if not items:
    embed.description = "Your inventory is empty."
  else:
    for item in items:
      if item['quantity'] > 0:
        # Fetch item details from the Items table
        item_response = await bot.loop.run_in_executor(
            None,
            lambda: supabase.table('Items').select('item_displayname').eq(
                'item_id', item['item_id']).execute())
        if item_response.data:
          item_name = item_response.data[0]['item_displayname']
        else:
          item_name = f"Item {item['item_id']}"

        # Calculate remaining cooldown
        cooldown_str = ""

        if item['cooldown']:
          # Parse the cooldown time to a naive datetime object (without timezone)
          cooldown_time = datetime.fromisoformat(item['cooldown'].replace(
              'Z', '')).replace(tzinfo=None)

          # Get the current time as a naive datetime object (without timezone)
          now = datetime.utcnow().replace(tzinfo=None)

          # Calculate the remaining cooldown time
          remaining_time = cooldown_time - now
          if remaining_time.total_seconds() > 0:
            # Calculate hours and minutes from remaining_time
            hours, remainder = divmod(int(remaining_time.total_seconds()),
                                      3600)
            minutes, _ = divmod(remainder, 60)
            # Format the cooldown string
            cooldown_str = f"Ready in: {hours}h {minutes}m"

        # Add fields to the embed
        embed.add_field(
            name="",
            value=f"**{item_name}**: {item['quantity']}\n{cooldown_str}"
            if cooldown_str else f"**{item_name}**: {item['quantity']}",
            inline=False)

  # Send the embed
  await ctx.send(embed=embed)


@bot.command(name="heal", help="Heals you using a Healing Potion.")
async def heal(ctx):
  # Call the imported `healing` function
  heal_message = await healing(ctx, bot)
  await ctx.send(heal_message)


# -----------------------------------------------------------------------------
# No touch beyond this point

try:
  url = os.getenv("SUPABASE_URL") or ""
  key = os.getenv("SUPABASE_KEY") or ""
  supabase: Client = create_client(url, key)

  token = os.getenv("TOKEN") or ""
  if token == "":
    raise Exception("Please add your token to the .env file.")
    # Call this before you run your bot

  # Hunt command setup
  hunt_setup(bot)
  shop_setup(bot)
  buy_setup(bot)
  hi_setup(bot)
  web_setup(bot)
  help_setup(bot)
  admin_setup(bot)
  dog_setup(bot)
  cat_setup(bot)
  use_setup(bot)
  sell_setup(bot)
  keep_alive()

  bot.run(token)
except nextcord.HTTPException as e:
  if e.status == 429:
    print(
        "The Discord servers denied the connection for making too many requests"
    )
    print(
        "Get help from https://stackoverflow.com/questions/66724687/in-discord-py-how-to-solve-the-error-for-toomanyrequests"
    )
  else:
    raise e

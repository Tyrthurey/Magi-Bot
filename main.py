import asyncio
import os
import requests
import json
import random
from dotenv import load_dotenv
import nextcord
from typing import List
from nextcord.ext import commands, tasks
from nextcord.ext.commands import has_permissions
from nextcord import SelectOption, message, Embed
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
from commands.suggest import setup as suggest_setup
from commands.bug import setup as bug_setup
from commands.dungeon import setup as dungeon_setup
from commands.adventure import setup as adv_setup
from commands.floor import setup as floor_setup

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

  try:
    supabase.table('Players').update({
        'using_command': False
    }).neq('discord_id', 0).execute()
  except Exception as e:
    print(f'An error occurred while resetting using_command field: {e}')

  print(f'Logged in as {bot.user.name}')
  # Loop through all the guilds the bot is a member of
  for guild in bot.guilds:
    server_name = guild.name
    member_amount = guild.member_count
    server_id = guild.id
    # Check if there is an entry for the guild in the database
    existing = supabase.table('ServerSettings').select('settings').eq(
        'server_id', guild.id).execute()

    # If there is no entry, insert the default settings
    if not existing.data:
      default_settings = {"embed_color": "green", "prefix": "::"}
      supabase.table('ServerSettings').insert({
          'server_id': guild.id,
          'settings': default_settings,
          'server_name': server_name,
          'member_amount': member_amount
      }).execute()
      print(f"Inserted default settings for guild ID {guild.id}")
    else:
      supabase.table('ServerSettings').update({
          'server_name': server_name,
          'member_amount': member_amount
      }).eq('server_id', server_id).execute()
    bot_settings[server_id] = await load_settings(server_id)
  print("All guild settings are checked and updated/inserted if necessary.")

  print(f'Logged in as {bot.user.name}')
  # Set the playing status
  game = nextcord.Game("::hunt | ::help | ::shop")
  await bot.change_presence(activity=game)


@bot.event
async def on_message(message):
  # Avoid responding to the bot's own messages
  if message.author == bot.user:
    return

  # Get the server settings
  server_id = message.guild.id if message.guild else None
  if server_id:
    settings = await load_settings(server_id)
    operation_channel_id = settings.get('channel_id')

    # Check if the message is in the designated channel
    if operation_channel_id and message.channel.id != operation_channel_id:
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


@bot.command(
    name="start",
    help="Starts the game and creates a profile for you if it doesn't exist.")
async def start(ctx):
  # Get user information
  user_id = ctx.author.id
  username = str(ctx.author)

  # Check if the user is already in the database
  def check_user():
    return supabase.table('Users').select('discord_id').eq(
        'discord_id', user_id).execute()

  def insert_new_user():
    # Set the initial values for the new user
    initial_data = {
        'discord_id': user_id,
        'username': username,
        'location': 'Tutorial',
        'adventure_exp': 0,
        'level': 1,
        'free_points': 5,
        'health': 25,
        'max_health': 25,
        'energy': 13,
        'max_energy': 13,
        'strength': 5,
        'dexterity': 5,
        'vitality': 5,
        'cunning': 5,
        'magic': 5,
        'luck': 5,
        'recovery_speed': 5,
        'damage': 12,
        'defence': 12,
        'bal': 100,
        'floor': 1,
        'max_floor': 1,
        'level_ignore': 0,
        'crit_chance': 4,
        'dodge_chance': 10,
        'escape_chance': 50,
        'accuracy': 50,
        'deaths': 0,
        'server_exp': 0,
        'server_level': 0
    }
    return supabase.table('Users').insert(initial_data).execute()

  response = await bot.loop.run_in_executor(None, check_user)

  if response.data:
    # The user exists, send a message
    await ctx.send("You have already started the game and your profile exists."
                   )
  else:
    # The user doesn't exist, so add them to the database with initial values
    await bot.loop.run_in_executor(None, insert_new_user)
    # Send a message with the tutorial
    await ctx.send("Welcome to the game! Here is a small tutorial...\n"
                   "(*Add your game tutorial here*)")


## Bot command to send a random gif
# @bot.command(name="gif",
#             aliases=["feed", "play", "sleep"],
#             help="Sends a random dog gif.")
# async def gif(ctx):
#  with open("gifs.json") as f:
#    links = json.load(f)
#  await ctx.send(random.choice(links[ctx.invoked_with]))


@bot.command(name="gif",
             aliases=["feed", "play", "sleep"],
             help="Sends a random dog gif.")
async def gif(ctx):
  # Check if the user is in the database
  def check_user():
    user_id = ctx.author.id
    return supabase.table('Users').select('discord_id').eq(
        'discord_id', user_id).execute()

  response = await bot.loop.run_in_executor(None, check_user)

  if response.data:
    # The user exists, proceed with the command
    with open("gifs.json") as f:
      links = json.load(f)
    await ctx.send(random.choice(links[ctx.invoked_with]))
  else:
    # The user doesn't exist, send a message to run /start
    await ctx.send("Profile Not Found, Please run /start")


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
        f"{self.title.split()[-1]} changed to `{new_value}`", ephemeral=False)


@bot.command(name="settings",
             help="Shows or updates current settings with interactive buttons."
             )
@has_permissions(administrator=True)
async def settings_command(ctx):
  bot_settings = await load_settings(ctx.guild.id)
  embed_color = await get_embed_color(ctx.guild.id)
  embed = nextcord.Embed(title='Bot Settings',
                         description='Configure the bot settings below.',
                         color=embed_color)

  # Display the current operation channel
  operation_channel_id = bot_settings.get('channel_id')
  if operation_channel_id:
    operation_channel = bot.get_channel(operation_channel_id)
    operation_channel_name = operation_channel.mention if operation_channel else "Invalid Channel"
  else:
    operation_channel_name = "Not Set"

  embed.add_field(
      name="Embed Color",
      value=
      f"Current embed color is `{bot_settings.get('embed_color', 'green')}`.\n---\n*Available Colors:* \ndefault, teal dark_teal, green, dark_green,\n blue, dark_blue, purple, dark_purple, magenta,\n dark_magenta, gold, dark_gold, orange,\n dark_orange, red, dark_red, lighter_grey,\n dark_grey, light_grey, darker_grey,\n blurple, greyple, dark_theme",
      inline=True)
  embed.add_field(
      name="Prefix",
      value=f"Current prefix is `{bot_settings.get('prefix', '::')}`",
      inline=True)
  embed.add_field(
      name="Operation Channel",
      value=
      f"Current operation channel is {operation_channel_name}\nUse `{bot_settings.get('prefix', '::')}setchannel <channel>` to change this.",
      inline=True)
  embed.add_field(name="Click the buttons below to change the settings.",
                  value="",
                  inline=False)
  view = View(timeout=60)

  async def change_prefix_callback(interaction: nextcord.Interaction):
    if interaction.user != ctx.author:
      await interaction.response.send_message(
          "You are not authorized to change the settings. Is this a bug? Type `::bug <description>` to report it!",
          ephemeral=True)
      return
    modal = CustomIdModal(title="Change Prefix", guild_id=ctx.guild.id)
    await interaction.response.send_modal(modal)

  async def change_color_callback(interaction: nextcord.Interaction):
    if interaction.user != ctx.author:
      await interaction.response.send_message(
          "You are not authorized to change the settings. Is this a bug? Type `::bug <description>` to report it!",
          ephemeral=True)
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
    await ctx.send(
        "You need administrator permissions to change the settings. Is this a bug? Type `::bug <description>` to report it!"
    )


@bot.command(name="setchannel",
             help="Sets a specific channel for the bot to operate in.")
@has_permissions(administrator=True)
async def setchannel(ctx, channel: nextcord.TextChannel = None):
  server_id = ctx.guild.id

  if channel is None:
    # Clear the operation channel setting
    await save_settings(server_id, {'channel_id': None})
    await ctx.send(
        "Bot operation channel has been cleared. The bot will now operate in all channels."
    )
  else:
    # Set the new operation channel
    await save_settings(server_id, {'channel_id': channel.id})
    await ctx.send(f"Bot operation channel set to {channel.mention}")


# Error handling for the setchannel command
@setchannel.error
async def setchannel_error(ctx, error):
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
  user_data_response = await bot.loop.run_in_executor(
      None, lambda: supabase.table('Users').select('*').eq(
          'discord_id', user_id).execute())

  # Check if the user has a profile
  if not user_data_response.data:
    await ctx.send(
        f"{username} does not have a profile yet.\nPlease type `::start`.")
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

  # Fetch the user's inventory data from the database
  inventory_response = await bot.loop.run_in_executor(
      None, lambda: supabase.table('Inventory').select('titles').eq(
          'discord_id', user_id).execute())

  # Check if the user has any titles
  user_title = "Rookie Adventurer"  # default title
  if inventory_response.data:
    inventory_data = inventory_response.data[0]
    titles = inventory_data.get('titles', [])

    # Check if the user has an equipped title
    equipped_title = next(
        (title for title in titles if title["equipped"] is True), None)
    if equipped_title:
      # Fetch the title name from the Titles table
      title_response = await bot.loop.run_in_executor(
          None, lambda: supabase.table('Titles').select('title_name').eq(
              'id', equipped_title['title_id']).execute()
      )  # Replace 'id' with your actual column name

      if title_response.data:
        user_title = title_response.data[0]['title_name']
      else:
        user_title = "Rookie Adventurer"

  # Create the embed with the updated user data
  embed = nextcord.Embed(title=user_title, color=embed_color)
  embed.set_author(name=f"{username}'s Profile", icon_url=avatar_url)

  total_stats = user_data['strength'] + user_data['dexterity'] + user_data[
      'vitality'] + user_data['cunning'] + user_data['magic'] + user_data[
          'luck']

  embed.add_field(
      name="__Status:__",
      value=f"**Level:** {user_data['level']}\n"
      f"**EXP:** {user_data['adventure_exp']}/{needed_adv_level_exp}\n"
      f"**Gold:** {user_data['bal']}\n"
      f"**Location:** {user_data['location']}\n"
      f"**Health:** {user_data['health']}/{user_data['max_health']}\n"
      f"**Energy:** {user_data['energy']}/{user_data['max_energy']}",
      inline=True)

  embed.add_field(name="__Stats:__",
                  value=f"**Strength:** {user_data['strength']}\n"
                  f"**Dexterity:** {user_data['dexterity']}\n"
                  f"**Vitality:** {user_data['vitality']}\n"
                  f"**Cunning:** {user_data['cunning']}\n"
                  f"**Magic:** {user_data['magic']}\n"
                  f"**Luck:** {user_data['luck']}\n"
                  f"**Stats Score:** {total_stats}\n"
                  f"**Free Points:** {user_data['free_points']}\n",
                  inline=True)

  embed.add_field(name="__Equipment:__", value="N/A", inline=False)

  # Set the thumbnail to the user's Discord avatar
  embed.set_thumbnail(url=avatar_url)

  # Set the footer to the bot's name and icon
  embed.set_footer(
      text=f"{bot.user.name} - Help us improve! Use ::suggest <suggestion>",
      icon_url=bot.user.avatar.url)

  # Send the embed
  await ctx.send(embed=embed)


# Converters to handle the user argument
@profile.error
async def profile_error(ctx, error):
  if isinstance(error, nextcord.ext.commands.errors.BadArgument):
    await ctx.send("Couldn't find that user.")


@bot.command(name="leaderboard",
             aliases=["lb"],
             help="Displays the top players by level.")
async def leaderboard(ctx):
  # Fetch top 10 users by level
  results = supabase.table('Players').select('*').eq('is_bot', False).order(
      'level', desc=True).order('adventure_exp',
                                desc=True).limit(10).execute()

  # Check if the request was successful
  if results.data:
    leaderboard = "\n".join([
        f"{idx + 1}. {user['username']} - Level {user['level']} (EXP: {user['adventure_exp']})"
        for idx, user in enumerate(results.data)
    ])
    await ctx.send(
        f"Top Players by Level and Experience:\n(Top 3 in both Level and EXP of The Beta-Testers will get a reward.)\n{leaderboard}"
    )
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
  user_data_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Players').select('*').eq(
          'discord_id', ctx.author.id).execute())
  if not user_data_response.data:
    await ctx.send("You do not have a profile yet.")
    return
  user_data = user_data_response.data[0]
  using_command = user_data['using_command']
  if using_command:
    await ctx.send(
        "You're already in a command. Finish it before starting another.")
    return
  # Call the imported `healing` function
  heal_message = await healing(ctx, bot)
  await ctx.send(heal_message)


@bot.command(name='alsodummycombat')
async def combat(ctx):
  # Simulate combat logic or get stats from your game system
  # Here, we're just using some made-up static values for demonstration purposes
  player_stats = {'hp': 47, 'max_hp': 212, 'mp': 60, 'max_mp': 90}
  enemy_stats = {'hp': 0, 'max_hp': 210, 'mp': 25, 'max_mp': 80}
  player_damage = 52
  enemy_damage = 21
  enemy_name = "Skeleton"
  threat_level = "Easy"
  combat_log = [
      "Skeleton stole 21 HP", "Skeleton has dealt a critical hit! 46 damage",
      f"{ctx.author.display_name} has dealt {player_damage} magic damage",
      f"{ctx.author.display_name} won"
  ]

  # Create the embed
  embed = nextcord.Embed(
      title="Dungeon Floor 1",
      description=
      f"You encountered a {enemy_name}!\nThreat Level: {threat_level}",
      color=0x1abc9c)
  embed.set_thumbnail(url=ctx.author.avatar.url)
  embed.add_field(
      name=f"{enemy_name}'s Stats",
      value=
      f"{enemy_stats['hp']}/{enemy_stats['max_hp']}❤️, {enemy_stats['mp']}/{enemy_stats['max_mp']}💧",
      inline=False)
  embed.add_field(
      name="Your Stats",
      value=
      f"{player_stats['hp']}/{player_stats['max_hp']}❤️, {player_stats['mp']}/{player_stats['max_mp']}💧",
      inline=False)
  # Add combat stats (icons can be custom emojis or standard emoji characters)
  embed.add_field(name="⚔️ 46 | 🛡️ 26 | 🌟 18% | 🎯 112%",
                  value="Player combat stats here",
                  inline=False)
  embed.add_field(name="💫 53 | 🌀 26 | ✨ 11% | 🎲 +18",
                  value="Additional stats or effects",
                  inline=False)

  # Add a separator line
  embed.add_field(name="\u200b",
                  value="------------------------------------",
                  inline=False)

  # Add combat log
  for log in combat_log:
    embed.add_field(name="\u200b", value=log, inline=False)

  # Send the embed
  await ctx.send(embed=embed)


# @bot.command(name="titles", aliases=["t"], help="Displays the user's titles.")
# async def titles(ctx):
#   embed_color = await get_embed_color(ctx.guild.id)
#   user_id = ctx.author.id

#   # Fetch the latest user data from the database
#   user_data_response = await bot.loop.run_in_executor(
#       None, lambda: supabase.table('Users').select('*').eq(
#           'discord_id', user_id).execute())

#   # Check if the user has a profile
#   if not user_data_response.data:
#     await ctx.send(
#         f"{ctx.author} does not have a profile yet.\nPlease type `::start`.")
#     return

#   # Fetch the inventory data for the user
#   inventory_response = await bot.loop.run_in_executor(
#       None, lambda: supabase.table('Inventory').select('titles').eq(
#           'discord_id', user_id).execute())

#   if not inventory_response.data:
#     await ctx.send("You don't have any titles yet.")
#     return

#   inventory_data = inventory_response.data[0]
#   titles = inventory_data.get('titles', [])

#   if not titles:
#     await ctx.send("You don't have any titles yet.")
#     return

#   # Create an embed for the titles
#   embed = Embed(title="Your Titles", color=embed_color)

#   for title in titles:
#     # Fetch the title name from the Titles table
#     title_response = await bot.loop.run_in_executor(
#         None, lambda: supabase.table('Titles').select('title_name').eq(
#             'id', title['title_id']).execute()
#     )  # Replace 'id' with your actual column name

#     if title_response.data:
#       title_name = title_response.data[0]['title_name']
#       embed.add_field(name="ID: " + str(title['title_id']),
#                       value=title_name,
#                       inline=False)

#   embed.add_field(name="", value="Use `title equip <id>`", inline=False)
#   await ctx.send(embed=embed)


@bot.group(invoke_without_command=True,
           aliases=["t"],
           help="Manage your titles.")
async def titles(ctx):
  # await ctx.send("Please use a subcommand, e.g., `::title equip <id>`.")
  embed_color = await get_embed_color(ctx.guild.id)
  user_id = ctx.author.id

  # Fetch the latest user data from the database
  user_data_response = await bot.loop.run_in_executor(
      None, lambda: supabase.table('Users').select('*').eq(
          'discord_id', user_id).execute())

  # Check if the user has a profile
  if not user_data_response.data:
    await ctx.send(
        f"{ctx.author} does not have a profile yet.\nPlease type `::start`.")
    return

  # Fetch the inventory data for the user
  inventory_response = await bot.loop.run_in_executor(
      None, lambda: supabase.table('Inventory').select('titles').eq(
          'discord_id', user_id).execute())

  if not inventory_response.data:
    await ctx.send("You don't have any titles yet.")
    return

  inventory_data = inventory_response.data[0]
  titles = inventory_data.get('titles', [])

  if not titles:
    await ctx.send("You don't have any titles yet.")
    return

  # Create an embed for the titles
  embed = Embed(title="Your Titles", color=embed_color)

  for title in titles:
    # Fetch the title name from the Titles table
    title_response = await bot.loop.run_in_executor(
        None, lambda: supabase.table('Titles').select('title_name').eq(
            'id', title['title_id']).execute()
    )  # Replace 'id' with your actual column name

    if title_response.data:
      title_name = title_response.data[0]['title_name']
      embed.add_field(name="ID: " + str(title['title_id']),
                      value=title_name,
                      inline=False)

  embed.add_field(name="", value="Use `titles equip <id>`", inline=False)
  await ctx.send(embed=embed)


@titles.command(help="Equip a title.")
async def equip(ctx, title_id: int):
  user_id = ctx.author.id

  # Fetch the latest user data from the database
  user_data_response = await bot.loop.run_in_executor(
      None, lambda: supabase.table('Users').select('*').eq(
          'discord_id', user_id).execute())

  # Check if the user has a profile
  if not user_data_response.data:
    await ctx.send(
        f"{ctx.author} does not have a profile yet.\nPlease type `::start`.")
    return

  # Fetch the inventory data for the user
  inventory_response = await bot.loop.run_in_executor(
      None, lambda: supabase.table('Inventory').select('titles').eq(
          'discord_id', user_id).execute())

  if not inventory_response.data:
    await ctx.send("You don't have any titles yet.")
    return

  inventory_data = inventory_response.data[0]
  titles = inventory_data.get('titles', [])

  if not titles:
    await ctx.send("You don't have any titles yet.")
    return

  # Check if the user has the title they're trying to equip
  title_to_equip = None
  for title in titles:
    if title['title_id'] == title_id:
      title_to_equip = title
      break

  if not title_to_equip:
    await ctx.send("You don't have this title.")
    return

  # Unequip the currently equipped title
  for title in titles:
    if title.get('equipped', False):
      title['equipped'] = False

  # Equip the new title
  title_to_equip['equipped'] = True

  # Update the inventory data
  updated_inventory_data = {'titles': titles}
  await bot.loop.run_in_executor(
      None,
      lambda: supabase.table('Inventory').update(updated_inventory_data).eq(
          'discord_id', user_id).execute())

  await ctx.send(f"You have equipped the title with ID {title_id}.")


@bot.command(name="get_title", help="Gives the user a title.")
async def get_title(ctx):
  user_id = ctx.author.id
  new_title_id = 4  # Change this to the title_id you want to give

  # Fetch the inventory data for the user
  inventory_response = await bot.loop.run_in_executor(
      None, lambda: supabase.table('Inventory').select('titles').eq(
          'discord_id', user_id).execute())

  inventory_data = inventory_response.data
  titles = []

  # Check if inventory data exists for the user
  if inventory_data:
    inventory_record = inventory_data[0]
    titles = inventory_record.get('titles', [])
    if titles is None:
      titles = []

  # Check if the user already has the title
  for title in titles:
    if title['title_id'] == new_title_id:
      await ctx.send("You already have this title!")
      return  # Stop the function here

  # Add the new title
  new_title = {'title_id': new_title_id, 'equipped': False}
  titles.append(new_title)

  # Prepare the updated inventory data
  updated_inventory_data = {'titles': titles}

  # If inventory data exists, update it
  if inventory_data:
    await bot.loop.run_in_executor(
        None,
        lambda: supabase.table('Inventory').update(updated_inventory_data).eq(
            'discord_id', user_id).execute())
  else:
    # If inventory data does not exist, create it
    updated_inventory_data[
        'discord_id'] = user_id  # Ensure the discord_id is included
    await bot.loop.run_in_executor(
        None, lambda: supabase.table('Inventory').insert(updated_inventory_data
                                                         ).execute())

  await ctx.send("You've been given a new title!")


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
  suggest_setup(bot)
  bug_setup(bot)
  dungeon_setup(bot)
  adv_setup(bot)
  floor_setup(bot)

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

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

# from commands.heal import healing
from functions.check_inventory import check_inventory
from functions.item_write import item_write
from functions.load_settings import load_settings, command_prefix, get_prefix, get_embed_color
from functions.cooldown_manager import cooldown_manager_instance
from functions.get_achievement import GetAchievement

from classes.TutorialView import TutorialView

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
from commands.new_hunt import setup as new_hunt_setup

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


bot_settings = {}


# Bot event for when the bot is ready
@bot.event
async def on_ready():
  global bot_settings
  global level_progression_data

  try:
    supabase.table('Users').update({
        'using_command': False
    }).neq('discord_id', 0).execute()
  except Exception as e:
    print(f'An error occurred while resetting using_command field: {e}')

  print(f'Logged in as {bot.user.name}')
  # Loop through all the guilds the bot is a member of
  for guild in bot.guilds:
    if guild is not None:
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
    else:
      server_name = "DMs"
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
    return supabase.table('Players').select('*').eq('discord_id',
                                                    user_id).execute()

  def update_user_exp_and_command_time(new_total_exp):
    return supabase.table('Players').update({
        'total_server_exp':
        new_total_exp,
        'last_message_time':
        datetime.utcnow().isoformat()
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
        'free_points': 0,
        'last_message_time':
        datetime.utcnow().isoformat()  # Initialize with the current time
    }
    return supabase.table('Players').insert(initial_data).execute()

  response = await bot.loop.run_in_executor(None, check_user)

  if response.data:
    # The user exists, so increment their total_exp by 1
    user_data = response.data[0]
    new_total_exp = user_data['total_server_exp'] + 1
    # Update the user's total_exp and last_command_time in the database
    await bot.loop.run_in_executor(None, update_user_exp_and_command_time,
                                   new_total_exp)
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
        'location': 0,
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
    tutorial_embeds = [
        nextcord.Embed(
            title="Welcome, and congratulations! (1/9)",
            description=
            "Apocalypse System Initialized!\n\nIn the greater universe, there exist two primary categories of world. The first and most numerous are systemless worlds, which exist in closed-off bubbles of reality. \n\nThey function in accordance to their own localized physics or magical systems, and their sentient and non-sentient beings survive without any of the system’s balancing effects."
        ),
        nextcord.Embed(
            title="Welcome, and congratulations! (2/9)",
            description=
            "Other, luckier worlds exist. This second category of world has been fully initiated. They live and die by the system rules. \n\nThe system grants beings within its influence strength, yet carefully balances that strength to ensure an even playing field in which various sentient races survive and thrive on their individual merits."
        ),
        nextcord.Embed(
            title="Welcome, and congratulations! (3/9)",
            description=
            "A typical system integration takes place over dozens of generations as the system carefully introduces tweaks, changes, and adjustments meant to nudge a world towards a state in which it can seamlessly function with the greater universe as a whole, like a cog in a well-designed built clock. \n\nBut, as stated, this process takes time. Over every period of time of a certain length, a few lucky planets are selected for integration."
        ),
        nextcord.Embed(
            title="Welcome, and congratulations! (4/9)",
            description=
            "A third category of world, one which does not fit neatly into either category, also exists. Some worlds, by nature of developing further and faster than the system anticipated, delve deeply into forces they cannot fully control. \n\nIn doing so, they breach the containment of their bubble-realities, and trigger the system’s influence to leak in a less gentle and controlled manner."
        ),
        nextcord.Embed(
            title="Welcome, and congratulations! (5/9)",
            description=
            "Due to the fact that this invariably dooms a world in the process, the denizens of the system universe refer to these scenarios as “an apocalypse”. The planet you have known as Earth is doomed. Nothing can stop its destruction. \n\nThe process of its downfall will take time, but whether that time is measured in years, decades, or centuries, the outcome will be the same. Earth will be destroyed, along with everything on it."
        ),
        nextcord.Embed(
            title="Welcome, and congratulations! (6/9)",
            description=
            "It is not, however, the system’s will or intent that this should happen or that your people should vanish. \n\nAs such, certain allowances are made to assure that what made your pocket of reality unique and worthwhile survives."
        ),
        nextcord.Embed(
            title="Welcome, and congratulations! (7/9)",
            description=
            "As a resident of Earth, you have been granted access to The Apocalypse System. This system allows you to augment your body and mind such that your chances of survival increase in the midst of the chaos that is to come. \n\nBut with mayhem is opportunity, and you will find that escape and more waits for those who show themselves worthy of grasping for it."
        ),
        nextcord.Embed(
            title="Welcome, and congratulations! (8/9)",
            description=
            "No official guide for the Apocalypse System exists, nor do you need one. \n\nIt is best learned by trial and error, through experimentation that eventually becomes knowledge and direction."
        ),
        nextcord.Embed(
            title="Welcome, and congratulations! (9/9)",
            description=
            "It is the system’s desire and hope that you will rise above the storm, find strength, and survive. \n\nGood luck!"
        ),
        nextcord.Embed(
            title="System Information",
            description=
            "Use `::help` to find out which commands you can use. \nUse `::help <command>` (without the < >) to find out more about a specific command."
        )
        # Add more embeds as needed...
    ]
    view = TutorialView(ctx, tutorial_embeds)
    await ctx.send(content="Starting tutorial...",
                   embed=tutorial_embeds[0],
                   view=view)
    await view.tutorial_done.wait()  # Wait for the tutorial to finish

    get_achievement_cog = GetAchievement(bot)
    await get_achievement_cog.get_achievement(ctx, ctx.author.id, 1)


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
        "You need administrator permissions to change the settings.\nIf you are in DMs, personal settings aren't implemented yet.\nIs this a bug? Type `::bug <description>` to report it!"
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


#   # Create the embed
#   embed = nextcord.Embed(
#       title="Dungeon Floor 1",
#       description=
#       f"You encountered a {enemy_name}!\nThreat Level: {threat_level}",
#       color=0x1abc9c)
#   embed.set_thumbnail(url=ctx.author.avatar.url)
#   embed.add_field(
#       name=f"{enemy_name}'s Stats",
#       value=
#       f"{enemy_stats['hp']}/{enemy_stats['max_hp']}❤️, {enemy_stats['mp']}/{enemy_stats['max_mp']}💧",
#       inline=False)
#   embed.add_field(
#       name="Your Stats",
#       value=
#       f"{player_stats['hp']}/{player_stats['max_hp']}❤️, {player_stats['mp']}/{player_stats['max_mp']}💧",
#       inline=False)
#   # Add combat stats (icons can be custom emojis or standard emoji characters)
#   embed.add_field(name="⚔️ 46 | 🛡️ 26 | 🌟 18% | 🎯 112%",
#                   value="Player combat stats here",
#                   inline=False)
#   embed.add_field(name="💫 53 | 🌀 26 | ✨ 11% | 🎲 +18",
#                   value="Additional stats or effects",
#                   inline=False)

#   # # Add a separator line
#   # embed.add_field(name="\u200b",
#   #                 value="------------------------------------",
#   #                 inline=False)

#   # # Add combat log
#   # for log in combat_log:
#   #   embed.add_field(name="\u200b", value=log, inline=False)

#   # Send the embed
#   await ctx.send(embed=embed)

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
  new_hunt_setup(bot)
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

  bot.load_extension("commands.titles")
  bot.load_extension("commands.get_title")
  bot.load_extension("commands.heal")
  bot.load_extension("commands.inventory")
  bot.load_extension("commands.profile")
  bot.load_extension("commands.cooldowns")
  bot.load_extension("commands.leaderboard")
  bot.load_extension("commands.changelog")
  bot.load_extension("commands.achievements")
  bot.load_extension("commands.area")

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

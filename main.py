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
from nextcord import Interaction, InteractionResponse
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
from nextcord.ext.commands import CommandNotFound
from difflib import get_close_matches

from bs4 import BeautifulSoup

# Add the directory containing the 'commands' package to sys.path
commands_dir = Path(__file__).parent.resolve()
sys.path.append(str(commands_dir))

# from commands.heal import healing
from functions.check_inventory import check_inventory
from functions.item_write import item_write
from functions.load_settings import load_settings, command_prefix, get_prefix, get_embed_color
import functions.settings_manager
from functions.settings_manager import update_settings_cache_here, get_settings_cache
from functions.cooldown_manager import cooldown_manager_instance
from functions.get_achievement import GetAchievement

from classes.TutorialView import TutorialView
from classes.Player import Player

from commands.website import setup as web_setup
from commands.admin import setup as admin_setup
from commands.help import setup as help_setup
from commands.hunt import setup as hunt_setup
from commands.shop import setup as shop_setup
from commands.gemshop import setup as gemshop_setup
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

from nextcord.ext import tasks


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
      default_settings = {"embed_color": "green", "prefix": "apo "}
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
  global settings_cache

  # try:
  #   supabase.table('Users').update({
  #       'using_command': False
  #   }).neq('discord_id', 0).execute()
  # except Exception as e:
  #   print(f'An error occurred while resetting using_command field: {e}')

  print(f'Logged in as {bot.user.name}')
  # Loop through all the guilds the bot is a member of

  # On bot start, populate the cache with settings from all servers

  for guild in bot.guilds:
    if guild is not None:
      server_name = guild.name
      member_amount = guild.member_count
      server_id = guild.id
      settings = await load_settings(server_id)
      await update_settings_cache(server_id, settings)
      # Check if there is an entry for the guild in the database
      existing = supabase.table('ServerSettings').select('settings').eq(
          'server_id', guild.id).execute()

      # If there is no entry, insert the default settings
      if not existing.data:
        default_settings = {"embed_color": "green", "prefix": "apo "}
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

      settings = await load_settings(server_id)
      bot_settings[server_id] = settings
      #settings_cache[server_id] = settings
      print("--------------------------------------------")
      print(f"\nLoaded settings for guild ID {server_id}")
      print(f"Settings: {settings}" + "\n")
      print("--------------------------------------------")
      await update_settings_cache(server_id, settings)

    else:
      server_name = "DMs"
  print("All guild settings are checked and updated/inserted if necessary.")

  print(f'Logged in as {bot.user.name}')
  # Set the playing status
  game = nextcord.Game("apo start | apo help | apo gemshop")
  await bot.change_presence(activity=game)


class CalibrationView(nextcord.ui.View):

  def __init__(self, ctx, user, attempts=0):
    super().__init__()
    self.ctx = ctx
    self.user = user
    self.attempts = attempts
    self.next_button.disabled = False  # Ensure the button is enabled initially

  @nextcord.ui.button(label="Next", style=nextcord.ButtonStyle.green)
  async def next_button(self, button: nextcord.ui.Button,
                        interaction: nextcord.Interaction):
    self.next_button.disabled = True  # Disable the button to prevent rapid clicks
    try:
      print(self.user)
      await self.user.send(
          "Test DM: Calibration successful! You can now play freely!")
      await self.ctx.channel.send("DM sent successfully!")
      await asyncio.get_event_loop().run_in_executor(
          None, lambda: supabase.table('Users').update({
              'open_dms': True
          }).eq('discord_id', self.user.id).execute())
      self.stop()
    except nextcord.HTTPException as e:
      if e.status == 403:  # Check if the error is a Forbidden error
        if self.attempts < 1:
          self.attempts += 1
          self.next_button.disabled = False  # Re-enable the button for retry
          await self.handle_admin_notification()
          await self.ctx.channel.send(
              "Error sending DM. Please make sure your DMs are open and try again.\nContact <@243351582052188170> for assistance.\nThey have been notified.",
              view=self)

        else:
          await self.handle_admin_notification()
          await self.ctx.channel.send(
              "Unable to send DM. Please contact an admin (<@243351582052188170>) for assistance.\nThey have been notified."
          )
          self.stop()
      elif e.status == 429:  # Check if the error is a rate limit error
        await self.ctx.channel.send(
            "Rate limit exceeded. Please wait a moment before trying again.")
        self.stop()

  async def handle_admin_notification(self):
    try:
      admin_id = 243351582052188170
      admin = await bot.fetch_user(admin_id)
      await admin.send(
          f"User <@{self.user.id}> ({self.user}) in server **{self.ctx.guild}** ({self.ctx.guild.id}) is having issues receiving DMs."
      )
      self.stop()
    except nextcord.HTTPException as e:
      if e.status == 429:
        await self.ctx.channel.send(
            "Too many bad requests. Please contact an admin (<@243351582052188170>) for assistance."
        )
        self.stop()


# Cache for storing the lock state
locked = False


@bot.event
async def on_message(message):
  print("------------------------------------------------")
  # Avoid responding to the bot's own messages
  if message.author == bot.user:
    return

  # Use cached settings
  server_id = message.guild.id if message.guild else None
  if server_id:
    settings = get_settings_cache(server_id)
    if settings:
      operation_channel_id = settings.get('channel_id')

      # Check if the message is in the designated channel
      if operation_channel_id and message.channel.id != operation_channel_id:
        return

  old_prefix = '::'

  prefix = await command_prefix(bot, message)

  if message.content.startswith(old_prefix) and (old_prefix != prefix):
    await message.channel.send(
        f"The prefix `::` has been discontinued. Please use `apo <command>` instead."
    )
    return
  # Ensure 'apo' is always lowercase, but the rest of the message remains as in the original

  backup_message_content = message.content

  # Split the backup_message_content by spaces
  parts = backup_message_content.split(' ')
  # Make the first word lowercase
  parts[0] = parts[0].lower()
  # Make the second word lowercase only if it exists
  if len(parts) > 1:
    parts[1] = parts[1].lower()

  # Rejoin the parts into the modified message content
  backup_message_content = ' '.join(parts)
  print(backup_message_content)

  message.content = message.content.lower()

  if not message.content.startswith(prefix.lower()):
    return

  response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Users').select('*').eq(
          'discord_id', message.author.id).execute())

  if response.data:
    response = response.data[0]

    open_dms = response.get('open_dms', False)
    main_tutorial = response.get('main_tutorial', False)

    if main_tutorial:
      await message.channel.send("Please finish the tutorial!!!")
      return

    if not open_dms and main_tutorial:
      await message.channel.send("Please calibrate your DMs first.")
      await message.channel.send(
          f"<@{message.author.id}> Please make sure you have DMs from server members open on this server, or invite the bot to a personal server and allow it to DM you from there. \n\n**Important notifications will be sent directly as DMs.**\n\n**Mobile:** Simply *long press* the server icon, tap *'More Options'*, and scroll down until you find *'Allow Direct Messages'*. Enable that. \n**Desktop:** https://i.imgur.com/PE797Rv.png"
      )

      # await asyncio.get_event_loop().run_in_executor(
      #     None, lambda: supabase.table('Users').update({
      #         'using_command': True
      #     }).eq('discord_id', message.author.id).execute())

      await message.channel.send(view=CalibrationView(message, message.author))
      return

  # Check if the bot is locked
  if locked and message.author.id != 243351582052188170:
    await message.channel.send(
        ":lock: The bot is currently locked. :lock:\nDon't worry, this usually means some sort of update, or a restart, and it will be unlocked in **`1-3 minutes`**."
    )
    return

  # Remove the prefix from the message and save the command without the prefix to message_content
  # Extract the main command from the message content
  # Extract the command or alias from the message content
  message_content = message.content[len(prefix):].strip().split()[0]
  command_aliases = {
      'a': 'adventure',
      'adv': 'adventure',
      'b': 'buy',
      'p': 'profile',
      'ip': 'img_profile',
      'cd': 'cooldowns',
      'title': 'titles',
      'h': 'hunt',
      '?': 'help',
      'dio': 'help',
      'inv': 'inventory',
      'web': 'website'

      # Add more aliases and their corresponding commands here
  }
  # Replace alias with the main command name if an alias is detected
  message_content = command_aliases.get(message_content, message_content)

  # If the command is executed in a server/guild, add the guild/server name
  server_name = message.guild.name if message.guild else 'DMs'
  server_id = message.guild.id if message.guild else 0

  data = {
      'user_id': message.author.id,
      'user_id_str': f'{message.author.id}',
      'username': message.author.name,
      'command_used': message_content,
      'server_name': server_name,
      'server_id_str': f"{server_id}"
  }
  supabase.table('Log').insert(data).execute()

  message.content = backup_message_content

  # Process commands (if any)
  await bot.process_commands(message)


@bot.event
async def on_interaction(interaction: nextcord.Interaction):
  print("------------------------------------------------")

  # Handling Command Interactions
  if interaction.type == nextcord.InteractionType.application_command:
    # Adapted code for logging interaction data
    command_name = interaction.data[
        'name'] if 'name' in interaction.data else 'unknown_command'

    # If the interaction is executed in a server/guild, add the guild/server name
    server_name = interaction.guild.name if interaction.guild else 'DMs'
    server_id = interaction.guild.id if interaction.guild else 0

    data = {
        'user_id': interaction.user.id,
        'user_id_str': f"{interaction.user.id}",
        'username': interaction.user.name,
        'command_used': command_name,
        'server_name': server_name,
        'server_id_str': f"{server_id}"
    }
    supabase.table('Log').insert(data).execute()

    # Get server ID and cached settings
    server_id = interaction.guild_id
    settings = get_settings_cache(server_id) if server_id else None

    if settings:
      operation_channel_id = settings.get('channel_id')
      # Check if the interaction is in the designated channel
      if operation_channel_id and interaction.channel_id != operation_channel_id:
        await interaction.response.send_message(
            f"This isnt the designated channel. Please use <#{operation_channel_id}>"
        )
        return

    # Check if the bot is locked
    if locked:
      await interaction.response.send_message("The bot is currently locked.")
      return
    # If not locked, continue processing the command
    # Continue with other interaction checks here if necessary

  await bot.process_application_commands(interaction)


# Remember to add a function to update the cache when settings change
async def update_settings_cache(server_id, new_settings):
  update_settings_cache_here(server_id, new_settings)


@bot.event
async def on_command_error(ctx, error):
  # Check if the command was not found
  if isinstance(error, CommandNotFound):
    # Get the invoked command
    invoked_command = ctx.invoked_with

    # Extract a list of all command names
    command_names = [command.name for command in bot.commands]

    # Find the closest match to the invoked command
    closest_match = get_close_matches(invoked_command,
                                      command_names,
                                      n=1,
                                      cutoff=0.6)

    # If a close match was found
    if closest_match:
      # Ask user if they meant the closest matching command
      await ctx.send(
          f"Command '{invoked_command}' not found. Did you mean '{closest_match[0]}'?"
      )
    else:
      prefix = await command_prefix(bot, ctx)
      # If no close match, just inform the user the command was not found
      await ctx.send(
          f"Command '{invoked_command}' not found. Use `{prefix}help` for a list of commands."
      )

  # else:
  #     # If the error is not CommandNotFound, handle other errors (existing error handling logic)
  #     # ...


@bot.command(name="lockdown",
             help="Locks down the bot. Only usable by the bot owner.")
async def lockdown(ctx):
  global locked
  if ctx.author.id == 243351582052188170:
    locked = not locked
    state = "locked" if locked else "unlocked"
    await ctx.send(f":lock: Bot is now {state}.")
  else:
    await ctx.send("You do not have permission to use this command.")


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

  async def insert_new_user():
    print("---------------------------------------")
    print("A NEW HAND HAS TOUTCHED THE BEACON")
    print(f"ALL HAIL THE NEWBIE: {username}")
    print("---------------------------------------")
    admin_id = 243351582052188170
    admin = await bot.fetch_user(admin_id)
    guild = ctx.guild if ctx.guild else "DMs"
    guild_id = ctx.guild.id if ctx.guild else None
    await admin.send(
        f"A NEW HAND HAS TOUTCHED THE BEACON\nALL HAIL THE NEWBIE <@{ctx.author.id}> (**{username}**) JOINING FROM **{guild}** ({guild_id})."
    )
    # Set the initial values for the new user
    initial_data = {
        'discord_id': user_id,
        'discord_str_id': f'{user_id}',
        'username': username,
        'using_command': True
    }
    return supabase.table('Users').insert(initial_data).execute()

  response = await bot.loop.run_in_executor(None, check_user)

  if response.data:
    # The user exists, send a message
    await ctx.send("You have already started the game and your profile exists."
                   )
  else:
    # The user doesn't exist, so add them to the database with initial values
    # await bot.loop.run_in_executor(None, insert_new_user)
    await insert_new_user()
    # Send a message with the tutorial
    tutorial_embeds = [
        nextcord.Embed(title="Welcome, and congratulations!",
                       description="Apocalypse System Initialized!"),
        nextcord.Embed(
            title="Welcome, and congratulations!",
            description=
            "It is the system’s desire and hope that you will rise above the storm, find strength, and survive. \n\nGood luck!"
        ),
        nextcord.Embed(
            title="Profile Information",
            description=
            "After this tutorial, type `apo profile` to open up your character sheet.\nWithin it you will find your stats, which are **💪 STR**, **💨 DEX**, **❤️‍🔥 VIT**, **🧠SAV**, **🪄 MAG**, and **🍀 LUCK**.\n\nThese are your physical and mental stats. The **Free Points:** section indicates how many stat points you can allocate. \n\nEach stat contributes in some way. 💪STR, 🧠SAV and 🪄MAG all contribute to your attack power. 💨DEX and ❤️‍🔥VIT both contribute to your defense, which reduces the damage you take from enemy hits."
        ),
        nextcord.Embed(
            title="Profile Customization",
            description=
            "Now, onto getting your character a face! If you type `apo player_settings`, or `apo psettings` for short, it will open a window giving you two options.\n\nYou can either use your Discord profile picture as your characters picture, or you can choose from a selection of different custom sprites for your character, as well as purchasable backgrounds from the gem shop (`apo gemshop`).\n\nAfter choosing your character and background, simply type `apo img_profile` or `apo ip` for short, and you'll be able to view your new character! It also shows all of the information within the `apo profile` page."
        )
        # Add more embeds as needed...
    ]
    view = TutorialView(ctx, tutorial_embeds, bot)
    await ctx.send(content="Starting tutorial...",
                   embed=tutorial_embeds[0],
                   view=view)
    await view.tutorial_done.wait()  # Wait for the tutorial to finish

    embed = nextcord.Embed(
        color=nextcord.Color.green(),
        title="System Information",
        description=
        "Hunt monsters using `apo hunt`, or adventure with `apo adventure`!\nBrowse the shop using `apo shop` and buy or sell using `apo buy <item>` or `apo sell <item>`!\nCheck your inventory using `apo inventory`!\n\nUse `apo help` to see all the commands you can use. \nUse `apo help <command>` (without the < >) to find out more about a specific command, and to see its aliases (aka for `apo hunt` it is `apo h`)."
    )

    await ctx.send(embed=embed)

    get_achievement_cog = GetAchievement(bot)
    await get_achievement_cog.get_achievement(ctx, ctx.author.id, 1)

    await ctx.send(
        f"<@{ctx.author.id}> Please make sure you have DMs from server members open on this server, or invite the bot to a personal server and allow it to DM you from there. \n\n**Important notifications will be sent directly as DMs.**\n\n**Mobile:** Simply *long press* the server icon, tap *'More Options'*, and scroll down until you find *'Allow Direct Messages'*. Enable that. \n**Desktop:** https://i.imgur.com/PE797Rv.png"
    )
    await ctx.send(view=CalibrationView(ctx, ctx.author))
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Users').update({
            'using_command': False,
            'open_dms': True,
            'main_tutorial': False
        }).eq('discord_id', ctx.author.id).execute())


# Bot command to send a random gif
@bot.command(name="gif",
             aliases=["feed", "play", "sleep"],
             help="Sends a random dog gif.")
async def gif(ctx):
  with open("gifs.json") as f:
    links = json.load(f)
  await ctx.send(random.choice(links[ctx.invoked_with]))


@bot.slash_command(name="gif", description="Sends a random dog gif.")
async def slash_gif(interaction: nextcord.Interaction):
  with open("gifs.json") as f:
    links = json.load(f)
  random_word = random.choice(["feed", "play", "sleep", "gif"])
  await interaction.response.send_message(random.choice(links[random_word]))


class CustomIdModal(nextcord.ui.Modal):

  def __init__(self, title, guild_id):
    super().__init__(title=title)
    self.guild_id = guild_id
    self.add_item(
        nextcord.ui.TextInput(label="New Value",
                              placeholder="Enter a new value here..."))

  async def callback(self, interaction: nextcord.Interaction):
    new_value = self.children[0].value
    # If using a special character to represent space, replace it back to space here
    new_value = new_value.replace('<space>', ' ')
    settings = {}
    if self.title == "Change Prefix":
      settings["prefix"] = new_value
    elif self.title == "Change Embed Color":
      settings["embed_color"] = new_value

    logging.info(f"New settings for guild {self.guild_id}: {settings}")
    await save_settings(self.guild_id, settings)
    await update_settings_cache(self.guild_id, settings)
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
      value=
      f"Current prefix is `{bot_settings.get('prefix', 'apo ')}`\n---\n**To add a space to your prefix use *<space>***",
      inline=True)
  embed.add_field(
      name="Operation Channel",
      value=
      f"Current operation channel is {operation_channel_name}\nUse `{bot_settings.get('prefix', 'apo ')}setchannel <channel>` to change this.",
      inline=True)
  embed.add_field(name="Click the buttons below to change the settings.",
                  value="",
                  inline=False)
  view = View(timeout=60)

  async def change_prefix_callback(interaction: nextcord.Interaction):
    if interaction.user != ctx.author:
      await interaction.response.send_message(
          f"You are not authorized to change the settings. Is this a bug? Type `{bot_settings.get('prefix', 'apo ')}bug <description>` to report it!",
          ephemeral=True)
      return
    modal = CustomIdModal(title="Change Prefix", guild_id=ctx.guild.id)
    await interaction.response.send_modal(modal)

  async def change_color_callback(interaction: nextcord.Interaction):
    if interaction.user != ctx.author:
      await interaction.response.send_message(
          f"You are not authorized to change the settings. Is this a bug? Type `{bot_settings.get('prefix', 'apo ')}bug <description>` to report it!",
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
        "You need administrator permissions to change the settings.\nIf you are in DMs, personal settings aren't implemented yet.\nIs this a bug? Type `apo bug <description>` to report it!"
    )


@bot.command(name="setchannel",
             help="Sets a specific channel for the bot to operate in.")
@has_permissions(administrator=True)
async def setchannel(ctx, channel: nextcord.TextChannel = None):
  server_id = ctx.guild.id
  new_settings = await load_settings(server_id)

  if channel is None:
    # Clear the operation channel setting
    await save_settings(server_id, {'channel_id': None})
    new_settings['channel_id'] = None
    await ctx.send(
        "Bot operation channel has been cleared. The bot will now operate in all channels."
    )
  else:
    # Set the new operation channel
    new_settings['channel_id'] = channel.id
    await save_settings(server_id, {'channel_id': channel.id})
    await update_settings_cache(server_id, new_settings)
    await ctx.send(f"Bot operation channel set to {channel.mention}")


# Error handling for the setchannel command
@setchannel.error
async def setchannel_error(ctx, error):
  if isinstance(error, commands.MissingPermissions):
    await ctx.send("You need administrator permissions to change the settings."
                   )


previous_data = {}


@tasks.loop(hours=24)
async def scrape_and_send_data():
  # This function runs every 24 hours at 1pm GMT
  current_time = datetime.utcnow()
  if current_time.hour == 13:  # Check if it's 1pm GMT
    print("Scraping and sending data...")
    user_1_id = 243351582052188170  # Replace with the actual user ID
    user_2_id = 1115808407446880336

    fiction_ids = [77238, 71319]
    for fiction_id in fiction_ids:
      print(f"Scraping data for fiction ID: {fiction_id}")
      url = f'https://www.royalroad.com/fiction/{fiction_id}/'
      response = requests.get(url)

      if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        data_elements = soup.find_all('li',
                                      class_='bold uppercase font-red-sunglo')
        data_values = [element.text.strip() for element in data_elements]
        data_keys = [
            'TOTAL VIEWS', 'AVERAGE VIEWS', 'FOLLOWERS', 'FAVORITES',
            'RATINGS', 'PAGES'
        ]
        data = dict(zip(data_keys, data_values))

        # Extract the title
        title_element = soup.find('h1', class_='font-white')
        if title_element:
          title_text = title_element.text.strip()
          data['TITLE'] = title_text
        else:
          data['TITLE'] = 'Title not found'

        print(f"Data for fiction ID {fiction_id}: {data}")

        embed = Embed(title=f'{data["TITLE"]} - Statistics',
                      color=nextcord.Color.blue())

        embed.add_field(
            name='-----------------------------------------------------------',
            value="",
            inline=False)

        embed.add_field(name='', value="", inline=True)

        overall_score_element = soup.find('li',
                                          class_='bold uppercase list-item',
                                          text='Overall Score')
        if overall_score_element:
          overall_score_span = overall_score_element.find_next_sibling(
              'li').find('span', class_='popovers')
          overall_score = overall_score_span[
              'data-content'] if overall_score_span else 'N/A'
          overall_score = overall_score.split('/')[0].strip()
          embed.add_field(name='OVERALL SCORE',
                          value=overall_score,
                          inline=True)

        embed.add_field(name='', value="", inline=True)

        embed.add_field(
            name='-----------------------------------------------------------',
            value="",
            inline=False)

        for key, value in data.items():

          # Skip processing for the TITLE key
          if key == "TITLE":
            continue

          embed.add_field(name=key, value=value, inline=True)

        embed.add_field(
            name='-----------------------------------------------------------',
            value="",
            inline=False)

        data['OVERALL SCORE'] = overall_score

        # Check if the text file exists, if not, create it
        if not os.path.exists(f'fic_data/scraped_data_{fiction_id}.txt'):
          with open(f'fic_data/scraped_data_{fiction_id}.txt', 'w') as file:
            file.write('{}')  # Create an empty JSON object in the file

        # Load previous data from the text file
        with open(f'fic_data/scraped_data_{fiction_id}.txt', 'r') as file:
          previous_data = json.load(file)

        # Prepare the message for Slack
        slack_message = [f"*{data['TITLE']} - Statistics*"]
        slack_message.append("--------------------------------------")
        for key, value in data.items():
          # Skip processing for the TITLE key
          if key == "TITLE":
            continue
          slack_message.append(f"* *{key}*: {value}")

        slack_message.append("--------------------------------------")

        # Compare the new data with the previous data and add fields to the embed for changes
        change = 0
        for key in data:
          if key in previous_data and data[key] != previous_data[key]:
            previous_value = previous_data[key]
            current_value = data[key]
            try:
              # Convert values to numbers for comparison
              previous_number = int(previous_value.replace(',', ''))
              current_number = int(current_value.replace(',', ''))
              change = current_number - previous_number
              if change > 0:
                slack_message.append(f"*{key}* - *INCREASE*: +{change}")
                embed.add_field(name=f'{key} - INCREASE',
                                value=f'Up by: {change}',
                                inline=False)
              elif change < 0:
                slack_message.append(f"*{key}* - *DECREASE*: -{abs(change)}")
                embed.add_field(name=f'{key} - DECREASE',
                                value=f'Down by: {abs(change)}',
                                inline=False)
            except ValueError:
              # Handle non-numeric data (like OVERALL SCORE)
              if previous_value != current_value:
                slack_message.append(
                    f"{key} - *CHANGE*: {previous_value} -> {current_value}")
                embed.add_field(name=f'{key} - CHANGE',
                                value=f'{previous_value} -> {current_value}',
                                inline=False)
        if change != 0:
          slack_message.append("--------------------------------------")
        # Save new data to text file
        with open(f'fic_data/scraped_data_{fiction_id}.txt', 'w') as file:
          file.write(json.dumps(data, indent=4))

        fields = []

        fields.append({
            "title": "",
            "value": "\n".join(slack_message),
            "short":
            False  # Set to False if you want each field in its own line
        })

        attachment = [{
            "color": "#36a64f",  # Can be any hex color code
            "title": "",
            "fields": fields
        }]

        # Send message to Slack via webhook
        webhook_url = "https://hooks.slack.com/services/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"
        payload = {"text": "", "attachments": attachment}
        response = requests.post(webhook_url, json=payload)
        if response.status_code != 200:
          print(
              f"Error sending message to Slack: {response.status_code} {response.text}"
          )

        user1 = await bot.fetch_user(user_1_id)
        user2 = await bot.fetch_user(user_2_id)
        await user1.send(embed=embed)

        await asyncio.sleep(10)

        await user2.send(embed=embed)

        await asyncio.sleep(10)
      else:
        print('Failed to retrieve the webpage')


@scrape_and_send_data.before_loop
async def before_scheduled_task():
  await bot.wait_until_ready()
  current_time = datetime.utcnow()
  target_time = current_time.replace(hour=13,
                                     minute=0,
                                     second=0,
                                     microsecond=0)
  if current_time.hour >= 13:  # If it's past 1pm GMT, schedule for the next day
    target_time += timedelta(days=1)
  seconds_until_start = (target_time - current_time).total_seconds()
  print("TIME UNTIL START: ", seconds_until_start)
  await asyncio.sleep(seconds_until_start)


scrape_and_send_data.start()

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
  # new_hunt_setup(bot)
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
  gemshop_setup(bot)

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
  bot.load_extension("commands.(slash) adventure")
  bot.load_extension("commands.(slash) heal")
  bot.load_extension("commands.(slash) suggest")

  bot.load_extension("commands.img_profile")
  bot.load_extension("commands.profile_settings")
  bot.load_extension("commands.recipes")
  bot.load_extension("commands.daily")
  bot.load_extension("commands.status")
  bot.load_extension("commands.skill")
  bot.load_extension("commands.replicateAIcmd")

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

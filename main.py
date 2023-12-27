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
  global settings_cache

  try:
    supabase.table('Users').update({
        'using_command': False
    }).neq('discord_id', 0).execute()
  except Exception as e:
    print(f'An error occurred while resetting using_command field: {e}')

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
  game = nextcord.Game("::start | ::help | ::shop")
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
          "Test DM: Calibration successful! Welcome to the game, you are now ready."
      )
      await self.ctx.channel.send("DM sent successfully. You are ready to go!")
      await asyncio.get_event_loop().run_in_executor(
          None, lambda: supabase.table('Users').update({
              'using_command': False,
              'open_dms': True
          }).eq('discord_id', self.user.id).execute())
      self.stop()
    except nextcord.HTTPException as e:
      if e.status == 403:  # Check if the error is a Forbidden error
        if self.attempts < 2:
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

  prefix = await command_prefix(bot, message)
  if not message.content.startswith(prefix):
    return

  response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Users').select('open_dms').eq(
          'discord_id', message.author.id).execute())

  if response.data:
    response = response.data[0]

    open_dms = response.get('open_dms', False)

    if not open_dms:
      await message.channel.send("Please calibrate your DMs first.")
      await message.channel.send(
          f"<@{message.author.id}> Please make sure you have DMs from server members open on this server, or invite the bot to a personal server and allow it to DM you from there. \n\n**Important notifications will be sent directly as DMs.**\n\n**Mobile:** Simply *long press* the server icon, tap *'More Options'*, and scroll down until you find *'Allow Direct Messages'*. Enable that. \n**Desktop:** https://i.imgur.com/PE797Rv.png"
      )

      await asyncio.get_event_loop().run_in_executor(
          None, lambda: supabase.table('Users').update({
              'using_command': True
          }).eq('discord_id', message.author.id).execute())

      await message.channel.send(view=CalibrationView(message, message.author))
      return

  # Check if the bot is locked
  if locked and message.author.id != 243351582052188170:
    await message.channel.send("The bot is currently locked.")
    return

  # Process commands (if any)
  await bot.process_commands(message)


@bot.event
async def on_interaction(interaction: nextcord.Interaction):
  print("------------------------------------------------")

  # Handling Command Interactions
  if interaction.type == nextcord.InteractionType.application_command:
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


@bot.command(name="lockdown",
             help="Locks down the bot. Only usable by the bot owner.")
async def lockdown(ctx):
  global locked
  if ctx.author.id == 243351582052188170:
    locked = not locked
    state = "locked" if locked else "unlocked"
    await ctx.send(f"Bot is now {state}.")
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

    await ctx.send(
        f"<@{ctx.author.id}> Please make sure you have DMs from server members open on this server, or invite the bot to a personal server and allow it to DM you from there. \n\n**Important notifications will be sent directly as DMs.**\n\n**Mobile:** Simply *long press* the server icon, tap *'More Options'*, and scroll down until you find *'Allow Direct Messages'*. Enable that. \n**Desktop:** https://i.imgur.com/PE797Rv.png"
    )
    await ctx.send(view=CalibrationView(ctx, ctx.author))
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Users').update({
            'using_command': False,
            'open_dms': True
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
async def slash_gif(ctx):
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

import asyncio
import os
import requests
import json
import random
from dotenv import load_dotenv
import nextcord
from nextcord.ext import commands, tasks
from nextcord.ext.commands import has_permissions
from nextcord import SelectOption
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

load_dotenv()

logging.basicConfig(level=logging.INFO)


async def command_prefix(bot, message):
  # Get the server ID from the message
  guild_id = message.guild.id if message.guild else None  # DMs do not have a guild

  if guild_id:
    # Query the prefix setting from the Supabase for the specific guild
    response = supabase.table('ServerSettings').select('settings').eq(
        'server_id', guild_id).execute()
    if response.data:
      settings = response.data[0]['settings']
      return settings.get('prefix', '::')  # Default to '::' if not found
  return '::'  # Default to '::' if we are in DMs or if the guild_id is not found


intents = nextcord.Intents.default()
intents.message_content = True


async def get_prefix(bot, message):
  # This is your previously defined async function to get the prefix
  prefix = await command_prefix(bot, message)
  return prefix


# When you instantiate your bot, use the following lambda for the command_prefix
bot = commands.Bot(command_prefix=command_prefix,
                   intents=intents,
                   help_command=None)


async def load_settings(server_id: int):
  response = supabase.table('ServerSettings').select('settings').eq(
      'server_id', server_id).execute()
  if response.data:
    return response.data[0]['settings']
  else:
    # If there are no settings for this server, return some defaults
    return {'embed_color': 'green', 'prefix': '::'}


async def load_level_progression():
  async with aiofiles.open('level_progression.json', 'r') as f:
    data = await f.read()
    return json.loads(data)


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
      await supabase.table('ServerSettings').update({
          'settings':
          updated_settings
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


async def get_embed_color(guild_id: int):
  # Query the embed_color setting from the Supabase for the specific guild
  response = supabase.table('ServerSettings').select('settings').eq(
      'server_id', guild_id).execute()

  if response.data:
    settings = response.data[0]['settings']
    color_name = settings.get('embed_color', 'green')
  else:
    color_name = 'green'  # Default to green if not found

  # Use getattr to get the nextcord.Color method corresponding to the color_name
  color_method = getattr(nextcord.Color, color_name.lower(),
                         nextcord.Color.green)
  # Call the method to get the color object
  return color_method()


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
    level_progression_data = await load_level_progression()
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
    return supabase.table('Players').select('total_exp').eq(
        'discord_id', user_id).execute()

  def update_user_exp(new_total_exp):
    return supabase.table('Players').update({
        'total_exp': new_total_exp
    }).eq('discord_id', user_id).execute()

  def insert_new_user():
    initial_data = {
        'discord_id': user_id,
        'username': username,
        'health': 100,
        'max_health': 100,
        'level': 1,
        'level_exp': 0,
        'total_exp': 0,
        'adventure_rank': 0,
        'adventure_exp': 0,
        'adventure_total_exp': 0,
        'atk': 1,
        'def': 1,
        'magic': 1,
        'magic_def': 1,
        'bal': 100,
        'floor': 1
    }
    return supabase.table('Players').insert(initial_data).execute()

  response = await bot.loop.run_in_executor(None, check_user)

  if response.data:
    # The user exists, so increment their total_exp by 1
    user_data = response.data[0]
    new_total_exp = user_data['total_exp'] + 1
    # Update the user's total_exp in the database
    await bot.loop.run_in_executor(None, update_user_exp, new_total_exp)
  else:
    # The user doesn't exist, so add them to the database with initial values
    await bot.loop.run_in_executor(None, insert_new_user)

  # Process commands (if any)
  await bot.process_commands(message)


# Bot command to send a hello message
@bot.command(name="hi", help="Sends a hello message.")
async def send_message(ctx):
  await ctx.send('Hello!')


# Bot command to send a hello message
@bot.command(name="use", help="Use an item. (UNDER CONSTRUCTION)")
async def use(ctx):
  await ctx.send('"use" doesnt work for now, please use heal!')


# Bot command to send a hello message
@bot.command(name="shop", help="The shop. (UNDER CONSTRUCTION)")
async def shop(ctx):
  await ctx.send(
      'The shop doesnt work yet. Please use `buy health potion` for health.')


@bot.command(name="website",
             aliases=["web", "site"],
             help="The bot's website.")
async def website(ctx):
  await ctx.send('# [Magi RPG website](https://magi-bot.tyrthurey.repl.co/)')


# Bot command to send a hello message
@bot.command(name="admin", help="Makes you an admin!")
async def admin(ctx):
  await ctx.send('Nope, nice try tho!')


# Bot command to send a random dog picture
@bot.command(name="dog", help="Sends a random dog pic.")
async def dog(ctx):
  async with aiohttp.ClientSession() as session:
    async with session.get(
        "https://dog.ceo/api/breeds/image/random") as response:
      if response.status == 200:
        data = await response.json()
        image_link = data.get("message", "No image found.")
        await ctx.send(image_link)
      else:
        await ctx.send("Couldn't fetch a dog image. :(")


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


@bot.command(name="help", aliases=["?"], help="Self explanatory :P")
async def help_command(ctx):
  # Fetch the embed color from settings
  embed_color = await get_embed_color(ctx.guild.id)

  embed = nextcord.Embed(title='Help Menu', color=embed_color)

  embed.set_footer(text=bot.user.name, icon_url=bot.user.avatar.url)
  for command in bot.commands:
    if command.hidden:
      continue

    # Await the command_prefix coroutine here for each command
    command_prefix_str = await command_prefix(bot, ctx.message)
    command_name = f"{command_prefix_str}{command.name}"
    help_text = command.help or "No description provided."

    if command.aliases:
      aliases = ", ".join(
          [f"{command_prefix_str}{alias}" for alias in command.aliases])
      help_text += f"\n*Aliases: {aliases}*"

    embed.add_field(name=command_name, value=help_text, inline=False)

  await ctx.send(embed=embed)


@bot.command(name="hunt",
             aliases=["h", "hunting"],
             help="Go on a hunting adventure and gain experience.")
@commands.cooldown(1, 60,
                   BucketType.user)  # Cooldown: 1 time per 60 seconds per user
async def hunting(ctx):
  user_id = ctx.author.id

  # Retrieve the current user data
  user_data_response = supabase.table('Players').select('*').eq(
      'discord_id', user_id).execute()
  if not user_data_response.data:
    await ctx.send("You do not have a profile yet.")
    return

  user_data = user_data_response.data[0]
  current_health = user_data['health']
  max_health = user_data['max_health']
  current_exp = user_data['adventure_exp']
  user_level = user_data['level']
  user_gold = user_data['bal']

  # Calculate the health reduction and gold reward
  health_loss_percentage = random.randint(40, 80)
  health_loss = math.floor(health_loss_percentage / 100 * max_health)
  gold_reward = random.randint(10, 40)
  new_health = current_health - health_loss

  # Check if the user "dies"
  if new_health <= 0:
    new_health = max_health  # Reset health to max if died
    new_level = max(1, user_level - 1)  # Ensure level does not go below 1
    new_exp = 0
    gold_loss = random.randint(10, 30)
    user_gold = max(0, user_gold - math.floor(
        gold_loss / 100 * user_gold))  # Ensure gold does not go below 0
    lost_atk = max(1, user_data['atk'] - 1)
    lost_def = max(1, user_data['def'] - 1)
    lost_magic = max(1, user_data['magic'] - 1)
    lost_magic_def = max(1, user_data['magic_def'] - 1)
    lost_max_health = max(100, max_health - 5)

    # Update the player's health, level, adventure_exp, and gold in the database
    supabase.table('Players').update({
        'health': new_health,
        'level': new_level,
        'adventure_exp': new_exp,
        'bal': user_gold,
        'atk': lost_atk,
        'def': lost_def,
        'magic': lost_magic,
        'magic_def': lost_magic_def,
        'max_health': lost_max_health
    }).eq('discord_id', user_id).execute()

    # Inform the user that they "died"
    await ctx.send(
        f"You have died during the hunt, when you got hit for `{health_loss}` HP.\n"
        f"You lost all rewards, including `1` level and `{gold_loss}`% of your gold."
    )
    return
  else:
    # Calculate the experience gained
    additional_exp = random.randint(
        10, 20) + (user_level - 1) * random.randint(3, 8)
    new_exp = current_exp + additional_exp

    # Initialize stat increases to 0
    additional_atk = 0
    additional_def = 0
    additional_magic = 0
    additional_max_health = 0

    # Check for level up
    needed_exp_for_next_level = level_progression_data['levels'].get(
        str(user_level + 1), {}).get('total_level_exp', float('inf'))
    level_up = new_exp >= needed_exp_for_next_level

    if level_up:
      new_level = user_level + 1
      new_exp -= needed_exp_for_next_level  # Reset exp to 0 for next level
      # Increase stats
      additional_atk = 1
      additional_def = 1
      additional_magic = 1
      additional_magic_def = 1
      additional_max_health = 5
      new_max_health = max_health + additional_max_health

    # Update the player's health, adventure_exp, and gold in the database
    update_response = supabase.table('Players').update({
        'health':
        max(1, new_health),  # Ensure health does not go below 1
        'adventure_exp':
        new_exp,
        'level':
        new_level if level_up else user_level,
        'bal':
        user_gold + gold_reward,
        # Only update these if there's a level up
        **({
            'atk': user_data['atk'] + additional_atk,
            'def': user_data['def'] + additional_def,
            'magic': user_data['magic'] + additional_magic,
            'magic_def': user_data['magic_def'] + additional_magic_def,
            'max_health': new_max_health
        } if level_up else {})
    }).eq('discord_id', user_id).execute()

    # Inform the user of the outcome of the hunt
    if level_up:
      await ctx.send(
          f"**{ctx.author}** killed some :skull: **SKELETONS**! \n"
          f"Gained `{additional_exp}`EXP, and `{gold_reward}` gold! \n"
          f"Lost `{health_loss}`HP. Current Health: `{max(1, new_health)}/{new_max_health}`HP. \n"
          f":arrow_up: Level Up to lvl `{new_level}`! New Stats: ATK: `{user_data['atk'] + additional_atk}`, "
          f"DEF: `{user_data['def'] + additional_def}`, MAGIC: `{user_data['magic'] + additional_magic}`, "
          f"MAGIC DEF: `{user_data['magic_def'] + additional_magic_def}`"
          f"Health: `{new_max_health}`HP!")
    else:
      await ctx.send(
          f"**{ctx.author}** killed some :skull: **SKELETONS**! \n"
          f"Gained `{additional_exp}`EXP, and `{gold_reward}` gold! \n"
          f"Lost `{health_loss}`HP. Current Health: `{max(1, new_health)}/{max_health}`HP."
      )


# Error handling for the hunting command
@hunting.error
async def hunting_error(ctx, error):
  if isinstance(error, commands.CommandOnCooldown):
    # Cooldown is in effect; let the user know how much time is left
    await ctx.send(
        f"This command is on cooldown.\nYou can use it again in `{error.retry_after:.2f}` seconds."
    )
  else:
    # Handle other potential errors
    await ctx.send(f"An error occurred: {error}")


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

  # Check if the user has a profile
  if not response.data:
    await ctx.send(f"{username} does not have a profile yet.")
    return

  user_data = response.data[0]  # User data from the database

  # Use the loaded level progression data to get the total_adv_level_exp for the user's current level
  user_level = str(user_data['level'] +
                   1)  # Ensure it's a string to match the JSON keys
  needed_adv_level_exp = level_progression_data['levels'][user_level][
      'total_level_exp']

  # Create the embed with the updated user data
  embed = nextcord.Embed(title="Rookie Adventurer", color=embed_color)
  embed.set_author(name=f"{username}'s Profile", icon_url=avatar_url)

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
                  f"**MAGIC DEF:** {user_data['magic_def']}\n",
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
  results = supabase.table('Players').select('*').order(
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
async def cooldowns(ctx):
  embed_color = await get_embed_color(ctx.guild.id)
  # Fetch the prefix from Supabase for the current guild
  guild_settings = await load_settings(ctx.guild.id)
  guild_prefix = guild_settings.get(
      'prefix', '::')  # Use the default prefix if not found in the settings

  embed = nextcord.Embed(title='Cooldowns', color=embed_color)
  embed.set_author(name=ctx.author.display_name,
                   icon_url=ctx.author.avatar.url
                   if ctx.author.avatar else ctx.author.default_avatar.url)

  # Loop through all commands
  for command in bot.commands:
    # Skip if the command is hidden or does not have a cooldown
    if command.hidden or not hasattr(command._buckets, '_cooldown'):
      continue

    # Get the bucket for the command
    bucket = command._buckets.get_bucket(ctx.message)

    # Check if there's a cooldown to report
    if bucket and bucket.get_tokens() < bucket.rate:
      retry_after = bucket.get_retry_after()
      if retry_after:
        # Command is on cooldown
        minutes, seconds = divmod(int(retry_after), 60)
        hours, minutes = divmod(minutes, 60)
        cooldown_message = f":x: {hours}h {minutes}m {seconds}s remaining"
        # Add the command and its cooldown status to the embed
        embed.add_field(name=f"{guild_prefix}{command.name}",
                        value=f"{cooldown_message}",
                        inline=False)

  # If the embed has no fields, it means no commands are on cooldown
  if len(embed.fields) == 0:
    embed.description = "No commands on cooldown!"

  # Send the embed
  await ctx.send(embed=embed)


@bot.command(name="inventory",
             aliases=["inv"],
             help="Displays the user's inventory.")
async def inventory(ctx):
  embed_color = await get_embed_color(ctx.guild.id)
  user_id = ctx.author.id
  username = ctx.author.display_name
  avatar_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url

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


# Buy command
@bot.command(name="buy", help="Buys an item from the shop.")
async def buy(ctx, *args):
  # Check if at least the item name is provided
  if not args:
    await ctx.send("Usage: ::buy [item display name] [amount]")
    return

  # Check if the last argument is an integer (the amount), and if not, default the amount to 1
  try:
    amount = int(args[-1])
    if amount <= 0:
      raise ValueError
    item_display_name = " ".join(args[:-1]).lower()
  except ValueError:  # Last argument is not an integer, so we assume it's part of the item name
    amount = 1
    item_display_name = " ".join(args).lower()

  # Lookup item ID, price, and other necessary details from the Items table
  item_response = await bot.loop.run_in_executor(
      None, lambda: supabase.table('Items').select('*').ilike(
          'item_displayname', f'%{item_display_name}%').execute())

  if not item_response.data:
    await ctx.send("Item not found or amount invalid.")
    return

  item_data = item_response.data[0]
  ITEM_ID = item_data['item_id']
  ITEM_COST = item_data[
      'price'] * amount  # Now we use the price from the Items table

  user_id = ctx.author.id
  # Check user's balance
  balance_response = await bot.loop.run_in_executor(
      None, lambda: supabase.table('Players').select('bal').eq(
          'discord_id', user_id).execute())

  if balance_response.data:
    balance = balance_response.data[0]['bal']
    if balance < ITEM_COST:
      await ctx.send(
          f"You don't have enough gold to buy this.\n It costs `{ITEM_COST}` Gold."
      )
    else:
      # Deduct cost from balance
      new_balance = balance - ITEM_COST
      # Update the player's balance
      await bot.loop.run_in_executor(
          None, lambda: supabase.table('Players').update({
              'bal': new_balance
          }).eq('discord_id', user_id).execute())

      # Update inventory using the item_write function
      await item_write(user_id, ITEM_ID, amount)

      await ctx.send(
          f"You have successfully bought `{amount}` **{item_data['item_displayname']}**(s) for `{ITEM_COST}` Gold."
      )
  else:
    await ctx.send("You do not have a profile yet.")


@bot.command(name="heal", help="Heals you using a Healing Potion.")
async def heal(ctx):
  # Call the imported `healing` function
  heal_message = await healing(ctx.author.id)
  await ctx.send(heal_message)


"""
@bot.command(name="use", help="Uses an item.")
async def use(ctx, *, item: str):
  ITEM_NAME = 'health_potion'
  ITEM_ID = 1  # As per your Health Potion data

  if item.lower() != 'health potion':
    await ctx.send("You don't have that item to use.")
    return

  user_id = ctx.author.id

  # Get the user's health and max_health
  player_response = await bot.loop.run_in_executor(
      None,
      lambda: supabase.table('Players').select('health', 'max_health').eq(
          'discord_id', user_id).execute())

  if player_response.data:
    player_data = player_response.data[0]
    current_health = player_data['health']
    max_health = player_data['max_health']

    if current_health < max_health:
      # Check if the user has a health potion in inventory
      inventory_response = await bot.loop.run_in_executor(
          None, lambda: supabase.table('Inventory').select('quantity').eq(
              'item_id', ITEM_ID).eq('discord_id', user_id).execute())

      if inventory_response.data[0]['quantity'] > 0:
        # Decrease the potion count by one
        new_quantity = inventory_response.data[0]['quantity'] - 1
        await bot.loop.run_in_executor(
            None,
            lambda: supabase.table('Inventory').update({
                'quantity': new_quantity
            }).eq('item_id', ITEM_ID).eq('discord_id', user_id).execute())

        # Update the player's health to max_health
        await bot.loop.run_in_executor(
            None, lambda: supabase.table('Players').update({
                'health': max_health
            }).eq('discord_id', user_id).execute())

        await ctx.send(
            "You've used a health potion and your health is now full!")
      else:
        await ctx.send("You don't have any health potions.")
    else:
      await ctx.send("Your health is already full.")
  else:
    await ctx.send("You do not have a profile yet.")
"""

# No touch beyond this point

try:
  url = os.getenv("SUPABASE_URL") or ""
  key = os.getenv("SUPABASE_KEY") or ""
  supabase: Client = create_client(url, key)

  token = os.getenv("TOKEN") or ""
  if token == "":
    raise Exception("Please add your token to the .env file.")
    # Call this before you run your bot

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

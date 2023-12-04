import asyncio
from datetime import datetime
import nextcord
from nextcord.ui import Button, View
from nextcord.ext import commands
from main import bot, supabase  # Import necessary objects from your project
from functions.load_settings import get_embed_color
from classes.Player import Player
from functions.get_achievement import GetAchievement
from PIL import Image, ImageDraw, ImageFont
import os
from io import BytesIO
import requests


def draw_centered_text(draw, text, position, font, fill_color):
  # Get the width of the text to be drawn
  text_width = draw.textlength(text, font=font)

  # Calculate the x position of the text's start point (y remains the same)
  x = position[0] - text_width / 2
  y = position[1]

  # Draw the text
  draw.text((x, y), text, font=font, fill=fill_color)


async def create_profile_image(ctx, profile_data):
  # Load the profile image template
  template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'resources', 'profile_template.png')
  image = Image.open(template_path)
  draw = ImageDraw.Draw(image)

  # Define the font path relative to the resources folder
  font_filename = "enso.ttf"
  font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'resources', font_filename)
  font_size = 40
  font = ImageFont.truetype(font_path, font_size)

  # Define text positions (you'll need to adjust these)
  center_positions = {
      'title': (354, 55)
      # Add all other fields you want to include
  }

  # Draw text for each field in profile_data
  for field, center_position in center_positions.items():
    text = str(profile_data.get(field, ''))
    draw_centered_text(draw, text, center_position, font, fill_color='black')

  font_size = 30
  font = ImageFont.truetype(font_path, font_size)

  # Define text positions (you'll need to adjust these)
  center_positions = {
      'username': (354, 124)
      # Add all other fields you want to include
  }
  positions = {'level': (395, 508)}

  # Draw text for each field in profile_data
  for field, center_position in center_positions.items():
    text = str(profile_data.get(field, ''))
    draw_centered_text(draw, text, center_position, font, fill_color='black')

  # Draw text for each field in profile_data
  for field, (x, y) in positions.items():
    value = str(profile_data.get(field, ''))
    draw.text((x, y), value, font=font, fill='black')

  font_size = 20
  font = ImageFont.truetype(font_path, font_size)

  center_positions = {
      'adventure_exp': (335, 577),
      'dash': (370, 577),
      'needed_adv_level_exp': (415, 577),
      'location': (120, 565),
      'class': (354, 547),
      'vitality': (175, 189),
      'dexterity': (140, 243),
      'strength': (122, 301),
      'cunning': (125, 357),
      'magic': (145, 412),
      'luck': (185, 468),
      'atk': (565, 565),
      'dash2': (592, 565),
      'def': (625, 565)
  }

  positions = {
      'gold': (595, 240),
      'stat_score': (615, 469),
      'free_points': (635, 189),
      'health': (610, 300),
      # 'max_health': (610, 307),
      'energy': (612, 355),
      # 'max_energy': (620, 365),
  }

  # Draw text for each field in profile_data
  for field, center_position in center_positions.items():
    text = str(profile_data.get(field, ''))
    draw_centered_text(draw, text, center_position, font, fill_color='black')

  # Draw text for each field in profile_data
  for field, (x, y) in positions.items():
    value = str(profile_data.get(field, ''))
    draw.text((x, y), value, font=font, fill='black')

  # Save to a bytes buffer
  buffer = BytesIO()
  image.save(buffer, format='PNG')
  buffer.seek(0)  # Move to the start of the buffer

  # Send the image to the channel
  file = nextcord.File(fp=buffer, filename='profile.png')
  await ctx.send(file=file)


class IMGProfile(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  last_profile_views = {}

  # New function to get location name
  async def get_location_name(self, location_id):
    location_response = await bot.loop.run_in_executor(
        None, lambda: supabase.table('Areas').select('name').eq(
            'id', location_id).execute())
    return location_response.data[0][
        'name'] if location_response.data else 'Unknown'

  @commands.command(
      name="img_profile",
      aliases=["ip", "imgp", "imgprof"],
      help=
      "Displays the user's or another user's game profile. BUT IN IMAGE STYLE BABYYY"
  )
  async def profile(self, ctx, *, user: nextcord.User = None):
    embed_color = await get_embed_color(
        None if ctx.guild is None else ctx.guild.id)

    # If no user is specified, show the profile of the author of the message
    if user is None:
      user = ctx.author

    user_id = user.id
    username = user.display_name
    avatar_url = user.avatar.url if user.avatar else user.default_avatar.url

    # Create a Player instance for the user
    player = Player(user)

    # If the player does not exist in the database yet
    if not player.exists:
      await ctx.send(
          f"{ctx.author} does not have a profile yet.\nPlease type `::start`.")
      return

    # Fetch the user's next level progression data
    level_progression_response = await bot.loop.run_in_executor(
        None, lambda: supabase.table('LevelProgression').select('*').eq(
            'level', player.level + 1).execute())
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

    location = player.location
    location_name = await self.get_location_name(location)

    get_achievement_cog = GetAchievement(self.bot)

    # Define the profile data
    profile_data = {
        'username': username,
        'level': player.level,
        'adventure_exp': player.adventure_exp,
        'dash': "/",
        'needed_adv_level_exp': needed_adv_level_exp,
        'gold': player.bal,
        'location': location_name,
        'class': player.class_displayname,
        'atk': player.damage,
        'dash2': "/",
        'def': player.defense,
        'health': player.health,
        'dash3': "/",
        'max_health': player.max_health,
        'energy': player.energy,
        'dash4': "/",
        'max_energy': player.max_energy,
        'strength': player.strength,
        'dexterity': player.dexterity,
        'vitality': player.vitality,
        'cunning': player.cunning,
        'magic': player.magic,
        'luck': player.luck,
        'stat_score': player.stat_score,
        'free_points': player.free_points,
        'title': user_title,
        # Add all other fields you want to include
    }

    # Call the function with the context and profile data
    await create_profile_image(ctx, profile_data)

    # # Send the embed and store the view and message in the dictionary
    # message = await ctx.send(embed=embed, view=view)
    # if view:
    #   view.message = message  # Store the message in the view
    #   self.last_profile_views[ctx.author.id] = view

    get_achievement_cog = GetAchievement(self.bot)
    await get_achievement_cog.get_achievement(ctx, ctx.author.id, 4)

  # @profile.error
  # async def profile_error(self, ctx, error):
  #   if isinstance(error, nextcord.ext.commands.errors.BadArgument):
  #     await ctx.send("Couldn't find that user.")


def setup(bot):
  bot.add_cog(IMGProfile(bot))

import asyncio
from datetime import datetime
import nextcord
from nextcord.ui import Button, View
from nextcord.ext import commands
from main import bot, supabase  # Import necessary objects from your project
from functions.load_settings import get_embed_color
from classes.Player import Player
from functions.get_achievement import GetAchievement
from PIL import Image, ImageDraw, ImageFont, ImageOps
import os
from io import BytesIO
import requests
import json


def draw_centered_text(draw, text, position, font, fill_color):
  # Get the width of the text to be drawn
  text_width = draw.textlength(text, font=font)

  # Calculate the x position of the text's start point (y remains the same)
  x = position[0] - text_width / 2
  y = position[1]

  # Draw the text
  draw.text((x, y), text, font=font, fill=fill_color)


async def fetch_user_settings(user_id):
  response = await bot.loop.run_in_executor(
      None, lambda: supabase.table('Inventory').select('settings').eq(
          'discord_id', user_id).execute())
  data = response.data
  if data and 'settings' in data[0]:
    settings = data[0]['settings']
    return settings
  return None  # or return a default settings structure


async def create_profile_image(ctx, profile_data, avatar_url, user_id):
  fill_color = 'white'
  premade_avatar = 'True'
  # Default settings if not found in the database
  premade_avatar_id = 0
  premade_avatar_gender = 'male'
  profile_background_id = 0
  # Load the profile image template

  current_settings = await fetch_user_settings(user_id)
  for setting in current_settings:
    if 'premade_avatar_id' in setting:
      premade_avatar_id = setting['premade_avatar_id']
    elif 'premade_avatar_gender' in setting:
      premade_avatar_gender = setting['premade_avatar_gender']
    elif 'premade_avatar' in setting:
      premade_avatar = setting['premade_avatar']
    elif 'profile_avatar_url' in setting:
      avatar_custom_url = setting['profile_avatar_url']
    elif 'profile_text_color' in setting:
      fill_color = setting['profile_text_color']
    elif 'profile_ring_id' in setting:
      profile_ring_id = setting['profile_ring_id']
    elif 'profile_background_id' in setting:
      profile_background_id = setting['profile_background_id']

  template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'resources', 'profile_bgs', 'bgs',
                               f'{profile_background_id}.png')
  image = Image.open(template_path)
  draw = ImageDraw.Draw(image)

  if premade_avatar == 'False':
    # Code to load and process the Discord user's avatar
    center_x, center_y = (352, 331)  # Center X, Y coordinates on the template
    avatar_size = (315, 315)  # Width, Height
    avatar_position = (center_x - avatar_size[0] // 2,
                       center_y - avatar_size[1] // 2)

    response = requests.get(avatar_url)
    avatar = Image.open(BytesIO(response.content))
    avatar = avatar.convert("RGBA")
    avatar = avatar.resize(avatar_size, Image.Resampling.LANCZOS)

    mask = Image.new('L', avatar_size, 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0) + avatar_size, fill=255)

    circular_avatar = ImageOps.fit(avatar, mask.size, centering=(0.5, 0.5))
    circular_avatar.putalpha(mask)
    image.paste(circular_avatar, avatar_position, circular_avatar)

    # Load the default ring image
    ring_image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'resources', 'default_ring.png')
    ring_image = Image.open(ring_image_path)

    # Paste the circular avatar onto the template
    image.paste(circular_avatar, avatar_position, circular_avatar)

    # Paste the ring image on top
    image.paste(ring_image, (0, 0), ring_image)
  elif premade_avatar == 'True':
    # Path to the selected profile image
    profile_image_path = os.path.join('commands', 'resources',
                                      f'{premade_avatar_gender}_pfps', 'pfps',
                                      f'{premade_avatar_id}.png')
    if os.path.exists(profile_image_path):
      selected_image = Image.open(profile_image_path)
      image.paste(selected_image, (0, 0), selected_image)

    # Load the selected profile image
    if os.path.exists(profile_image_path):
      selected_image = Image.open(profile_image_path)
      image.paste(selected_image, (0, 0),
                  selected_image)  # Pasting at the top-left corner
    else:
      # Load a default image if the selected image does not exist
      default_image_path = os.path.join('commands', 'resources', 'male_pfps',
                                        'pfps', '0.png')
      selected_image = Image.open(default_image_path)

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
    draw_centered_text(draw, text, center_position, font, fill_color)

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
    draw_centered_text(draw, text, center_position, font, fill_color)

  # Draw text for each field in profile_data
  for field, (x, y) in positions.items():
    value = str(profile_data.get(field, ''))
    draw.text((x, y), value, font=font, fill=fill_color)

  font_size = 20
  font = ImageFont.truetype(font_path, font_size)

  center_positions = {
      'adventure_exp': (335, 577),
      'dash': (370, 577),
      'needed_adv_level_exp': (415, 577),
      'location': (120, 565),
      'class': (354, 547),
      'vitality': (135, 188),
      'dexterity': (135, 243),
      'strength': (135, 300),
      'cunning': (135, 355),
      'magic': (135, 410),
      'luck': (135, 466),
      # 'dash2': (592, 565)
  }

  # Draw text for each field in profile_data
  for field, center_position in center_positions.items():
    text = str(profile_data.get(field, ''))
    draw_centered_text(draw, text, center_position, font, fill_color)

  font_size = 18
  font = ImageFont.truetype(font_path, font_size)

  positions = {
      'gold': (605, 265),
      'stat_score': (615, 188),
      'free_points': (635, 221),
      'atk': (595, 308),
      'def': (595, 343),
      'health': (610, 532),
      # 'max_health': (610, 307),
      'energy': (612, 565)
      # 'max_energy': (620, 365),
  }

  # Draw text for each field in profile_data
  for field, (x, y) in positions.items():
    value = str(profile_data.get(field, ''))
    draw.text((x, y), value, font=font, fill=fill_color)

  # # Desired center position for the avatar
  # center_x, center_y = (354, 245)  # Center X, Y coordinates on the template

  # # Specify the size for the profile picture
  # avatar_size = (80, 80)  # Width, Height

  # # Calculate top-left corner position for pasting
  # avatar_position = (center_x - avatar_size[0] // 2,
  #                    center_y - avatar_size[1] // 2)

  # # Fetch and open the profile picture
  # response = requests.get(avatar_url)
  # avatar = Image.open(BytesIO(response.content))

  # # Ensure the avatar is in RGBA mode
  # avatar = avatar.convert("RGBA")

  # # Resize the avatar to the desired size using LANCZOS
  # avatar = avatar.resize(avatar_size, Image.Resampling.LANCZOS)

  # # Create a mask for the circular crop
  # mask = Image.new('L', avatar_size, 0)
  # draw_mask = ImageDraw.Draw(mask)
  # draw_mask.ellipse((0, 0) + avatar_size, fill=255)

  # # Apply the mask to the avatar to get a circular image
  # circular_avatar = ImageOps.fit(avatar, mask.size, centering=(0.5, 0.5))
  # circular_avatar.putalpha(mask)

  # # Paste the circular avatar onto the template
  # image.paste(circular_avatar, avatar_position, circular_avatar)

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

    displayname = player.displayname if player.displayname != 'Default' else player.name

    # Define the profile data
    profile_data = {
        'username': displayname,
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
    await create_profile_image(ctx, profile_data, avatar_url, user_id)

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

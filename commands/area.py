import asyncio
from nextcord.ext import commands
from nextcord import slash_command, SlashOption
import nextcord
from nextcord import Embed, ButtonStyle, ui
from nextcord.ui import Button, View
from main import bot, supabase  # Import necessary objects from your project
from functions.load_settings import get_embed_color
from classes.Player import Player
from functions.using_command_failsafe import using_command_failsafe_instance as failsafes
import os
from PIL import Image, ImageSequence
import io
import functools


class Area(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @slash_command(name="area", description="See area information.")
  async def area_slash(self, interaction: nextcord.Interaction):
    await self.area(interaction)

  @commands.command(name="area",
                    aliases=["areas"],
                    help="See area information.")
  async def area_text(self, ctx):
    await self.area(ctx)

  async def area(self, interaction):
    # If it's a text command, get the author from the context
    if isinstance(interaction, commands.Context):
      user_id = interaction.author.id
      author = interaction.author
      channel = interaction.channel
      send_message = interaction.send
    # If it's a slash command, get the author from the interaction
    elif isinstance(interaction, nextcord.Interaction):
      user_id = interaction.user.id
      author = interaction.user
      channel = interaction.channel
      send_message = interaction.response.send_message

    self.player = Player(author)

    if (self.player.level < 5 and self.player.level > 0):
      await send_message(
          "You need to be at least **`Level 5`** to access this command.\n"
          "Leaving before that is simply suicide.\n"
          "This is level-locked because of a certain someone.\n"
          "They know who they are.")
      return

    # Check if the player is already in a command
    if self.player.using_command:
      using_command_failsafe = failsafes.get_last_used_command_time(
          user_id, "general_failsafe")
      if not using_command_failsafe > 0:
        await send_message("Failsafe activated! Commencing with command!")
        self.player.using_command = False
      else:
        await send_message(
            "You're already in a command. Finish it before starting another.\n"
            f"Failsafe will activate in `{using_command_failsafe:.2f}` seconds if you're stuck."
        )
        return

    # Fetch user data to get current ring
    user_data_response = await bot.loop.run_in_executor(
        None, lambda: supabase.table('Users').select('ring').eq(
            'discord_id', user_id).execute())
    if not user_data_response.data:
      await send_message(
          f"{author} does not have a profile yet.\nPlease type `apo start`.")
      return

    user_data = user_data_response.data[0]
    ring_id = user_data.get('ring', None)

    # Display the map based on the ring
    map_image_path = os.path.join('commands', 'resources', 'rings',
                                  f'ring{ring_id}map.png')
    # Note: Implement the logic to overlay the GIF on the map image here

    ring_response = await bot.loop.run_in_executor(
        None, lambda: supabase.table('Rings').select('name').eq('id', ring_id).
        execute())

    ring_name = ring_response.data[0][
        'name'] if ring_response.data else 'Unknown'

    # Fetch area data including IDs
    areas_response = await bot.loop.run_in_executor(
        None, lambda: supabase.table('Areas').select('*').eq('ring', ring_id).
        execute())

    view = View(timeout=180)
    row = 1
    button_count = 0
    current_coords = (100, 100)

    # Iterate through the areas and create a button for each one
    for area in areas_response.data:
      area_name = area['name']
      area_id = area['id']
      if area_id == self.player.location:
        current_coords = area['marker_coords']
      marker_coords = area['marker_coords']
      button = Button(label=area_name,
                      style=ButtonStyle.primary,
                      row=row,
                      custom_id=str(area_id))
      button.callback = functools.partial(self.on_area_button_pressed,
                                          area_id=area_id,
                                          marker_coords=marker_coords)
      view.add_item(button)
      button_count += 1

      if button_count == 2:  # Check if the row already has 2 buttons
        row += 1
        button_count = 0  # Reset the counter for the new row

    # row += 1
    # button = Button(label="Show Ring Map (Disabled for now)",
    #                 style=ButtonStyle.gray,
    #                 row=row)
    # view.add_item(button)

    # Load the base map image
    map_image_path = os.path.join('commands', 'resources', 'rings',
                                  f'ring{ring_id}map.png')
    self.map_image_path = map_image_path
    base_map = Image.open(map_image_path).convert('RGBA')
    self.base_map = base_map

    # Load the marker GIF
    marker_gif_path = os.path.join('commands', 'resources', 'rings',
                                   'marker.gif')
    self.marker_gif_path = marker_gif_path
    marker_gif = Image.open(marker_gif_path)
    self.marker_gif = marker_gif
    frames = []

    # Overlay the GIF onto the map at the specified coordinates
    x, y = map(int, current_coords)
    # Overlay the GIF onto the map at the specified coordinates
    for frame in ImageSequence.Iterator(marker_gif):
      # Create a copy of the base map for each frame
      temp_map = base_map.copy()

      # Overlay the marker GIF frame onto the map copy
      temp_map.paste(frame, (x, y), frame.convert('RGBA'))

      # Add the composite image to the list of frames
      frames.append(temp_map)

    marker_gif = marker_gif.convert('RGBA')

    # Save to an in-memory file
    final_buffer = io.BytesIO()
    frames[0].save(final_buffer,
                   format='GIF',
                   save_all=True,
                   append_images=frames[1:],
                   loop=0,
                   duration=marker_gif.info['duration'])
    final_buffer.seek(0)  # Reset buffer pointer

    # Send the image in a Discord embed
    file = nextcord.File(final_buffer, filename='map.gif')
    embed = nextcord.Embed(title=f"{ring_name} - Map")
    embed.set_author(name=self.player.name)
    embed.set_image(url='attachment://map.gif')
    self.view = view
    await send_message(file=file, embed=embed, view=view)

    # Close the images
    # base_map.close()
    # marker_gif.close()

    # # Send the map image with area buttons
    # file = nextcord.File(map_image_path, filename=f"ring{ring_id}map.png")
    # embed = nextcord.Embed(title=f"{ring_name} - Map")
    # embed.set_image(url=f"attachment://ring{ring_id}map.png")
    # await ctx.send(file=file, embed=embed, view=view)

  async def on_area_button_pressed(self, interaction: nextcord.Interaction,
                                   area_id, marker_coords):
    if interaction.user.id != self.player.user_id:
      await interaction.response.send_message(
          "This isn't your screen! Go make your own lol.", ephemeral=True)
      return

    # Convert marker_coords to integers
    x, y = map(int, marker_coords)

    # Update the player's location in the database
    user_id = interaction.user.id
    updated_user_data = {'location': area_id}
    await bot.loop.run_in_executor(
        None, lambda: supabase.table('Users').update(updated_user_data).eq(
            'discord_id', user_id).execute())

    # Fetch the new area's name for the confirmation message
    area_response = await bot.loop.run_in_executor(
        None, lambda: supabase.table('Areas').select('name').eq('id', area_id).
        execute())

    area_name = area_response.data[0][
        'name'] if area_response.data else 'Unknown Area'

    # Generate the new GIF with the marker in the new position
    new_gif_buffer = await self.generate_location_gif(x, y)

    # Send the new GIF as a follow-up message
    file = nextcord.File(new_gif_buffer, filename='map.gif')
    embed = nextcord.Embed(title=f"{area_name} - Location Updated")
    embed.set_author(name=self.player.name)
    embed.set_image(url='attachment://map.gif')
    await interaction.response.send_message(file=file,
                                            embed=embed,
                                            view=self.view)

    # Optionally delete the original message if needed
    await interaction.message.delete()

    # No need to edit the original message
    await interaction.followup.send(
        f"**{self.player.name}** has been transported to **{area_name}**.",
        ephemeral=False)

  # Utility method to generate the location GIF
  async def generate_location_gif(self, x, y):
    # Repeat the same logic used in the area command to generate the GIF
    frames = []
    # Overlay the GIF onto the map at the new coordinates
    for frame in ImageSequence.Iterator(self.marker_gif):
      temp_map = self.base_map.copy()
      # Overlay the marker GIF frame onto the map copy
      frame = frame.convert('RGBA')
      temp_map.paste(frame, (x, y), frame)
      frames.append(temp_map)

    # Save to an in-memory file
    final_buffer = io.BytesIO()
    frames[0].save(final_buffer,
                   format='GIF',
                   save_all=True,
                   append_images=frames[1:],
                   loop=0,
                   duration=self.marker_gif.info['duration'])
    final_buffer.seek(0)  # Reset buffer pointer

    return final_buffer


def setup(bot):
  bot.add_cog(Area(bot))

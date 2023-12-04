import asyncio
from nextcord.ext import commands
from nextcord import Embed, ButtonStyle, ui
from nextcord.ui import Button, View
from main import bot, supabase  # Import necessary objects from your project
from functions.load_settings import get_embed_color
from classes.Player import Player


class Area(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @commands.group(invoke_without_command=True,
                  aliases=["areas"],
                  help="See area information.")
  async def area(self, ctx):
    user_id = ctx.author.id

    # Fetch user data to get current location
    user_data_response = await bot.loop.run_in_executor(
        None, lambda: supabase.table('Users').select('location').eq(
            'discord_id', user_id).execute())

    if not user_data_response.data:
      await ctx.send(
          f"{ctx.author} does not have a profile yet.\nPlease type `::start`.")
      return

    user_data = user_data_response.data[0]
    location_id = user_data.get('location', None)

    # Fetch location data
    location_response = await bot.loop.run_in_executor(
        None, lambda: supabase.table('Areas').select('*').eq(
            'id', location_id).execute())

    if not location_response.data:
      await ctx.send("Error: Your current location could not be found.")
      return

    location_data = location_response.data[0]
    location_name = location_data['name']
    location_desc = location_data['description']

    # Create embed for the location
    embed = Embed(title=f"Location: {location_name}",
                  description=location_desc,
                  color=await
                  get_embed_color(None if ctx.guild is None else ctx.guild.id))
    embed.add_field(
        name="",
        value="------------------\n**Use `area list` to see all areas.**",
        inline=False)

    await ctx.send(embed=embed)

  @area.command(name="move", help="Move to a different area.")
  async def area_move(self, ctx, area_id: int):
    user_id = ctx.author.id

    player = Player(ctx.author)
    # Check if the player is already in a command
    if player.using_command:
      await ctx.send(
          "You're already in a command. Finish it before starting another.")
      return

    # Fetch area data
    area_response = await bot.loop.run_in_executor(
        None,
        lambda: supabase.table('Areas').select('*').eq('id', area_id).execute(
        ))

    if not area_response.data:
      await ctx.send("This area does not exist.")
      return

    area_data = area_response.data[0]

    # Check if user level is high enough
    user_data_response = await bot.loop.run_in_executor(
        None, lambda: supabase.table('Users').select('level').eq(
            'discord_id', user_id).execute())

    if not user_data_response.data:
      await ctx.send(
          f"{ctx.author} does not have a profile yet.\nPlease type `::start`.")
      return

    user_level = user_data_response.data[0]['level']
    if user_level < area_data['level_req']:
      await ctx.send(
          f"You do not meet the level requirement for this area ({area_data['level_req']}). Continue your adventure to level up."
      )
      return

    # Update user location
    updated_user_data = {'location': area_id}
    await bot.loop.run_in_executor(
        None, lambda: supabase.table('Users').update(updated_user_data).eq(
            'discord_id', user_id).execute())

    await ctx.send(f"You have moved to {area_data['name']}.")

  @area.command(name="list", help="List all accessible areas.")
  async def area_list(self, ctx):
    user_id = ctx.author.id

    # Fetch user level
    user_data_response = await bot.loop.run_in_executor(
        None, lambda: supabase.table('Users').select('level').eq(
            'discord_id', user_id).execute())

    if not user_data_response.data:
      await ctx.send(
          f"{ctx.author} does not have a profile yet.\nPlease type `::start`.")
      return

    user_level = user_data_response.data[0]['level']

    # Fetch all areas
    areas_response = await bot.loop.run_in_executor(
        None, lambda: supabase.table('Areas').select('*').execute())

    if not areas_response.data:
      await ctx.send("No areas found.")
      return

    areas = sorted(areas_response.data, key=lambda area: area['id'])

    accessible_areas = [
        area for area in areas if area['level_req'] <= user_level
    ]
    locked_areas = [area for area in areas if area['level_req'] > user_level]

    # Create embed for the list of areas
    embed = Embed(title="Areas",
                  color=await
                  get_embed_color(None if ctx.guild is None else ctx.guild.id))

    for area in accessible_areas:
      embed.add_field(
          name="",
          value=
          f"**ID:** `{area['id']}` - **{area['name']}** \nLevel Requirement: `{area['level_req']}`",
          inline=False)

    for area in locked_areas:
      embed.add_field(
          name="",
          value=
          f"**ID: `{area['id']}` - {area['name']} - LOCKED** \nLevel Requirement: `{area['level_req']}`",
          inline=False)
    embed.add_field(
        name="",
        value=
        "------------------\n**Use `area move <id>` to go to a new area.**",
        inline=False)
    await ctx.send(embed=embed)


def setup(bot):
  bot.add_cog(Area(bot))

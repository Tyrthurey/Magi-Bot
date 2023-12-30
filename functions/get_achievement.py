import asyncio
import nextcord
from nextcord.ext import commands
from supabase import Client, create_client
from dotenv import load_dotenv
from functions.load_settings import command_prefix, get_embed_color
import os
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


class GetAchievement():

  def __init__(self, bot):
    self.bot = bot

  async def remove_achievement(self, user_id, achievement_id):
    # Fetch the inventory data for the user
    inventory_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Inventory').select('achievements').eq(
            'discord_id', user_id).execute())

    inventory_data = inventory_response.data

    # Check if inventory data exists for the user
    if inventory_data:
      inventory_record = inventory_data[0]
      achievements = inventory_record.get('achievements', [])

      # Remove the achievement if it exists
      achievements = [a for a in achievements if a['id'] != achievement_id]

      # Prepare the updated inventory data
      updated_inventory_data = {'achievements': achievements}

      # Update the inventory data
      await asyncio.get_event_loop().run_in_executor(
          None, lambda: supabase.table('Inventory').update(
              updated_inventory_data).eq('discord_id', user_id).execute())

      # Notify the user via DM
      user = await self.bot.fetch_user(user_id)
      if user:  # Check if the user object is valid
        try:
          embed_color = await get_embed_color(None)  # Adjust as needed
          embed = nextcord.Embed(
              title="Achievement Lost",
              description="You have lost the first place achievement.",
              color=embed_color)
          await user.send(embed=embed)
        except Exception as e:
          logging.error(f"Error sending DM: {e}")
      else:
        logging.error(f"Could not fetch user with ID: {user_id}")

  async def get_dm_achievement(self, user_id, achievement_id):
    # Fetch the inventory data for the user
    inventory_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Inventory').select('achievements').eq(
            'discord_id', user_id).execute())

    inventory_data = inventory_response.data
    achievements = []

    # Check if inventory data exists for the user
    if inventory_data:
      inventory_record = inventory_data[0]
      achievements = inventory_record.get('achievements', [])
      if achievements is None:
        achievements = []

    # Check if the user already has the achievement
    for achievement in achievements:
      if achievement['id'] == achievement_id:
        # await ctx.send("You already have this achievement!")
        return  # Stop the function here

    # Add the new achievement
    new_achievement = {'id': achievement_id, 'awarded': True}
    achievements.append(new_achievement)

    # Prepare the updated inventory data
    updated_inventory_data = {'achievements': achievements}

    # If inventory data exists, update it
    if inventory_data:
      await asyncio.get_event_loop().run_in_executor(
          None, lambda: supabase.table('Inventory').update(
              updated_inventory_data).eq('discord_id', user_id).execute())
    else:
      # If inventory data does not exist, create it
      updated_inventory_data[
          'discord_id'] = user_id  # Ensure the discord_id is included
      await asyncio.get_event_loop().run_in_executor(
          None, lambda: supabase.table('Inventory').insert(
              updated_inventory_data).execute())

    # Fetch the achievement data to present to the user
    achievement_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Achievements').select(
            'achievement_name, achievement_description').eq(
                'id', achievement_id).execute())

    achievement_data = achievement_response.data
    embed_color = 0x000000

    # Check if achievement data exists
    if achievement_data:
      achievement_record = achievement_data[0]
      achievement_name = achievement_record.get('achievement_name', '')
      achievement_description = achievement_record.get(
          'achievement_description', '')

      # avatar_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url

      # Notify the user via DM
      user = await self.bot.fetch_user(user_id)
      if user:  # Check if the user object is valid
        try:
          embed_color = await get_embed_color(None)  # Adjust as needed
          # Create an embed object
          embed = nextcord.Embed(title="🎉 Achievement Earned! 🎉",
                                 color=embed_color)
          # embed.set_author(name=ctx.author.display_name)
          embed.add_field(name="Name",
                          value=f"🏆 {achievement_name} 🏆",
                          inline=False)
          embed.add_field(name="Description",
                          value=f"📜 {achievement_description}",
                          inline=False)
          await user.send(embed=embed)
        except Exception as e:
          logging.error(f"Error sending DM: {e}")
      else:
        logging.error(f"Could not fetch user with ID: {user_id}")

  async def get_achievement(self, ctx, user_id, achievement_id):

    # Fetch the inventory data for the user
    inventory_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Inventory').select('achievements').eq(
            'discord_id', user_id).execute())

    inventory_data = inventory_response.data
    achievements = []

    # Check if inventory data exists for the user
    if inventory_data:
      inventory_record = inventory_data[0]
      achievements = inventory_record.get('achievements', [])
      if achievements is None:
        achievements = []

    # Check if the user already has the achievement
    for achievement in achievements:
      if achievement['id'] == achievement_id:
        # await ctx.send("You already have this achievement!")
        return  # Stop the function here

    # Add the new achievement
    new_achievement = {'id': achievement_id, 'awarded': True}
    achievements.append(new_achievement)

    # Prepare the updated inventory data
    updated_inventory_data = {'achievements': achievements}

    # If inventory data exists, update it
    if inventory_data:
      await asyncio.get_event_loop().run_in_executor(
          None, lambda: supabase.table('Inventory').update(
              updated_inventory_data).eq('discord_id', user_id).execute())
    else:
      # If inventory data does not exist, create it
      updated_inventory_data[
          'discord_id'] = user_id  # Ensure the discord_id is included
      await asyncio.get_event_loop().run_in_executor(
          None, lambda: supabase.table('Inventory').insert(
              updated_inventory_data).execute())

    # Fetch the achievement data to present to the user
    achievement_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Achievements').select(
            'achievement_name, achievement_description').eq(
                'id', achievement_id).execute())

    achievement_data = achievement_response.data
    try:
      embed_color = await get_embed_color(
          None if ctx.guild is None else ctx.guild.id)
    except AttributeError:
      embed_color = 0x000000

    # Check if achievement data exists
    if achievement_data:
      achievement_record = achievement_data[0]
      achievement_name = achievement_record.get('achievement_name', '')
      achievement_description = achievement_record.get(
          'achievement_description', '')

      avatar_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url

      # Create an embed object
      embed = nextcord.Embed(title="🎉 Achievement Earned! 🎉",
                             color=embed_color)
      embed.set_author(name=ctx.author.display_name, icon_url=avatar_url)
      embed.add_field(name="Name",
                      value=f"🏆 {achievement_name} 🏆",
                      inline=False)
      embed.add_field(name="Description",
                      value=f"📜 {achievement_description}",
                      inline=False)

      # Send the embed to the user
      await ctx.send(embed=embed)
    else:
      await ctx.send(
          "There was an error fetching your achievement. Please contact support (use `apo bug`)."
      )

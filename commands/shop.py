import asyncio
import logging
import os
import nextcord
from nextcord.ext import commands
from supabase import Client, create_client
from dotenv import load_dotenv
from functions.load_settings import command_prefix, get_embed_color

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


async def shopping(ctx):
  embed_color = await get_embed_color(
      None if ctx.guild is None else ctx.guild.id)
  user = ctx.author

  user_id = user.id
  username = user.display_name
  avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
  # avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
  # Fetch the latest user data from the database
  user_data_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Users').select('bal').eq(
          'discord_id', user_id).execute())

  # Check if the user has a profile
  if not user_data_response.data:
    await ctx.send(f"{username} does not have a profile yet.")
    return

  user_data = user_data_response.data[0]  # User data from the database

  # Fetch the shop items from the database
  response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Items').select(
          'item_displayname', 'rarity', 'description', 'price').eq(
              'buyable', True).execute())

  # Check if we got data back
  if response.data:
    items_to_display = response.data
  else:
    await ctx.send("The shop is currently closed. Please try again later.")
    return

  embed = nextcord.Embed(
      title="Item Shop",
      description=
      f"Welcome to the shop! You have `{user_data['bal']}` gold!\nHere are the items available for purchase:",
      color=embed_color)

  # Add items to the embed
  for item in items_to_display:
    embed.add_field(
        name=item['item_displayname'],
        value=
        f"**Rarity:** {item['rarity']}\n**Description:** {item['description']}\n**Price:** {item['price']} <:apocalypse_coin:1182666655420125319>",
        inline=False)
  embed.set_author(name=ctx.author.display_name, icon_url=avatar_url)
  embed.set_footer(text="Help us improve! Use apo suggest <suggestion>.")
  await ctx.send(embed=embed)


# Command function
@commands.command(name="shop",
                  aliases=["s"],
                  help="Open the shop and browse the wares!")
@commands.cooldown(1, 5, commands.BucketType.user
                   )  # Cooldown: 1 time per 5 seconds per user
async def shop(ctx):
  await shopping(ctx)


# Error handler
async def shopping_error(ctx, error):
  if isinstance(error, commands.CommandOnCooldown):
    await ctx.send(
        f"This command is on cooldown. You can use it again in `{error.retry_after:.2f}` seconds."
    )
  else:
    await ctx.send(f"An error occurred: {error}")


# Assign the error handler to the command
shop.error(shopping_error)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(shop)

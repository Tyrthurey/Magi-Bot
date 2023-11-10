import asyncio
import logging
import os
import nextcord
from nextcord.ext import commands
from supabase import Client, create_client
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


async def shopping(ctx):
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
      "Welcome to the shop! Here are the items available for purchase:",
      color=nextcord.Color.blue())

  # Add items to the embed
  for item in items_to_display:
    embed.add_field(
        name=item['item_displayname'],
        value=
        f"**Rarity:** {item['rarity']}\n**Description:** {item['description']}\n**Price:** {item['price']} Gold",
        inline=False)
  embed.set_author(name=ctx.author.display_name,
                   icon_url=ctx.author.avatar.url)
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

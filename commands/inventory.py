import asyncio
from datetime import datetime
import nextcord
from nextcord.ext import commands
from main import bot, supabase  # Import necessary objects from your project
from functions.load_settings import get_embed_color


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


class Inventory(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @commands.command(name="inventory",
                    aliases=["inv"],
                    help="Displays the user's inventory.")
  async def inventory(self, ctx, *, user: nextcord.User = None):
    embed_color = await get_embed_color(
        None if ctx.guild is None else ctx.guild.id)
    if user is None:
      user = ctx.author

    user_id = user.id
    username = user.display_name
    avatar_url = user.avatar.url if user.avatar else user.default_avatar.url

    items = await get_items(user_id)

    embed = nextcord.Embed(color=embed_color)
    embed.set_author(name=f"{username}'s Inventory", icon_url=avatar_url)

    if not items:
      embed.description = "Your inventory is empty."
    else:
      # Initialize different strings for different types of items
      items_str = ""
      consumables_str = ""
      other_str = ""

      for item in items:
        if item['quantity'] > 0:
          item_response = await asyncio.get_event_loop().run_in_executor(
              None, lambda: supabase.table('Items').select(
                  'item_displayname', 'type').eq('item_id', item['item_id']).
              execute())
          if item_response.data:
            item_name = item_response.data[0]['item_displayname']
            item_type = item_response.data[0]['type']
          else:
            item_name = f"Item {item['item_id']}"
            item_type = "other"

          cooldown_str = ""

          if item['cooldown']:
            cooldown_time = datetime.fromisoformat(item['cooldown'].replace(
                'Z', '')).replace(tzinfo=None)
            now = datetime.utcnow().replace(tzinfo=None)

            remaining_time = cooldown_time - now
            if remaining_time.total_seconds() > 0:
              hours, remainder = divmod(int(remaining_time.total_seconds()),
                                        3600)
              minutes, _ = divmod(remainder, 60)
              cooldown_str = f"Ready in: {hours}h {minutes}m"

          # Append to the appropriate string based on the item's type
          item_str = f"**{item_name}**: {item['quantity']}\n{cooldown_str}\n" if cooldown_str else f"**{item_name}**: {item['quantity']}\n"
          if item_type in ["drop", "item"]:
            items_str += item_str
          elif item_type == "consumable":
            consumables_str += item_str
          else:
            other_str += item_str

      # Add each string as a separate field to the embed
      if items_str:
        embed.add_field(name="Items", value=items_str, inline=True)
      if consumables_str:
        embed.add_field(name="Consumables", value=consumables_str, inline=True)
      if other_str:
        embed.add_field(name="Other", value=other_str, inline=True)

    await ctx.send(embed=embed)


def setup(bot):
  bot.add_cog(Inventory(bot))

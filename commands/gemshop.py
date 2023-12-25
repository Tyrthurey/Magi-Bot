import asyncio
import logging
import os
import nextcord
from nextcord.ext import commands
from nextcord.ui import View, Button
from supabase import Client, create_client
from dotenv import load_dotenv
from functions.load_settings import command_prefix, get_embed_color
from functools import partial
import functools

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


class PurchaseModal(nextcord.ui.Modal):

  def __init__(self, title: str, label: str, price: int, user_id: int,
               column_name: str):
    super().__init__(title=title)
    self.price = price
    self.user_id = user_id
    self.column_name = column_name
    self.add_item(
        nextcord.ui.TextInput(label=label,
                              placeholder='Enter the ID',
                              min_length=1,
                              max_length=18,
                              style=nextcord.TextInputStyle.short))

  async def callback(self, interaction: nextcord.Interaction):
    if interaction.user.id != self.user_id:
      await interaction.response.send_message("Dis aint yo Gem Shop, bruv.",
                                              ephemeral=True)
      return
    item_id = int(self.children[0].value)
    # Fetch the user's current unlocked cosmetics
    unlocked_cosmetics = await fetch_user_cosmetics(self.user_id)
    unlocked_avatars = unlocked_cosmetics[0].get('unlocked_avatars', [])
    unlocked_backgrounds = unlocked_cosmetics[1].get('unlocked_backgrounds',
                                                     [])
    unlocked_rings = unlocked_cosmetics[2].get('unlocked_profile_rings', [])

    unlocked_avatar_ids = [avatar['avatar_id'] for avatar in unlocked_avatars]
    unlocked_background_ids = [
        background['background_id'] for background in unlocked_backgrounds
    ]
    unlocked_ring_ids = [ring['profile_ring_id'] for ring in unlocked_rings]

    # Check if user already owns the item
    if item_id in (unlocked_avatar_ids
                   if self.column_name == 'avatar' else unlocked_background_ids
                   if self.column_name == 'background' else unlocked_ring_ids):
      await interaction.response.send_message(f"You already own this item.",
                                              ephemeral=True)
      return

    else:
      # Deduct gems
      user_data_response = await asyncio.get_event_loop().run_in_executor(
          None, lambda: supabase.table('Users').select('gems').eq(
              'discord_id', self.user_id).execute())
      user_data = user_data_response.data[0]  # User data from the database
      if user_data['gems'] < self.price:
        await interaction.response.send_message("You don't have enough gems.",
                                                ephemeral=True)
        return

      new_gems_total = user_data['gems'] - self.price
      # Update user's gems
      supabase.table('Users').update({
          'gems': new_gems_total
      }).eq('discord_id', self.user_id).execute()

      # This is the logic that needs to be adjusted:

      # Find the dictionary in the list that corresponds to the item category
      for category_dict in unlocked_cosmetics:
        if self.column_name == 'avatar' and 'unlocked_avatars' in category_dict:
          # Append the new avatar_id to the 'unlocked_avatars' list
          category_dict['unlocked_avatars'].append({'avatar_id': item_id})
          break
        elif self.column_name == 'background' and 'unlocked_backgrounds' in category_dict:
          # Append the new background_id to the 'unlocked_backgrounds' list
          category_dict['unlocked_backgrounds'].append(
              {'background_id': item_id})
          break
        elif self.column_name == 'profile_ring' and 'unlocked_profile_rings' in category_dict:
          # Append the new profile_ring_id to the 'unlocked_profile_rings' list
          category_dict['unlocked_profile_rings'].append(
              {'profile_ring_id': item_id})
          break

      # Update the Inventory table
      supabase.table('Inventory').update({
          'unlocked_cosmetics':
          unlocked_cosmetics
      }).eq('discord_id', self.user_id).execute()

      await interaction.response.send_message(
          f"Item with ID {item_id} purchased for **`{self.price}`** <:apocalypse_gem:1183576348485234698>!",
          ephemeral=False)


async def fetch_user_cosmetics(user_id):
  response = await asyncio.get_event_loop().run_in_executor(
      None,
      lambda: supabase.table('Inventory').select('unlocked_cosmetics').eq(
          'discord_id', user_id).execute())
  data = response.data
  if data and 'unlocked_cosmetics' in data[0]:
    unlocked_cosmetics = data[0]['unlocked_cosmetics']
    return unlocked_cosmetics
  return None


async def avatar_button_callback(interaction, item_price, user_id):
  if interaction.user.id != user_id:
    await interaction.response.send_message("Dis aint yo Gem Shop, bruv.",
                                            ephemeral=True)
    return
  await interaction.response.send_modal(
      PurchaseModal("Purchase Avatar", "Enter the Avatar ID", item_price,
                    user_id, 'avatar'))


async def background_button_callback(interaction, item_price, user_id):
  if interaction.user.id != user_id:
    await interaction.response.send_message("Dis aint yo Gem Shop, bruv.",
                                            ephemeral=True)
    return
  await interaction.response.send_modal(
      PurchaseModal("Purchase Background", "Enter the Background ID",
                    item_price, user_id, 'background'))


async def shopping(ctx):
  embed_color = await get_embed_color(
      None if ctx.guild is None else ctx.guild.id)
  user = ctx.author
  user_cosmetics = await fetch_user_cosmetics(ctx.author.id)
  unlocked_avatar_ids = []
  unlocked_background_ids = []
  unlocked_ring_ids = []
  items_to_display = []

  user_data_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Users').select('gems').eq(
          'discord_id', ctx.author.id).execute())

  # Check if the user has a profile
  if not user_data_response.data:
    await ctx.send(f"{ctx.author} does not have a profile yet.")
    return

  user_data = user_data_response.data[0]

  if user_cosmetics:
    # Extracting avatars
    unlocked_avatars = user_cosmetics[0].get('unlocked_avatars', [])
    unlocked_backgrounds = user_cosmetics[1].get('unlocked_backgrounds', [])
    unlocked_rings = user_cosmetics[2].get('unlocked_profile_rings', [])

    unlocked_avatar_ids = [avatar['avatar_id'] for avatar in unlocked_avatars]
    unlocked_background_ids = [
        background['background_id'] for background in unlocked_backgrounds
    ]
    unlocked_ring_ids = [ring['profile_ring_id'] for ring in unlocked_rings]

    # Printing the IDs for debugging
    print("Unlocked Avatars IDs:", unlocked_avatar_ids)
    print("Unlocked Backgrounds IDs:", unlocked_background_ids)
    print("Unlocked Profile Rings IDs:", unlocked_ring_ids)

  user_id = user.id
  username = user.display_name
  avatar_url = user.avatar.url if user.avatar else user.default_avatar.url

  # Fetch Gems Shop Items
  response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('GemShopItems').select(
          'id', 'item_displayname', 'rarity', 'description', 'price').eq(
              'available', True).execute())

  if response.data:
    items_to_display = response.data
  else:
    await ctx.send("The shop is currently closed. Please try again later.")
    return

  # Create the embed for display
  embed = nextcord.Embed(
      description="## __Apocalypse Emporium__\n"
      f"### **Gems:** `{user_data['gems']}` <:apocalypse_gem:1183576348485234698>\n"
      "### Get more gems here: [**__Apocalypse RPG Store__**](https://potomacstories.com/product-category/rpg-store/)"
      "\n----------------------------------------"
      f"\n**Unlocked Avatar IDs:** `{unlocked_avatar_ids}`"
      f"\n**Unlocked Background IDs:** `{unlocked_background_ids}`"
      f"\n**Unlocked Ring IDs:** `{unlocked_ring_ids}`"
      "\n----------------------------------------",
      color=embed_color)

  # Create the view to hold the buttons
  view = nextcord.ui.View()

  for item in items_to_display:
    embed.add_field(
        name=f"__{item['item_displayname']}__",
        value=
        f"**Price:** `{item['price']}` <:apocalypse_gem:1183576348485234698>\n\n{item['description']}",
        inline=True)

    if 'avatar' in item['item_displayname'].lower():
      avatar_button = Button(label="Input Avatar ID",
                             style=nextcord.ButtonStyle.primary)
      # Use a regular function call with functools.partial to pass extra arguments
      avatar_button.callback = functools.partial(avatar_button_callback,
                                                 item_price=item['price'],
                                                 user_id=user_id)
      view.add_item(avatar_button)
    elif 'background' in item['item_displayname'].lower():
      background_button = Button(label="Input Background ID",
                                 style=nextcord.ButtonStyle.primary)
      background_button.callback = functools.partial(
          background_button_callback,
          item_price=item['price'],
          user_id=user_id)
      view.add_item(background_button)

  embed.set_author(name=username, icon_url=avatar_url)
  await ctx.send(embed=embed, view=view)


@commands.command(name="gemshop",
                  aliases=["gs"],
                  help="Browse the gem shop and make purchases.")
@commands.cooldown(1, 5, commands.BucketType.user)
async def gemshop(ctx):
  await shopping(ctx)


def setup(bot):
  bot.add_command(gemshop)

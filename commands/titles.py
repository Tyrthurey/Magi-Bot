from nextcord.ext import commands
from nextcord import Embed, ButtonStyle, ui
import nextcord
from nextcord.ui import Button, View
from main import bot, supabase, get_embed_color


class Paginator(ui.View):

  def __init__(self, ctx, embed_updater, max_pages, embed):
    super().__init__(timeout=60)
    self.ctx = ctx
    self.embed_updater = embed_updater
    self.max_pages = max_pages
    self.page = 0
    self.user_id = ctx.author.id
    self.embed = embed

  @nextcord.ui.button(label="⬅️",
                      style=nextcord.ButtonStyle.primary,
                      custom_id="previous_btn")
  async def previous_button(self, button: ui.Button,
                            interaction: nextcord.Interaction):
    if interaction.user.id != self.user_id:
      await interaction.response.send_message("These aren't your titles!",
                                              ephemeral=True)
      return
    if self.page > 0:
      self.page -= 1
      await self.embed_updater(self.page)
      await interaction.message.edit(embed=self.embed, view=self)

  @nextcord.ui.button(label="➡️",
                      style=nextcord.ButtonStyle.primary,
                      custom_id="next_btn")
  async def next_button(self, button: Button,
                        interaction: nextcord.Interaction):
    if interaction.user.id != self.user_id:
      await interaction.response.send_message("These aren't your titles!",
                                              ephemeral=True)
      return
    if self.page < self.max_pages:
      self.page += 1
      await self.embed_updater(self.page)
      await interaction.message.edit(embed=self.embed, view=self)


class Titles(commands.Cog):

  def __init__(self, bot):
    self.bot = bot
    self.per_page = 4
    self.page = 0

  async def update_embed(self, page):
    start = page * self.per_page
    end = start + self.per_page
    self.embed.clear_fields()
    self.embed.title = f"Your Titles"
    self.embed.add_field(name=f"-----------------------------------------",
                         value="",
                         inline=False)

    for i in range(start, min(end, len(self.titles))):
      title = self.titles[i]
      title_name = title['title_name']
      self.embed.add_field(name="",
                           value="**ID:** `" + str(title['id']) + "` - **" +
                           title_name + "**",
                           inline=False)
      self.embed.add_field(name=f"-----------------------------------------",
                           value="",
                           inline=False)

    self.embed.add_field(name="",
                         value="Use `titles equip <id>`",
                         inline=False)
    self.embed.add_field(name=f"Page {page + 1}/{self.max_pages + 1}",
                         value="",
                         inline=False)

  @commands.group(invoke_without_command=True,
                  aliases=["t", "title"],
                  help="Manage your titles.")
  async def titles(self, ctx):
    self.user_id = ctx.author.id

    # Fetch the inventory data for the user
    inventory_response = await bot.loop.run_in_executor(
        None, lambda: supabase.table('Inventory').select('titles').eq(
            'discord_id', self.user_id).execute())

    if not inventory_response.data:
      await ctx.send("You don't have any titles yet.")
      return

    inventory_data = inventory_response.data[0]
    inventory_titles = inventory_data.get('titles', [])

    if not inventory_titles:
      await ctx.send("You don't have any titles yet.")
      return

    # Fetch title names from the Titles table
    self.titles = []
    for title in inventory_titles:
      title_response = await bot.loop.run_in_executor(
          None, lambda: supabase.table('Titles').select('*').eq(
              'id', title['title_id']).execute())
      if title_response.data:
        title_data = title_response.data[0]
        title_data['equipped'] = title['equipped']
        self.titles.append(title_data)

    # Create an embed for the titles
    embed_color = await get_embed_color(
        None if ctx.guild is None else ctx.guild.id)
    self.embed = Embed(color=embed_color)
    avatar_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
    self.embed.set_author(name=ctx.author.display_name, icon_url=avatar_url)

    self.max_pages = (len(self.titles) - 1) // self.per_page

    await self.update_embed(0)

    view = Paginator(ctx, self.update_embed, self.max_pages, self.embed)

    await ctx.send(embed=self.embed, view=view)

  @titles.command(help="Equip a title.")
  async def equip(self, ctx, id: int):
    user_id = ctx.author.id

    # Fetch the latest user data from the database
    user_data_response = await bot.loop.run_in_executor(
        None, lambda: supabase.table('Users').select('*').eq(
            'discord_id', user_id).execute())

    # Check if the user has a profile
    if not user_data_response.data:
      await ctx.send(
          f"{ctx.author} does not have a profile yet.\nPlease type `::start`.")
      return

    # Fetch the inventory data for the user
    inventory_response = await bot.loop.run_in_executor(
        None, lambda: supabase.table('Inventory').select('titles').eq(
            'discord_id', user_id).execute())

    if not inventory_response.data:
      await ctx.send("You don't have any titles yet.")
      return

    inventory_data = inventory_response.data[0]
    titles = inventory_data.get('titles', [])

    if not titles:
      await ctx.send("You don't have any titles yet.")
      return

    # Check if the user has the title they're trying to equip
    title_to_equip = None
    for title in titles:
      if title['title_id'] == id:
        title_to_equip = title
        break

    if not title_to_equip:
      await ctx.send("You don't have this title.")
      return

    # Unequip the currently equipped title
    for title in titles:
      if title.get('equipped', False):
        title['equipped'] = False

    # Equip the new title
    title_to_equip['equipped'] = True

    # Update the inventory data
    updated_inventory_data = {'titles': titles}
    await bot.loop.run_in_executor(
        None,
        lambda: supabase.table('Inventory').update(updated_inventory_data).eq(
            'discord_id', user_id).execute())

    await ctx.send(f"You have equipped the title with ID {title_id}.")


def setup(bot):
  bot.add_cog(Titles(bot))

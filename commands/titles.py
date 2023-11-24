from nextcord.ext import commands
from nextcord import Embed
from main import bot, supabase, get_embed_color  # Import necessary objects from your project


class Titles(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @commands.group(invoke_without_command=True,
                  aliases=["t", "title"],
                  help="Manage your titles.")
  async def titles(self, ctx):
    # await ctx.send("Please use a subcommand, e.g., `::title equip <id>`.")
    embed_color = await get_embed_color(
        None if ctx.guild is None else ctx.guild.id)
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

    # Create an embed for the titles
    embed = Embed(title="Your Titles", color=embed_color)

    for title in titles:
      # Fetch the title name from the Titles table
      title_response = await bot.loop.run_in_executor(
          None, lambda: supabase.table('Titles').select('title_name').eq(
              'id', title['title_id']).execute()
      )  # Replace 'id' with your actual column name

      if title_response.data:
        title_name = title_response.data[0]['title_name']
        embed.add_field(name="ID: " + str(title['title_id']),
                        value=title_name,
                        inline=False)

    embed.add_field(name="", value="Use `titles equip <id>`", inline=False)
    await ctx.send(embed=embed)

  @titles.command(help="Equip a title.")
  async def equip(self, ctx, title_id: int):
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
      if title['title_id'] == title_id:
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

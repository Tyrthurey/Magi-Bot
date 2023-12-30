from nextcord.ext import commands
from main import bot, supabase  # Import necessary objects from your project


class GetTitle(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @commands.command(name="get_title", help="Gives the user a title.")
  async def get_title(self, ctx):
    user_id = ctx.author.id
    new_title_id = 4  # Change this to the title_id you want to give

    # Fetch the inventory data for the user
    inventory_response = await self.bot.loop.run_in_executor(
        None, lambda: supabase.table('Inventory').select('titles').eq(
            'discord_id', user_id).execute())

    inventory_data = inventory_response.data
    titles = []

    # Check if inventory data exists for the user
    if inventory_data:
      inventory_record = inventory_data[0]
      titles = inventory_record.get('titles', [])
      if titles is None:
        titles = []

    # Check if the user already has the title
    for title in titles:
      if title['title_id'] == new_title_id:
        await ctx.send(f"You already have this title! (ID: `{new_title_id}`)")
        return  # Stop the function here

    # Add the new title
    new_title = {'title_id': new_title_id, 'equipped': False}
    titles.append(new_title)

    # Prepare the updated inventory data
    updated_inventory_data = {'titles': titles}

    # If inventory data exists, update it
    if inventory_data:
      await self.bot.loop.run_in_executor(
          None, lambda: supabase.table('Inventory').update(
              updated_inventory_data).eq('discord_id', user_id).execute())
    else:
      # If inventory data does not exist, create it
      updated_inventory_data[
          'discord_id'] = user_id  # Ensure the discord_id is included
      await self.bot.loop.run_in_executor(
          None, lambda: supabase.table('Inventory').insert(
              updated_inventory_data).execute())

    await ctx.send("You've been given a new title! \nUse `apo titles` to see your titles.")


def setup(bot):
  bot.add_cog(GetTitle(bot))

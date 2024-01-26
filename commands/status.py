# In commands/status.py
import nextcord
from nextcord.ext import commands
import datetime
from main import supabase
import pytz


class StatusCommand(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  async def fetch_data(self, user_id: int):
    # Your existing method to fetch data
    data = await self.bot.loop.run_in_executor(
        None, lambda: supabase.table('Log').select('*').eq('user_id', user_id).
        execute())
    return data.data if data.data else []

  @commands.command()
  async def status(self, ctx, user_id: int):
    # Check if the user is the one with the specified ID
    if ctx.author.id != 243351582052188170:
      await ctx.send("You do not have permission to use this command.")
      return

    # Fetch data using your custom function
    data = await self.fetch_data(user_id)
    username = 'Default'
    print(data)

    # Initialize statistics
    command_counts = {}
    total_hunt_times = 0
    total_adventure_times = 0

    # Process data
    for row in data:
      username = row['username']
      command = row['command_used']
      command_counts[command] = command_counts.get(command, 0) + 1
      if command == 'hunt':
        total_hunt_times += 1
      elif command == 'adventure':
        total_adventure_times += 1

    # Calculate averages
    now = datetime.datetime.now(datetime.timezone.utc)
    print(now)
    one_week_ago = now - datetime.timedelta(days=7)
    print(one_week_ago)

    # Debugging: Print to check the format of the date strings
    for row in data:
      print(row['date'])

    # Handling timezone and converting to datetime
    def parse_date(date_str):
      try:
        # Parse the date string to datetime
        date_without_tz = datetime.datetime.fromisoformat(
            date_str.replace('Z', '+00:00'))
        # Standardize to UTC
        return date_without_tz.astimezone(pytz.utc)
      except ValueError as e:
        print(f"Error parsing date: {e}")
        return None

    weekly_data = [
        row for row in data
        if parse_date(row['date']) and parse_date(row['date']) > one_week_ago
    ]
    print(weekly_data)
    weekly_hunt = sum(1 for row in weekly_data
                      if row['command_used'] == 'hunt')
    print(weekly_hunt)
    weekly_adventure = sum(1 for row in weekly_data
                           if row['command_used'] == 'adventure')
    print(weekly_adventure)
    hunt_average_24h = total_hunt_times / 7
    print(hunt_average_24h)
    adventure_average_24h = total_adventure_times / 7
    weekly_hunt_average = weekly_hunt / 7
    weekly_adventure_average = weekly_adventure / 7

    # Create embed
    embed = nextcord.Embed(title=f"Status for User {username}")
    stats = []
    for command, count in command_counts.items():
      if command in ['hunt', 'adventure']:
        continue
      stats.append(f"{command}: {count}")
    stats.append(f"Hunt average per 24h: {hunt_average_24h:.2f}")
    stats.append(f"Adventure average per 24h: {adventure_average_24h:.2f}")
    stats.append(f"Weekly hunt average: {weekly_hunt_average:.2f}")
    stats.append(f"Weekly adventure average: {weekly_adventure_average:.2f}")

    embed.add_field(name="Command Usage", value="\n".join(stats), inline=False)

    await ctx.send(embed=embed)


def setup(bot):
  bot.add_cog(StatusCommand(bot))

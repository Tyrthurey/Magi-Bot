from nextcord.ext import commands


async def send_message(ctx):
  await ctx.send('Wasssuuup!')


# Bot command to send a hello message
@commands.command(name="hi", help="Sends a hello message.")
async def hi(ctx):
  await send_message(ctx)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(hi)

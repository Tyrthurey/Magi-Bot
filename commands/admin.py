from nextcord.ext import commands


async def administrate(ctx):
  await ctx.send('Nope, nice try tho!')


# Bot command to send a hello message
@commands.command(name="admin", help="Makes you an admin!")
async def admin(ctx):
  await administrate(ctx)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(admin)

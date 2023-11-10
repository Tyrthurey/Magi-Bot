from nextcord.ext import commands


async def website(ctx):
  await ctx.send('# [Magi RPG website](https://magi-bot.tyrthurey.repl.co/)')


# Bot command to send a hello message
@commands.command(name="website",
                  aliases=["web", "site"],
                  help="The bot's website.")
async def web(ctx):
  await website(ctx)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(web)

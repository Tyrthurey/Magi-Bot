from nextcord.ext import commands
import nextcord


async def website(ctx):
  await ctx.send('# [Apocalypse RPG Website](https://apocalypserpg.com/)')


# Bot command to send a hello message
@commands.command(name="website",
                  aliases=["web", "site"],
                  help="The bot's website.")
async def web(ctx):
  await website(ctx)


@nextcord.slash_command(name="website", description="The bot's website.")
async def slash_website(interaction: nextcord.Interaction):
  await interaction.response.send_message(
      '# [Apocalypse RPG Website](https://apocalypserpg.com/)')


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(web)

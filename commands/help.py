import nextcord
from nextcord.ext import commands

from functions.load_settings import load_settings, command_prefix, get_prefix, get_embed_color

intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True  # Enables the member intent

# When you instantiate your bot, use the following lambda for the command_prefix
bot = commands.Bot(command_prefix=command_prefix,
                   intents=intents,
                   help_command=None,
                   case_insensitive=True)


# The help function should not take 'bot' as a parameter, it's accessible from ctx.
async def helping(ctx):
  # Fetch the embed color from settings
  embed_color = await get_embed_color(ctx.guild.id)

  embed = nextcord.Embed(title='Help Menu', color=embed_color)

  embed.set_footer(text=ctx.bot.user.name, icon_url=ctx.bot.user.avatar.url)
  for command in ctx.bot.commands:
    if command.hidden:
      continue

    # Await the command_prefix coroutine here for each command
    command_prefix_str = await command_prefix(ctx.bot, ctx.message)
    command_name = f"{command_prefix_str}{command.name}"
    help_text = command.help or "No description provided."

    if command.aliases:
      aliases = ", ".join(
          [f"{command_prefix_str}{alias}" for alias in command.aliases])
      help_text += f"\n*Aliases: {aliases}*"

    embed.add_field(name=command_name, value=help_text, inline=True)

  await ctx.send(embed=embed)


# The command decorator should not expect an additional 'bot' argument.
@commands.command(name="help",
                  aliases=["?"],
                  help="Shows help information for commands.")
async def help(ctx):
  await helping(ctx)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(help)

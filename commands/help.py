import nextcord
from nextcord.ext import commands

from functions.load_settings import load_settings, command_prefix, get_prefix, get_embed_color


async def helping(ctx, bot):
  # Fetch the embed color from settings
  embed_color = await get_embed_color(ctx.guild.id)

  embed = nextcord.Embed(title='Help Menu', color=embed_color)

  embed.set_footer(text=bot.user.name, icon_url=bot.user.avatar.url)
  for command in bot.commands:
    if command.hidden:
      continue

    # Await the command_prefix coroutine here for each command
    command_prefix_str = await command_prefix(bot, ctx.message)
    command_name = f"{command_prefix_str}{command.name}"
    help_text = command.help or "No description provided."

    if command.aliases:
      aliases = ", ".join(
          [f"{command_prefix_str}{alias}" for alias in command.aliases])
      help_text += f"\n*Aliases: {aliases}*"

    embed.add_field(name=command_name, value=help_text, inline=True)

  await ctx.send(embed=embed)


@commands.command(name="help", aliases=["?"], help="Self explanatory :P")
async def help(ctx, bot):
  await helping(ctx, bot)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(help)

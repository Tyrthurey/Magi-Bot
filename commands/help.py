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
  command_prefix_str = await command_prefix(ctx.bot, ctx.message)
  embed_color = await get_embed_color(
      None if ctx.guild is None else ctx.guild.id)

  embed = nextcord.Embed(
      title="Help Menu",
      description=
      f"Welcome to the help menu! To start your adventure, use `{command_prefix_str}start`!\n\nYou can earn titles and achievements! Simply complete various tasks and milestones!\n\nYou can use `{command_prefix_str}area` to move around and go on an adventure with `{command_prefix_str}adventure`!\n\nType `{command_prefix_str}profile` to see your stats!\nIf you feel extra fancy, you can use `{command_prefix_str}img_profile` or `{command_prefix_str}ip`!~\n\nA lot of the commands have aliases,\nso make sure to look them up using `{command_prefix_str}help <command name>`!\n\nYou can use `{command_prefix_str}area` to move around.\nSoon, you will even have access to a tutorial! :P\n\n------------------------------------\nUsage: `{command_prefix_str}help <command>`\n------------------------------------\nBot creator: <@243351582052188170>\n------------------------------------",
      colour=embed_color)

  embed.set_author(name=ctx.bot.user.name,
                   url="https://magi-bot.tyrthurey.repl.co/",
                   icon_url=ctx.bot.user.avatar.url)

  embed.add_field(
      name="RPG Commands",
      value=
      f"`{command_prefix_str}start`\n`{command_prefix_str}profile`\n`{command_prefix_str}img_profile`\n`{command_prefix_str}profile_settings`\n`{command_prefix_str}adventure`\n`{command_prefix_str}area`\n`{command_prefix_str}titles`\n`{command_prefix_str}achievements`\n`{command_prefix_str}cooldowns`\n`{command_prefix_str}inventory`\n`{command_prefix_str}shop`\n`{command_prefix_str}buy`\n`{command_prefix_str}sell`\n`{command_prefix_str}use`\n`{command_prefix_str}heal`",
      inline=True)
  embed.add_field(
      name="General Commands",
      value=
      f"`{command_prefix_str}changelog`\n---\n`{command_prefix_str}suggest`\n`{command_prefix_str}bug`\n`{command_prefix_str}website`\n`{command_prefix_str}leaderboard`\n`{command_prefix_str}hi`\n`{command_prefix_str}cat`\n`{command_prefix_str}dog`\n`{command_prefix_str}gif`\n`{command_prefix_str}help`\n`{command_prefix_str}get_title`\n`{command_prefix_str}admin`",
      inline=True)
  embed.add_field(
      name="Server Admin Stuff",
      value=f"`{command_prefix_str}settings`\n`{command_prefix_str}setchannel`",
      inline=True)

  #embed.set_thumbnail(url=ctx.bot.user.avatar.url)

  embed.set_footer(
      text=
      f"Help us improve! Use `{command_prefix_str}suggest <suggestion>` and `{command_prefix_str}bug <bug-report>`!",
      icon_url=ctx.bot.user.avatar.url)

  await ctx.send(embed=embed)


# The command decorator should not expect an additional 'bot' argument.
@commands.command(name="help",
                  aliases=["?", "dio"],
                  help="Shows help information for commands.")
async def help(ctx, command_name: str = None):
  if command_name is None:
    await helping(ctx)  # Show help for all commands
  else:
    command = ctx.bot.get_command(command_name)
    if command is not None and not command.hidden:
      await help_for_command(ctx,
                             command)  # Show help for the specified command
    else:
      await ctx.send(f"No command named '{command_name}' found.")


async def help_for_command(ctx, command):
  # Fetch the embed color from settings
  embed_color = await get_embed_color(
      None if ctx.guild is None else ctx.guild.id)

  embed = nextcord.Embed(title=f"Help for '{command.name}'", color=embed_color)

  command_prefix_str = await command_prefix(ctx.bot, ctx.message)
  command_name = f"{command_prefix_str}{command.name}"
  help_text = command.help or "No description provided."

  if command.aliases:
    aliases = ", ".join(
        [f"{command_prefix_str}{alias}" for alias in command.aliases])
    help_text += f"\n*Aliases: {aliases}*"

  embed.add_field(name=command_name, value=help_text, inline=True)

  await ctx.send(embed=embed)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(help)

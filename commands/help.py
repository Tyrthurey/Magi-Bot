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

  embed = nextcord.Embed(title='Help Menu', color=embed_color)
  embed.add_field(
      name="",
      value=
      f"Welcome to the help menu!\nTo start your adventure, use `{command_prefix_str}start`!",
      inline=False)
  embed.add_field(
      name="",
      value=
      f"You can earn titles and achievements!\n Simply complete various tasks and milestones!",
      inline=False)
  embed.add_field(
      name="",
      value=
      f"You can use `{command_prefix_str}area` to move around! \nAnd `{command_prefix_str}profile` to see your stats!",
      inline=False)
  embed.add_field(name="",
                  value=f"Soon, you will even have access to a tutorial!",
                  inline=False)
  embed.add_field(name="",
                  value=f"Usage: `{command_prefix_str}help <command>`",
                  inline=False)

  embed.set_footer(text=ctx.bot.user.name, icon_url=ctx.bot.user.avatar.url)
  for command in ctx.bot.commands:
    if command.hidden:
      continue
    command_name = f"{command_prefix_str}{command.name}"

    embed.add_field(name=command_name, value="", inline=True)

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

import asyncio
from datetime import datetime
import nextcord
from nextcord.ext import commands
from main import bot, cooldown_manager_instance, get_embed_color, load_settings  # Import necessary objects from your project


class Cooldowns(commands.Cog):

  def __init__(self, bot):
    self.bot = bot
    self.cooldown_list = []

  @nextcord.slash_command(
      name="cooldowns", description="Displays your current command cooldowns.")
  async def slash_cooldowns(self,
                            interaction: nextcord.Interaction,
                            discord_user: nextcord.User = None):
    # Determine the target user for the cooldown display
    user = discord_user if discord_user else interaction.user
    embed_color = await get_embed_color(
        None if interaction.guild is None else interaction.guild.id)

    user_id = user.id
    username = user.display_name
    avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
    # if interaction.guild is not None:
    #   guild_settings = await load_settings(interaction.guild.id)
    #   guild_prefix = guild_settings.get('prefix', 'apo ')
    # else:
    #   guild_prefix = 'apo '

    embed = nextcord.Embed(title='Cooldowns', color=embed_color)
    embed.set_author(name=username, icon_url=avatar_url)

    commands = ['adventure', 'hunt', 'daily']

    # Loop through all commands and get cooldowns from the CooldownManager
    for command in commands:

      # Get the remaining cooldown for this command and user
      cooldown_remaining = cooldown_manager_instance.get_cooldown(
          user_id, command)

      if cooldown_remaining > 0:
        # Command is on cooldown
        minutes, seconds = divmod(int(cooldown_remaining), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        if days > 0:
          cooldown_message = f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
          cooldown_message = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
          cooldown_message = f"{minutes}m {seconds}s"
        else:
          cooldown_message = f"{seconds}s"
        # Add the command and its cooldown status to the embed
        self.cooldown_list.append(
            f":x: ~ **`{command}`** (**{cooldown_message}**)")
      else:
        # Command is not on cooldown
        self.cooldown_list.append(f":white_check_mark: ~ **`{command}`**")

    embed.add_field(name="",
                    value="\n".join(self.cooldown_list[-10:]),
                    inline=False)

    # Send the embed
    await interaction.response.send_message(embed=embed)
    self.cooldown_list = []

  @commands.command(name="cooldowns",
                    aliases=["cd"],
                    help="Displays your current command cooldowns.")
  async def cooldowns(self, ctx, *, user: nextcord.User = None):
    embed_color = await get_embed_color(
        None if ctx.guild is None else ctx.guild.id)
    # If no user is specified, show the profile of the author of the message
    if user is None:
      user = ctx.author

    user_id = user.id
    username = user.display_name
    avatar_url = user.avatar.url if user.avatar else user.default_avatar.url

    # if ctx.guild.id is not None:
    #   guild_settings = await load_settings(ctx.guild.id)
    #   guild_prefix = guild_settings.get('prefix', 'apo ')
    # else:
    #   guild_prefix = 'apo '

    embed = nextcord.Embed(title='Cooldowns', color=embed_color)
    embed.set_author(name=username, icon_url=avatar_url)

    commands = ['adventure', 'hunt', 'daily']

    # Loop through all commands and get cooldowns from the CooldownManager
    for command in commands:

      # Get the remaining cooldown for this command and user
      cooldown_remaining = cooldown_manager_instance.get_cooldown(
          user_id, command)

      if cooldown_remaining > 0:
        # Command is on cooldown
        minutes, seconds = divmod(int(cooldown_remaining), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        if days > 0:
          cooldown_message = f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
          cooldown_message = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
          cooldown_message = f"{minutes}m {seconds}s"
        else:
          cooldown_message = f"{seconds}s"
        # Add the command and its cooldown status to the embed
        self.cooldown_list.append(
            f":x: ~ **`{command}`** (**{cooldown_message}**)")
      else:
        # Command is not on cooldown
        self.cooldown_list.append(f":white_check_mark: ~ **`{command}`**")

    embed.add_field(name="",
                    value="\n".join(self.cooldown_list[-10:]),
                    inline=False)

    # Send the embed
    await ctx.send(embed=embed)
    self.cooldown_list = []


def setup(bot):
  bot.add_cog(Cooldowns(bot))

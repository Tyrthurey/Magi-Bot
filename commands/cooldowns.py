import asyncio
from datetime import datetime
import nextcord
from nextcord.ext import commands
from main import bot, cooldown_manager_instance, get_embed_color, load_settings  # Import necessary objects from your project


class Cooldowns(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

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
    guild_settings = await load_settings(ctx.guild.id)
    guild_prefix = guild_settings.get(
        'prefix', '::')  # Use the default prefix if not found in the settings

    embed = nextcord.Embed(title='Cooldowns', color=embed_color)
    embed.set_author(name=username, icon_url=avatar_url)

    # Loop through all commands and get cooldowns from the CooldownManager
    for command in bot.commands:
      # Skip if the command is hidden
      if command.hidden:
        continue

      # Get the remaining cooldown for this command and user
      cooldown_remaining = cooldown_manager_instance.get_cooldown(
          user_id, command.name)

      if cooldown_remaining > 0:
        # Command is on cooldown
        minutes, seconds = divmod(int(cooldown_remaining), 60)
        hours, minutes = divmod(minutes, 60)
        cooldown_message = f":x: {hours}h {minutes}m {seconds}s remaining"
        # Add the command and its cooldown status to the embed
        embed.add_field(name=f"{guild_prefix}{command.name}",
                        value=cooldown_message,
                        inline=False)

    # If the embed has no fields, it means no commands are on cooldown
    if len(embed.fields) == 0:
      embed.description = "No commands on cooldown!"

    # Send the embed
    await ctx.send(embed=embed)


def setup(bot):
  bot.add_cog(Cooldowns(bot))

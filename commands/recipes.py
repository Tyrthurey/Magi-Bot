from nextcord.ext import commands
from nextcord import slash_command, SlashOption
import nextcord
from nextcord import Embed, ButtonStyle, ui
from nextcord.ui import Button, View
from main import bot, supabase
from functions.load_settings import get_embed_color
from classes.Player import Player
from functions.using_command_failsafe import using_command_failsafe_instance as failsafes


class Recipes(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @slash_command(name="recipes",
                 description="Crafting recipes and information.")
  async def recipes_slash(self, interaction: nextcord.Interaction):
    await self.recipes(interaction)

  @commands.command(name="recipes",
                    aliases=["recipe"],
                    help="Crafting recipes and information.")
  async def recipes_text(self, ctx):
    await self.recipes(ctx)

  async def recipes(self, interaction):
    # If it's a text command, get the author from the context
    if isinstance(interaction, commands.Context):
      user_id = interaction.author.id
      author = interaction.author
      channel = interaction.channel
      send_message = interaction.send
    # If it's a slash command, get the author from the interaction
    elif isinstance(interaction, nextcord.Interaction):
      user_id = interaction.user.id
      author = interaction.user
      channel = interaction.channel
      send_message = interaction.response.send_message

    self.player = Player(author)

    # Check if the player is already in a command
    if self.player.using_command:
      using_command_failsafe = failsafes.get_last_used_command_time(
          user_id, "general_failsafe")
      if not using_command_failsafe > 0:
        await send_message("Failsafe activated! Commencing with command!")
        self.player.using_command = False
      else:
        await send_message(
            "You're already in a command. Finish it before starting another.\n"
            f"Failsafe will activate in `{using_command_failsafe:.2f}` seconds if you're stuck."
        )
        return

    embed_color = await get_embed_color(
        None if interaction.guild is None else interaction.guild.id)

    embed = nextcord.Embed(title="Recipes", color=embed_color)

    embed.add_field(name="Recipes", value="recipe 1, 2, 3")

    await send_message(embed=embed)

    # Instead of `ctx.send`, use `send_message`
    # Instead of `ctx.author`, use the `author` variable

    # When sending responses for slash commands, use `await interaction.response.send_message` aka "send_message()"
    # For follow-up messages, use `await interaction.followup.send`

    # Example:
    # await send_message("This is a response that works for both text and slash commands.")


def setup(bot):
  bot.add_cog(Recipes(bot))

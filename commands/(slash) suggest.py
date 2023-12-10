import asyncio
import logging
import os
import nextcord
from nextcord.ext import commands
from nextcord.ui import Button, View
from supabase import Client, create_client
from dotenv import load_dotenv
from functions.load_settings import get_embed_color

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


# Create a class for the cog
class SuggestionCog(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  # Function to handle the suggestion submission
  async def submit_suggestion(self, interaction, user_id, username,
                              suggestion):
    # Insert the suggestion into the Supabase database
    response = await interaction.client.loop.run_in_executor(
        None,
        lambda: supabase.table('Suggestions').insert({
            'user_id': user_id,
            'username': username,
            'suggestion': suggestion
        }).execute())

    if response:
      await interaction.followup.send(
          "Your suggestion has been submitted successfully!")
    else:
      await interaction.followup.send(
          "There was an error submitting your suggestion.")

  # Function to create the confirmation embed
  async def confirm_suggestion(self, interaction, suggestion):
    avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
    embed_color = await get_embed_color(
        interaction.guild.id if interaction.guild else None)
    embed = nextcord.Embed(title=":notepad_spiral: Suggestion Confirmation",
                           description=f"**Your Suggestion:**\n{suggestion}",
                           color=embed_color)
    embed.set_author(name=interaction.user.display_name, icon_url=avatar_url)

    # Create buttons
    view = View()

    async def yes_callback(button_interaction: nextcord.Interaction):
      await self.submit_suggestion(interaction, interaction.user.id,
                                   str(interaction.user), suggestion)
      view.stop()

    async def no_callback(button_interaction: nextcord.Interaction):
      await button_interaction.response.send_message("Suggestion cancelled.",
                                                     ephemeral=False)
      view.stop()

    yes_button = Button(style=nextcord.ButtonStyle.green, label="Yes")
    yes_button.callback = yes_callback
    view.add_item(yes_button)

    no_button = Button(style=nextcord.ButtonStyle.red, label="No")
    no_button.callback = no_callback
    view.add_item(no_button)

    await interaction.response.send_message(embed=embed, view=view)

  # The command decorator for the 'suggest' command
  @nextcord.slash_command(name="suggest", description="Submit a suggestion.")
  async def suggest_command(self, interaction: nextcord.Interaction,
                            suggestion: str):
    user_data_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Users').select('using_command').eq(
            'discord_id', interaction.user.id).execute())
    if not user_data_response.data:
      await interaction.response.send_message("You do not have a profile yet.")
      return

    user_data = user_data_response.data[0]
    using_command = user_data['using_command']
    # Check if the player is already in a command
    if using_command:
      await interaction.response.send_message(
          "You're already in a command. Finish it before starting another.")
      return
    await self.confirm_suggestion(interaction, suggestion)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_cog(SuggestionCog(bot))

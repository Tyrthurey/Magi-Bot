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


# Function to handle the suggestion submission
async def submit_suggestion(ctx, user_id, username, suggestion):
  # Insert the suggestion into the Supabase database
  response = await ctx.bot.loop.run_in_executor(
      None,
      lambda: supabase.table('Suggestions').insert({
          'user_id': user_id,
          'username': username,
          'suggestion': suggestion
      }).execute())

  if response:
    await ctx.send("Your suggestion has been submitted successfully!")
  else:
    await ctx.send("There was an error submitting your suggestion.")


# Function to create the confirmation embed
async def confirm_suggestion(ctx, suggestion):
  avatar_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
  embed_color = await get_embed_color(
      None if ctx.guild is None else ctx.guild.id)
  embed = nextcord.Embed(title="Suggestion Confirmation",
                         description=f"**Your Suggestion:**\n{suggestion}",
                         color=embed_color)
  embed.set_author(name=ctx.author.display_name, icon_url=avatar_url)

  # Create buttons
  view = View()

  async def yes_callback(interaction):
    if interaction.user != ctx.author:
      await interaction.response.send_message(
          "You are not allowed to do this.", ephemeral=True)
      return
    await submit_suggestion(ctx, ctx.author.id, str(ctx.author), suggestion)
    view.stop()

  async def no_callback(interaction):
    if interaction.user != ctx.author:
      await interaction.response.send_message(
          "You are not allowed to do this.", ephemeral=True)
      return
    await interaction.response.send_message("Suggestion cancelled.",
                                            ephemeral=True)
    view.stop()

  yes_button = Button(style=nextcord.ButtonStyle.green, label="Yes")
  yes_button.callback = yes_callback
  view.add_item(yes_button)

  no_button = Button(style=nextcord.ButtonStyle.red, label="No")
  no_button.callback = no_callback
  view.add_item(no_button)

  await ctx.send(embed=embed, view=view)


# The command decorator for the 'suggest' command
@commands.command(name="suggest",
                  aliases=["suggestion", "sugg"],
                  help="Submit a suggestion.\n\nUsage: `suggest <suggestion>`")
async def suggest_command(ctx, *, suggestion):
  user_data_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Players').select('using_command').eq(
          'discord_id', ctx.author.id).execute())
  if not user_data_response.data:
    await ctx.send("You do not have a profile yet.")
    return

  user_data = user_data_response.data[0]
  using_command = user_data['using_command']
  # Check if the player is already in a command
  if using_command:
    await ctx.send(
        "You're already in a command. Finish it before starting another.")
    return
  await confirm_suggestion(ctx, suggestion)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(suggest_command)

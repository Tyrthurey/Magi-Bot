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


# Function to handle the bug submission
async def submit_bug(ctx, user_id, username, bug_description):
  # Insert the bug into the Supabase database
  response = await ctx.bot.loop.run_in_executor(
      None, lambda: supabase.table('BugReports').insert(
          {
              'user_id': user_id,
              'username': username,
              'bug_description': bug_description
          }).execute())

  if response:
    await ctx.send("Your bug report has been submitted successfully!")
  else:
    await ctx.send("There was an error submitting your bug report.")


# Function to create the confirmation embed
async def confirm_bug(ctx, bug_description):
  avatar_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
  embed_color = await get_embed_color(ctx.guild.id)
  embed = nextcord.Embed(
      title="Bug Report Confirmation",
      description=f"**Your Bug Report:**\n{bug_description}",
      color=embed_color)
  embed.set_author(name=ctx.author.display_name, icon_url=avatar_url)

  # Create buttons
  view = View()

  async def yes_callback(interaction):
    if interaction.user != ctx.author:
      await interaction.response.send_message(
          "You are not allowed to do this.", ephemeral=True)
      return
    await submit_bug(ctx, ctx.author.id, str(ctx.author), bug_description)
    view.stop()

  async def no_callback(interaction):
    if interaction.user != ctx.author:
      await interaction.response.send_message(
          "You are not allowed to do this.", ephemeral=True)
      return
    await interaction.response.send_message("Bug report cancelled.",
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
@commands.command(name="bug",
                  help="Report a bug.\n\nUsage: `bug <bug description>`")
async def bug_command(ctx, *, bug):
  await confirm_bug(ctx, bug)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(bug_command)

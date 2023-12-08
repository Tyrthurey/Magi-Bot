from datetime import datetime
import nextcord
from nextcord.ui import Button, View
from nextcord.ext import commands
import os
import json
from main import supabase


class DevProfileSettings(commands.Cog):

  def __init__(self, bot):
    self.bot = bot
    self.profile_pictures = {
        'male': os.listdir('commands/resources/male_pfps'),
        'female': os.listdir('commands/resources/female_pfps')
    }
    self.current_index = 0
    self.current_gender = 'male'
    self.ctx = None

  @commands.command(
      name="dev_profile_settings",
      #aliases=["psettings", "ps", "profsettings", "profilesettings"],
      help="Displays the user's profile settings.")
  async def profile_settings(self, ctx):
    self.ctx = ctx
    # Fetch current profile picture from database
    current_profile_pic = 'default.png'  # Replace with actual database query

    embed = nextcord.Embed(title="Profile Settings",
                           color=nextcord.Color.blue())
    embed.set_image(url=f'attachment://{current_profile_pic}')

    view = nextcord.ui.View()

    embed.set_author(name="Apocalypse RPG")
    embed.add_field(
        name="Change Profile Picture",
        value=
        "Here you can choose from a variety of male and female avatars!~ (Currently only 6 per gender available, more coming soon)",
        inline=True)
    embed.add_field(
        name="Use Discord Avatar",
        value=
        "Pressing this, you set your Discord profile picture as your avatar! Soon, you will be able to choose profile rings as well.",
        inline=True)
    embed.add_field(
        name="Choose Avatar Ring",
        value=
        "Paired with 'Use Discord Avatar'. Not available yet. When it will be, it will alow you to choose a custom ring around your profile~",
        inline=True)

    # Add buttons for selecting avatar, background, and profile ring
    select_avatar_button = nextcord.ui.Button(
        label="Select Avatar",
        custom_id="select_avatar",
        style=nextcord.ButtonStyle.primary)
    select_avatar_button.callback = self.select_avatar
    view.add_item(select_avatar_button)

    select_background_button = nextcord.ui.Button(
        label="Select Background",
        custom_id="select_background",
        style=nextcord.ButtonStyle.primary)
    select_background_button.callback = self.select_background
    view.add_item(select_background_button)

    select_ring_button = nextcord.ui.Button(label="Select Profile Ring",
                                            custom_id="select_profile_ring",
                                            style=nextcord.ButtonStyle.primary)
    select_ring_button.callback = self.select_profile_ring
    view.add_item(select_ring_button)

    view.timeout = 300

    await ctx.send(embed=embed, view=view)

  # Modal class for selecting avatar
  class AvatarSelectionModal(nextcord.ui.Modal):

    def __init__(self, callback):
      super().__init__(title="Select Your Avatar")
      self.callback = callback
      self.avatar_id = nextcord.ui.TextInput(
          label="Avatar ID",
          placeholder="Enter the ID of the avatar you want to use")

    async def on_submit(self, interaction: nextcord.Interaction):
      avatar_id = int(self.avatar_id.value)  # Validate and convert to int
      await self.callback(interaction, avatar_id)

  # Callback for avatar selection button
  async def select_avatar(self, interaction: nextcord.Interaction):
    modal = self.AvatarSelectionModal(callback=self.update_avatar_selection)
    await interaction.response.send_modal(modal)

  # Method to handle avatar selection update
  async def update_avatar_selection(self, interaction: nextcord.Interaction,
                                    avatar_id: int):
    user_id = interaction.user.id
    # Fetch and update user's avatar ID in the database
    # (Implement similar methods for background and profile ring selection)

  # Existing update_user_settings method...


def setup(bot):
  bot.add_cog(DevProfileSettings(bot))

from datetime import datetime
import nextcord
from nextcord.ui import Button, View
from nextcord.ext import commands
import os
import json
from main import supabase


class ProfileSettings(commands.Cog):

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
      name="profile_settings",
      aliases=["psettings", "ps", "profsettings", "profilesettings"],
      help="Displays the user's profile settings.")
  async def profile_settings(self, ctx):
    self.ctx = ctx
    # Fetch current profile picture from database
    current_profile_pic = 'default.png'  # Replace with actual database query

    embed = nextcord.Embed(title="Profile Settings",
                           color=nextcord.Color.blue())
    embed.set_image(url=f'attachment://{current_profile_pic}')

    view = nextcord.ui.View()
    change_pp = nextcord.ui.Button(label="Change Profile Picture",
                                   custom_id="change_pp")
    change_pp.callback = self.change_profile_picture
    view.add_item(change_pp)

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

    # Add 'Use Discord Avatar' button
    use_discord_avatar_button = nextcord.ui.Button(
        label="Use Discord Avatar",
        custom_id="use_discord_avatar",
        style=nextcord.ButtonStyle.secondary)
    use_discord_avatar_button.callback = self.use_discord_avatar
    view.add_item(use_discord_avatar_button)

    view.timeout = 300

    await ctx.send(embed=embed, view=view)

  async def use_discord_avatar(self, interaction: nextcord.Interaction):
    if interaction.user != self.ctx.author:
      await interaction.response.send_message("These aint yo settings, bro.",
                                              ephemeral=True)
      return

    # Set profile picture to use Discord avatar
    new_settings = {
        "profile_pic_name": "discord",
        "profile_pic_gender": "discord"
    }

    # Update the user's settings in the Inventory table
    user_id = interaction.user.id
    await self.update_user_settings(user_id, new_settings)

    await interaction.response.send_message(
        "Profile picture set to use Discord avatar.", ephemeral=False)

  async def change_profile_picture(self, interaction: nextcord.Interaction):
    if interaction.user != self.ctx.author:
      await interaction.response.send_message("These aint yo settings, bro.",
                                              ephemeral=True)
      return

    view = nextcord.ui.View()
    # Correct way to assign a callback to a button
    male_button = nextcord.ui.Button(label="Male",
                                     custom_id="male",
                                     style=nextcord.ButtonStyle.primary)
    male_button.callback = self.display_gender_pictures

    female_button = nextcord.ui.Button(label="Female",
                                       custom_id="female",
                                       style=nextcord.ButtonStyle.primary)
    female_button.callback = self.display_gender_pictures

    view.add_item(male_button)
    view.add_item(female_button)

    await interaction.response.edit_message(view=view)

  async def display_gender_pictures(self, interaction: nextcord.Interaction):
    gender = interaction.data['custom_id']
    self.current_gender = gender  # Update the current gender
    self.current_index = 0  # Reset the index to 0
    file_name = self.profile_pictures[gender][self.current_index]

    file_path = os.path.join('commands', 'resources', f'{gender}_pfps',
                             file_name)
    file = nextcord.File(file_path, filename=file_name)
    embed = nextcord.Embed(
        title=f"Choose Your {gender.capitalize()} Profile Picture",
        color=nextcord.Color.green())
    embed.set_image(url=f'attachment://{file_name}')

    view = nextcord.ui.View()

    prev_button = nextcord.ui.Button(
        label="Previous",
        custom_id="prev",
        style=nextcord.ButtonStyle.secondary,
    )

    prev_button.callback = self.picture_navigation
    view.add_item(prev_button)

    next_button = nextcord.ui.Button(
        label="Next",
        custom_id="next",
        style=nextcord.ButtonStyle.secondary,
    )

    next_button.callback = self.picture_navigation
    view.add_item(next_button)

    save_button = nextcord.ui.Button(
        label="Choose This",
        custom_id="choose",
        style=nextcord.ButtonStyle.success,
    )

    save_button.callback = self.save_picture_choice
    view.add_item(save_button)

    await interaction.response.edit_message(embed=embed, view=view, file=file)

  async def picture_navigation(self, interaction: nextcord.Interaction):
    if interaction.user != self.ctx.author:
      await interaction.response.send_message("These aint yo settings, bro.",
                                              ephemeral=True)
      return
    action = interaction.data['custom_id']
    gender = self.current_gender  # Use the current gender

    if action == 'next':
      self.current_index = (self.current_index + 1) % len(
          self.profile_pictures[gender])
    elif action == 'prev':
      self.current_index = (self.current_index - 1 + len(
          self.profile_pictures[gender])) % len(self.profile_pictures[gender])

    file_name = self.profile_pictures[gender][self.current_index]
    file_path = os.path.join('commands', 'resources', f'{gender}_pfps',
                             file_name)
    file = nextcord.File(
        file_path, filename=file_name)  # Create file object for the image

    embed = nextcord.Embed(
        title=f"Choose Your {gender.capitalize()} Profile Picture",
        color=nextcord.Color.green())
    embed.set_image(url=f'attachment://{file_name}')

    await interaction.response.edit_message(embed=embed, file=file)

  async def save_picture_choice(self, interaction: nextcord.Interaction):
    if interaction.user != self.ctx.author:
      await interaction.response.send_message("These aint yo settings, bro.",
                                              ephemeral=True)
      return
    gender = self.current_gender  # Determine current gender selection
    if 0 <= self.current_index < len(self.profile_pictures[gender]):
      chosen_pic = self.profile_pictures[gender][self.current_index]
      # Directly create a dictionary for settings
      new_settings = {
          "profile_pic_name": chosen_pic,
          "profile_pic_gender": gender
      }

      # Update the user's settings in the Inventory table
      user_id = interaction.user.id
      await self.update_user_settings(user_id, new_settings)

      await interaction.response.send_message(
          "Profile picture updated successfully!", ephemeral=False)
    else:
      # Handle the error, perhaps reset the index or send an error message
      await interaction.response.send_message("Invalid picture selection.",
                                              ephemeral=False)

  async def update_user_settings(self, user_id, new_settings):
    supabase.table('Inventory').update({
        'settings': new_settings
    }).eq('discord_id', user_id).execute()
    # Handle update_response appropriately


# Remember to add the necessary error handling and database interaction code
def setup(bot):
  bot.add_cog(ProfileSettings(bot))

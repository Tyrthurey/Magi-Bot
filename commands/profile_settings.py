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
        'male': os.listdir('commands/resources/male_pfps/showcase'),
        'female': os.listdir('commands/resources/female_pfps/showcase')
    }
    self.background_pictures = os.listdir(
        'commands/resources/profile_bgs/showcase')
    self.current_index = 0
    self.current_gender = 'male'
    self.ctx = None
    self.avatar_id = 0

  @commands.command(
      name="profile_settings",
      aliases=["psettings", "ps", "profsettings", "profilesettings"],
      help="Displays the user's profile settings.")
  async def profile_settings(self, ctx):
    self.ctx = ctx
    user_cosmetics = await self.fetch_user_cosmetics(ctx.author.id)

    if user_cosmetics:
      # Extracting avatars
      unlocked_avatars = next(
          (item['unlocked_avatars']
           for item in user_cosmetics if 'unlocked_avatars' in item), [])
      self.unlocked_avatar_ids = [
          avatar['avatar_id'] for avatar in unlocked_avatars
      ]

      # Extracting backgrounds
      unlocked_backgrounds = next(
          (item['unlocked_backgrounds']
           for item in user_cosmetics if 'unlocked_backgrounds' in item), [])
      self.unlocked_background_ids = [
          background['background_id'] for background in unlocked_backgrounds
      ]

      # Extracting profile rings
      unlocked_rings = next(
          (item['unlocked_profile_rings']
           for item in user_cosmetics if 'unlocked_profile_rings' in item), [])
      self.unlocked_ring_ids = [
          ring['profile_ring_id'] for ring in unlocked_rings
      ]

      # Printing the IDs for debugging
      print("Unlocked Avatars:", self.unlocked_avatar_ids)
      print("Unlocked Backgrounds:", self.unlocked_background_ids)
      print("Unlocked Profile Rings:", self.unlocked_ring_ids)

    # Fetch current profile picture from database
    # current_profile_pic = '0.png'  # Replace with actual database query

    embed = nextcord.Embed(title="Profile Settings",
                           color=nextcord.Color.blue())
    # embed.set_image(url=f'attachment://{current_profile_pic}')

    view = nextcord.ui.View()

    embed.set_author(name="Apocalypse RPG")
    embed.add_field(
        name="Change Profile Picture",
        value="Here you can choose from a variety of male and female avatars!"
        f"\n**Unlocked IDs:** `{self.unlocked_avatar_ids}`",
        inline=True)
    embed.add_field(name="Change Background",
                    value="Here you can choose from a variety of backgrounds!"
                    f"\n**Unlocked IDs:** `{self.unlocked_background_ids}`",
                    inline=True)
    embed.add_field(
        name="Choose Avatar Ring",
        value="Paired with 'Use Discord Avatar'. Not available yet."
        f"\n**Unlocked IDs:** `{self.unlocked_ring_ids}`",
        inline=True)

    # Add buttons for selecting avatar, background, and profile ring
    select_avatar_button = nextcord.ui.Button(
        label="Select Avatar",
        custom_id="select_avatar",
        style=nextcord.ButtonStyle.primary)
    select_avatar_button.callback = self.change_avatar
    view.add_item(select_avatar_button)

    select_background_button = nextcord.ui.Button(
        label="Select Background",
        custom_id="select_background",
        style=nextcord.ButtonStyle.primary)
    select_background_button.callback = self.display_bg_pictures
    view.add_item(select_background_button)

    select_ring_button = nextcord.ui.Button(label="Select Profile Ring",
                                            custom_id="select_profile_ring",
                                            style=nextcord.ButtonStyle.primary)
    select_ring_button.callback = self.select_profile_ring
    # view.add_item(select_ring_button)

    view.timeout = 300

    await ctx.send(embed=embed, view=view)

  def create_start_embed(self):
    embed = nextcord.Embed(title="Profile Settings",
                           color=nextcord.Color.blue())
    embed.set_author(name="Apocalypse RPG")
    embed.add_field(
        name="Change Profile Picture",
        value="Here you can choose from a variety of male and female avatars!"
        f"\n**Unlocked IDs:** `{self.unlocked_avatar_ids}`",
        inline=True)
    embed.add_field(name="Change Background",
                    value="Here you can choose from a variety of backgrounds!"
                    f"\n**Unlocked IDs:** `{self.unlocked_background_ids}`",
                    inline=True)
    embed.add_field(
        name="Choose Avatar Ring",
        value="Paired with 'Use Discord Avatar'. Not available yet."
        f"\n**Unlocked IDs:** `{self.unlocked_ring_ids}`",
        inline=True)
    # Depending on your functionality, add more fields to the initial embed as needed
    return embed

  async def go_back_to_start(self, interaction: nextcord.Interaction):
    if interaction.user != self.ctx.author:
      await interaction.response.send_message("These ain't yo settings, bro.",
                                              ephemeral=True)
      return
    # Create the original view
    original_view = self.create_start_view()
    # Create the original embed
    original_embed = self.create_start_embed()
    # Edit the message with the original embed and view
    await interaction.response.edit_message(embed=original_embed,
                                            view=original_view,
                                            attachments=[])

  def create_start_view(self):
    view = nextcord.ui.View()

    select_avatar_button = nextcord.ui.Button(
        label="Select Avatar",
        custom_id="select_avatar",
        style=nextcord.ButtonStyle.primary)
    select_avatar_button.callback = self.change_avatar

    select_background_button = nextcord.ui.Button(
        label="Select Background",
        custom_id="select_background",
        style=nextcord.ButtonStyle.primary)
    select_background_button.callback = self.display_bg_pictures

    select_ring_button = nextcord.ui.Button(label="Select Profile Ring",
                                            custom_id="select_profile_ring",
                                            style=nextcord.ButtonStyle.primary)
    select_ring_button.callback = self.select_profile_ring

    view.add_item(select_avatar_button)
    view.add_item(select_background_button)
    #view.add_item(select_ring_button)

    return view

  async def use_discord_avatar(self, interaction: nextcord.Interaction):
    if interaction.user != self.ctx.author:
      await interaction.response.send_message("These ain't yo settings, bro.",
                                              ephemeral=True)
      return

    user_id = interaction.user.id
    current_settings = await self.fetch_user_settings(user_id)

    # Update the settings for using Discord avatar
    for setting in current_settings:
      if 'premade_avatar' in setting:
        setting['premade_avatar'] = "False"

    await self.update_user_settings(user_id, current_settings)
    await interaction.response.send_message(
        "Profile picture set to use Discord avatar.", ephemeral=False)

  # Modal class for selecting avatar
  class SelectionModal(nextcord.ui.Modal):

    def __init__(self, title, label, callback):
      super().__init__(title=title)
      self._callback = callback  # Store the callback as an internal attribute
      self.add_item(
          nextcord.ui.TextInput(label=label,
                                placeholder="Enter the ID you want to use.",
                                min_length=1,
                                max_length=18))

    async def callback(self, interaction: nextcord.Interaction):
      id_value = self.children[0].value.strip()
      if id_value.isdigit():
        await self._callback(interaction, int(id_value))
      else:
        await interaction.response.send_message("Please enter a valid number.",
                                                ephemeral=True)

  async def change_avatar(self, interaction: nextcord.Interaction):
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

    # Add 'Use Discord Avatar' button
    use_discord_avatar_button = nextcord.ui.Button(
        label="Use Discord Avatar",
        custom_id="use_discord_avatar",
        style=nextcord.ButtonStyle.secondary)
    use_discord_avatar_button.callback = self.use_discord_avatar
    view.add_item(use_discord_avatar_button)

    # Add a back button to the view
    back_button = nextcord.ui.Button(label="Back",
                                     custom_id="back_to_start",
                                     style=nextcord.ButtonStyle.secondary)
    back_button.callback = self.go_back_to_start
    view.add_item(back_button)

    await interaction.response.edit_message(view=view)

  async def display_gender_pictures(self, interaction: nextcord.Interaction):
    if interaction.user != self.ctx.author:
      await interaction.response.send_message("These ain't yo settings, bro.",
                                              ephemeral=True)
      return
    gender = interaction.data['custom_id']
    self.current_gender = gender  # Update the current gender
    self.current_index = 0  # Reset the index to 0
    file_name = self.profile_pictures[gender][self.current_index]

    file_path = os.path.join('commands', 'resources', f'{gender}_pfps',
                             'showcase', file_name)
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

    prev_button.callback = self.avatar_picture_navigation
    view.add_item(prev_button)

    next_button = nextcord.ui.Button(
        label="Next",
        custom_id="next",
        style=nextcord.ButtonStyle.secondary,
    )

    next_button.callback = self.avatar_picture_navigation
    view.add_item(next_button)

    save_button = nextcord.ui.Button(
        label="Input ID",
        custom_id="choose",
        style=nextcord.ButtonStyle.success,
    )
    # Add a back button to the view
    back_button = nextcord.ui.Button(label="Main Menu",
                                     custom_id="back_to_start",
                                     style=nextcord.ButtonStyle.secondary)
    back_button.callback = self.go_back_to_start
    view.add_item(back_button)

    save_button.callback = self.select_avatar
    view.add_item(save_button)

    await interaction.response.edit_message(embed=embed, view=view, file=file)

  async def avatar_picture_navigation(self, interaction: nextcord.Interaction):
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
                             'showcase', file_name)
    file = nextcord.File(
        file_path, filename=file_name)  # Create file object for the image

    embed = nextcord.Embed(
        title=f"Choose Your {gender.capitalize()} Profile Picture",
        color=nextcord.Color.green())
    embed.set_image(url=f'attachment://{file_name}')

    await interaction.response.edit_message(embed=embed, file=file)

  async def display_bg_pictures(self, interaction: nextcord.Interaction):
    if interaction.user != self.ctx.author:
      await interaction.response.send_message("These ain't yo settings, bro.",
                                              ephemeral=True)
      return
    self.current_index = 0  # Reset the index to 0
    file_name = self.background_pictures[self.current_index]

    file_path = os.path.join('commands', 'resources', 'profile_bgs',
                             'showcase', file_name)
    file = nextcord.File(file_path, filename=file_name)
    embed = nextcord.Embed(title="Choose Your Background",
                           color=nextcord.Color.green())
    embed.set_image(url=f'attachment://{file_name}')

    view = nextcord.ui.View()

    prev_button = nextcord.ui.Button(
        label="Previous",
        custom_id="prev",
        style=nextcord.ButtonStyle.secondary,
    )

    prev_button.callback = self.background_picture_navigation
    view.add_item(prev_button)

    next_button = nextcord.ui.Button(
        label="Next",
        custom_id="next",
        style=nextcord.ButtonStyle.secondary,
    )

    next_button.callback = self.background_picture_navigation
    view.add_item(next_button)

    save_button = nextcord.ui.Button(
        label="Input ID",
        custom_id="choose",
        style=nextcord.ButtonStyle.success,
    )

    save_button.callback = self.select_background
    view.add_item(save_button)

    back_button = nextcord.ui.Button(label="Main Menu",
                                     custom_id="back_to_start",
                                     style=nextcord.ButtonStyle.secondary)
    back_button.callback = self.go_back_to_start
    view.add_item(back_button)

    await interaction.response.edit_message(embed=embed, view=view, file=file)

  async def background_picture_navigation(self,
                                          interaction: nextcord.Interaction):
    if interaction.user != self.ctx.author:
      await interaction.response.send_message("These aint yo settings, bro.",
                                              ephemeral=True)
      return
    action = interaction.data['custom_id']

    if action == 'next':
      self.current_index = (self.current_index + 1) % len(
          self.background_pictures)
    elif action == 'prev':
      self.current_index = (self.current_index - 1 + len(
          self.background_pictures)) % len(self.background_pictures)

    file_name = self.background_pictures[self.current_index]
    file_path = os.path.join('commands', 'resources', f'profile_bgs',
                             'showcase', file_name)
    file = nextcord.File(
        file_path, filename=file_name)  # Create file object for the image

    embed = nextcord.Embed(title="Choose Your Background",
                           color=nextcord.Color.green())
    embed.set_image(url=f'attachment://{file_name}')

    await interaction.response.edit_message(embed=embed, file=file)

  async def select_avatar(self, interaction: nextcord.Interaction):
    try:
      modal = self.SelectionModal("Select Your Avatar", "Avatar ID",
                                  self.update_avatar_selection)
      await interaction.response.send_modal(modal)
    except Exception as e:
      print(f"Error in sending modal: {e}")

  async def select_background(self, interaction: nextcord.Interaction):
    modal = self.SelectionModal("Select Your Background", "Background ID",
                                self.update_background_selection)
    await interaction.response.send_modal(modal)

  async def select_profile_ring(self, interaction: nextcord.Interaction):
    modal = self.SelectionModal("Select Your Profile Ring", "Profile Ring ID",
                                self.update_profile_ring_selection)
    await interaction.response.send_modal(modal)

  # Methods to handle selections update
  async def update_avatar_selection(self, interaction: nextcord.Interaction,
                                    avatar_id: int):
    print("Avatar ID:", avatar_id)
    self.avatar_id = avatar_id
    if avatar_id in self.unlocked_avatar_ids:
      await self.save_picture_choice(interaction)
    else:
      await interaction.response.send_message(
          "You have not unlocked this avatar yet.", ephemeral=True)

  async def update_background_selection(self,
                                        interaction: nextcord.Interaction,
                                        background_id: int):
    print("Background ID:", background_id)
    self.background_id = background_id
    if background_id in self.unlocked_background_ids:
      response = await self.bot.loop.run_in_executor(
          None,
          lambda: supabase.table('ProfileBackgrounds').select('color').eq(
              'id', self.background_id).execute())
      data = response.data
      if data and 'color' in data[0]:
        text_color = data[0]['color']

      # Set player attributes with the new stats
      self.text_color = text_color
      print(self.text_color)
      await self.save_background_choice(interaction)
    else:
      await interaction.response.send_message(
          "You have not unlocked this background yet.", ephemeral=True)

  async def update_profile_ring_selection(self,
                                          interaction: nextcord.Interaction,
                                          ring_id: int):
    print("Profile Ring ID:", ring_id)
    # Update logic for profile ring selection
    pass

  async def save_picture_choice(self, interaction: nextcord.Interaction):
    gender = self.current_gender
    if 0 <= self.current_index < len(self.profile_pictures[gender]):
      chosen_pic = self.avatar_id

      user_id = interaction.user.id
      # Fetch current settings and update them
      current_settings = await self.fetch_user_settings(user_id)
      updated_settings = self.update_settings_with_avatar_choice(
          current_settings, chosen_pic, gender)

      await self.update_user_settings(user_id, updated_settings)

      await interaction.response.send_message(
          "Profile picture updated successfully!", ephemeral=False)
    else:
      await interaction.response.send_message("Invalid picture selection.",
                                              ephemeral=False)

  async def save_background_choice(self, interaction: nextcord.Interaction):
    if 0 <= self.current_index < len(self.background_pictures):
      chosen_pic = self.background_id

      user_id = interaction.user.id
      text_color = self.text_color
      # Fetch current settings and update them
      current_settings = await self.fetch_user_settings(user_id)
      updated_settings = self.update_settings_with_bg_choice(
          current_settings, chosen_pic, text_color)

      await self.update_user_settings(user_id, updated_settings)

      await interaction.response.send_message(
          "Profile background updated successfully!", ephemeral=False)
    else:
      await interaction.response.send_message("Invalid background selection.",
                                              ephemeral=False)

  async def fetch_user_settings(self, user_id):
    response = await self.bot.loop.run_in_executor(
        None, lambda: supabase.table('Inventory').select('settings').eq(
            'discord_id', user_id).execute())
    data = response.data
    if data and 'settings' in data[0]:
      settings = data[0]['settings']
      return settings
    return None  # or return a default settings structure

  async def fetch_user_cosmetics(self, user_id):
    response = await self.bot.loop.run_in_executor(
        None,
        lambda: supabase.table('Inventory').select('unlocked_cosmetics').eq(
            'discord_id', user_id).execute())
    data = response.data
    if data and 'unlocked_cosmetics' in data[0]:
      unlocked_cosmetics = data[0]['unlocked_cosmetics']
      return unlocked_cosmetics
    return None

  def update_settings_with_avatar_choice(self, settings, chosen_pic, gender):
    for setting in settings:
      if 'premade_avatar_id' in setting:
        setting['premade_avatar_id'] = chosen_pic
      elif 'premade_avatar_gender' in setting:
        setting['premade_avatar_gender'] = gender
      elif 'premade_avatar' in setting:
        setting['premade_avatar'] = "True"
      # Add more conditions as needed for other settings
    return settings

  def update_settings_with_bg_choice(self, settings, chosen_pic, text_color):
    for setting in settings:
      if 'profile_background_id' in setting:
        setting['profile_background_id'] = chosen_pic
      elif 'profile_text_color' in setting:
        setting['profile_text_color'] = text_color
      # Add more conditions as needed for other settings
    return settings

  async def update_user_settings(self, user_id, new_settings):
    response = await self.bot.loop.run_in_executor(
        None,
        lambda: supabase.table('Inventory').update({
            'settings': new_settings
        }).eq('discord_id', user_id).execute())
    # Handle the response appropriately


def setup(bot):
  bot.add_cog(ProfileSettings(bot))

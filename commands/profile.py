import asyncio
from datetime import datetime
import nextcord
from nextcord.ui import Button, View
from nextcord.ext import commands
from main import bot, supabase  # Import necessary objects from your project
from functions.load_settings import get_embed_color
from classes.Player import Player
from functions.get_achievement import GetAchievement


class StatView(View):

  def __init__(self, bot, ctx, player, user_title, embed_color, avatar_url,
               location_name, username, needed_adv_level_exp,
               get_achievement_cog):
    super().__init__(timeout=300)
    self.bot = bot
    self.ctx = ctx
    self.player = player
    self.username = username
    self.user_title = user_title
    self.embed_color = embed_color
    self.avatar_url = avatar_url
    self.location_name = location_name
    self.needed_adv_level_exp = needed_adv_level_exp
    self.get_achievement_cog = get_achievement_cog

  async def disable_buttons(self):
    for item in self.children:
      if isinstance(item, Button):
        item.disabled = True

  try:

    @nextcord.ui.button(label="+STR", style=nextcord.ButtonStyle.primary)
    async def add_str(self, button: Button, interaction: nextcord.Interaction):
      if interaction.user.id != self.player.user_id:
        await interaction.response.send_message("This isn't your profile!",
                                                ephemeral=True)
        return
      if self.player.free_points > 0:
        self.player.base_strength += 1
        self.player.free_points -= 1
        self.player.save_strength_choice()
        await self.check_and_update_class(interaction)
        await self.update_embed(interaction)

    @nextcord.ui.button(label="+DEX", style=nextcord.ButtonStyle.primary)
    async def add_dex(self, button: Button, interaction: nextcord.Interaction):
      if interaction.user.id != self.player.user_id:
        await interaction.response.send_message("This isn't your profile!",
                                                ephemeral=True)
        return
      if self.player.free_points > 0:
        self.player.base_dexterity += 1
        self.player.free_points -= 1
        self.player.save_dexterity_choice()
        await self.check_and_update_class(interaction)
        await self.update_embed(interaction)

    @nextcord.ui.button(label="+VIT", style=nextcord.ButtonStyle.primary)
    async def add_vit(self, button: Button, interaction: nextcord.Interaction):
      if interaction.user.id != self.player.user_id:
        await interaction.response.send_message("This isn't your profile!",
                                                ephemeral=True)
        return
      if self.player.free_points > 0:
        self.player.base_vitality += 1
        self.player.free_points -= 1
        self.player.save_vitality_choice()
        await self.check_and_update_class(interaction)
        await self.update_embed(interaction)

    @nextcord.ui.button(label="+SAV", style=nextcord.ButtonStyle.primary)
    async def add_cun(self, button: Button, interaction: nextcord.Interaction):
      if interaction.user.id != self.player.user_id:
        await interaction.response.send_message("This isn't your profile!",
                                                ephemeral=True)
        return
      if self.player.free_points > 0:
        self.player.base_cunning += 1
        self.player.free_points -= 1
        self.player.save_cunning_choice()
        await self.check_and_update_class(interaction)
        await self.update_embed(interaction)

    @nextcord.ui.button(label="+MAG", style=nextcord.ButtonStyle.primary)
    async def add_mag(self, button: Button, interaction: nextcord.Interaction):
      if interaction.user.id != self.player.user_id:
        await interaction.response.send_message("This isn't your profile!",
                                                ephemeral=True)
        return
      if self.player.free_points > 0:
        self.player.base_magic += 1
        self.player.free_points -= 1
        self.player.save_magic_choice()
        await self.check_and_update_class(interaction)
        await self.update_embed(interaction)

    async def check_and_update_class(self, interaction):
      # Retrieve and sort the player's stats
      current_stats = {
          'Strength': self.player.base_strength,
          'Vitality': self.player.base_vitality,
          'Dexterity': self.player.base_dexterity,
          'Savvy': self.player.base_cunning,
          'Magic': self.player.base_magic,
          'Luck': self.player.luck
      }

      # Sort stats by value, then alphabetically
      sorted_stats = sorted(current_stats.items(), key=lambda x: (-x[1], x[0]))
      top_stat_name, top_stat_value = sorted_stats[0]

      # Fetch all classes
      classes_response = await bot.loop.run_in_executor(
          None, lambda: supabase.table('Classes').select('*').execute())

      best_match_class = None

      if classes_response.data:
        for class_data in classes_response.data:
          # Check if the top stat meets the primary requirement
          if (class_data['required_top_stat_name'] == top_stat_name
              and class_data['required_top_stat_value'] <= top_stat_value):
            # Check if any stat meets the secondary requirement
            for stat_name, stat_value in current_stats.items():
              if (class_data['required_secondary_stat_name'] == stat_name and
                  class_data['required_secondary_stat_value'] <= stat_value):
                # This class matches the requirements
                best_match_class = class_data
                break

      if best_match_class and best_match_class[
          'class_id'] != self.player.class_id:
        # Update the player's class in the database
        update_response = await bot.loop.run_in_executor(
            None, lambda: supabase.table('Users').update({
                'class':
                best_match_class['class_id']
            }).eq('discord_id', self.player.user_id).execute())

        # Update was successful
        self.player.class_id = best_match_class['class_id']
        await interaction.response.send_message(
            f"**{self.username}**, your class has been changed to **{best_match_class['class_displayname']}**!"
        )
        await self.get_achievement_cog.get_achievement(self.ctx,
                                                       self.player.user_id, 9)

    async def update_embed(self, interaction):
      # Update your embed here with new player stats
      embed = nextcord.Embed(title=self.user_title, color=self.embed_color)
      embed.set_author(name=f"{self.username}'s Profile",
                       icon_url=self.avatar_url)

      embed.add_field(
          name="__Stats:__",
          value=
          f":muscle: **STR:** {self.player.base_strength} ({self.player.strength})\n"
          f":dash: **DEX:** {self.player.base_dexterity} ({self.player.dexterity})\n"
          f":heart_on_fire: **VIT:** {self.player.base_vitality} ({self.player.vitality})\n"
          f":brain: **SAV:** {self.player.base_cunning} ({self.player.cunning})\n"
          f":magic_wand: **MAG:** {self.player.base_magic} ({self.player.magic})\n"
          f":four_leaf_clover: **LUCK:** {self.player.luck}\n"
          f"**Stat Score:** {self.player.stat_score}\n"
          f"**Free Points:** {self.player.free_points}\n",
          inline=True)

      embed.add_field(
          name="__Status:__",
          value=f"**Class:** {self.player.class_displayname}\n"
          f"**:crossed_swords:/:shield:** {self.player.damage}/{self.player.defense}\n"
          f"**<:level:1182666619378487396>** {self.player.level}\n"
          f"**<:EXP:1182800499037196418>** {self.player.adventure_exp}/{self.needed_adv_level_exp}\n"
          f"**<:apocalypse_coin:1182666655420125319>** {self.player.bal}\n"
          f"**:map:** {self.location_name}\n"
          f"**<:life:1175932745256554506>** {self.player.health}/{self.player.max_health}\n"
          f"**:zap:** {self.player.energy}/{self.player.max_energy}",
          inline=True)

      embed.add_field(name="__Equipment:__", value="N/A", inline=False)

      # Set the thumbnail to the user's Discord avatar
      embed.set_thumbnail(url=self.avatar_url)

      # Set the footer to the bot's name and icon
      embed.set_footer(
          text=f"{bot.user.name} - Help us improve! Use ::suggest <suggestion>",
          icon_url=bot.user.avatar.url)
      # Add fields to embed
      await interaction.message.edit(
          embed=embed, view=self if self.player.free_points > 0 else None
      )  # Remove buttons if no points left

      await self.get_achievement_cog.get_achievement(self.ctx,
                                                     self.player.user_id, 5)

      # Award another achievement if the player passes 10 points in any of the primary stats
      if self.player.base_magic >= 10 or self.player.base_cunning >= 10 or self.player.base_vitality >= 10 or self.player.base_dexterity >= 10 or self.player.base_strength >= 10:
        await self.get_achievement_cog.get_achievement(self.ctx,
                                                       self.player.user_id, 6)

      # Award another achievement if the player passes 10 points in any of the primary stats
      if self.player.base_magic >= 10 and self.player.base_cunning >= 10 and self.player.base_vitality >= 10 and self.player.base_dexterity >= 10 and self.player.base_strength >= 10:
        await self.get_achievement_cog.get_achievement(self.ctx,
                                                       self.player.user_id, 8)

  except nextcord.HTTPException as e:
    print(f"HTTPException: {e.text}")


class Profile(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  last_profile_views = {}

  # New function to get location name
  async def get_location_name(self, location_id):
    location_response = await bot.loop.run_in_executor(
        None, lambda: supabase.table('Areas').select('name').eq(
            'id', location_id).execute())
    return location_response.data[0][
        'name'] if location_response.data else 'Unknown'

  @commands.command(name="profile",
                    aliases=["p", "prof"],
                    help="Displays the user's or another user's game profile.")
  async def profile(self, ctx, *, user: nextcord.User = None):
    embed_color = await get_embed_color(
        None if ctx.guild is None else ctx.guild.id)

    # If no user is specified, show the profile of the author of the message
    if user is None:
      user = ctx.author

    user_id = user.id
    username = user.display_name
    avatar_url = user.avatar.url if user.avatar else user.default_avatar.url

    # Create a Player instance for the user
    player = Player(user)

    # If the player does not exist in the database yet
    if not player.exists:
      await ctx.send(
          f"{ctx.author} does not have a profile yet.\nPlease type `::start`.")
      return

    # Fetch the user's next level progression data
    level_progression_response = await bot.loop.run_in_executor(
        None, lambda: supabase.table('LevelProgression').select('*').eq(
            'level', player.level + 1).execute())
    if level_progression_response.data:
      needed_adv_level_exp = level_progression_response.data[0][
          'total_level_exp']
    else:
      needed_adv_level_exp = "N/A"

    # Fetch the user's inventory data from the database
    inventory_response = await bot.loop.run_in_executor(
        None, lambda: supabase.table('Inventory').select('titles').eq(
            'discord_id', user_id).execute())

    # Check if the user has any titles
    user_title = "Rookie Adventurer"  # default title
    if inventory_response.data:
      inventory_data = inventory_response.data[0]
      titles = inventory_data.get('titles', [])

      # Check if the user has an equipped title
      equipped_title = next(
          (title for title in titles if title["equipped"] is True), None)
      if equipped_title:
        # Fetch the title name from the Titles table
        title_response = await bot.loop.run_in_executor(
            None, lambda: supabase.table('Titles').select('title_name').eq(
                'id', equipped_title['title_id']).execute()
        )  # Replace 'id' with your actual column name

        if title_response.data:
          user_title = title_response.data[0]['title_name']
        else:
          user_title = "Rookie Adventurer"

    location = player.location
    location_name = await self.get_location_name(location)

    get_achievement_cog = GetAchievement(self.bot)

    # Check if the user is calling their own profile to decide if stat buttons should be shown
    show_buttons = user is None or user.id == ctx.author.id

    # Disable buttons of the previous profile view for the user if it exists
    last_view = self.last_profile_views.get(ctx.author.id)
    if last_view:
      await last_view.disable_buttons(
      )  # Method to disable buttons in StatView
      await last_view.message.edit(
          view=last_view)  # Update the previous message to remove buttons

    # Create a new StatView only if stat buttons should be shown
    view = StatView(bot, ctx, player, user_title, embed_color, avatar_url,
                    location_name, username, needed_adv_level_exp,
                    get_achievement_cog
                    ) if show_buttons and player.free_points > 0 else None

    # Create the embed with the updated user data
    embed = nextcord.Embed(title=user_title, color=embed_color)
    embed.set_author(name=f"{username}'s Profile", icon_url=avatar_url)

    embed.add_field(
        name="__Stats:__",
        value=f":muscle: **STR:** {player.base_strength} ({player.strength})\n"
        f":dash: **DEX:** {player.base_dexterity} ({player.dexterity})\n"
        f":heart_on_fire: **VIT:** {player.base_vitality} ({player.vitality})\n"
        f":brain: **SAV:** {player.base_cunning} ({player.cunning})\n"
        f":magic_wand: **MAG:** {player.base_magic} ({player.magic})\n"
        f":four_leaf_clover: **LUCK:** {player.luck}\n"
        f"**Stat Score:** {player.stat_score}\n"
        f"**Free Points:** {player.free_points}\n",
        inline=True)

    embed.add_field(
        name="__Status:__",
        value=f"**Class:** {player.class_displayname}\n"
        f"**:crossed_swords:/:shield:** {player.damage}/{player.defense}\n"
        f"**<:level:1182666619378487396>** {player.level}\n"
        f"**<:EXP:1182800499037196418>** {player.adventure_exp}/{needed_adv_level_exp}\n"
        f"**<:apocalypse_coin:1182666655420125319>** {player.bal}\n"
        f"**:map:** {location_name}\n"
        f"**<:life:1175932745256554506>** {player.health}/{player.max_health}\n"
        f"**:zap:** {player.energy}/{player.max_energy}",
        inline=True)

    embed.add_field(name="__Equipment:__", value="N/A", inline=False)

    # Set the thumbnail to the user's Discord avatar
    embed.set_thumbnail(url=avatar_url)

    # Set the footer to the bot's name and icon
    embed.set_footer(
        text=f"{bot.user.name} - Help us improve! Use ::suggest <suggestion>",
        icon_url=bot.user.avatar.url)

    # Send the embed and store the view and message in the dictionary
    message = await ctx.send(embed=embed, view=view)
    if view:
      view.message = message  # Store the message in the view
      self.last_profile_views[ctx.author.id] = view

    get_achievement_cog = GetAchievement(self.bot)
    await get_achievement_cog.get_achievement(ctx, ctx.author.id, 4)

  # @profile.error
  # async def profile_error(self, ctx, error):
  #   if isinstance(error, nextcord.ext.commands.errors.BadArgument):
  #     await ctx.send("Couldn't find that user.")


def setup(bot):
  bot.add_cog(Profile(bot))

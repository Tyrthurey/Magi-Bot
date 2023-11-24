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
        await self.update_embed(interaction)

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
          f"**Atk/Def:** {self.player.damage}/{self.player.defense}\n"
          f"**Level:** {self.player.level}\n"
          f"**EXP:** {self.player.adventure_exp}/{self.needed_adv_level_exp}\n"
          f"**:coin: Gold:** {self.player.bal}\n"
          f"**:map: Location:** {self.location_name}\n"
          f"**<:life:1175932745256554506> Health:** {self.player.health}/{self.player.max_health}\n"
          f"**:zap: Energy:** {self.player.energy}/{self.player.max_energy}",
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

  except nextcord.HTTPException as e:
    print(f"HTTPException: {e.text}")


class Profile(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

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
    # Create and send the embed with the buttons
    view = StatView(bot, ctx, player, user_title, embed_color, avatar_url,
                    location_name, username, needed_adv_level_exp,
                    get_achievement_cog) if player.free_points > 0 else None

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
        f"**Atk/Def:** {player.damage}/{player.defense}\n"
        f"**Level:** {player.level}\n"
        f"**EXP:** {player.adventure_exp}/{needed_adv_level_exp}\n"
        f"**:coin: Gold:** {player.bal}\n"
        f"**:map: Location:** {location_name}\n"
        f"**<:life:1175932745256554506> Health:** {player.health}/{player.max_health}\n"
        f"**:zap: Energy:** {player.energy}/{player.max_energy}",
        inline=True)

    embed.add_field(name="__Equipment:__", value="N/A", inline=False)

    # Set the thumbnail to the user's Discord avatar
    embed.set_thumbnail(url=avatar_url)

    # Set the footer to the bot's name and icon
    embed.set_footer(
        text=f"{bot.user.name} - Help us improve! Use ::suggest <suggestion>",
        icon_url=bot.user.avatar.url)

    # Send the embed
    await ctx.send(embed=embed, view=view)
    get_achievement_cog = GetAchievement(self.bot)
    await get_achievement_cog.get_achievement(ctx, ctx.author.id, 4)

  # @profile.error
  # async def profile_error(self, ctx, error):
  #   if isinstance(error, nextcord.ext.commands.errors.BadArgument):
  #     await ctx.send("Couldn't find that user.")


def setup(bot):
  bot.add_cog(Profile(bot))

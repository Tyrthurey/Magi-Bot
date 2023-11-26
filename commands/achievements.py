from nextcord.ext import commands
from nextcord import Embed, Reaction, User, ButtonStyle, ui
from nextcord.ui import Button, View
import asyncio
import nextcord
from supabase import Client, create_client
from dotenv import load_dotenv
from functions.load_settings import command_prefix, get_embed_color
import os
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


class Paginator(ui.View):

  def __init__(self, ctx, embed_updater, max_pages, embed):
    super().__init__(timeout=60)
    self.ctx = ctx
    self.embed_updater = embed_updater
    self.max_pages = max_pages
    self.page = 0
    self.user_id = ctx.author.id
    self.embed = embed

  @nextcord.ui.button(label="⬅️",
                      style=nextcord.ButtonStyle.primary,
                      custom_id="previous_btn")
  async def previous_button(self, button: ui.Button,
                            interaction: nextcord.Interaction):
    if interaction.user.id != self.user_id:
      await interaction.response.send_message(
          "These aren't your achievements!", ephemeral=True)
      return
    if self.page > 0:
      self.page -= 1
      await self.embed_updater(self.page)
      await interaction.message.edit(embed=self.embed, view=self)

  @nextcord.ui.button(label="➡️",
                      style=nextcord.ButtonStyle.primary,
                      custom_id="next_btn")
  async def next_button(self, button: Button,
                        interaction: nextcord.Interaction):
    if interaction.user.id != self.user_id:
      await interaction.response.send_message(
          "These aren't your achievements!", ephemeral=True)
      return
    if self.page < self.max_pages:
      self.page += 1
      await self.embed_updater(self.page)
      await interaction.message.edit(embed=self.embed, view=self)


class Achievements(commands.Cog):

  def __init__(self, bot):
    self.bot = bot
    self.per_page = 4
    self.page = 0

  async def update_embed(self, page):
    start = page * self.per_page
    end = start + self.per_page
    self.embed.clear_fields()
    self.embed.title = f"Your Achievements"
    self.embed.add_field(name=f"-----------------------------------------",
                         value="",
                         inline=False)

    for i in range(start, min(end, len(self.visible_achievements))):
      achievement_data = self.visible_achievements[i]
      achievement_id = achievement_data['id']
      user_achievement = self.user_achievements_dict.get(achievement_id, None)

      if user_achievement and user_achievement['awarded']:
        self.embed.add_field(
            name=f"{achievement_data['achievement_name']}",
            value=f"📜 {achievement_data['achievement_description']}",
            inline=False)
      else:
        self.embed.add_field(
            name=f"🔒 ~~{achievement_data['achievement_name']}~~ 🔒",
            value=f"📜 {achievement_data['achievement_requirement']}",
            inline=False)
      self.embed.add_field(name=f"-----------------------------------------",
                           value="",
                           inline=False)
    self.embed.add_field(
        name="",
        value=
        f"**Completed:** {self.completed_achievements}/{self.total_achievements}<:literallynothing:1175951091800740000> | <:literallynothing:1175951091800740000>**Hidden:** {self.hidden_achievements}",
        inline=False)
    self.embed.add_field(name=f"Page {page + 1}/{self.max_pages + 1}",
                         value="",
                         inline=False)

  @commands.group(invoke_without_command=True,
                  aliases=["ach", "achievement"],
                  help="Display your achievements.")
  async def achievements(self, ctx):
    self.user_id = ctx.author.id

    # Fetch all achievements from the Achievements table
    all_achievements_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Achievements').select(
            'id, achievement_name, achievement_description, achievement_requirement, hidden'
        ).execute())

    if not all_achievements_response.data:
      await ctx.send("There are no achievements available.")
      return

    all_achievements = sorted(all_achievements_response.data,
                              key=lambda area: area['id'])

    # Fetch the inventory data for the user
    inventory_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Inventory').select('achievements').eq(
            'discord_id', self.user_id).execute())

    inventory_data = inventory_response.data[
        0] if inventory_response.data else None
    user_achievements = inventory_data.get('achievements',
                                           []) if inventory_data else []

    # Convert user achievements to a dict for easy lookup
    self.user_achievements_dict = {ach['id']: ach for ach in user_achievements}

    # Create an embed for the achievements
    embed_color = await get_embed_color(
        None if ctx.guild is None else ctx.guild.id)
    self.embed = Embed(color=embed_color)
    avatar_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
    self.embed.set_author(name=ctx.author.display_name, icon_url=avatar_url)

    self.per_page = 4

    # Calculate visible achievements
    self.visible_achievements = [
        ach for ach in all_achievements if not ach['hidden']
    ]

    self.completed_achievements = len(
        [ach for ach in user_achievements if ach['awarded']])

    self.max_pages = (len(self.visible_achievements) - 1) // self.per_page

    self.total_achievements = len(all_achievements)
    self.hidden_achievements = self.total_achievements - len(
        self.visible_achievements)

    await self.update_embed(0)

    view = Paginator(ctx, self.update_embed, self.max_pages, self.embed)

    await ctx.send(embed=self.embed, view=view)


def setup(bot):
  bot.add_cog(Achievements(bot))

import asyncio
import logging
import os
import random
import math
from nextcord.ext import commands
from nextcord import slash_command, SlashOption
import nextcord
from nextcord import Embed, ButtonStyle, ui
from nextcord.ui import Button, View

from functions.load_settings import get_embed_color
from functions.using_command_failsafe import using_command_failsafe_instance as failsafes

from supabase import Client, create_client
from dotenv import load_dotenv
from functions.item_write import item_write
from functions.cooldown_manager import cooldown_manager_instance as cooldowns
from classes.Player import Player
from classes.Enemy import Enemy

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


class Hunting(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  # New function to get location name
  async def get_location_name(self, location_id):
    location_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Areas').select('name').eq(
            'id', location_id).execute())
    return location_response.data[0][
        'name'] if location_response.data else 'Unknown'

  @slash_command(name="hunt", description="Hunt, kill, loot!")
  async def hunt_slash(self, interaction: nextcord.Interaction):
    await self.hunting(interaction)

  @commands.command(name="hunt", aliases=["h"], help="Hunt, kill, loot!")
  async def new_hunt(self, ctx):
    await self.hunting(ctx)

  async def hunting(self, interaction):
    send_message = interaction
    user_id = None
    author = None
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

    embed_color = await get_embed_color(
        None if interaction.guild is None else interaction.guild.id)

    # If the player does not exist in the database yet
    if not self.player.exists:
      await send_message(
          f"{author} does not have a profile yet.\nPlease type `apo start`.")
      return

    # Check if the player is already in a command
    if self.player.using_command:
      using_command_failsafe = failsafes.get_last_used_command_time(
          user_id, "general_failsafe")
      if not using_command_failsafe > 0:
        # await send_message("Failsafe activated! Commencing with command!")
        self.player.using_command = False
      else:
        embed = nextcord.Embed(title="Already in a command...",
                               color=embed_color)

        embed.add_field(
            name="",
            value=
            "You're already in a command. Finish it before starting another.\n"
            f"Failsafe will activate in `{using_command_failsafe:.0f}` seconds if you're stuck."
        )

        await send_message(embed=embed)
        return

    failsafes.set_last_used_command_time(self.player.user_id, "hunt", 60)
    failsafes.set_last_used_command_time(self.player.user_id,
                                         "general_failsafe", 70)

    action_id = 1

    command_data_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Actions').select('*').eq(
            'id', action_id).execute())

    if not command_data_response.data:
      await send_message("This command does not exist.")
      return

    command_data = command_data_response.data[0]
    command_name = command_data['name']
    command_cd = command_data['normal_cd']
    # command_patreon_cd = command_data['patreon_cd']

    # command_name = ctx.command.name
    cooldown_remaining = cooldowns.get_cooldown(user_id, command_name)

    if cooldown_remaining > 0:
      embed = nextcord.Embed(
          title=f"Command on Cooldown. Wait {cooldown_remaining:.0f}s...",
          color=embed_color)

      embed.add_field(
          name="",
          value=
          f"Tired of waiting? You can help us out by subscribing to our [Patreon](https://www.patreon.com/RCJoshua) for a reduced cooldown!\n*(COMING SOON - NOT YET IMPLEMENTED)*"
      )

      await send_message(embed=embed)
      return

    cooldown = command_cd

    # Set the cooldown for the hunt command
    cooldowns.set_cooldown(user_id, command_name, cooldown)

    self.player.set_using_command(True)
    self.player.combat_log = []

    mob_data_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Mobs').select('*').eq(
            'area', self.player.location).execute())

    location = self.player.location
    location_name = await self.get_location_name(location)

    mobs_list = mob_data_response.data if mob_data_response.data else []
    if not mobs_list:
      await send_message(f"No creatures to hunt in {location_name}.")
      return

    # Select a mob based on appearance chance
    appear_chances = [mob['appear_chance'] for mob in mobs_list]
    print("\n-=-=-=-=-=-=-=-=-=-=-=-=-\nAPPEAR CHANCES: ", appear_chances)
    total_chance = sum(appear_chances)
    roll = random.uniform(0.001, total_chance)
    print("-=-=-=-=-=-=-=-=-=-=-=-=-\nROLL: ", roll,
          "\n-=-=-=-=-=-=-=-=-=-=-=-=-\n")
    current = 0
    # Sort mobs by appear chance, smallest to largest
    mobs_list.sort(key=lambda mob: mob['appear_chance'])
    equal_chance = all(mob['appear_chance'] == mobs_list[0]['appear_chance']
                       for mob in mobs_list)

    if equal_chance:
      selected_mob = random.choice(mobs_list)
    else:
      for mob in mobs_list:
        current += mob['appear_chance']
        if roll <= current:
          selected_mob = mob
          break

    mob_id = selected_mob['id']
    mob_exp = selected_mob['exp']
    mob_gold = selected_mob['gold_drop']

    low_exp, high_exp = map(int, mob_exp)
    low_gold, high_gold = map(int, mob_gold)

    # Initialize Enemy with mob_id and other required parameters (you may need to adjust this per your Enemy class)
    enemy = Enemy(mob_id)

    pl_initiative = random.randint(1,
                                   20) + math.floor(self.player.luck / 5 + 1)
    mob_initiative = random.randint(5, 20)
    first = 'player'
    mob_damage = 0
    player_damage = 0
    level_up = False
    player_win = False

    if pl_initiative > mob_initiative:
      first = 'player'
    elif pl_initiative < mob_initiative:
      first = 'mob'
    else:
      first = 'tie'

    if first == 'player':
      mob_damage = self.player.melee_attack(enemy)
      print(
          f"{self.player.name} attacks {enemy.name} for {mob_damage} damage!")
      self.player.combat_log.append(f"**{self.player.name}** attacks first!")

      if enemy.health > 0:
        player_damage = enemy.attack(self.player)
        print(
            f"{enemy.name} attacks {self.player.name} for {player_damage} damage!"
        )
    elif first == 'mob':
      player_damage = enemy.attack(self.player)
      print(
          f"{enemy.name} attacks {self.player.name} for {player_damage} damage!"
      )
      self.player.combat_log.append(f"{enemy.name} attacks first!")
    else:
      print(
          f"{self.player.name} and {enemy.name} weren't looking well and crashed into each other!"
      )
      self.player.combat_log.append(
          f"**{self.player.name}** and {enemy.name} weren't looking well and crashed into each other!"
      )
      self.player.health = self.player.health - 10
      enemy.health = enemy.health - 10
      mob_damage = mob_damage + 10
      player_damage = player_damage + 10

    while enemy.health > 0 and self.player.health > 0:
      mob_damage = mob_damage + self.player.melee_attack(enemy)
      print(
          f"{self.player.name} attacks {enemy.name} for {mob_damage} damage!")

      player_damage = player_damage + enemy.attack(self.player)
      print(
          f"{enemy.name} attacks {self.player.name} for {player_damage} damage!"
      )

    if self.player.health > 0:
      self.player.combat_log.append(
          f"**{self.player.name}** did `{mob_damage}` damage!")
      self.player.combat_log.append(
          f"{enemy.name} did `{player_damage}` damage!")
      self.player.combat_log.append(f"**{self.player.name}** has won!")
      print(f"{self.player.name} killed {enemy.name}!")
      self.player.combat_log.append(
          f"**{self.player.name}** killed {enemy.name}!")

      exp_reward = math.floor(random.randint(low_exp, high_exp) * 0.7)
      self.player.adventure_exp += exp_reward

      gold_reward = math.floor(random.randint(low_gold, high_gold) * 0.7)
      self.player.bal += gold_reward

      # Fetch level progression data from Supabase
      level_progression_response = await asyncio.get_event_loop(
      ).run_in_executor(
          None,
          lambda: supabase.table('LevelProgression').select('*').execute())

      level_progression_data = {
          str(level['level']): level
          for level in level_progression_response.data
      }

      # Check for level up
      needed_exp_for_next_level = level_progression_data.get(
          str(self.player.level + 1), {}).get('total_level_exp', float('inf'))
      level_up = self.player.adventure_exp >= needed_exp_for_next_level

      if level_up:
        self.player.level += 1
        self.player.adventure_exp = 0
        self.player.free_points += 5

      # Determine if an item is dropped
      drop_chance = enemy.drop_chance
      drop_roll = random.randint(1, 100)  # Roll a number between 1 and 100
      item_dropped = drop_roll <= drop_chance  # Determine if the roll is within the drop chance

      # Debug stuff
      print("------------------------------------------------------------")
      print("Drop chance: ")
      print(drop_chance)
      print("------------------------------------------------------------")
      print("Drop roll: ")
      print(drop_roll)
      print("------------------------------------------------------------")
      print("Item dropped: ")
      print(item_dropped)
      print("------------------------------------------------------------")

      # If an item is dropped, add it to the player's inventory
      if item_dropped:
        dropped_item_id = enemy.drop_item_id
        await item_write(user_id, dropped_item_id, 1)  # Amount is 1

      # Now send a message to the user with the outcome of the hunt
      # Including whether an item was dropped and which mob was encountered
      item_name = "nothing"
      if item_dropped:
        # Fetch the item's display name from Items table
        item_response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: supabase.table('Items').select('item_displayname').eq(
                'item_id', dropped_item_id).execute())
        if item_response.data:
          item_name = item_response.data[0]['item_displayname'].lower()

      # Debug stuff
      print("------------------------------------------------------------")
      print("Item name: ")
      print(item_name)
      print("------------------------------------------------------------")

      player_win = True

    else:
      self.player.combat_log.append(
          f"**{self.player.name}** did `{mob_damage}` damage!")
      self.player.combat_log.append(
          f"{enemy.name} did `{player_damage}` damage!")
      self.player.combat_log.append(f"**{self.player.name}** died...")
      print(f"{enemy.name} killed **{self.player.name}**!")
      self.player.combat_log.append(
          f"{enemy.name} has defeated **{self.player.name}**!")
      self.player.adventure_exp = 0

      gold_loss = random.randint(10, 30)
      self.player.bal = max(
          0, self.player.bal - math.floor(gold_loss / 100 * self.player.bal))
      if self.player.bal < 20:
        self.player.bal = 20
      self.player.health = self.player.max_health
      self.player.deaths = self.player.deaths + 1

      player_win = False

    self.player.save_data()

    embed = nextcord.Embed(title="Hunting...", color=embed_color)

    embed.add_field(
        name="", value=f"**{self.player.name}** encountered a {enemy.name}!\n")

    embed.add_field(name="------------------------------",
                    value="\n".join(self.player.combat_log[-6:]),
                    inline=False)  # Only show the last 4 actions

    if player_win:
      embed.add_field(
          name="------------------------------",
          value=f"Gained `{exp_reward}` <:EXP:1182800499037196418>\n"
          f"Gained `{gold_reward}` <:apocalypse_coin:1182666655420125319>\n"
          f"Current Health: `{self.player.health}/{self.player.max_health}` <:life:1175932745256554506> \n"
          f"{f'**{self.player.name}** got `1` {item_name}' if item_name!='nothing' else ''}\n"
          f"{f'<a:LV_UP:1182650004486242344> Level Up to Lvl `{self.player.level}`! Gained `5` Free Stat Points to use!' if level_up else ''}\n",
          inline=False)
    else:
      embed.add_field(
          name="------------------------------",
          value=
          f"**{self.player.name}** lost all rewards, including their experience towards the next level and `{gold_loss}`% of their gold.\n"
          f"Deaths: `{self.player.deaths}`",
          inline=False)

    await send_message(embed=embed)
    self.player.combat_log = []
    self.player.set_using_command(False)

    # Instead of `ctx.send`, use `send_message`
    # Instead of `ctx.author`, use the `author` variable

    # When sending responses for slash commands, use `await interaction.response.send_message` aka "send_message()"
    # For follow-up messages, use `await interaction.followup.send`

    # Example:
    # await send_message("This is a response that works for both text and slash commands.")


def setup(bot):
  bot.add_cog(Hunting(bot))

import asyncio
import logging
import math
import nextcord
import os
import random
import time

from dotenv import load_dotenv
from nextcord.ui import Button
from supabase import Client, create_client

from classes.CombatView import CombatView
from functions.item_write import item_write
from functions.check_inventory import check_inventory
from functions.item_write import item_write

logging.basicConfig(level=logging.INFO)

load_dotenv()

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)


class AdvCombatView(CombatView):

  def __init__(self, ctx, player, enemy):
    super().__init__(ctx, player, enemy)
    self.ctx = ctx
    self.player = player
    self.enemy = enemy
    self.combat_log = []
    self.cooldowns = {}
    self.threat_level = enemy.determine_threat_level(player.strength +
                                                     player.dexterity +
                                                     player.vitality +
                                                     player.cunning +
                                                     player.magic)

  # def update_button_states(self, player_turn: bool):
  #   #Enable buttons if it's the player's turn, disable otherwise.
  #   for item in self.children:
  #     if isinstance(item, nextcord.ui.Button):
  #       item.disabled = not player_turn

  async def interaction_check(self, interaction):
    # Only the user who started the hunt can interact with the buttons
    return interaction.user == self.ctx.author

  # async def on_timeout(self):
  #   # Handle what happens when the view times out
  #   await self.ctx.send(f"Combat with {self.enemy.name} has timed out.")

  def is_on_cooldown(self, user):
    return user.id in self.cooldowns and time.time() < self.cooldowns[user.id]

  # Starts a cooldown for a user
  def start_cooldown(self, user, duration=2):
    self.cooldowns[user.id] = time.time() + duration

  async def update_embed(self, interaction):
    avatar_url = self.ctx.author.avatar.url if self.ctx.author.avatar else self.ctx.author.default_avatar.url
    embed = nextcord.Embed(title=f"{self.player.name}'s adventure")
    embed.set_thumbnail(url='')
    embed.add_field(
        name=f"{self.enemy.name}'s Stats",
        value=f"**Threat Level:** {self.threat_level}\n{str(self.enemy)}",
        inline=False)
    embed.add_field(name="__Your Stats__",
                    value=str(self.player),
                    inline=False)
    embed.add_field(name="------------------------------",
                    value="\n".join(self.combat_log[-6:]),
                    inline=False)  # Only show the last 4 actions
    embed.add_field(name="------------------------------",
                    value="",
                    inline=False)

    embed.add_field(name="",
                    value="⚔️ --> Melee Attack \n🛡️ --> Defend",
                    inline=True)

    embed.add_field(name="", value="🔨 --> Use Item \n💨 --> Flee", inline=True)

    await interaction.message.edit(embed=embed, view=self)

  # In the CombatView class.
  @nextcord.ui.button(label="⚔️", style=nextcord.ButtonStyle.green)
  async def melee_attack_button(self, button: Button,
                                interaction: nextcord.Interaction):
    # Check for cooldown before proceeding with melee attack
    if self.is_on_cooldown(interaction.user):
      await interaction.response.send_message(
          "You're doing that too often. Try again in a few seconds.",
          ephemeral=True)
      return
    # If not on cooldown, handle the melee attack and start cooldown
    await self.handle_combat_turn(interaction, "melee")
    self.start_cooldown(interaction.user)

  @nextcord.ui.button(label="🛡️", style=nextcord.ButtonStyle.gray)
  async def defend(self, button: Button, interaction: nextcord.Interaction):
    # Defense logic
    if self.is_on_cooldown(interaction.user):
      await interaction.response.send_message(
          "You're doing that too often. Try again in a few seconds.",
          ephemeral=True)
      return
    # If not on cooldown, handle the melee attack and start cooldown
    await self.handle_combat_turn(interaction, "defend")
    self.start_cooldown(interaction.user)

  @nextcord.ui.button(label="🔨",
                      style=nextcord.ButtonStyle.blurple,
                      disabled=True)
  async def use_item(self, button: Button, interaction: nextcord.Interaction):
    # Item usage logic

    ITEM_ID = 1

    # Check if the user has a health potion in inventory
    inventory_response = await check_inventory(self.player.user_id, ITEM_ID,
                                               'item')

    if ITEM_ID == 1000:
      if inventory_response > 0:
        # Decrease the pill count by one
        await item_write(self.player.user_id, ITEM_ID, -1)
        heal_amount = random.randint(15, 25)
        self.player.health += heal_amount
        if self.player.health >= self.player.max_health:
          self.player.health = self.player.max_health
        self.combat_log.append(
            f"**{self.player.name}** uses a <:healthpotion:1175114505013968948> **Health Potion (Lesser)**: +`{heal_amount}` HP!"
        )
      else:
        self.combat_log.append(
            f"**{self.player.name}** desn't have any Lesser Health Potions. Sadge."
        )
    await self.update_embed(interaction)
    # Check for end of combat
    await self.handle_combat_turn(interaction, "item")
    self.start_cooldown(interaction.user)

  @nextcord.ui.button(label="💨", style=nextcord.ButtonStyle.red)
  async def flee(self, button: Button, interaction: nextcord.Interaction):
    await self.handle_combat_turn(interaction, "flee")

  # ------------------------------------------------------------------------------------
  # Death handler
  # ------------------------------------------------------------------------------------

  async def handle_death(self, interaction: nextcord.Interaction):
    # Call this method when the player's health reaches 0
    self.combat_log.append(f"**{self.player.name}** has been defeated!")

    self.player.adventure_exp = 0
    # level_change = 0  if self.player.level == 1 else 1

    # self.player.level = self.player.level - level_change
    gold_loss = random.randint(10, 30)
    self.player.bal = max(
        0, self.player.bal - math.floor(gold_loss / 100 * self.player.bal))
    if self.player.bal < 20:
      self.player.bal = 20
    self.player.health = self.player.max_health
    self.player.deaths = self.player.deaths + 1

    lostrewardsmsg = (
        # f"**{self.player.name}** lost all rewards, including `{level_change}` level and `{gold_loss}`% of their gold."
        #if level_change > 0 else
        f"**{self.player.name}** lost all rewards, including their experience towards the next level and `{gold_loss}`% of their gold."
    )

    # Update the embed to show the player's action
    await self.update_embed(interaction)
    await self.ctx.send(
        f"**{self.player.name}** could not handle a {self.enemy.name}! Noob.\n"
        f"{lostrewardsmsg}\n"
        f"Deaths: `{self.player.deaths}`")

    self.player.set_using_command(False)  # Reset the using_command field
    self.player.save_data()
    self.stop()  # Stop the view to clean up

  async def handle_enemy_defeat(self, interaction: nextcord.Interaction):
    self.combat_log.append(f"{self.enemy.name} has been defeated!")
    self.player.set_using_command(False)

    # Determine if an item is dropped
    drop_chance = self.enemy.drop_chance
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
      dropped_item_id = self.enemy.drop_item_id
      await item_write(self.ctx.author.id, dropped_item_id, 1)  # Amount is 1

    # Now send a message to the user with the outcome of the hunt
    # Including whether an item was dropped and which mob was encountered
    item_name = "nothing"
    if item_dropped:
      # Fetch the item's display name from Items table
      item_response = await asyncio.get_event_loop().run_in_executor(
          None, lambda: supabase.table('Items').select('item_displayname').eq(
              'item_id', dropped_item_id).execute())
      if item_response.data:
        item_name = item_response.data[0]['item_displayname'].lower()

    # Debug stuff
    print("------------------------------------------------------------")
    print("Item name: ")
    print(item_name)
    print("------------------------------------------------------------")

    # Calculate the experience gained
    additional_exp = random.randint(0, 10) + self.enemy.exp_drop

    self.player.adventure_exp = self.player.adventure_exp + additional_exp

    # Fetch level progression data from Supabase
    level_progression_response = await asyncio.get_event_loop(
    ).run_in_executor(
        None, lambda: supabase.table('LevelProgression').select('*').execute())

    level_progression_data = {
        str(level['level']): level
        for level in level_progression_response.data
    }

    # Check for level up
    needed_exp_for_next_level = level_progression_data.get(
        str(self.player.level + 1), {}).get('total_level_exp', float('inf'))
    level_up = self.player.adventure_exp >= needed_exp_for_next_level

    gold_reward = random.randint(50,
                                 90) + self.player.location * random.randint(
                                     20, 50) + self.player.location * 10
    self.player.bal = self.player.bal + gold_reward

    stat_ratio = self.player.damage / self.enemy.atk
    # Message templates
    message2_templates = [
        f"The {self.enemy.name} never stood a chance against **{self.player.name}**'s DOUBLE TROUBLE ATTACK!!!",
        f"With TWICE the power, **{self.player.name}** sends the {self.enemy.name} flying into next week!!",
        f"**{self.player.name}**'s power level is OVER 9000, annihilating the {self.enemy.name} with DOUBLE FORCE!!!",
        f"The earth quakes as **{self.player.name}** unleashes a DUAL-WIELD SMASH on the {self.enemy.name}!!!",
        f"Watch out! **{self.player.name}**'s DOUBLE DRAGON STRIKE turns the {self.enemy.name} into stardust!!",
        f"It's a one-hit K.O.! **{self.player.name}**'s TWIN FIST FURY decimates the {self.enemy.name}!!",
        f"**{self.player.name}** channels DOUBLE SPIRIT ENERGY and obliterates the {self.enemy.name}!!!",
        f"With a TWOFOLD SLASH, **{self.player.name}** cuts the {self.enemy.name} down to size!!",
        f"**{self.player.name}**'s DOUBLE DASH DANCE leaves the {self.enemy.name} in a dizzy daze!!!",
        f"In a flash, **{self.player.name}**'s TWIN TORNADO TECHNIQUE whirls the {self.enemy.name} away!!!"
    ]

    message3_templates = [
        f"**{self.player.name}** ABSOLUTELY DECIMATED a {self.enemy.name} by having TRIPLE stats!?! \n",
        f"**{self.player.name}** triples the terror with a TRI-FORCE TAKEDOWN on the {self.enemy.name}!!!\n",
        f"THREE TIMES THE MIGHT! **{self.player.name}** launches a TRIPLE THUNDER STRIKE on the {self.enemy.name}!!\n",
        f"**{self.player.name}** summons THREE DRAGONS OF DOOM to devour the {self.enemy.name}!!\n",
        f"It's a TRIPLE TROUBLE TRAMPLE! **{self.player.name}** stomps the {self.enemy.name} into oblivion!!!\n",
        f"With TRIPLE SWORD SYMPHONY, **{self.player.name}** slices the {self.enemy.name} into cosmic confetti!!\n",
        f"**{self.player.name}**'s TRIPLE ENERGY ECLIPSE blasts the {self.enemy.name} into another dimension!!\n",
        f"In an epic showdown, **{self.player.name}**'s TRI-BEAM BLAST vaporizes the {self.enemy.name}!!!\n",
        f"**{self.player.name}** performs a TRIPLE SPIRIT SHOT, sending the {self.enemy.name} to the shadow realm!!\n",
        f"THREE-HEADED HYDRA HAVOC! **{self.player.name}**'s attack leaves the {self.enemy.name} in ruins!!\n",
        f"**{self.player.name}** unleashes a TRIPLE WIND WHIRLWIND, sweeping the {self.enemy.name} off their feet!!\n"
    ]

    message4_templates = [
        f"QUAD DAMAGE! **{self.player.name}**'s FOUR-FOLD FURY flattens the {self.enemy.name}!!!\n",
        f"In a blaze of glory, **{self.player.name}**'s QUADRUPLE QUASAR QUEST incinerates the {self.enemy.name}!!!\n",
        f"**{self.player.name}**'s FOUR HORSEMEN CHARGE tramples the {self.enemy.name} into dust!!!\n",
        f"With a QUADRUPLE KAMEHAMEHA, **{self.player.name}** blasts the {self.enemy.name} to the next galaxy!!\n",
        f"QUAD-LOCKED! **{self.player.name}** locks the {self.enemy.name} in a four-dimensional prison!!!\n",
        f"FOUR-FISTED FRENZY! **{self.player.name}** pummels the {self.enemy.name} with unstoppable force!!\n",
        f"The {self.enemy.name} is caught in **{self.player.name}**'s QUADRUPLE SPIRAL SLASH vortex!!!\n",
        f"**{self.player.name}** executes a PERFECT QUADRUPLE COMBO, sending the {self.enemy.name} to oblivion!!\n",
        f"QUADRUPLE CLONE CATASTROPHE! **{self.player.name}**'s clones overwhelm the {self.enemy.name}!!\n",
        f"In a flash of light, **{self.player.name}**'s QUADRA DRAGON DANCE devours the {self.enemy.name}!!\n",
    ]

    message2_template = random.choice(message2_templates)
    message3_template = random.choice(message3_templates)
    message4_template = random.choice(message4_templates)

    message1 = (
        f"**{self.player.name}** BULLIED THE :broken_heart: HEARTBROKEN {self.enemy.name} SO HARD THEIR HEART STOPPED DUE TO THEIR ***OCTUPLE STATS***!!!!?!?!?!?!?! \n"
        if stat_ratio >= 8 else
        f"**{self.player.name}** made {self.enemy.name} happy ONLY TO DESTROY THEIR WHOLE LIFE AND MARRIAGE :broken_heart: due to having ***SEPTUPLE*** the stats!!!!????????? \n"
        if stat_ratio >= 7 else
        f"**{self.player.name}** **DESTROYS EVERYTHING** THE {self.enemy.name} LOVES by having ***SEXTUPLE*** their stats!!!!???? \n"
        if stat_ratio >= 6 else
        f"**{self.player.name}** DOES UNSPEAKABLE THINGS to the poor {self.enemy.name} simply by having ***PENTUPLE*** the stats!!!! \n"
        if stat_ratio >= 5 else message4_template
        if stat_ratio >= 4 else message3_template if stat_ratio >= 3 else
        f"**{self.player.name}** killed a {self.enemy.name}! \n")

    message2 = (
        f"**{self.player.name}** BULLIED THE :broken_heart: HEARTBROKEN {self.enemy.name} SO HARD THEIR HEART STOPPED DUE TO THEIR ***OCTAPLE STATS***!!!!?!?!?!?!?! \n"
        if stat_ratio >= 8 else
        f"**{self.player.name}** made {self.enemy.name} happy ONLY TO DESTROY THEIR WHOLE LIFE AND :broken_heart: MARRIAGE due to having ***SEPTUPLE*** the stats!!!!????????? \n"
        if stat_ratio >= 7 else
        f"**{self.player.name}** **DESTROYS EVERYTHING** THE {self.enemy.name} LOVES by having ***SEXTUPLE*** their stats!!!!???? \n"
        if stat_ratio >= 6 else
        f"**{self.player.name}** DOES UNSPEAKABLE THINGS to the poor {self.enemy.name} simply by having ***PENTUPLE*** the stats!!!! \n"
        if stat_ratio >= 5 else message4_template
        if stat_ratio >= 4 else message3_template if stat_ratio >= 3 else
        f"**{self.player.name}** killed a {self.enemy.name}! \n")

    if level_up:
      self.player.level = self.player.level + 1
      self.player.adventure_exp -= needed_exp_for_next_level  # Reset exp to 0 for next level, carry over exp
      self.player.free_points = self.player.free_points + 5

    await self.ctx.send(
        f'{message1}'
        f"Gained `{additional_exp}` <:EXP:1182800499037196418>, and `{gold_reward}` <:apocalypse_coin:1182666655420125319>! \n"
        f"Current Health: `{self.player.health}/{self.player.max_health}` <:life:1175932745256554506> \n"
        f"{f'<a:LV_UP:1182650004486242344> Level Up to Lvl `{self.player.level}`! Gained `5` Free Stat Points to use!' if level_up else ''}\n"
        f"{f'**{self.player.name}** got `1` {item_name}' if item_name!='nothing' else ''}"
    )

    self.player.save_data()
    # Update the embed to show the player's action
    await self.update_embed(interaction)
    self.player.set_using_command(False)  # Reset the using_command field

    self.stop()  # Stop the view to clean up
    pass

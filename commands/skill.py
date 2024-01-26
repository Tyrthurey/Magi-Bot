import asyncio
from sys import int_info
from nextcord.ext import commands
from nextcord import slash_command
import nextcord
from main import supabase
from functions.load_settings import get_embed_color
from classes.Player import Player
from functions.using_command_failsafe import using_command_failsafe_instance as failsafes
from functions.cooldown_manager import cooldown_manager_instance as cooldowns

# Assuming you have a function to fetch data from your database


def get_user_data(player):
  # Implement logic to get the player's Discord user data
  return player


def calculate_damage(mana, player):
  # Damage calculation logic
  return 5 * mana  # Example calculation


def get_enemy_data(enemy_id):
  # Implement logic to get the enemy's data
  return {'enemy_id': enemy_id}  # Placeholder return


def select_target(entity):
  # Logic to select the target entity (player or enemy)
  return entity


# def activate_skill(skill_sequence, player, target=None):
#   # Execute the skill based on the processed sequence
#   result = ""
#   for action in skill_sequence[:-1]:  # Exclude 'activate' from this loop
#     if action.isdigit():
#       # If action is a number (e.g., mana cost)
#       result += f"Used {action} mana. "
#     elif action in skill_actions:
#       result += skill_actions[action](player, target) + " "
#   return result


class Skill(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  async def fetch_skill(self, skill_id):
    # Replace with actual database fetching logic
    # For example, fetching from Supabase:
    data = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Skills').select('*').eq(
            'skill_id', skill_id).execute())
    return data.data[0] if data.data else None

  # @slash_command(name="skill", description="Command information.")
  # async def command_slash(self, interaction: nextcord.Interaction,
  #                         skill_id: int):
  #   await self.use_skill(interaction, skill_id)

  @commands.command(name="skill", aliases=["sk"], help="Command information.")
  async def command_text(self, ctx, skill_id: int, *args):
    await self.use_skill(ctx, skill_id, *args)

  async def use_skill(self, interaction, skill_id: int, *args):
    send_message = interaction
    author = "Unknown"
    user_id = 0

    print(args)
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

    player = Player(author)

    embed_color = await get_embed_color(
        None if interaction.guild is None else interaction.guild.id)

    # Check if the player is already in a command
    if player.using_command:
      using_command_failsafe = failsafes.get_last_used_command_time(
          user_id, "general_failsafe")
      if not using_command_failsafe > 0:
        # await send_message("Failsafe activated! Commencing with command!")
        player.using_command = False
      else:
        await send_message(
            "You're already in a command. Finish it before starting another.\n"
            f"Failsafe will activate in `{using_command_failsafe:.2f}` seconds if you're stuck."
        )
        return

    skill_data = await self.fetch_skill(skill_id)
    if not skill_data:
      await send_message("Skill not found.")
      return

    # Dictionary mapping skill sequence terms to actions
    # skill_actions = {
    #     "self": get_user_data,
    #     # "explosion": calculate_damage,
    #     # "enemy": get_enemy_data,
    #     # "select_target": select_target,
    #     # "activate": activate_skill
    # }

    skill_sequence = skill_data["skill_sequence"]
    skill_sequence = skill_sequence["skill_sequence"]
    fail = False
    complete = False
    recipient = player

    heal_amount = 0
    skill_log = []
    print(skill_sequence)

    for element in skill_sequence:
      if not fail and not complete:
        if element == "self":
          recipient = player

          # Check if the first argument is a player mention and initialize Player
          if args and args[0].startswith('<@') and args[0].endswith(
              '>'):  # Check if it's a mention
            mentioned_id = int(
                args[0][2:-1])  # Extract the ID from the mention
            user = await self.bot.fetch_user(mentioned_id)
            recipient = Player(user)  # Initialize Player with the mentioned ID

          skill_log.append(f"Selected target: {recipient.name}.")

        # elif element == "enemy":
        #   recipient = "enemy"

        elif element == "heal":
          # Next element should be 'heal' if this is a heal amount
          previous_index = skill_sequence.index(element) - 1
          try:
            heal_value = int(skill_sequence[previous_index])
          except ValueError:
            fail = True
            continue

          if player.energy >= heal_value:
            print(f"Mana used: {heal_value}")
            skill_log.append(f"Energy used: {heal_value}")
            heal_amount = heal_value * 5
            print(f"Heal amount: {heal_amount}")
            skill_log.append(f"Healed {heal_amount} HP.")
            recipient.health += heal_amount
            if recipient.health > recipient.max_health:
              recipient.health = recipient.max_health
            player.energy -= heal_value
          else:
            fail = True
            skill_log.append(f"Not enough energy to heal {heal_value} HP.")
        elif element == "activate":
          complete = True

    if complete:
      recipient.save_data()
      player.save_data()
      embed = nextcord.Embed(title=f"Skill Used: {skill_data['skill_name']}",
                             description="\n".join(skill_log),
                             color=embed_color)
      await send_message(embed=embed)
    else:
      embed = nextcord.Embed(title="Skill Failed",
                             description="\n".join(skill_log),
                             color=embed_color)
      await send_message(embed=embed)

    # Instead of `ctx.send`, use `send_message`
    # Instead of `ctx.author`, use the `author` variable

    # When sending responses for slash commands, use `await interaction.response.send_message` aka "send_message()"
    # For follow-up messages, use `await interaction.followup.send`

    # Example:
    # await send_message("This is a response that works for both text and slash commands.")


def setup(bot):
  bot.add_cog(Skill(bot))

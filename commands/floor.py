import nextcord
from nextcord.ext import commands
from nextcord.ext.commands import has_permissions
from classes.Player import Player
from classes.TutorialView import TutorialView


# Bot command to send a random dog picture
@commands.command(name="floor", help="Go to an unlocked dungeon floor.")
@has_permissions(administrator=True)
async def floor(ctx, floor_num: int):
  player = Player(ctx.author)

  # Check if the player is already in a command
  if player.using_command:
    await ctx.send(
        "You're already in a command. Finish it before starting another.")
    return

  if not floor_num:
    await ctx.send("Specify a floor number. Usage: `apo floor <number>`")
    return

  player.set_using_command(True)

  # Define your tutorial messages here
  tutorial_messages = [
      # Tutorial part 1
      "Floors are different areas in the dungeon.\n"
      "They hold one type of mob with certain variations depending on its leading stat.",
      # Tutorial part 2
      "The higher up you go, the harder the mobs!\nBut remember, returning to a lower floor while up high carries a penalty if your stats are five or more times higher than the mob you are hunting ;)",
      # Tutorial part 3
      "The penalty is... death. After you so shamelessly completely disintegrate their kind, a monster will eventually rise up, hiding its strength, and kick you right where it hurts; the ~~nu-~~ level.",
      # Add all the tutorial parts here...
      "Have fun!~\nTo go to a certain floor just type `floor <number>`!"
  ]

  if player.max_floor < floor_num:
    await ctx.send(
        "You can't go to a floor, go fight the dungeon boss or earn the right hidden achievement, noob."
    )
    player.set_using_command(False)
    player.save_data()
    return
  elif player.floor == floor_num:
    await ctx.send("You're already on this floor, dumbass!")
    player.set_using_command(False)
    player.save_data()
    return
  else:
    # Check if the user is new and should see the tutorial
    if player.floor_tutorial:
      # Show the tutorial
      tutorial_view = TutorialView(ctx, tutorial_messages)
      await ctx.send(content=tutorial_messages[0], view=tutorial_view)
      # Wait for the tutorial to be done
      await tutorial_view.tutorial_done.wait()
      ctx.send(f"You have moved to floor {floor_num}.")
      player.floor = floor_num


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(floor)

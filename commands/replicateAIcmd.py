import asyncio
from nextcord.ext import commands
from nextcord import slash_command, SlashOption
import nextcord
from nextcord import Embed, ButtonStyle, ui
from nextcord.ui import Button, View
from main import bot, supabase
from functions.load_settings import get_embed_color
from classes.Player import Player
from functions.using_command_failsafe import using_command_failsafe_instance as failsafes
from functions.cooldown_manager import cooldown_manager_instance as cooldowns
import os
from PIL import Image, ImageSequence
import io
import functools
import replicate
from difflib import get_close_matches
import replicate.exceptions
import time
import requests
import random

token = os.getenv("REPLICATE_API_TOKEN") or ""

model_dict = {
    "stable_diffusion": "stability-ai/stable-diffusion",
    # "pokemon": "lambdal/text-to-pokemon",
    # "pixel_art": "andreasjansson/monkey-island-sd",
    # "logo": "laion-ai/erlich",
    # "anime": "cjwbw/waifu-diffusion",
    "sdxl": "stability-ai/sdxl",
    "animate-diffusion": "lucataco/animate-diff",
    "stable-video-diffusion": "stability-ai/stable-video-diffusion"
}

timestamp_dict = {
    "stable_diffusion": 30,
    # "pokemon": 2,
    # "pixel_art": 2,
    # "logo": 2,
    # "anime": 2,
    "sdxl": 30,
    "animate-diffusion": 66,
    "stable-video-diffusion": 140
}


class Replicate(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @slash_command(
      name="imagine",
      description=
      "Generate an image or video from a text prompt using the specified model."
  )
  async def command_slash(
      self,
      interaction: nextcord.Interaction,
      model: str = SlashOption(
          name="model",
          description="Choose the AI model for image generation",
          required=True,
          choices=model_dict.keys()),
      prompt: str = SlashOption(
          name="prompt",
          description="Enter the text prompt for the AI model",
          required=True)):
    await self.command(interaction, model, prompt)

  @commands.command(
      name="imagine",
      aliases=["im"],
      help="Generate an image from a text prompt using the specified model.")
  async def command_text(self, ctx, model, *, prompt):
    await self.command(ctx, model, prompt)

  async def command(self, interaction, model, prompt):
    print("COMMAND TRIGGERED")
    # author = "Unknown"
    # user_id = 0
    # If it's a text command, get the author from the context
    if isinstance(interaction, commands.Context):
      print("ITS A CTX COMMAND!")
      user_id = interaction.author.id
      author = interaction.author
      channel = interaction.channel
      channel_send = interaction.send
      edit_message = None
      edit_after_defer = None
      reply_message = interaction.reply
      delete_message = None
      followup_message = interaction.reply
      send_message = interaction.send
    # If it's a slash command, get the author from the interaction
    elif isinstance(interaction, nextcord.Interaction):
      print("ITS AN INTERACTION!")
      user_id = interaction.user.id
      author = interaction.user
      channel = interaction.channel
      edit_message = interaction.edit_original_message
      edit_after_defer = interaction.response.edit_message
      delete_message = interaction.delete_original_message
      followup_message = interaction.followup.send
      reply_message = interaction.response.send_message
      channel_send = interaction.channel.send
      send_message = interaction.response.send_message
    else:
      print("SOMETHING BROKE HORRIBLY")

    print("REACHED PLAYER")

    player = Player(author)
    print("GOT PLAYER")

    if not player.imagine_allow:
      await send_message("This command is still in beta.")
      return

    embed_color = await get_embed_color(
        None if interaction.guild is None else interaction.guild.id)

    # Check if the player is already in a command
    if player.using_command:
      using_command_failsafe = failsafes.get_last_used_command_time(
          user_id, "general_failsafe")
      if not using_command_failsafe > 0:
        await send_message("Failsafe activated! Commencing with command!")
        player.using_command = False
      else:
        await send_message(
            "You're already in a command. Finish it before starting another.\n"
            f"Failsafe will activate in `{using_command_failsafe:.2f}` seconds if you're stuck."
        )
        return

    print("REACHED AFTER USING COMMAND")
    print(prompt)
    print(model)

    command_name = 'imagine'
    command_cd = 5
    # command_patreon_cd = command_data['patreon_cd']

    # command_name = ctx.command.name
    cooldown_remaining = cooldowns.get_cooldown(user_id, command_name)

    if cooldown_remaining > 0:
      embed = nextcord.Embed(
          title=f"Command on Cooldown. Wait {cooldown_remaining:.2f}s...",
          color=embed_color)

      await send_message(embed=embed)
      return

    cooldown = command_cd

    # Set the cooldown for the hunt command
    cooldowns.set_cooldown(user_id, command_name, cooldown)

    # Find the closest match to the model name with a cutoff of 0.6 for 60% match
    model_matches = get_close_matches(model,
                                      model_dict.keys(),
                                      n=1,
                                      cutoff=0.3)
    image = 'none'

    if model_matches:
      # If there's a match, use the first one as the model
      selected_model = model_dict[model_matches[0]]
      model_name = model_matches[0]
      print(selected_model)
      # _model = replicate.models.get(selected_model)
      # print(_model)
      # await ctx.send(f'Model selected: {model_matches[0]}')

    else:
      # If there's no match, inform the user and return
      await reply_message(
          'No matching model found. Please check the model name and try again.'
      )
      return

    current_timestamp = int(time.time())
    future_timestamp = current_timestamp + timestamp_dict[model_name]
    discord_timestamp = f"<t:{future_timestamp}:R>"

    msg = await reply_message(
        f"“**`{prompt}`**”\n> Generating using `{selected_model}`...\n**Approx. time until finish:** {discord_timestamp}"
    )

    # Request
    image = None
    video = None
    file_name = None
    img_prompt_url = None
    video_length = None
    loop = asyncio.get_event_loop()
    try:
      if model_name == "stable_diffusion":
        func = functools.partial(
            replicate.run,
            "stability-ai/stable-diffusion:ac732df83cea7fff18b8472768c88ad041fa750ff7682a21affe81863cbe77e4",
            input={"prompt": f"{prompt}"})

        output = await loop.run_in_executor(None, func)

        # Extract the image URL from the output list and remove brackets
        image_url = output[0].strip('[]')
        image = image_url.replace("'", "")

      elif model_name == "sdxl":

        func = functools.partial(
            replicate.run,
            "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            input={"prompt": f"{prompt}"})

        output = await loop.run_in_executor(None, func)

        print(output)

        # Extract the image URL from the output list and remove brackets
        image_url = output[0].strip('[]')
        image = image_url.replace("'", "")

      elif model_name == "animate-diffusion":
        # Generating a random integer between 0 and 2147483647
        random_integer = random.randint(0, 2147483647)

        func = functools.partial(
            replicate.run,
            "lucataco/animate-diff:beecf59c4aee8d81bf04f0381033dfa10dc16e845b4ae00d281e2fa377e48a9f",
            input={
                "path": "toonyou_beta3.safetensors",
                "seed": random_integer,
                "steps": 25,
                "prompt": f"{prompt}",
                "n_prompt":
                "badhandv4, easynegative, ng_deepnegative_v1_75t, verybadimagenegative_v1.3, bad-artist, bad_prompt_version2-neg, teeth, deformed iris, deformed pupils, mutated hands and fingers, deformed, distorted, disfigured, poorly drawn, bad anatomy, wrong anatomy, extra limb, missing limb, floating limbs, disconnected limbs, mutation, mutated, ugly, disgusting, amputation",
                "motion_module": "mm_sd_v14",
                "guidance_scale": 7.5
            })

        output = await loop.run_in_executor(None, func)

        print(output)

        video = output

      elif model_name == "stable-video-diffusion":

        # Check if the prompt contains only a URL
        if not (prompt.startswith('http://') or prompt.startswith('https://')):
          await msg.edit(
              content='Error: The prompt *must* contain an image URL.')
          return

        # Parse the prompt for --frames or --fr argument
        frames_arg = None
        prompt_parts = prompt.split()
        for i, part in enumerate(prompt_parts):
          if part in ['--frames', '--fr'] and i + 1 <= len(prompt_parts):
            frames_arg = prompt_parts[i + 1]
            if frames_arg not in ['14', '25']:
              await msg.edit(
                  content=
                  'Error: Invalid frames option. Only `--frames 14` and `--frames 25` are valid options (or `--fr` for short).'
              )
              return
            break

        # Validate the URL to ensure it ends with an image extension
        if prompt.endswith(('.png', '.jpg', '.jpeg')):
          img_prompt_url = prompt

        elif '?' in prompt:
          img_prompt_url = prompt.split('?')[0]
          if not img_prompt_url.endswith(('.png', '.jpg', '.jpeg')):
            await msg.edit(
                content='Error: The URL must end with .png, .jpg, or .jpeg.')
            return

        elif '--frames' in prompt or '--fr' in prompt:
          # Extract only the image URL from the prompt
          img_prompt_url = prompt.split()[0]
          if not img_prompt_url.endswith(('.png', '.jpg', '.jpeg')):
            await msg.edit(
                content='Error: The URL must end with .png, .jpg, or .jpeg.')
            return

        else:
          await msg.edit(
              content='Error: The URL must end with .png, .jpg, or .jpeg.')
          return

        # Extract the file name from the URL
        file_name = os.path.basename(img_prompt_url)

        video_length = "14_frames_with_svd"

        if frames_arg:
          if frames_arg == "14":
            video_length = "14_frames_with_svd"
          elif frames_arg == "25":
            video_length = "25_frames_with_svd_xt"

        print("------------------------------------------")
        print(frames_arg)
        print("------------------------------------------")
        print(video_length)
        print("------------------------------------------")

        func = functools.partial(
            replicate.run,
            "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
            input={
                "cond_aug": 0.02,
                "decoding_t": 7,
                "input_image": img_prompt_url,
                "video_length": f"{video_length}",
                "sizing_strategy": "maintain_aspect_ratio",
                "motion_bucket_id": 127,
                "frames_per_second": 6
            })

        output = await loop.run_in_executor(None, func)

        print(output)

        video = output
      else:
        func = functools.partial(
            replicate.run,
            "stability-ai/stable-diffusion:ac732df83cea7fff18b8472768c88ad041fa750ff7682a21affe81863cbe77e4",
            input={"prompt": f"{prompt}"})

        output = await loop.run_in_executor(None, func)

        # Extract the image URL from the output list and remove brackets
        image_url = output[0].strip('[]')
        image = image_url.replace("'", "")

    except replicate.exceptions.ModelError as e:
      await msg.edit(
          content=
          f"“**`{prompt}`**” (using `{selected_model}`) **failed**. This is most likely due to either the image URL being innacessible or the model generating an NSFW image. Try again.\n\n**Error:** `{e}`\n\nPlease Contact the Developer for assistance. If you believe this is an error, please report it using `apo bug <error description>`."
      )
      print(e)
      return
    except Exception as e:
      await msg.edit(
          content=
          f"“{prompt}” (`{selected_model}`) **failed** for some reason. This is probably my fault. \n\n**Error:** `{e}`\n\nPlease Contact the Developer for assistance. If you believe this is an error, please report it using `apo bug <error description>`."
      )
      print(e)
      return

    # Response
    if image:
      # Download the video to the commands/temp folder and save the file path
      image_response = requests.get(image)

      image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'temp', f'{file_name}.png')

      with open(image_path, 'wb') as f:
        f.write(image_response.content)

      # Attach it to the ctx.send message
      with open(image_path, 'rb') as f:
        await channel_send(content=f"**Prompt:** `{prompt}`\n"
                           f"**Requested by:** {author.mention}\n"
                           f"**Model:** `{selected_model}`\n"
                           f"---------------------------\n"
                           f"**`Apocalypse RPG Image Gen`**\n",
                           file=nextcord.File(f, filename=f'{file_name}.png'))

      # After the message is sent, delete the video from the folder
      os.remove(image_path)
      if isinstance(interaction, commands.Context):
        await msg.delete()
      elif isinstance(interaction, nextcord.Interaction):
        await interaction.delete_original_message()

      # user = ctx.author
      # avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
      # # prompt = file_name if file_name is not None else prompt

      # # Create an embed to display the image in Discord
      # embed = nextcord.Embed(title=f"{prompt}", color=nextcord.Color.random())

      # embed.set_author(name=ctx.author.name, icon_url=avatar_url)
      # embed.set_image(url=image)
      # embed.add_field(name="Model: ",
      #                 value=f"`{selected_model}`",
      #                 inline=False)
      # embed.set_footer(text=f"Apocalypse RPG Image Gen",
      #                  icon_url=bot.user.avatar.url)
      # await msg.edit(content="", embed=embed)

    elif video:
      # Download the video to the commands/temp folder and save the file path
      video_response = requests.get(video)

      video_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'temp', f'{file_name}.mp4')

      with open(video_path, 'wb') as f:
        f.write(video_response.content)

      frames_text = f"Frames: `{video_length}`\n" if video_length else ""
      reference = f"**Reference image:** [{file_name}](<{img_prompt_url}>)\n" if img_prompt_url else f"**Prompt:** `{prompt}`\n"

      # Attach it to the ctx.send message
      with open(video_path, 'rb') as f:
        await channel_send(content=f"{reference}"
                           f"**Requested by:** {author.mention}\n"
                           f"**Model:** `{selected_model}`\n"
                           f"{frames_text}"
                           f"---------------------------\n"
                           f"**`Apocalypse RPG Video Gen`**\n",
                           file=nextcord.File(f, filename=f'{file_name}.mp4'))

      # After the message is sent, delete the video from the folder
      os.remove(video_path)
      if isinstance(interaction, commands.Context):
        await msg.delete()
      elif isinstance(interaction, nextcord.Interaction):
        await interaction.delete_original_message()

      # await msg.edit(content=f"\u201C{prompt}\u201D", embed=embed)

    else:
      await msg.edit(content=f"“{prompt}” (`{selected_model}`) **failed**.")

    # Instead of `ctx.send`, use `send_message`
    # Instead of `ctx.author`, use the `author` variable

    # When sending responses for slash commands, use `await interaction.response.send_message` aka "send_message()"
    # For follow-up messages, use `await interaction.followup.send`

    # Example:
    # await send_message("This is a response that works for both text and slash commands.")


def setup(bot):
  bot.add_cog(Replicate(bot))

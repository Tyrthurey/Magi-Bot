from nextcord.ext import commands
import aiohttp


async def send_dog(ctx):
  async with aiohttp.ClientSession() as session:
    async with session.get(
        "https://dog.ceo/api/breeds/image/random") as response:
      if response.status == 200:
        data = await response.json()
        image_link = data.get("message", "No image found.")
        await ctx.send(image_link)
      else:
        await ctx.send("Couldn't fetch a dog image. :(")


# Bot command to send a random dog picture
@commands.command(name="dog", help="Sends a random dog pic.")
async def dog(ctx):
  await send_dog(ctx)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(dog)

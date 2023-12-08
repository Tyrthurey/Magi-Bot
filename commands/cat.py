from nextcord.ext import commands
import aiohttp


async def send_cat(ctx):
  async with aiohttp.ClientSession() as session:
    async with session.get(
        "https://api.thecatapi.com/v1/images/search") as response:
      if response.status == 200:
        data = await response.json()
        image_link = data[0][
            'url']  # data is a list of dictionaries, and we want the 'url' of the first one
        await ctx.send(image_link)
      else:
        await ctx.send("Couldn't fetch a cat image. :(")


# Bot command to send a random cat picture
@commands.command(name="cat", help="Sends a random cat pic.")
async def cat(ctx):
  print("---------------------------------------")
  print(f"{ctx.author} ran the cat command.")
  print("---------------------------------------")
  await send_cat(ctx)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(cat)

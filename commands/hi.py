import random
from nextcord.ext import commands

# List of 100 different greetings
greetings = [
    "Hi!", "Hello!", "Hey there!", "Howdy!", "Greetings!", "Hello, friend!",
    "Good day!", "What's up?", "Heya!", "Hiya!", "Sup?", "Yo!",
    "How's it going?", "Salutations!", "Cheers!", "Hello there!", "Bonjour!",
    "Hola!", "Aloha!", "Good to see you!", "Hi there!", "Hey!",
    "How are things?", "What's new?", "Hello, hello!", "Nice to meet you!",
    "How do you do?", "Good morning!", "Good afternoon!", "Good evening!",
    "Hey, pal!", "Hey, buddy!", "Glad you're here!", "Hey, mate!",
    "How's everything?", "How's life?", "How's your day?", "It's you again!",
    "Look what the cat dragged in!", "Hey, superstar!",
    "What's cookin', good lookin'?", "YOOOOO DAAAWG!", "Hello, Earthling!",
    "Greetings, human!", "Howdy-doody!", "Ahoy!", "Whassup, homeslice!",
    "Yoohoo!", "Hey, you!", "Wasssuuup!", "Howzit!", "G'day, mate!",
    "Ello, gov'na!", "Hey, champ!", "Hello, friend!", "What's crackin'?",
    "Good tidings!", "Hi-de-ho!", "Hey, hot stuff!", "Well, hello there!",
    "Cheers, mate!", "What's shaking, bacon?", "Peek-a-boo!", "How goes it?",
    "Hey, wizard!", "Greetings and salutations!", "Hi, beautiful!",
    "'Ello, 'ello!", "Lookin' good!", "Yo, yo, yo!", "Well met!",
    "Hey, tiger!", "A wild bundle of awesomeness has appeared!", "Hi, hi, hi!",
    "Ola!", "Ready for some fun?", "What's the haps?", "G'day, sunshine!",
    "Hey, rockstar!", "Hello, gorgeous!", "Yo, VIP!", "Hey, smarty pants!",
    "Hi, genius!", "Hello, brave one!", "Hi, champ!", "Salute!",
    "Hey, legend!", "Hello, hero!", "Greetings, champion!",
    "I SHALL RETURN THIS GREETING OF YOURS WITH ONE OF MINE! HELLO, MORTAL!",
    "Greetings, sovereign of the stars!", "Salutations, omnipotent one!",
    "Salutations, cosmic overlord!", "Greetings, harbinger of starlight!",
    "How goes the journey through space-time?", "What’s up in your world?",
    "Hey, reality surfer!", "Hello, sentient being!",
    "Salutations, universe observer!", "Hello, galactic citizen!",
    "Hi, fellow earthling!", "Salutations, earth dweller!",
    "Greetings, digital wanderer!",
    "I greet the fellow human, for I am human too!", "How fares thee?",
    "How have your travels through this digital universe been lately?~"
]


async def send_message(ctx):

  # Randomly select a greeting
  greeting = random.choice(greetings)
  await ctx.send(greeting)


# Bot command to send a hello message
@commands.command(name="hi", help="Sends a hello message.")
async def hi(ctx):
  await send_message(ctx)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_command(hi)

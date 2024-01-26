from flask import Flask, render_template, jsonify, request, session, redirect
import threading
import supabase
import os
import asyncio
from supabase import create_client, Client
from waitress import serve
from zenora import APIClient
from classes.Player import Player

app = Flask('')

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)

token = os.getenv("TOKEN") or ""

redirect_uri = "https://3d679f0f-06d3-46a3-b645-8cf309d1be3f-00-z6h7j9fc522a.worf.replit.dev/oauth/callback"

oath_url = "https://discord.com/api/oauth2/authorize?client_id=530708819458654219&response_type=code&redirect_uri=https%3A%2F%2F3d679f0f-06d3-46a3-b645-8cf309d1be3f-00-z6h7j9fc522a.worf.replit.dev%2Foauth%2Fcallback&scope=identify+email"

client_secret = os.getenv("CLIENT_SECRET") or ""

app = Flask(__name__,
            template_folder='website',
            static_folder='website/static')

client = APIClient(token, client_secret=client_secret)

app.config["SECRET_KEY"] = "verysecret"


@app.route('/')
def homepage():
  servers_response = supabase.table('ServerSettings').select('*').execute()
  servercount = len(servers_response.data)

  players_response = supabase.table('Users').select('*').execute()
  playercount = len(players_response.data)

  achievements_response = supabase.table('Achievements').select('*').execute()
  achievementcount = len(achievements_response.data)

  if 'token' in session:
    bearer_client = APIClient(session.get('token'), bearer=True)
    current_user = bearer_client.users.get_current_user()
    if current_user.discriminator == "0":
      print(f"[*] Logged in as: {current_user.username}")
    else:
      print(
          f"[*] Logged in as: {current_user.username}#{current_user.discriminator}"
      )
  else:
    current_user = None

  return render_template('index.html',
                         current_user=current_user,
                         servercount=servercount,
                         playercount=playercount,
                         achievementcount=achievementcount)


# async def fetch_profile_data(user_id):
#   user_data_response = await asyncio.get_event_loop().run_in_executor(
#       None, lambda: supabase.table('Users').select('*').eq(
#           'discord_id', user_id).execute())
#   return user_data_response


def fetch_level_prog(player):
  # Fetch the user's next level progression data
  level_progression_response = supabase.table('LevelProgression').select(
      '*').eq('level', player.level + 1).execute()
  if level_progression_response.data:
    needed_adv_level_exp = level_progression_response.data[0][
        'total_level_exp']
  else:
    needed_adv_level_exp = "N/A"
  return needed_adv_level_exp


def fetch_title(user_id):
  # Fetch the user's inventory data from the database
  inventory_response = supabase.table('Inventory').select('titles').eq(
      'discord_id', user_id).execute()

  title_count = get_gained_titles(inventory_response)

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
      title_response = supabase.table('Titles').select('title_name').eq(
          'id', equipped_title['title_id']).execute()

      if title_response.data:
        user_title = title_response.data[0]['title_name']
      else:
        user_title = "Rookie Adventurer"
  return user_title, title_count


# New function to get location name
def get_location_name(location_id):
  location_response = supabase.table('Areas').select('name').eq(
      'id', location_id).execute()
  return location_response.data[0][
      'name'] if location_response.data else 'Unknown'


def get_completed_achievements(user_id):
  # Fetch the inventory data for the user
  inventory_response = supabase.table('Inventory').select('achievements').eq(
      'discord_id', user_id).execute()

  inventory_data = inventory_response.data[
      0] if inventory_response.data else None
  user_achievements = inventory_data.get('achievements',
                                         []) if inventory_data else []

  completed_achievements = len(
      [ach for ach in user_achievements if ach['awarded']])

  return completed_achievements


def get_gained_titles(inventory_response):

  inventory_data = inventory_response.data[
      0] if inventory_response.data else None
  user_titles = inventory_data.get('titles', []) if inventory_data else []

  completed_titles = len(user_titles)

  return completed_titles


@app.route('/profile')
def profile():
  if 'token' in session:
    bearer_client = APIClient(session.get('token'), bearer=True)
    current_user = bearer_client.users.get_current_user()
    if current_user.discriminator == "0":
      print(f"[*] Logged in as: {current_user.username}")
    else:
      print(
          f"[*] Logged in as: {current_user.username}#{current_user.discriminator}"
      )
    player = Player(current_user)
    if player.exists:
      title, completed_titles = fetch_title(current_user.id)
      titles_held = completed_titles
      level_progression = fetch_level_prog(player)
      location_name = get_location_name(player.location)
      ach_gained_counter = get_completed_achievements(current_user.id)
      return render_template('profile.html',
                             current_user=current_user,
                             player=player,
                             title=title,
                             location_name=location_name,
                             level_progression=level_progression,
                             titles_held=titles_held,
                             ach_gained_counter=ach_gained_counter)
    else:
      return render_template('profile-error.html')

  else:
    return render_template('profile-error.html')


@app.route('/home')
def index():
  servers_response = supabase.table('ServerSettings').select('*').execute()
  servercount = len(servers_response.data)

  players_response = supabase.table('Users').select('*').execute()
  playercount = len(players_response.data)

  achievements_response = supabase.table('Achievements').select('*').execute()
  achievementcount = len(achievements_response.data)

  if 'token' in session:
    bearer_client = APIClient(session.get('token'), bearer=True)
    current_user = bearer_client.users.get_current_user()
    if current_user.discriminator == "0":
      print(f"[*] Logged in as: {current_user.username}")
    else:
      print(
          f"[*] Logged in as: {current_user.username}#{current_user.discriminator}"
      )
  else:
    current_user = None

  return render_template('index.html',
                         current_user=current_user,
                         servercount=servercount,
                         playercount=playercount,
                         achievementcount=achievementcount)


@app.route('/leaderboard')
def leaderboard():
  return render_template('leaderboard.html', )


@app.route('/discord')
def discord():
  return redirect("https://discord.gg/7JkkXRA3nf")


@app.route("/invite")
def invite():
  return redirect(
      "https://discord.com/oauth2/authorize?client_id=450701451522736138&permissions=9332427451456&scope=bot%20applications.commands"
  )


@app.route('/oauth/callback')
def callback():
  code = request.args['code']
  access_token = client.oauth.get_access_token(code, redirect_uri).access_token
  session['token'] = access_token
  return redirect("/")


@app.route("/logout")
def logout():
  session.clear()
  return redirect("/")


@app.route("/login")
def login():
  return redirect(oath_url)


@app.errorhandler(404)
def page_not_found(e):
  print(e)
  return render_template('error404.html'), 404


def fetch_leaderboard():
  # Query the database
  results = supabase.table('Users').select('*').execute()

  if results.data:
    # Sort the players first by level in descending order, then by adventure_exp in descending order
    sorted_data = sorted(results.data,
                         key=lambda x: (-x['level'], -x['adventure_exp']))
    return sorted_data[:10]  # Return only the top 10 players
  else:
    return []


@app.route('/leaderboard_data')
def leaderboard_route():
  leaderboard_data = fetch_leaderboard()
  # Convert the data to the format expected by the frontend
  formatted_data = [{
      "username": player.get('username'),
      "level": player.get('level'),
      "adventure_exp": player.get('adventure_exp')
  } for player in leaderboard_data]
  return jsonify(formatted_data)


def run():
  serve(app, host='0.0.0.0', port=8080)


def keep_alive():
  t = threading.Thread(target=run)
  t.start()


# Run the server if this file is executed directly
if __name__ == '__main__':
  keep_alive()

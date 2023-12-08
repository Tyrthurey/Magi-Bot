from flask import Flask, render_template, jsonify
import threading
import supabase
import os
from supabase import create_client, Client

app = Flask('')

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)

app = Flask(__name__,
            template_folder='website',
            static_folder='website/static')


@app.route('/')
def homepage():
  return render_template('index.html')


def fetch_leaderboard():
  # Query the database, filtering out bots and getting the top players
  results = supabase.table('Users').select('*').execute()

  if results.data:
    # Sort the players first by level in descending order, then by adventure_exp in descending order
    sorted_data = sorted(results.data,
                         key=lambda x: (-x['level'], -x['adventure_exp']))
    return sorted_data[:10]  # Return only the top 10 players
  else:
    return []


@app.route('/leaderboard')
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
  app.run(host='0.0.0.0', port=8080)


def keep_alive():
  t = threading.Thread(target=run)
  t.start()


# Run the server if this file is executed directly
if __name__ == '__main__':
  keep_alive()

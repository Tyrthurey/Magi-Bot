from flask import Flask, render_template_string, jsonify
import threading
import supabase
import os
from supabase import create_client, Client

app = Flask('')

url = os.getenv("SUPABASE_URL") or ""
key = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(url, key)

# ... (the rest of your Python code remains unchanged)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Magi RPG Bot</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { 
            background-color: #121212; 
            color: #fff; 
            font-family: 'Roboto', sans-serif; 
            text-align: center; 
            margin: 0;
            padding: 0;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        h1, h2 { 
            color: #4CAF50; /* Greenish color for the titles */
            text-shadow: 2px 2px 4px #000000;
        }
        #leaderboard {
            width: 90%;
            max-width: 600px;
            background: #232323;
            border-radius: 25px;
            box-shadow: 0 10px 25px rgba(0, 255, 0, 0.5);
            padding: 20px;
            box-sizing: border-box;
            margin: 20px;
            overflow: visible;
        }
        ol {
            counter-reset: leaderboard-item;
            padding: 0;
            list-style-type: none;
        }
        ol li {
            counter-increment: leaderboard-item;
            padding: 10px 0;
            border-bottom: 1px solid #444;
            position: relative;
            margin: 10px 0;
            background: linear-gradient(90deg, rgba(0,0,0,0.1), transparent);
            animation: fadeIn 0.3s ease-in-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        ol li::before {
            content: counter(leaderboard-item);
            position: absolute;
            left: 10px; /* Adjusted to ensure the numbers appear inside the box */
            top: 50%;
            transform: translateY(-50%);
            background-color: #4CAF50;
            color: #fff;
            width: 24px;
            height: 24px;
            text-align: center;
            line-height: 24px;
            border-radius: 50%;
            font-weight: bold;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.5); /* Optional: adds depth to the numbers */
        }
        ol li:last-child {
            border-bottom: none;
        }
        .player-name {
            font-weight: bold;
        }
        .player-level {
            float: right;
            opacity: 0.7;
        }
        ol li:hover {
            background-color: rgba(76, 175, 80, 0.2);
        }
        @media (max-width: 768px) {
            #leaderboard {
                width: 95%;
                max-width: none;
            }
        }
    </style>
</head>
<body>
    <h1>Magi RPG Bot</h1>
    <h2>Adventure Leaderboard</h2>
    <div id="leaderboard">
        <!-- Leaderboard will be populated by the script below -->
    </div>
    <script>
        function updateLeaderboard() {
            fetch('/leaderboard').then(function(response) {
                return response.json();
            }).then(function(data) {
                var leaderboardDiv = document.getElementById('leaderboard');
                leaderboardDiv.innerHTML = '<ol>' +
                    data.map(function(player) {
                        return '<li><span class="player-name">' + player.username + '</span>' + 
                        '<span class="player-level">Level ' + player.level + '</span></li>';
                    }).join('') +
                '</ol>';
            }).catch(function(error) {
                console.error('Error:', error);
            });
        }

        setInterval(updateLeaderboard, 300000); // Update every 300 seconds
        updateLeaderboard(); // Initial update on page load
        
    </script>
</body>
</html>
"""


@app.route('/')
def homepage():
  return render_template_string(HTML_TEMPLATE)


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

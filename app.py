# To run this Flask application:
# 1. Make sure you have Python installed.
# 2. Install Flask: pip install Flask
# 3. Open your terminal, navigate to the root directory of this project.
# 4. Run the server: python app.py
# 5. Open your browser and go to http://127.0.0.1:5000/

from flask import Flask, send_from_directory, jsonify

app = Flask(__name__)

@app.route('/')
def serve_index():
    # Serve index.html from the root directory
    return send_from_directory('.', 'index.html')

@app.route('/api/gamestate', methods=['GET'])
def get_game_state():
    game_state = {
        "player_hand": [
            { "color": "red", "value": "1" },
            { "color": "green", "value": "7" },
            { "color": "blue", "value": "drawTwo" },
            { "color": "yellow", "value": "0" },
            { "color": "red", "value": "skip" },
            { "color": "black", "value": "wild" }
        ],
        "discard_pile_top_card": { "color": "green", "value": "4" },
        "deck_card_count": 40, # Example count
        "current_player_color": "green" # Example color
    }
    return jsonify(game_state)

if __name__ == '__main__':
    app.run(debug=True)

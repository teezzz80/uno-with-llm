# To run this Flask application:
# 1. Make sure you have Python installed.
# 2. Install Flask: pip install Flask
# 3. Open your terminal, navigate to the root directory of this project.
# 4. Run the server: python app.py
# 5. Open your browser and go to http://127.0.0.1:5000/

import random
from flask import Flask, send_from_directory, jsonify

# --- UNO Deck Definition and Utilities ---
COLORS = ["red", "yellow", "green", "blue"]
NUMBERS = [str(i) for i in range(10)] + [str(i) for i in range(1, 10)] 
ACTION_CARDS = ["skip", "reverse", "drawTwo"] 
WILD_CARDS_BASE_VALUE = ["wild", "wildDrawFour"]

def create_deck():
    deck = []
    for color in COLORS:
        for number in NUMBERS:
            deck.append({"color": color, "value": number})
        for _ in range(2): # Two of each action card per color
            for action in ACTION_CARDS:
                deck.append({"color": color, "value": action})
    for _ in range(4): # Four of each wild type
        deck.append({"color": "black", "value": "wild"}) 
        deck.append({"color": "black", "value": "wildDrawFour"})
    return deck

def shuffle_deck(deck):
    random.shuffle(deck)
    return deck

# --- Global Game State Variables ---
game_deck = []
player_hands = {} 
discard_pile = [] 
discard_pile_top_card = None 
current_chosen_color = None 

players = ["Player1", "Player2"] 
current_player_index = 0
game_started = False 
play_direction = 1 # 1 for forward, -1 for reverse

# --- Flask Application ---
app = Flask(__name__)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/api/gamestate', methods=['GET'])
def get_game_state():
    global game_started, game_deck, player_hands, discard_pile, discard_pile_top_card
    global current_player_index, current_chosen_color, play_direction, players

    if not game_started:
        game_deck = create_deck()
        shuffle_deck(game_deck)
        
        player_hands = {player: [] for player in players}
        for player in players:
            for _ in range(7): 
                if game_deck: 
                    player_hands[player].append(game_deck.pop())
                else:
                    print("Error: Deck ran out during initial deal.") 
                    break 
        
        if game_deck:
            card_to_discard = game_deck.pop()
            while card_to_discard["value"] == "wildDrawFour":
                print(f"Wild Draw Four drawn as first card, re-shuffling and re-drawing.")
                game_deck.insert(len(game_deck) // 2, card_to_discard) 
                shuffle_deck(game_deck) 
                if not game_deck: 
                    print("Error: Deck empty after trying to re-draw first discard card.")
                    discard_pile_top_card = {"color": "red", "value": "0"} 
                    break
                card_to_discard = game_deck.pop()
            
            discard_pile.append(card_to_discard)
            discard_pile_top_card = card_to_discard

            if discard_pile_top_card["color"] == "black": 
                current_chosen_color = COLORS[0] 
                print(f"A Wild card is the first on discard. Chosen color defaults to {current_chosen_color}.")
            else:
                current_chosen_color = discard_pile_top_card["color"] 
        else:
            print("Error: Deck empty before drawing first discard card.")
            discard_pile_top_card = {"color": "red", "value": "0"} 
            current_chosen_color = discard_pile_top_card["color"]

        current_player_index = 0
        play_direction = 1
        game_started = True
        print("Game started. Deck shuffled. Cards dealt. First discard placed.")

    current_player_name = players[current_player_index]
    hand_to_send = player_hands.get(current_player_name, [])

    game_state_response = {
        "player_hand": hand_to_send,
        "discard_pile_top_card": discard_pile_top_card if discard_pile_top_card else {"color": "grey", "value": "Empty"},
        "deck_card_count": len(game_deck),
        "current_player": current_player_name,
        "current_chosen_color": current_chosen_color,
        "players_list": players,
        "play_direction": "forward" if play_direction == 1 else "backward",
    }
    return jsonify(game_state_response)

@app.route('/api/draw_card', methods=['POST'])
def draw_card():
    global game_deck, player_hands, current_player_index, players, discard_pile, discard_pile_top_card
    global current_chosen_color, play_direction

    if not game_started:
        return jsonify({"error": "Game not started"}), 400

    current_player_name = players[current_player_index]
    message = ""

    if len(game_deck) == 0:
        print("Deck is empty. Attempting to reshuffle from discard pile.")
        if len(discard_pile) <= 1:
            message = "No cards left in deck or discard pile to draw."
            print(message)
        else:
            new_deck_cards = discard_pile[:-1] 
            game_deck.extend(new_deck_cards)
            discard_pile = [discard_pile_top_card] 
            shuffle_deck(game_deck)
            print(f"Reshuffled {len(game_deck)} cards from discard pile into deck.")
            if len(game_deck) == 0: 
                 message = "No cards left to draw after reshuffle attempt."
                 print(message)

    if len(game_deck) > 0:
        drawn_card = game_deck.pop(0) 
        player_hands[current_player_name].append(drawn_card)
        message = f"{current_player_name} drew: {drawn_card['color']} {drawn_card['value']}."
        print(message)
    else:
        if not message: 
            message = "Deck is empty, no card drawn for " + current_player_name + "."
        print(message)

    hand_to_send = player_hands.get(current_player_name, [])
    response_data = {
        "message": message,
        "player_hand": hand_to_send,
        "discard_pile_top_card": discard_pile_top_card if discard_pile_top_card else {"color": "grey", "value": "Empty"},
        "deck_card_count": len(game_deck),
        "current_player": current_player_name, # Current player (who drew)
        "current_chosen_color": current_chosen_color,
        "players_list": players,
        "play_direction": "forward" if play_direction == 1 else "backward",
    }
    return jsonify(response_data)

@app.route('/api/end_turn', methods=['POST'])
def end_turn():
    global current_player_index, players, game_started, play_direction
    global game_deck, player_hands, discard_pile_top_card, current_chosen_color # For response

    if not game_started:
        return jsonify({"error": "Game not started"}), 400

    # Advance to the next player
    num_players = len(players)
    current_player_index = (current_player_index + play_direction + num_players) % num_players
    
    next_player_name = players[current_player_index]
    message = f"Turn ended. Next player is {next_player_name}."
    print(message)

    # Construct the game state for the new current player
    hand_to_send = player_hands.get(next_player_name, [])
    response_data = {
        "message": message,
        "player_hand": hand_to_send,
        "discard_pile_top_card": discard_pile_top_card if discard_pile_top_card else {"color": "grey", "value": "Empty"},
        "deck_card_count": len(game_deck),
        "current_player": next_player_name,
        "current_chosen_color": current_chosen_color, # This might need to be reset if a wild was just played and its effect ends
        "players_list": players,
        "play_direction": "forward" if play_direction == 1 else "backward",
    }
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True)

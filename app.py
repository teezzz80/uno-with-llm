# To run this Flask application:
# 1. Make sure you have Python installed.
# 2. Install Flask: pip install Flask
# 3. Open your terminal, navigate to the root directory of this project.
# 4. Run the server: python app.py
# 5. Open your browser and go to http://127.0.0.1:5000/

import random
import uuid  # Added import
import requests # Added import
import json # Added import
from flask import Flask, send_from_directory, jsonify, request

# --- Ollama Configuration ---
OLLAMA_API_ENDPOINT = "http://localhost:11434/api/chat" # Or your actual Ollama endpoint
OLLAMA_MODEL = "gemma:2b" # Using a smaller model for potentially faster responses initially
OLLAMA_REQUEST_TIMEOUT = 60 # seconds

# --- UNO Deck Definition and Utilities ---
COLORS = ["red", "yellow", "green", "blue"]
NUMBERS = [str(i) for i in range(10)] + [str(i) for i in range(1, 10)] 
ACTION_CARDS = ["skip", "reverse", "drawTwo"] 
WILD_CARDS_BASE_VALUE = ["wild", "wildDrawFour"]

def create_deck():
    deck = []
    for color in COLORS:
        for number in NUMBERS:
            deck.append({"color": color, "value": number, "guid": uuid.uuid4().hex})  # Added guid
        for _ in range(2): # Two of each action card per color
            for action in ACTION_CARDS:
                deck.append({"color": color, "value": action, "guid": uuid.uuid4().hex})  # Added guid
    for _ in range(4): # Four of each wild type
        deck.append({"color": "black", "value": "wild", "guid": uuid.uuid4().hex})  # Added guid
        deck.append({"color": "black", "value": "wildDrawFour", "guid": uuid.uuid4().hex})  # Added guid
    return deck

def shuffle_deck(deck):
    random.shuffle(deck)
    return deck

def is_valid_play(played_card, top_discard_card, current_chosen_color):
    if not top_discard_card: 
        return True 

    if played_card['color'] == 'black':
        return True

    if top_discard_card['color'] == 'black':
        if current_chosen_color is None:
            print("Error: Wild card on discard but no chosen color set.")
            return False 
        return played_card['color'] == current_chosen_color

    if played_card['color'] == top_discard_card['color'] or \
       played_card['value'] == top_discard_card['value']:
        return True
        
    return False

# --- Global Game State Variables ---
game_deck = []
player_hands = {} 
discard_pile = [] 
discard_pile_top_card = None 
current_chosen_color = None 
awaiting_color_choice = False # True if a Wild card was played and server is waiting for color choice
pending_draw_amount = 0  # Added global variable
ai_last_banter = ""  # Added global variable
game_winner = None  # Added global variable

players = ["Player1", "Player2"] 
current_player_index = 0
game_started = False 
play_direction = 1 # 1 for forward, -1 for reverse

# --- Flask Application ---
app = Flask(__name__)

# --- AI Turn Implementation ---
def execute_ai_turn():
    # Explicitly bring necessary globals into scope for modification/use
    global game_deck, player_hands, discard_pile, discard_pile_top_card
    global current_chosen_color, awaiting_color_choice, players, current_player_index
    global play_direction, pending_draw_amount, ai_last_banter, game_winner, COLORS # COLORS needed for default wild choice

    ai_player_name = players[current_player_index]
    if ai_player_name != "Player2": # Safety check
        print(f"Error: execute_ai_turn called for {ai_player_name}")
        return

    print(f"AI ({ai_player_name}) is starting its turn.")
    original_banter_for_draw_action = "" # Store initial banter if AI has to draw first

    # 1. Handle any pending draw amount for the AI FIRST
    if pending_draw_amount > 0:
        num_to_draw = pending_draw_amount
        print(f"AI ({ai_player_name}) must draw {num_to_draw} cards due to pending_draw_amount.")
        drawn_cards_for_penalty_details = []
        for i in range(num_to_draw):
            if not game_deck:
                # Attempt to reshuffle, similar to logic in /api/draw_card
                # Simplified version: if discard_pile has more than 1 card, reshuffle
                if len(discard_pile) > 1:
                    new_deck_cards = discard_pile[:-1] # All but the current top card
                    game_deck.extend(new_deck_cards)
                    current_top_card = discard_pile[-1] # This is discard_pile_top_card
                    discard_pile = [current_top_card]
                    shuffle_deck(game_deck)
                    print(f"Reshuffled {len(game_deck)} cards from discard pile into deck for AI penalty draw.")
                else:
                    print("Deck empty and discard pile has too few cards to reshuffle for AI penalty draw.")

            if game_deck:
                card = game_deck.pop(0)
                player_hands[ai_player_name].append(card)
                drawn_cards_for_penalty_details.append(f"{card['color']} {card['value']}")
            else:
                print(f"AI ({ai_player_name}) could not draw card {i+1}/{num_to_draw} - deck empty after reshuffle attempt.")
                break
        original_banter_for_draw_action = f"AI drew {len(drawn_cards_for_penalty_details)} card(s) due to a penalty: {', '.join(drawn_cards_for_penalty_details)}."
        ai_last_banter = original_banter_for_draw_action # Set this as the current banter
        print(original_banter_for_draw_action)
        pending_draw_amount = 0 # Penalty served by AI
        # Rule: If AI drew from a Wild Draw Four, its turn might end. For now, we let it proceed.


    # 2. Gather Game State for LLM
    ai_hand = player_hands.get(ai_player_name, [])
    ai_hand_for_prompt = [{"guid": card["guid"], "color": card["color"], "value": card["value"]} for card in ai_hand]

    other_player_name = "Player1"
    other_player_card_count = len(player_hands.get(other_player_name, []))

    # Determine current valid color for LLM (especially if top card is wild)
    effective_game_color = current_chosen_color
    if discard_pile_top_card and discard_pile_top_card['color'] == 'black' and not current_chosen_color:
        # This state should ideally not happen if a wild is played and color is chosen.
        # If it does, default to a color or have LLM pick one if it plays another wild.
        print("Warning: Top card is wild but no current_chosen_color. AI might need to re-declare if playing a non-wild.")
        effective_game_color = "any" # Or prompt LLM to be careful

    game_state_for_llm = {
        "my_hand": ai_hand_for_prompt,
        "discard_top_card": discard_pile_top_card,
        "current_game_color": effective_game_color,
        "opponent_card_count": other_player_card_count,
    }

    # 3. Construct LLM Prompt
    system_prompt = f"""
You are an AI player named '{ai_player_name}' in a game of UNO. It's your turn.
The top card on the discard pile is: {discard_pile_top_card['color']} {discard_pile_top_card['value']}.
The current game color to follow is: {effective_game_color}. (If discard top is a regular card, match its color or value. If top was Wild, this is the chosen color).

Your hand:
{json.dumps(ai_hand_for_prompt, indent=1)}

Your opponent ({other_player_name}) has {other_player_card_count} card(s).

Choose an action:
1. PLAY_CARD: Play a card. It must match the discard's color or value, OR the current_game_color if a Wild was played previously. Wilds can be played on any card (except on a Draw Two, typically).
2. DRAW_CARD: If you have no valid card to play.

Respond ONLY with a JSON object in the specified format:
{{
  "action_type": "PLAY_CARD" | "DRAW_CARD",
  "card_guid_to_play": "guid_of_card_from_your_hand_if_playing_else_null",
  "declared_color": "red" | "yellow" | "green" | "blue" | null (MUST be provided if playing a 'wild' or 'wildDrawFour'),
  "call_uno": true | false (set to true if playing this card leaves you with 1 card),
  "banter": "A short, witty remark about your move or the game."
}}

Think step-by-step:
- Can I play any card from my hand?
- Which card is the most strategic? (e.g., change color, make opponent draw)
- If playing a Wild, which color should I choose? (Ideally, a color I have more of, or to change from opponent's strong color).
- If I can't play, I must draw.
Your goal is to empty your hand. Make sure your response is valid JSON.
"""
    llm_payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Current game state for your decision: {json.dumps(game_state_for_llm)}. What is your action in the specified JSON format?"}
        ],
        "format": "json",
        "stream": False
    }

    # 4. API Call to Ollama
    llm_action = None
    action_str_for_error_logging = ""
    try:
        print(f"AI ({ai_player_name}) sending prompt to Ollama ({OLLAMA_MODEL})...")
        response = requests.post(OLLAMA_API_ENDPOINT, json=llm_payload, timeout=OLLAMA_REQUEST_TIMEOUT)
        response.raise_for_status()

        response_data = response.json()
        # Assuming Ollama with format:"json" directly puts the JSON string in message.content
        action_str_for_error_logging = response_data.get("message", {}).get("content", "")
        if not action_str_for_error_logging: # Fallback for different Ollama structures
             action_str_for_error_logging = response_data.get("response", "") # Common for /api/generate

        if action_str_for_error_logging:
            llm_action = json.loads(action_str_for_error_logging)
            # Combine banters if AI drew penalty cards earlier
            new_banter = llm_action.get("banter", "AI is focused...")
            ai_last_banter = f"{original_banter_for_draw_action} {new_banter}".strip() if original_banter_for_draw_action else new_banter
            print(f"AI ({ai_player_name}) received action from LLM: {llm_action}")
        else:
            raise ValueError("LLM response content is empty or not in expected structure.")

    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama API: {e}")
        ai_last_banter = f"{original_banter_for_draw_action} AI had trouble thinking... will draw a card.".strip() if original_banter_for_draw_action else "AI had trouble thinking... will draw a card."
    except json.JSONDecodeError as e:
        print(f"Error parsing LLM JSON response: {e}. Response text: '{action_str_for_error_logging}'")
        ai_last_banter = f"{original_banter_for_draw_action} AI's thoughts were jumbled... will draw a card.".strip() if original_banter_for_draw_action else "AI's thoughts were jumbled... will draw a card."
    except Exception as e:
        print(f"An unexpected error occurred during LLM interaction: {e}")
        ai_last_banter = f"{original_banter_for_draw_action} AI encountered an unexpected glitch... will draw a card.".strip() if original_banter_for_draw_action else "AI encountered an unexpected glitch... will draw a card."


    # 5. Execute AI's Chosen Action
    if llm_action and llm_action.get("action_type") == "PLAY_CARD" and llm_action.get("card_guid_to_play"):
        card_guid_to_play = llm_action.get("card_guid_to_play")
        card_to_play_tuple = next(((idx, card) for idx, card in enumerate(ai_hand) if card["guid"] == card_guid_to_play), None)

        if card_to_play_tuple:
            card_idx, played_card = card_to_play_tuple
            print(f"AI ({ai_player_name}) plays: {played_card['color']} {played_card['value']} (GUID: {card_guid_to_play})")

            player_hands[ai_player_name].pop(card_idx)
            discard_pile.append(played_card)
            discard_pile_top_card = played_card

            if played_card['color'] == 'black':
                declared_color = llm_action.get("declared_color")
                if declared_color and declared_color in COLORS:
                    current_chosen_color = declared_color
                    print(f"AI ({ai_player_name}) declared color: {current_chosen_color}")
                    ai_last_banter = ai_last_banter.replace("...", f"and chose {current_chosen_color}.") # Update banter
                else:
                    current_chosen_color = random.choice(COLORS) # Default if LLM fails
                    print(f"AI ({ai_player_name}) failed to declare a valid color or none provided, defaulting to {current_chosen_color}")
                    ai_last_banter = ai_last_banter.replace("...", f"defaulting to {current_chosen_color}.")
            else:
                current_chosen_color = played_card['color']

            if played_card['value'] == 'drawTwo':
                pending_draw_amount += 2
            elif played_card['value'] == 'wildDrawFour':
                pending_draw_amount += 4

            if llm_action.get("call_uno", False) and len(player_hands[ai_player_name]) == 1:
                print(f"AI ({ai_player_name}) calls UNO!")
                ai_last_banter += " UNO!"

            if len(player_hands[ai_player_name]) == 0:
                print(f"AI ({ai_player_name}) has won!")
                game_winner = ai_player_name
                ai_last_banter += " And that's the game! I win!"
        else:
            print(f"AI ({ai_player_name}) tried to play card GUID {card_guid_to_play}, but it's not in its hand. Defaulting to draw.")
            llm_action = {"action_type": "DRAW_CARD"}
            ai_last_banter = f"{original_banter_for_draw_action} AI seems to have misplaced a card... draws instead.".strip() if original_banter_for_draw_action else "AI seems to have misplaced a card... draws instead."


    if not llm_action or llm_action.get("action_type") == "DRAW_CARD":
        if not game_winner: # Don't draw if AI already won
            print(f"AI ({ai_player_name}) chooses to draw a card (or defaulted to it).")
            # Reshuffle logic for AI draw
            if not game_deck:
                if len(discard_pile) > 1:
                    new_deck_cards = discard_pile[:-1]
                    game_deck.extend(new_deck_cards)
                    current_top_card = discard_pile[-1]
                    discard_pile = [current_top_card]
                    shuffle_deck(game_deck)
                    print(f"Reshuffled {len(game_deck)} cards from discard pile into deck for AI draw.")
                else:
                    print("Deck empty, cannot reshuffle for AI draw.")

            if game_deck:
                drawn_card = game_deck.pop(0)
                player_hands[ai_player_name].append(drawn_card)
                print(f"AI ({ai_player_name}) drew: {drawn_card['color']} {drawn_card['value']}")
                # Ensure banter isn't overwritten if it was set due to error/penalty draw
                if "drew" not in ai_last_banter.lower() and "jumbled" not in ai_last_banter.lower() and "glitch" not in ai_last_banter.lower() and "trouble thinking" not in ai_last_banter.lower() and "misplaced" not in ai_last_banter.lower():
                    ai_last_banter = f"{original_banter_for_draw_action} AI draws a card ({drawn_card['color']} {drawn_card['value']}).".strip() if original_banter_for_draw_action else f"AI draws a card ({drawn_card['color']} {drawn_card['value']})."
                elif not original_banter_for_draw_action and ("jumbled" in ai_last_banter.lower() or "glitch" in ai_last_banter.lower() or "trouble thinking" in ai_last_banter.lower() or "misplaced" in ai_last_banter.lower()):
                    # If error banter was set, append draw info
                    ai_last_banter += f" So, AI draws {drawn_card['color']} {drawn_card['value']}."
            else:
                print(f"AI ({ai_player_name}) has no cards to draw, deck is empty.")
                if "drew" not in ai_last_banter.lower():
                    ai_last_banter = f"{original_banter_for_draw_action} AI has no cards to draw, deck is empty.".strip() if original_banter_for_draw_action else "AI has no cards to draw, deck is empty."

    print(f"AI ({ai_player_name}) turn ended. Final Banter: '{ai_last_banter}'")

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/api/gamestate', methods=['GET'])
def get_game_state():
    global game_started, game_deck, player_hands, discard_pile, discard_pile_top_card
    global current_player_index, current_chosen_color, play_direction, players, awaiting_color_choice
    global pending_draw_amount, ai_last_banter, game_winner # Added to globals

    if not game_started:
        game_winner = None # Initialize game_winner
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
                    current_chosen_color = discard_pile_top_card["color"]
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
        awaiting_color_choice = False # Reset at game start
        game_started = True
        print("Game started. Deck shuffled. Cards dealt. First discard placed.")

    current_player_name = players[current_player_index]
    hand_to_send = player_hands.get(current_player_name, [])

    opponent_player_name = players[(current_player_index + 1) % len(players)]
    opponent_card_count = len(player_hands.get(opponent_player_name, []))


    game_state_response = {
        "player_hand": hand_to_send,
        "discard_pile_top_card": discard_pile_top_card if discard_pile_top_card else {"color": "grey", "value": "Empty"},
        "deck_card_count": len(game_deck),
        "current_player": current_player_name,
        "current_chosen_color": current_chosen_color,
        "awaiting_color_choice": awaiting_color_choice,
        "players_list": players,
        "play_direction": "forward" if play_direction == 1 else "backward",
        "pending_draw_amount": pending_draw_amount,  # Added to response
        "ai_last_banter": ai_last_banter,  # Added to response
        "game_winner": game_winner,  # Added to response
        "opponent_card_count": opponent_card_count # Added to response
    }
    return jsonify(game_state_response)

@app.route('/api/draw_card', methods=['POST'])
def draw_card():
    global game_deck, player_hands, current_player_index, players, discard_pile, discard_pile_top_card
    global current_chosen_color, play_direction, awaiting_color_choice, pending_draw_amount # Added pending_draw_amount

    if not game_started:
        return jsonify({"error": "Game not started"}), 400
    if awaiting_color_choice: # Cannot draw if waiting for color choice
        return jsonify({"error": "Must choose a color for the played Wild card first."}), 400


    current_player_name = players[current_player_index]
    message = ""
    cards_drawn_this_turn = 0

    def attempt_reshuffle():
        nonlocal message # Allow modification of outer scope message
        global game_deck, discard_pile, discard_pile_top_card
        print("Deck is empty. Attempting to reshuffle from discard pile.")
        if len(discard_pile) <= 1:
            # No cards to reshuffle other than the top discard card
            return False
        else:
            new_deck_cards = discard_pile[:-1]
            game_deck.extend(new_deck_cards)
            discard_pile = [discard_pile_top_card] # Keep only the top card on discard
            shuffle_deck(game_deck)
            print(f"Reshuffled {len(game_deck)} cards from discard pile into deck.")
            return len(game_deck) > 0

    draw_count = 0
    if pending_draw_amount > 0:
        draw_count = pending_draw_amount
        message = f"{current_player_name} must draw {draw_count} cards. "
        pending_draw_amount = 0 # Reset after acknowledging
    else:
        draw_count = 1 # Default draw 1 card

    for i in range(draw_count):
        if len(game_deck) == 0:
            if not attempt_reshuffle():
                message += "Deck and discard pile are empty. Cannot draw more cards."
                break # Exit loop if no cards to draw

        if len(game_deck) > 0:
            drawn_card = game_deck.pop(0)
            player_hands[current_player_name].append(drawn_card)
            cards_drawn_this_turn += 1
        else: # Should not happen if attempt_reshuffle worked and there were cards
            message += "Deck became empty unexpectedly during draw. "
            break

    if cards_drawn_this_turn > 0:
        if draw_count > 1: # Specifically for pending draw
             message += f"Drew {cards_drawn_this_turn} card(s)."
        else: # Standard draw or completed pending draw of 1
             message = f"{current_player_name} drew {cards_drawn_this_turn} card(s)."
        print(message)
    elif not message: # No cards drawn and no specific message set yet
        message = f"No cards drawn for {current_player_name} as deck was empty."
        print(message)

    hand_to_send = player_hands.get(current_player_name, [])
    response_data = {
        "message": message,
        "player_hand": hand_to_send,
        "discard_pile_top_card": discard_pile_top_card if discard_pile_top_card else {"color": "grey", "value": "Empty"},
        "deck_card_count": len(game_deck),
        "current_player": current_player_name, 
        "current_chosen_color": current_chosen_color,
        "awaiting_color_choice": awaiting_color_choice,
        "players_list": players,
        "play_direction": "forward" if play_direction == 1 else "backward",
    }
    return jsonify(response_data)

@app.route('/api/play_card', methods=['POST'])
def play_card_action():
    global game_started, player_hands, current_player_index, players, discard_pile_top_card, discard_pile
    global current_chosen_color, awaiting_color_choice, game_deck, play_direction, pending_draw_amount # Added pending_draw_amount

    if not game_started:
        return jsonify({"success": False, "message": "Game not started."}), 400
    
    if awaiting_color_choice and request.get_json().get('chosen_color') is None : # If waiting for color, but no color was sent with this play (e.g. trying to play another card)
         return jsonify({"success": False, "message": "A Wild card was played. Please choose a color first or play another card that is valid on the chosen color if applicable."}), 400


    played_card_data = request.get_json()
    if not played_card_data or 'color' not in played_card_data or 'value' not in played_card_data:
        return jsonify({"success": False, "message": "Invalid card data received."}), 400

    current_player_name = players[current_player_index]
    current_hand = player_hands.get(current_player_name, [])

    card_in_hand_to_play = None
    for card in current_hand:
        if card['color'] == played_card_data['color'] and card['value'] == played_card_data['value']:
            card_in_hand_to_play = card
            break
    
    if not card_in_hand_to_play:
        return jsonify({"success": False, "message": "Card not in player's hand."}), 400

    is_valid = is_valid_play(card_in_hand_to_play, discard_pile_top_card, current_chosen_color)

    if is_valid:
        current_hand.remove(card_in_hand_to_play)
        player_hands[current_player_name] = current_hand
        
        discard_pile.append(card_in_hand_to_play)
        discard_pile_top_card = card_in_hand_to_play

        message = f"{current_player_name} played: {card_in_hand_to_play['color']} {card_in_hand_to_play['value']}."
        
        # Card effects that modify pending_draw_amount
        played_value = card_in_hand_to_play['value']
        if played_value == "drawTwo":
            pending_draw_amount += 2
            message += f" Next player must draw 2."
        elif played_value == "wildDrawFour":
            pending_draw_amount += 4
            message += f" Next player must draw 4."

        awaiting_color_choice = False
        if card_in_hand_to_play['color'] == 'black':
            chosen_color_from_payload = played_card_data.get('chosen_color')
            if chosen_color_from_payload and chosen_color_from_payload in COLORS:
                current_chosen_color = chosen_color_from_payload
                message += f" Color chosen: {current_chosen_color}."
                # If a wild card is played, the turn usually ends immediately after color choice.
                # Card effects (like Draw Four) and turn ending are not handled yet.
            else:
                # This case means a Wild was played but no color was specified in THIS request.
                # This is correct for a card like "Wild" that needs a subsequent color choice.
                awaiting_color_choice = True
                current_chosen_color = None # Explicitly set to None, color must be chosen next
                message += " Please choose a color."
        else: # A colored card was played
            current_chosen_color = card_in_hand_to_play['color']
        
        print(message)
        # TODO: Implement card actions (Skip, Reverse, Draw Two, Wild Draw Four)
        # TODO: Check for win condition (player hand empty)
        # TODO: Advance turn if not awaiting color choice and no other action pending

        response_data = {
            "success": True,
            "message": message,
            "player_hand": player_hands.get(current_player_name, []), # Hand of the player who just played
            "discard_pile_top_card": discard_pile_top_card,
            "deck_card_count": len(game_deck),
            "current_player": current_player_name, # Still this player's turn if awaiting color
            "current_chosen_color": current_chosen_color,
            "awaiting_color_choice": awaiting_color_choice,
            "players_list": players,
            "play_direction": "forward" if play_direction == 1 else "backward"
        }
        return jsonify(response_data)
    else:
        return jsonify({"success": False, "message": "Invalid move!"}), 400


@app.route('/api/end_turn', methods=['POST'])
def end_turn():
    global current_player_index, players, game_started, play_direction
    global game_deck, player_hands, discard_pile_top_card, current_chosen_color, awaiting_color_choice
    global ai_last_banter, pending_draw_amount, game_winner # Ensure these are global

    if not game_started:
        return jsonify({"error": "Game not started"}), 400
    if awaiting_color_choice:
        return jsonify({"error": "A color must be chosen for the played Wild card before ending the turn."}), 400

    num_players = len(players)

    # Advance to the next player (could be Player2/AI)
    current_player_index = (current_player_index + play_direction + num_players) % num_players
    player_after_human_ends_turn = players[current_player_index]
    print(f"Turn ended by human. Tentative next player: {player_after_human_ends_turn}")

    if player_after_human_ends_turn == "Player2":
        print(f"Starting AI ({player_after_human_ends_turn}) turn...")
        # --- AI's Turn Execution ---
        # Player2 (AI) needs to handle any pending_draw_amount *before* making a move
        if pending_draw_amount > 0 and players[current_player_index] == "Player2":
            actual_drawn_count = 0
            # Simulate AI drawing cards based on pending_draw_amount
            # This part will be expanded in execute_ai_turn, for now, just log and clear
            print(f"AI ({players[current_player_index]}) must draw {pending_draw_amount} cards.")
            # (Actual drawing logic will be in execute_ai_turn)
            # For now, just acknowledge and clear for simulation purposes here
            # player_hands["Player2"].extend(...) # This will be in execute_ai_turn
            # game_deck.pop(...)
            ai_last_banter = f"AI draws {pending_draw_amount} cards!" # Placeholder
            pending_draw_amount = 0 # AI took the penalty

        execute_ai_turn() # AI makes its decision (play or draw)

        # After AI's turn, advance turn to the next player (Player1)
        current_player_index = (current_player_index + play_direction + num_players) % num_players
        print(f"AI ({player_after_human_ends_turn}) turn finished. Next player is now: {players[current_player_index]}")

    # At this point, current_player_index should be pointing to the player
    # whose turn it is to ACTUALLY play next (i.e., Player1).
    final_next_player_name = players[current_player_index]
    
    # If Player1 is now to play, and there's a pending_draw_amount (from AI's wildDrawFour/drawTwo)
    # Player1 will handle this at the start of their turn (e.g. when they click draw or play)
    # or the UI can prompt them. The draw_card endpoint already handles this.

    message = f"Turn ended. Next player is {final_next_player_name}."
    # Reset AI banter before potentially setting a new one from execute_ai_turn
    # ai_last_banter = "" # This was in the original prompt but execute_ai_turn sets it.
                        # If execute_ai_turn doesn't run, banter from previous AI turn might persist.
                        # For now, let's stick to the provided logic where execute_ai_turn sets it.

    if ai_last_banter: # Include AI banter if available
        message += f" AI says: '{ai_last_banter}'"


    # The hand sent should be for the player whose turn it is now (Player1)
    hand_to_send = player_hands.get(final_next_player_name, [])

    # Opponent card count for Player1 should be Player2's hand size
    opponent_name_for_player1 = "Player2" # Assuming Player1 is human, Player2 is AI
    opponent_card_count = len(player_hands.get(opponent_name_for_player1, []))


    response_data = {
        "message": message,
        "player_hand": hand_to_send, # Player1's hand
        "discard_pile_top_card": discard_pile_top_card if discard_pile_top_card else {"color": "grey", "value": "Empty"},
        "deck_card_count": len(game_deck),
        "current_player": final_next_player_name, # Should be Player1
        "current_chosen_color": current_chosen_color, 
        "awaiting_color_choice": awaiting_color_choice,
        "players_list": players,
        "play_direction": "forward" if play_direction == 1 else "backward",
        "ai_last_banter": ai_last_banter,
        "pending_draw_amount": pending_draw_amount, # Amount Player1 might have to draw
        "opponent_card_count": opponent_card_count,
        "game_winner": game_winner
    }
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True)

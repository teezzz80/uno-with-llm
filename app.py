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
OLLAMA_MODEL = "gemma3:4b" # Using a smaller model for potentially faster responses initially
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
is_next_player_skipped = False # True if a skip card was played

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
                drawn_cards_for_penalty_details.append(f"{card['color']} {card['value']}") # Keep for logging
            else:
                print(f"AI ({ai_player_name}) could not draw card {i+1}/{num_to_draw} - deck empty after reshuffle attempt.")
                break
        # Log the drawn cards for server admin, but don't put in banter
        if drawn_cards_for_penalty_details:
            print(f"AI ({ai_player_name}) drew penalty cards: {', '.join(drawn_cards_for_penalty_details)}")

        original_banter_for_draw_action = f"AI draws {len(drawn_cards_for_penalty_details)} card(s) due to a penalty."
        ai_last_banter = original_banter_for_draw_action # Set this as the current banter
        # print(original_banter_for_draw_action) # This would now be redundant with the log above and banter itself
        pending_draw_amount = 0 # Penalty served by AI
        # Rule: If AI drew from a Wild Draw Four, its turn might end. For now, we let it proceed.


    # 2. Gather Game State for LLM
    ai_hand = player_hands.get(ai_player_name, [])
    # Present hand to LLM without GUIDs, as it should decide based on color/value
    ai_hand_for_prompt = [{"color": card["color"], "value": card["value"]} for card in ai_hand]

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

Respond ONLY with a JSON object in the specified format. If playing a card, specify it using its color and value:
{{
  "action_type": "PLAY_CARD" | "DRAW_CARD",
  "card_to_play": {{ "color": "red", "value": "7" }},
  "declared_color": "red" | "yellow" | "green" | "blue" | null (MUST be provided if playing a 'wild' or 'wildDrawFour'),
  "call_uno": true | false (set to true if playing this card leaves you with 1 card),
  "banter": "A short, witty remark about your move or the game."
}}

Example for PLAY_CARD:
{{
  "action_type": "PLAY_CARD",
  "card_to_play": {{ "color": "blue", "value": "skip" }},
  "declared_color": null,
  "call_uno": false,
  "banter": "Skipping you!"
}}

Example for PLAY_CARD (Wild):
{{
  "action_type": "PLAY_CARD",
  "card_to_play": {{ "color": "black", "value": "wild" }},
  "declared_color": "green",
  "call_uno": true,
  "banter": "Going green and UNO!"
}}

Example for DRAW_CARD:
{{
  "action_type": "DRAW_CARD",
  "card_to_play": null,
  "declared_color": null,
  "call_uno": false,
  "banter": "Guess I'll draw."
}}

Think step-by-step:
- Review your hand.
- Review the discard top card and current game color.
- Can I play any card from my hand? It must match color/value or be a Wild.
- If playing a card, construct the "card_to_play" object with its "color" and "value".
- Which card is the most strategic? (e.g., change color, make opponent draw, get rid of high-point cards).
- If playing a Wild card (color "black"), I MUST provide a "declared_color". Choose a color that I have the most of in my remaining hand, or a strategic color.
- If I can't play, I must choose "DRAW_CARD".
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
    if llm_action and llm_action.get("action_type") == "PLAY_CARD" and llm_action.get("card_to_play"):
        card_to_play_from_llm = llm_action.get("card_to_play")

        # Find the first matching card in AI's hand (LLM provides color and value)
        # This assumes LLM picks a card it actually has. More robust validation could be added.
        card_to_play_tuple = None
        for idx, card_in_hand in enumerate(ai_hand):
            if card_in_hand["color"] == card_to_play_from_llm.get("color") and \
               card_in_hand["value"] == card_to_play_from_llm.get("value"):
                card_to_play_tuple = (idx, card_in_hand)
                break # Found the card

        if card_to_play_tuple:
            card_idx, played_card = card_to_play_tuple
            print(f"AI ({ai_player_name}) attempts to play: {played_card['color']} {played_card['value']} (GUID: {played_card['guid']}) based on LLM choice: {card_to_play_from_llm}")

            # Actual validation against game rules should happen here or be confirmed by is_valid_play
            # For now, we trust the LLM picked a playable card from its hand and proceed to remove it.
            # The is_valid_play check will happen in the calling context if this function is refactored
            # or we assume LLM's choice is valid if it's in hand and matches basic rules.
            # For simplicity here, we proceed with removal.

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
            # LLM chose a card not in its hand or with incorrect properties
            print(f"AI ({ai_player_name}) tried to play card {card_to_play_from_llm}, but it's not in its hand or invalid. Defaulting to draw.")
            llm_action = {"action_type": "DRAW_CARD"} # Force draw
            ai_last_banter = f"{original_banter_for_draw_action} AI seems to have imagined a card... draws instead.".strip() if original_banter_for_draw_action else "AI seems to have imagined a card... draws instead."

    # Fallback to DRAW_CARD if action type is not PLAY_CARD or if PLAY_CARD failed validation above
    if not llm_action or llm_action.get("action_type") != "PLAY_CARD" or not card_to_play_tuple: # card_to_play_tuple is None if play failed
        if not game_winner: # Don't draw if AI already won
            # Ensure action_type is DRAW_CARD if we fell through due to failed play
            if llm_action and llm_action.get("action_type") == "PLAY_CARD": # Play failed
                 print(f"AI ({ai_player_name}) failed its intended play, now defaulting to draw.")
            else: # Was already DRAW_CARD or no action from LLM
                 print(f"AI ({ai_player_name}) chooses to draw a card (or defaulted to it).")

            # Update llm_action to be DRAW_CARD for consistent logging/banter if it was a failed PLAY_CARD
            if not llm_action: llm_action = {} # Ensure llm_action exists
            llm_action["action_type"] = "DRAW_CARD" # Standardize for drawing part

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
                print(f"AI ({ai_player_name}) drew: {drawn_card['color']} {drawn_card['value']}") # Server log reveals card

                # Generic banter for drawing a card
                new_draw_banter = "AI draws a card."
                if original_banter_for_draw_action: # If penalty draw happened
                    # Check if the LLM's chosen banter already implies drawing or error
                    if not ("draw" in ai_last_banter.lower() or \
                            "jumbled" in ai_last_banter.lower() or \
                            "glitch" in ai_last_banter.lower() or \
                            "trouble thinking" in ai_last_banter.lower() or \
                            "misplaced" in ai_last_banter.lower() or \
                            "imagined" in ai_last_banter.lower() or \
                            "tried to play" in ai_last_banter.lower()):
                         # Append new_draw_banter if LLM banter was about something else (e.g. a play that became a draw)
                         ai_last_banter = f"{ai_last_banter} {new_draw_banter}".strip()
                    # If ai_last_banter already contains original_banter_for_draw_action, don't append new_draw_banter
                    # This case is tricky: original_banter_for_draw_action + LLM_banter + new_draw_banter
                    # The LLM banter might be "I guess I have to draw" which makes "AI draws a card. I guess I have to draw. AI draws a card"
                    # Simplification: if original_banter_for_draw_action is present, the LLM banter is primary for this phase.
                    # The generic "AI draws a card" is added if the LLM didn't provide a draw-specific one.
                    # Let's refine this:
                    # The LLM provides a banter for its *intended* action (e.g. "Take that!"). If that action fails and becomes a draw,
                    # the "imagined a card... draws instead" is already set.
                    # If LLM *chooses* to draw, its banter ("Guess I'll draw") should be primary.

                elif any(err_keyword in ai_last_banter.lower() for err_keyword in ["jumbled", "glitch", "trouble thinking", "misplaced", "imagined", "tried to play"]):
                    # If specific error/failed play banter was set, append the generic draw confirmation.
                    if "draws instead" not in ai_last_banter.lower() and "draw a card" not in ai_last_banter.lower() : # Avoid "draws instead. So, AI draws a card."
                         ai_last_banter += f" So, {new_draw_banter}"
                else: # No penalty, no error, likely LLM chose to draw or LLM response failed entirely
                    # If LLM provided banter, use it. If not, use generic.
                    # The LLM's banter for a DRAW_CARD action is already set in ai_last_banter by this point.
                    # If ai_last_banter is empty or generic placeholder, this means LLM failed to give banter.
                    if not ai_last_banter or ai_last_banter == "AI is focused...":
                        ai_last_banter = new_draw_banter
                    # If LLM's banter like "Guess I'll draw" is there, we don't want to overwrite or append "AI draws a card."
                    # So, if LLM provided a banter, and it's not an error one, we assume it's appropriate for drawing.
            else:
                print(f"AI ({ai_player_name}) has no cards to draw, deck is empty.")
                # Similar logic for banter if deck is empty
                empty_deck_banter = "AI has no cards to draw, deck is empty."
                if original_banter_for_draw_action:
                    ai_last_banter = f"{original_banter_for_draw_action} {empty_deck_banter}".strip()
                elif any(err_keyword in ai_last_banter.lower() for err_keyword in ["jumbled", "glitch", "trouble thinking", "misplaced", "imagined", "tried to play"]):
                    ai_last_banter += f" And {empty_deck_banter}" # Append to error message
                else:
                    ai_last_banter = empty_deck_banter

    print(f"AI ({ai_player_name}) turn ended. Final Banter: '{ai_last_banter}'")

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/api/gamestate', methods=['GET'])
def get_game_state():
    global game_started, game_deck, player_hands, discard_pile, discard_pile_top_card
    global current_player_index, current_chosen_color, play_direction, players, awaiting_color_choice
    global pending_draw_amount, ai_last_banter, game_winner, is_next_player_skipped # Added to globals

    if not game_started:
        game_winner = None # Initialize game_winner
        is_next_player_skipped = False # Initialize at game start
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
        is_next_player_skipped = False # Reset at game start
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
        "opponent_card_count": opponent_card_count, # Added to response
        "is_next_player_skipped": is_next_player_skipped # Added for completeness
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
    global current_chosen_color, awaiting_color_choice, game_deck, play_direction, pending_draw_amount, is_next_player_skipped # Added globals

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

        # Reset is_next_player_skipped by default for most cards
        # Only set to True if a skip or reverse (in 2P) is played by the current player
        if current_player_name == "Player1": # Only Player1's special cards affect AI skip status directly here
            is_next_player_skipped = False

        if played_value == "drawTwo":
            pending_draw_amount += 2
            message += f" Next player must draw 2."
        elif played_value == "wildDrawFour":
            pending_draw_amount += 4
            message += f" Next player must draw 4."
        elif played_value == 'skip':
            if current_player_name == "Player1": # Player1 playing skip
                 is_next_player_skipped = True
            # If AI plays skip, its logic in execute_ai_turn would handle AI skipping Player1 (not covered by this specific subtask but for future)
            message += " Next player is skipped."
        elif played_value == 'reverse':
            play_direction *= -1
            message += " Play direction reversed."
            if len(players) == 2 and current_player_name == "Player1": # In 2-player game, reverse acts as skip for Player1
                is_next_player_skipped = True
                message += " Next player is skipped (due to Reverse in 2P game)."

        awaiting_color_choice = False # Resetting by default
        if card_in_hand_to_play['color'] == 'black':
            # If Player1 (human) plays a black card
            if current_player_name == "Player1":
                awaiting_color_choice = True
                current_chosen_color = None # Player1 needs to choose a color
                message = f"{current_player_name} played: {card_in_hand_to_play['color']} {card_in_hand_to_play['value']}. Please choose a color."
                # Turn does not advance here for Player1 after playing a Wild.
            else: # AI played a black card (handled by execute_ai_turn, which includes color choice)
                chosen_color_from_payload = played_card_data.get('chosen_color')
                if chosen_color_from_payload and chosen_color_from_payload in COLORS:
                    current_chosen_color = chosen_color_from_payload
                    # message already includes AI played card, AI banter will handle color choice announcement
                else:
                    current_chosen_color = random.choice(COLORS) # Fallback if AI somehow didn't choose
                    # message already includes AI played card
        else: # A colored card was played (by either player)
            current_chosen_color = card_in_hand_to_play['color']
        
        print(message)
        # TODO: Check for win condition (player hand empty)
        # Note: Turn advancement logic is primarily in /api/end_turn.
        # If Player1 just played a wild, awaiting_color_choice is true, and end_turn will prevent turn advance.

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
    global current_player_index, players, game_started, play_direction, is_next_player_skipped # Added is_next_player_skipped
    global game_deck, player_hands, discard_pile_top_card, current_chosen_color, awaiting_color_choice
    global ai_last_banter, pending_draw_amount, game_winner

    if not game_started:
        return jsonify({"error": "Game not started"}), 400

    # Check for Player1 pending draw
    current_player_name = players[current_player_index]
    if current_player_name == "Player1" and pending_draw_amount > 0:
        return jsonify({"error": "You must draw your pending cards before ending your turn!"}), 400

    if awaiting_color_choice: # This check should likely be for Player1 as well.
        # If it's Player1's turn and they are awaiting color choice, they shouldn't end turn.
        if current_player_name == "Player1":
            return jsonify({"error": "A color must be chosen for the played Wild card before ending the turn."}), 400
        # If it's AI's turn (e.g. after human plays wild, then AI plays), this might not apply or be handled within AI logic.
        # For now, keeping the original broad check but contextualized.
        # Consider if AI could ever be 'awaiting_color_choice' in a way that blocks this. Unlikely.

    num_players = len(players)
    player_who_just_finished_turn = players[current_player_index]

    # Determine next player candidate based on current direction
    next_player_candidate_index = (current_player_index + play_direction + num_players) % num_players

    ai_was_skipped_this_turn = False
    if player_who_just_finished_turn == "Player1" and players[next_player_candidate_index] == "Player2" and is_next_player_skipped:
        print(f"Player1 played Skip/Reverse. AI ({players[next_player_candidate_index]}) turn is skipped.")
        ai_last_banter = "My turn was skipped! Guess I'll just chill."
        is_next_player_skipped = False # Consume the skip

        # Advance current_player_index past the AI, back to Player1
        current_player_index = (next_player_candidate_index + play_direction + num_players) % num_players
        ai_was_skipped_this_turn = True
        # pending_draw_amount (if any, e.g. from P1 playing +2 then Skip) will now apply to P1.

    elif players[next_player_candidate_index] == "Player2": # AI's turn, not skipped by Player1
        current_player_index = next_player_candidate_index # Officially AI's turn now
        # ai_last_banter = "" # Reset AI banter before its turn, execute_ai_turn will set it.
        print(f"Starting AI ({players[current_player_index]}) turn...")

        # Note: The placeholder logic for AI drawing due to pending_draw_amount was removed here.
        # execute_ai_turn() is responsible for handling pending_draw_amount at the START of its turn.

        execute_ai_turn() # AI makes its decision (handles its own pending draws, plays, sets banter)

        # Advance turn to the next player (should be Player1)
        current_player_index = (current_player_index + play_direction + num_players) % num_players
        print(f"AI ({players[next_player_candidate_index]}) turn finished. Next player is now: {players[current_player_index]}")

    else: # Should not happen in a 2-player game where P1 just ended their turn.
          # This would imply next player is P1 again without AI turn, or other logic error.
        current_player_index = next_player_candidate_index
        print(f"Warning: Unexpected turn sequence. Next player is {players[current_player_index]}")


    final_next_player_name = players[current_player_index]
    
    # If Player1 is now to play, and there's a pending_draw_amount (e.g. AI played +2/+4 on P1, or P1 skipped AI when P1 had played +X)
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
        "pending_draw_amount": pending_draw_amount,
        "opponent_card_count": opponent_card_count,
        "game_winner": game_winner,
        "is_next_player_skipped": is_next_player_skipped # For completeness
    }
    return jsonify(response_data)

@app.route('/api/choose_color', methods=['POST'])
def choose_color():
    global current_player_index, players, awaiting_color_choice, current_chosen_color, COLORS
    global game_deck, player_hands, discard_pile_top_card, play_direction, ai_last_banter, pending_draw_amount, game_winner # For full game state return

    current_player_name = players[current_player_index]

    if not game_started:
        return jsonify({"error": "Game not started."}), 400
    if current_player_name != "Player1":
        return jsonify({"error": "Not Player1's turn to choose a color."}), 400
    if not awaiting_color_choice:
        return jsonify({"error": "Not awaiting a color choice."}), 400

    data = request.get_json()
    chosen_color = data.get('chosen_color')

    if not chosen_color or chosen_color not in COLORS:
        return jsonify({"error": "Invalid color chosen."}), 400

    current_chosen_color = chosen_color
    awaiting_color_choice = False

    message = f"Player1 chose color: {current_chosen_color}."
    print(message)

    # Similar to get_game_state, return the full state so frontend can update.
    # This is after Player1 has chosen a color, so it's still Player1's "action phase" potentially,
    # or the turn is about to be passed. The key is that current_player is still Player1 here.
    hand_to_send = player_hands.get(current_player_name, [])
    opponent_player_name = players[(current_player_index + 1) % len(players)] # Should be Player2
    opponent_card_count = len(player_hands.get(opponent_player_name, []))


    # After choosing a color, if the card was a Wild Draw Four, the pending_draw_amount
    # would have already been set during the play_card action.
    # The turn should then proceed to the AI.
    # It might be good to call end_turn logic here if the user is expected to click "End Turn"
    # OR if choosing color automatically ends the "action" part of their turn.
    # For now, let's assume choosing color is the final part of their wild card play,
    # and the user will subsequently click "End Turn". The end_turn checks will then apply.

    game_state_response = {
        "success": True,
        "message": message,
        "player_hand": hand_to_send,
        "discard_pile_top_card": discard_pile_top_card if discard_pile_top_card else {"color": "grey", "value": "Empty"},
        "deck_card_count": len(game_deck),
        "current_player": current_player_name, # Still Player1
        "current_chosen_color": current_chosen_color,
        "awaiting_color_choice": awaiting_color_choice, # Should be false now
        "players_list": players,
        "play_direction": "forward" if play_direction == 1 else "backward",
        "pending_draw_amount": pending_draw_amount,
        "ai_last_banter": ai_last_banter, # Carry over any existing banter
        "game_winner": game_winner,
        "opponent_card_count": opponent_card_count
    }
    return jsonify(game_state_response)


if __name__ == '__main__':
    app.run(debug=True)

// Global game state variables
let playerHand = [];
let discardTopCard = null;
let deckCardCount = 0;
let currentPlayerName = '';
let currentChosenColorDisplay = ''; // For displaying the active color after a Wild
let playersList = [];
let playDirectionDisplay = '';
let awaiting_color_choice_frontend = false; // To manage UI state for color picking
// let messageFromServer = ""; // Optional: For displaying messages from server
let aiLastBanter = '';
let pendingDrawAmountFE = 0;
let showAiThinkingMessage = false;
let opponentCardCountFE = 0;
let gameWinnerFE = null;

class UnoCard {
  constructor(color, value) {
    this.color = color;
    this.value = value;
  }
}

// Global game layout variables
const HAND_CARD_WIDTH = 100;
const HAND_CARD_HEIGHT = 150;
const HAND_CARD_SPACING = 10; // Define spacing globally for consistency
const DECK_X = 200; // X position for the deck
let DISCARD_X; // Will be calculated in setup

let HAND_Y_POSITION; // Y position for the player's hand
let DECK_Y;          // Y position for the deck
let DISCARD_Y;       // Y position for the discard pile

let gameButtons = [];   // To hold button objects

async function fetchAndUpdateGameState() {
  try {
    const response = await fetch('/api/gamestate');
    if (!response.ok) {
      throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
    }
    const gameState = await response.json();
    console.log("Fetched game state:", gameState); // For debugging

    if (gameState.player_hand) playerHand = gameState.player_hand.map(cardData => new UnoCard(cardData.color, cardData.value));
    else { playerHand = [new UnoCard('grey', 'ErrorP')]; console.error("Player hand data missing in fetched state."); }

    if (gameState.discard_pile_top_card && gameState.discard_pile_top_card.color && gameState.discard_pile_top_card.value) {
      discardTopCard = new UnoCard(gameState.discard_pile_top_card.color, gameState.discard_pile_top_card.value);
    } else { discardTopCard = null; console.warn("Discard pile top card data missing or incomplete in fetched state. Setting to null.");}

    deckCardCount = gameState.deck_card_count !== undefined ? gameState.deck_card_count : 0;
    currentPlayerName = gameState.current_player || 'N/A';
    currentChosenColorDisplay = gameState.current_chosen_color || ''; 
    awaiting_color_choice_frontend = gameState.awaiting_color_choice !== undefined ? gameState.awaiting_color_choice : false;
    playersList = gameState.players_list || [];
    playDirectionDisplay = gameState.play_direction || 'N/A';
    // if(gameState.message) messageFromServer = gameState.message;
    aiLastBanter = gameState.ai_last_banter || '';
    pendingDrawAmountFE = gameState.pending_draw_amount !== undefined ? gameState.pending_draw_amount : 0;
    opponentCardCountFE = gameState.opponent_card_count !== undefined ? gameState.opponent_card_count : 0;
    gameWinnerFE = gameState.game_winner || null;
    
  } catch (error) {
    console.error('Failed to fetch and update game state:', error);
    playerHand = [new UnoCard('grey', 'ConnErrP')]; discardTopCard = new UnoCard('grey', 'ConnErrD');
    deckCardCount = 0; currentPlayerName = 'Error'; currentChosenColorDisplay = 'Error';
    awaiting_color_choice_frontend = false; playersList = []; playDirectionDisplay = 'Error';
    // messageFromServer = `Error: ${error.message}`;
    aiLastBanter = 'Error fetching banter.';
    pendingDrawAmountFE = 0;
    opponentCardCountFE = 0;
    gameWinnerFE = null;
  }
}


function drawUnoCard(card, x, y, cardWidth, cardHeight) {
  if (!card || !card.color || !card.value) {
    console.warn("Attempted to draw invalid card object:", card);
    fill(100); noStroke(); rect(x, y, cardWidth, cardHeight, cardWidth / 12);
    fill(255); textAlign(CENTER,CENTER); text("BAD", x + cardWidth/2, y + cardHeight/2);
    return;
  }
  const cornerRadius = cardWidth / 12; 
  const tiltAngle = 15;

  let cardColorValue;
  if (card.color === 'red') cardColorValue = color(255, 0, 0);
  else if (card.color === 'yellow') cardColorValue = color(255, 255, 0);
  else if (card.color === 'green') cardColorValue = color(0, 255, 0);
  else if (card.color === 'blue') cardColorValue = color(0, 0, 255);
  else if (card.color === 'black') cardColorValue = color(0, 0, 0);
  else if (card.color === 'grey') cardColorValue = color(128);
  else cardColorValue = color(200); 
  
  fill(cardColorValue); noStroke(); rect(x, y, cardWidth, cardHeight, cornerRadius);

  const isWild = card.value === 'wild';
  const isWildDrawFour = card.value === 'wildDrawFour';

  if (isWild || isWildDrawFour) {
    const segmentWidth = cardWidth * 0.35; const segmentHeight = cardHeight * 0.3;
    const centerX = x + cardWidth / 2; const centerY = y + cardHeight / 2;
    fill(255, 0, 0); rect(centerX - segmentWidth, centerY - segmentHeight, segmentWidth, segmentHeight);
    fill(255, 255, 0); rect(centerX, centerY - segmentHeight, segmentWidth, segmentHeight);
    fill(0, 255, 0); rect(centerX - segmentWidth, centerY, segmentWidth, segmentHeight);
    fill(0, 0, 255); rect(centerX, centerY, segmentWidth, segmentHeight);

    push(); translate(centerX, centerY);
    fill(255); stroke(0); strokeWeight(cardWidth / 60);
    textAlign(CENTER, CENTER); textStyle(BOLD);
    if (isWildDrawFour) { textSize(cardWidth / 3); text('+4', 0, 0); }
    else { textSize(cardWidth / 5); text('WILD', 0, 0); }
    pop();
  } else {
    const isErrorCard = ["ErrorP", "ErrorD", "ConnErrP", "ConnErrD", "X", "Y", "BAD", "Empty"].includes(card.value);
    if (!isErrorCard) {
      const ellipseWidth = cardWidth * 0.75; const ellipseHeight = cardHeight * 0.78; 
      push(); translate(x + cardWidth / 2, y + cardHeight / 2); rotate(tiltAngle);
      fill(255, 255, 255); noStroke(); ellipse(0, 0, ellipseWidth, ellipseHeight);
      pop();
    }

    push(); translate(x + cardWidth / 2, y + cardHeight / 2); rotate(tiltAngle);
    let centralTextColor, centralStrokeColor;
    if (card.color === 'yellow') { centralTextColor = color(0); centralStrokeColor = color(255); }
    else if (card.color === 'grey') { centralTextColor = color(255); centralStrokeColor = color(0); }
    else { centralTextColor = cardColorValue; centralStrokeColor = color(255); }

    fill(centralTextColor); stroke(centralStrokeColor); strokeWeight(cardWidth / 75); 
    textAlign(CENTER, CENTER); textStyle(BOLD);
    let centralValue = card.value; let centralTextSize = cardWidth / 2.5; 
    if (card.value === 'skip') { centralValue = 'S'; centralTextSize = cardWidth / 2; }
    else if (card.value === 'reverse') { centralValue = 'R'; centralTextSize = cardWidth / 2; }
    else if (card.value === 'drawTwo') { centralValue = '+2'; centralTextSize = cardWidth / 2; }
    textSize(centralTextSize); text(centralValue, 0, 0);
    pop();
  }

  let cornerValue = card.value;
  if (isWild) cornerValue = 'W'; else if (isWildDrawFour) cornerValue = 'W+4';
  else if (card.value === 'skip') cornerValue = 'S'; else if (card.value === 'reverse') cornerValue = 'R';
  else if (card.value === 'drawTwo') cornerValue = '+2';
  
  const cornerTextSize = cardWidth / 7; const cornerXOffset = cardWidth * 0.12; const cornerYOffset = cardHeight * 0.08; 
  fill(255); noStroke(); textStyle(BOLD); textSize(cornerTextSize); textAlign(CENTER, CENTER);
  text(cornerValue, x + cornerXOffset, y + cornerYOffset + (cornerTextSize / 3)); 
  push(); translate(x + cardWidth - cornerXOffset, y + cardHeight - cornerYOffset - (cornerTextSize / 3)); rotate(180);
  text(cornerValue, 0, 0);
  pop();
}

function drawPlayerHand(handArray, startX, startY, cardWidth, cardHeight, spacing) {
  if (!handArray) return; 
  for (let i = 0; i < handArray.length; i++) {
    const card = handArray[i];
    const currentX = startX + i * (cardWidth + spacing);
    drawUnoCard(card, currentX, startY, cardWidth, cardHeight);
  }
}

function drawDeck(x, y, cardWidth, cardHeight, count) { 
  const offsetX = 4; const offsetY = 4; const cornerRadius = cardWidth / 15; 
  if (count === 0) { 
    fill(0, 80, 0); noStroke(); rect(x,y, cardWidth, cardHeight, cornerRadius); return;
  }
  const displayStackCount = Math.min(count, 3); 
  fill(0); noStroke();
  for (let i = 0; i < displayStackCount -1; i++) {
    rect(x + i * offsetX, y - i * offsetY, cardWidth, cardHeight, cornerRadius);
  }
  const topX = x + (displayStackCount - 1) * offsetX; const topY = y - (displayStackCount - 1) * offsetY;
  fill(20, 20, 20); stroke(100); strokeWeight(1); rect(topX, topY, cardWidth, cardHeight, cornerRadius);
  push(); translate(topX + cardWidth / 2, topY + cardHeight / 2); rotate(15); 
  stroke(255); strokeWeight(cardWidth / 50); textAlign(CENTER, CENTER); textStyle(BOLD); textSize(cardHeight / 3.5); 
  fill(255,255,0); text('UNO', cardWidth/30, cardHeight/30); fill(255, 0, 0); text('UNO', 0, 0);
  pop();
}

function drawDiscardPile(dTopCard, x, y, cardWidth, cardHeight) { 
  if (dTopCard && dTopCard.color && dTopCard.value) { 
    drawUnoCard(dTopCard, x, y, cardWidth, cardHeight);
  } else {
    fill(0, 80, 0); noStroke(); rect(x, y, cardWidth, cardHeight, cardWidth / 15);
  }
}

function drawButtonPlaceholders(buttonDataArray) {
  if (!buttonDataArray) return;
  for (const buttonObject of buttonDataArray) {
    if (buttonObject.color) { if (typeof buttonObject.color === 'string') fill(buttonObject.color); else fill(buttonObject.color); }
    else fill(100); 
    noStroke(); rect(buttonObject.x, buttonObject.y, buttonObject.width, buttonObject.height, 5);
    if (buttonObject.textColor) { if (typeof buttonObject.textColor === 'string') fill(buttonObject.textColor); else fill(buttonObject.textColor); }
    else fill(0); 
    textAlign(CENTER, CENTER); textSize(buttonObject.height * 0.4); 
    text(buttonObject.label, buttonObject.x + buttonObject.width / 2, buttonObject.y + buttonObject.height / 2);
  }
}

async function setup() { 
  createCanvas(1200, 800); angleMode(DEGREES); textFont('Arial');
  HAND_Y_POSITION = height - HAND_CARD_HEIGHT - 40; DECK_Y = height / 2 - HAND_CARD_HEIGHT / 2;
  DISCARD_X = DECK_X + HAND_CARD_WIDTH + 50; DISCARD_Y = DECK_Y;
  let buttonWidth = 180; let buttonHeight = 50; 
  let firstButtonX = width - (buttonWidth * 3 + 2 * 10) - 40 ; 
  gameButtons = [
    { label: 'Draw Card', x: firstButtonX, y: HAND_Y_POSITION - buttonHeight - 30, width: buttonWidth, height: buttonHeight, color: color(0,150,0), textColor: color(255) },
    { label: 'UNO!', x: firstButtonX + buttonWidth + 10, y: HAND_Y_POSITION - buttonHeight - 30, width: buttonWidth, height: buttonHeight, color: color(255,223,0), textColor: color(0) }, 
    { label: 'End Turn', x: firstButtonX + 2*(buttonWidth + 10), y: HAND_Y_POSITION - buttonHeight - 30, width: buttonWidth, height: buttonHeight, color: color(200,0,0), textColor: color(255) }
  ];
  await fetchAndUpdateGameState(); 
}

function draw() {
  background(0, 100, 0); 
  
  const currentHandLength = playerHand ? playerHand.length : 0;
  const totalHandWidth = (currentHandLength * (HAND_CARD_WIDTH + HAND_CARD_SPACING)) - HAND_CARD_SPACING;
  const handStartX = (width - totalHandWidth) / 2;

  drawPlayerHand(playerHand, handStartX, HAND_Y_POSITION, HAND_CARD_WIDTH, HAND_CARD_HEIGHT, HAND_CARD_SPACING);
  drawDeck(DECK_X, DECK_Y, HAND_CARD_WIDTH, HAND_CARD_HEIGHT, deckCardCount); 
  drawDiscardPile(discardTopCard, DISCARD_X, DISCARD_Y, HAND_CARD_WIDTH, HAND_CARD_HEIGHT);
  drawButtonPlaceholders(gameButtons);

  // Game Status Text Display
  const statusTextX = 20;
  let statusTextY = 20;
  const statusTextLeading = 25; // Spacing between lines of text

  fill(255); // White text for general status
  textSize(18); // Slightly smaller for less critical info
  textAlign(LEFT, TOP);
  
  text(`Current Player: ${currentPlayerName}`, statusTextX, statusTextY);
  statusTextY += statusTextLeading;
  
  text(`Active Color: ${currentChosenColorDisplay || 'None'}`, statusTextX, statusTextY);
  statusTextY += statusTextLeading;
  
  text(`Players: ${playersList.join(', ')}`, statusTextX, statusTextY);
  statusTextY += statusTextLeading;
  
  text(`Direction: ${playDirectionDisplay}`, statusTextX, statusTextY);
  statusTextY += statusTextLeading;

  text(`Player2 (AI) Cards: ${opponentCardCountFE}`, statusTextX, statusTextY);
  statusTextY += statusTextLeading;

  if (pendingDrawAmountFE > 0 && currentPlayerName === 'Player1') {
    fill(255, 100, 100); // Light red for warning
    textSize(20);
    // textAlign(LEFT, TOP); // Already set
    text(`Must Draw: ${pendingDrawAmountFE} cards!`, statusTextX, statusTextY);
    statusTextY += statusTextLeading; // Increment if adding more text below
  }

  // statusTextY += statusTextLeading;
  // if (messageFromServer) { text(`Message: ${messageFromServer}`, statusTextX, statusTextY); }

  if (aiLastBanter) {
    fill(255, 255, 150); // Light yellow for banter
    textSize(16);
    textAlign(CENTER, TOP);
    text(`AI Says: "${aiLastBanter}"`, width / 2, statusTextY + statusTextLeading * 0.5); // Adjusted Y
  }
  textAlign(LEFT, TOP); // Reset alignment for other texts if changed

  // Prominent "Awaiting Color Choice" message
  if (awaiting_color_choice_frontend) {
    push(); // Isolate text style changes
    fill(255, 223, 0); // Bright yellow for emphasis
    textSize(28);
    textAlign(CENTER, CENTER);
    // Position it above the discard pile, or more centrally if preferred
    text("Wild Card Played! Choose a color.", DISCARD_X + HAND_CARD_WIDTH / 2, DISCARD_Y - HAND_CARD_HEIGHT / 2 - 30);
    pop();
  }

  if (showAiThinkingMessage) {
    push();
    fill(200, 200, 255, 200); // Semi-transparent overlay
    rect(0, 0, width, height);
    fill(0);
    textSize(32);
    textAlign(CENTER, CENTER);
    text("Player2 (AI) is thinking...", width / 2, height / 2);
    pop();
  }

  if (gameWinnerFE) {
    push();
    fill(0, 0, 0, 220); // Darker overlay
    rect(0, 0, width, height);
    fill(255, 220, 0); // Gold text
    textSize(50);
    textAlign(CENTER, CENTER);
    text(`${gameWinnerFE} has won the game!`, width / 2, height / 2 - 30);
    textSize(25);
    text("Refresh to play again.", width / 2, height / 2 + 30);
    pop();
    noLoop(); // Optional: stop drawing if game is over
  }
}

function mousePressed() {
  // Card click detection
  if (playerHand && playerHand.length > 0) {
    const currentHandLength = playerHand.length;
    const totalHandWidth = (currentHandLength * HAND_CARD_WIDTH) + ((currentHandLength > 0 ? currentHandLength - 1 : 0) * HAND_CARD_SPACING);
    let currentHandStartX = (width - totalHandWidth) / 2;

    for (let i = 0; i < currentHandLength; i++) {
      let cardX = currentHandStartX + i * (HAND_CARD_WIDTH + HAND_CARD_SPACING);
      let cardY = HAND_Y_POSITION;
      if (mouseX >= cardX && mouseX <= cardX + HAND_CARD_WIDTH &&
          mouseY >= cardY && mouseY <= cardY + HAND_CARD_HEIGHT) {
        
        const clickedCardObject = playerHand[i];
        const cardToPlay = { 
            color: clickedCardObject.color, 
            value: clickedCardObject.value 
        };
        console.log("Attempting to play card:", cardToPlay);

        fetch('/api/play_card', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(cardToPlay)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errData => {
                     console.error('Play card request failed:', response.status, errData.message || errData);
                     alert("Invalid Play: " + (errData.message || "Move not allowed."));
                     throw new Error(errData.message || `Play card request failed: ${response.statusText}`);
                }).catch((parsingError) => { 
                     console.error('Play card request failed or error JSON parsing failed:', response.status, response.statusText, parsingError);
                     alert("Invalid Play: " + response.statusText);
                     throw new Error(`Play card request failed: ${response.statusText} - Could not parse error JSON or already handled.`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                console.log('Play card successful:', data.message, data); 
                
                if (data.player_hand) playerHand = data.player_hand.map(cardData => new UnoCard(cardData.color, cardData.value));
                if (data.discard_pile_top_card && data.discard_pile_top_card.color && data.discard_pile_top_card.value) {
                    discardTopCard = new UnoCard(data.discard_pile_top_card.color, data.discard_pile_top_card.value);
                } else { discardTopCard = null; }
                deckCardCount = data.deck_card_count !== undefined ? data.deck_card_count : deckCardCount;
                currentPlayerName = data.current_player || currentPlayerName;
                currentChosenColorDisplay = data.current_chosen_color || ''; 
                awaiting_color_choice_frontend = data.awaiting_color_choice !== undefined ? data.awaiting_color_choice : awaiting_color_choice_frontend;
                playersList = data.players_list || playersList;
                playDirectionDisplay = data.play_direction || playDirectionDisplay;
                // if(data.message) messageFromServer = data.message;

            } else {
                console.error('Play card reported as not successful by server:', data.message);
                if (data.message) {
                    alert("Play Card Error: " + data.message);
                }
            }
        })
        .catch(error => { 
            console.error('Error sending play card request:', error);
        });
        return; 
      }
    }
  }

  // Button click detection 
  if (gameButtons && gameButtons.length > 0) {
    for (const button of gameButtons) {
      if (mouseX >= button.x && mouseX <= button.x + button.width &&
          mouseY >= button.y && mouseY <= button.y + button.height) {
        
        if (button.label === 'Draw Card') {
          console.log("Draw Card button clicked! - Attempting to draw from backend...");
          fetch('/api/draw_card', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' }
          })
          .then(response => {
              if (!response.ok) {
                  return response.json().then(errData => {
                      alert("Draw Card Error: " + (errData.message || "Failed to draw card."));
                      throw new Error(`Network response was not ok. Status: ${response.status}. Message: ${errData.error || errData.message || 'No error message from server.'}`);
                  }).catch(() => {
                      alert("Draw Card Error: " + response.statusText);
                      throw new Error(`Network response was not ok. Status: ${response.status}. Could not parse error from server.`);
                  });
              }
              return response.json(); 
          })
          .then(data => {
              console.log('Draw card action successful, new game state:', data);
              if(data.message) console.log("Message from server: " + data.message);
              if (data.player_hand) playerHand = data.player_hand.map(cardData => new UnoCard(cardData.color, cardData.value));
              if (data.discard_pile_top_card && data.discard_pile_top_card.color && data.discard_pile_top_card.value) {
                  discardTopCard = new UnoCard(data.discard_pile_top_card.color, data.discard_pile_top_card.value);
              } else { discardTopCard = null; }
              deckCardCount = data.deck_card_count !== undefined ? data.deck_card_count : 0;
              currentPlayerName = data.current_player || 'N/A';
              currentChosenColorDisplay = data.current_chosen_color || '';
              awaiting_color_choice_frontend = data.awaiting_color_choice !== undefined ? data.awaiting_color_choice : awaiting_color_choice_frontend;
              playersList = data.players_list || [];
              playDirectionDisplay = data.play_direction || '';
          })
          .catch(error => {
              console.error('Error during draw card action:', error);
          });
        } else if (button.label === 'End Turn') {
            console.log("End Turn button clicked! - Attempting to end turn via backend...");
            showAiThinkingMessage = true;
            redraw(); // Show "AI is thinking..." message

            fetch('/api/end_turn', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(errData => {
                        alert("End Turn Error: " + (errData.message || "Failed to end turn."));
                        throw new Error(`Network response was not ok. Status: ${response.status}. Message: ${errData.error || errData.message || 'No error message from server.'}`);
                    }).catch(() => {
                        alert("End Turn Error: " + response.statusText);
                        throw new Error(`Network response was not ok. Status: ${response.status}. Could not parse error from server.`);
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log('End turn response received, game state:', data);
                showAiThinkingMessage = false; // Hide "AI is thinking..."

                if(data.message) console.log("Message from server: " + data.message);
                if (data.player_hand) playerHand = data.player_hand.map(cardData => new UnoCard(cardData.color, cardData.value));

                if (data.discard_pile_top_card && data.discard_pile_top_card.color && data.discard_pile_top_card.value) {
                    discardTopCard = new UnoCard(data.discard_pile_top_card.color, data.discard_pile_top_card.value);
                } else { discardTopCard = null; } 

                deckCardCount = data.deck_card_count !== undefined ? data.deck_card_count : 0;
                currentPlayerName = data.current_player || 'N/A'; 
                currentChosenColorDisplay = data.current_chosen_color || '';
                awaiting_color_choice_frontend = data.awaiting_color_choice !== undefined ? data.awaiting_color_choice : awaiting_color_choice_frontend;
                playersList = data.players_list || [];
                playDirectionDisplay = data.play_direction || '';
                aiLastBanter = data.ai_last_banter || '';
                pendingDrawAmountFE = data.pending_draw_amount !== undefined ? data.pending_draw_amount : 0;
                opponentCardCountFE = data.opponent_card_count !== undefined ? data.opponent_card_count : 0;
                gameWinnerFE = data.game_winner || null;

                if (gameWinnerFE) {
                    redraw();
                    noLoop();
                }
            })
            .catch(error => {
                console.error('Error during end turn action:', error);
                showAiThinkingMessage = false;
                fetchAndUpdateGameState();
            });
        } else {
          console.log(button.label + " button clicked!");
        }
        break; 
      }
    }
  }
}

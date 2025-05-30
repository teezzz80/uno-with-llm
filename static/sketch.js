// Global variable to hold game state fetched from the server
let initialGameState;

class UnoCard {
  constructor(color, value) {
    this.color = color;
    this.value = value;
  }
}

// Global game layout variables
const HAND_CARD_WIDTH = 100;
const HAND_CARD_HEIGHT = 150;
const DECK_X = 200; // X position for the deck
let DISCARD_X; // Will be calculated in setup

let HAND_Y_POSITION; // Y position for the player's hand
let DECK_Y;          // Y position for the deck
let DISCARD_Y;       // Y position for the discard pile

let playerHand = []; // Initialize as empty, will be populated from fetched data

let discardTopCard; // To hold the card on top of the discard pile, populated from fetched data
let gameButtons = [];   // To hold button objects

function preload() {
  initialGameState = loadJSON('/api/gamestate', 
    (data) => {
      console.log('Game state fetched successfully:', data);
    },
    (error) => {
      console.error('Error fetching game state:', error);
      // Provide a fallback state if fetching fails
      initialGameState = { 
        player_hand: [
          { color: "red", value: "Error" }, 
          { color: "blue", value: "L" } // Load
        ],
        discard_pile_top_card: { color: "black", value: "Fail" }, // Error
        deck_card_count: 0,
        current_player_color: "grey"
      };
    }
  );
}

function drawUnoCard(card, x, y, cardWidth, cardHeight) {
  const cornerRadius = cardWidth / 12; // Proportional corner radius
  const tiltAngle = 15;

  // 1. Card Body
  let cardColorValue;
  if (card.color === 'red') {
    cardColorValue = color(255, 0, 0);
  } else if (card.color === 'yellow') {
    cardColorValue = color(255, 255, 0);
  } else if (card.color === 'green') {
    cardColorValue = color(0, 255, 0);
  } else if (card.color === 'blue') {
    cardColorValue = color(0, 0, 255);
  } else if (card.color === 'black') {
    cardColorValue = color(0, 0, 0);
  } else  if (card.color === 'grey') { // For fallback/error cards
    cardColorValue = color(128);
  }else {
    cardColorValue = color(200); // Default grey for unknown colors
  }
  fill(cardColorValue);
  noStroke();
  rect(x, y, cardWidth, cardHeight, cornerRadius);

  const isWild = card.value === 'wild';
  const isWildDrawFour = card.value === 'wildDrawFour';

  if (isWild || isWildDrawFour) {
    // 6. Special Handling for Wild Cards
    const segmentWidth = cardWidth * 0.35;
    const segmentHeight = cardHeight * 0.3;
    const centerX = x + cardWidth / 2;
    const centerY = y + cardHeight / 2;

    fill(255, 0, 0); // Red
    rect(centerX - segmentWidth, centerY - segmentHeight, segmentWidth, segmentHeight);
    fill(255, 255, 0); // Yellow
    rect(centerX, centerY - segmentHeight, segmentWidth, segmentHeight);
    fill(0, 255, 0); // Green
    rect(centerX - segmentWidth, centerY, segmentWidth, segmentHeight);
    fill(0, 0, 255); // Blue
    rect(centerX, centerY, segmentWidth, segmentHeight);

    if (isWildDrawFour) {
      push();
      translate(centerX, centerY);
      fill(255); 
      stroke(0); 
      strokeWeight(cardWidth / 60);
      textAlign(CENTER, CENTER);
      textStyle(BOLD);
      textSize(cardWidth / 3);
      text('+4', 0, 0);
      pop();
    } else { 
      push();
      translate(centerX, centerY);
      fill(255);
      stroke(0);
      strokeWeight(cardWidth / 70);
      textAlign(CENTER, CENTER);
      textStyle(BOLD);
      textSize(cardWidth / 5); 
      text('WILD', 0, 0);
      pop();
    }
  } else {
    // 3. Central White Ellipse (not for error cards like "Fail", "Error", "X", "Y")
    if (card.value !== "Error" && card.value !== "L" && card.value !== "Fail" && card.value !== "X" && card.value !== "Y") {
      const ellipseWidth = cardWidth * 0.75;
      const ellipseHeight = cardHeight * 0.78; 
      push();
      translate(x + cardWidth / 2, y + cardHeight / 2);
      rotate(tiltAngle);
      fill(255, 255, 255);
      noStroke();
      ellipse(0, 0, ellipseWidth, ellipseHeight);
      pop();
    }

    // 4. Central Symbol/Value Text
    push();
    translate(x + cardWidth / 2, y + cardHeight / 2);
    rotate(tiltAngle);
    
    let centralTextColor, centralStrokeColor;
    if (card.color === 'yellow') { 
        centralTextColor = color(0); 
        centralStrokeColor = color(255); 
    } else if (card.color === 'grey') {
        centralTextColor = color(255);
        centralStrokeColor = color(0);
    }
    else {
        centralTextColor = cardColorValue; 
        centralStrokeColor = color(255); 
    }

    fill(centralTextColor);
    stroke(centralStrokeColor);
    strokeWeight(cardWidth / 75); 
    textAlign(CENTER, CENTER);
    textStyle(BOLD);

    let centralValue = card.value;
    let centralTextSize = cardWidth / 2.5; 

    if (card.value === 'skip') {
      centralValue = 'S'; 
      centralTextSize = cardWidth / 2;
    } else if (card.value === 'reverse') {
      centralValue = 'R'; 
      centralTextSize = cardWidth / 2;
    } else if (card.value === 'drawTwo') {
      centralValue = '+2';
      centralTextSize = cardWidth / 2;
    }
    textSize(centralTextSize);
    text(centralValue, 0, 0);
    pop();
  }

  // 5. Corner Symbols/Value Texts (don't draw for fully custom error values if they don't map)
  let cornerValue = card.value;
  if (isWild) cornerValue = 'W';
  if (isWildDrawFour) cornerValue = 'W+4';
  if (card.value === 'skip') cornerValue = 'S';
  if (card.value === 'reverse') cornerValue = 'R';
  if (card.value === 'drawTwo') cornerValue = '+2';
  // For error/fallback cards, the value itself is descriptive enough for corners
  
  const cornerTextSize = cardWidth / 7; 
  const cornerXOffset = cardWidth * 0.12; 
  const cornerYOffset = cardHeight * 0.08; 

  fill(255); // White for corners generally good even for error cards
  noStroke();
  textStyle(BOLD);
  textSize(cornerTextSize);
  textAlign(CENTER, CENTER);

  text(cornerValue, x + cornerXOffset, y + cornerYOffset + (cornerTextSize / 3)); 

  push();
  translate(x + cardWidth - cornerXOffset, y + cardHeight - cornerYOffset - (cornerTextSize / 3));
  rotate(180);
  text(cornerValue, 0, 0);
  pop();
}

function drawPlayerHand(handArray, startX, startY, cardWidth, cardHeight, spacing) {
  if (!handArray) return; // Guard against null/undefined handArray
  for (let i = 0; i < handArray.length; i++) {
    const card = handArray[i];
    if (!card) continue; // Skip if a card object is missing
    const currentX = startX + i * (cardWidth + spacing);
    drawUnoCard(card, currentX, startY, cardWidth, cardHeight);
  }
}

function drawDeck(x, y, cardWidth, cardHeight, stackCount) {
  const offsetX = 4;
  const offsetY = 4;
  const cornerRadius = cardWidth / 15; 

  fill(0); 
  noStroke();
  for (let i = 0; i < stackCount -1; i++) {
    rect(x + i * offsetX, y - i * offsetY, cardWidth, cardHeight, cornerRadius);
  }

  const topX = x + (stackCount - 1) * offsetX;
  const topY = y - (stackCount - 1) * offsetY;
  fill(20, 20, 20); 
  stroke(100); 
  strokeWeight(1);
  rect(topX, topY, cardWidth, cardHeight, cornerRadius);

  push();
  translate(topX + cardWidth / 2, topY + cardHeight / 2);
  rotate(15); 
  stroke(255); 
  strokeWeight(cardWidth / 50);
  textAlign(CENTER, CENTER);
  textStyle(BOLD);
  textSize(cardHeight / 3.5); 
  
  fill(255,255,0); 
  text('UNO', cardWidth/30, cardHeight/30); 
  fill(255, 0, 0); 
  text('UNO', 0, 0);
  pop();
}

function drawDiscardPile(topCard, x, y, cardWidth, cardHeight) {
  if (topCard) { 
    drawUnoCard(topCard, x, y, cardWidth, cardHeight);
  } else {
    // Optional: Draw an empty slot placeholder
    // fill(0, 50, 0); 
    // noStroke();
    // rect(x, y, cardWidth, cardHeight, cardWidth / 15);
  }
}

function drawButtonPlaceholders(buttonDataArray) {
  if (!buttonDataArray) return;

  for (const buttonObject of buttonDataArray) {
    if (buttonObject.color) {
        if (typeof buttonObject.color === 'string') {
            fill(buttonObject.color); 
        } else {
            fill(buttonObject.color); 
        }
    } else {
        fill(100); 
    }
    noStroke(); 
    rect(buttonObject.x, buttonObject.y, buttonObject.width, buttonObject.height, 5);

    if (buttonObject.textColor) {
        if (typeof buttonObject.textColor === 'string') {
            fill(buttonObject.textColor);
        } else {
            fill(buttonObject.textColor);
        }
    } else {
        fill(0); 
    }
    textAlign(CENTER, CENTER);
    textSize(buttonObject.height * 0.4); 
    text(buttonObject.label, buttonObject.x + buttonObject.width / 2, buttonObject.y + buttonObject.height / 2);
  }
}

function setup() {
  createCanvas(1200, 800);
  angleMode(DEGREES); 
  textFont('Arial');

  // Calculate positions that depend on width/height
  HAND_Y_POSITION = height - HAND_CARD_HEIGHT - 40;
  DECK_Y = height / 2 - HAND_CARD_HEIGHT / 2;
  DISCARD_X = DECK_X + HAND_CARD_WIDTH + 50; // Place discard pile next to deck
  DISCARD_Y = DECK_Y;

  // Populate playerHand and discardTopCard from fetched data
  if (initialGameState && initialGameState.player_hand) {
    playerHand = initialGameState.player_hand.map(cardData => new UnoCard(cardData.color, cardData.value));
  } else {
    // Fallback if initialGameState or player_hand is missing
    playerHand = [new UnoCard('grey', 'X')]; // Default/error card
    console.error('Player hand data not available from server, using fallback.');
  }

  if (initialGameState && initialGameState.discard_pile_top_card) {
    discardTopCard = new UnoCard(initialGameState.discard_pile_top_card.color, initialGameState.discard_pile_top_card.value);
  } else {
    // Fallback for discard card
    discardTopCard = new UnoCard('grey', 'Y'); // Default/error card
    console.error('Discard pile data not available from server, using fallback.');
  }
  
  // Log other fetched game state info for debugging or future use
  if (initialGameState) {
    console.log("Deck count from server: " + initialGameState.deck_card_count);
    console.log("Current color from server: " + initialGameState.current_player_color);
  }


  let buttonWidth = 180;
  let buttonHeight = 50; 
  let firstButtonX = width - (buttonWidth * 3 + 2 * 10) - 40 ; 

  gameButtons = [
    { label: 'Draw Card', x: firstButtonX, y: HAND_Y_POSITION - buttonHeight - 30, width: buttonWidth, height: buttonHeight, color: color(0,150,0), textColor: color(255) },
    { label: 'UNO!', x: firstButtonX + buttonWidth + 10, y: HAND_Y_POSITION - buttonHeight - 30, width: buttonWidth, height: buttonHeight, color: color(255,223,0), textColor: color(0) }, 
    { label: 'End Turn', x: firstButtonX + 2*(buttonWidth + 10), y: HAND_Y_POSITION - buttonHeight - 30, width: buttonWidth, height: buttonHeight, color: color(200,0,0), textColor: color(255) }
  ];
}

function draw() {
  background(0, 100, 0); // Green card table background

  const handSpacing = 10; 
  // Ensure playerHand is not undefined before calculating totalHandWidth
  const currentHandLength = playerHand ? playerHand.length : 0;
  const totalHandWidth = (currentHandLength * (HAND_CARD_WIDTH + handSpacing)) - handSpacing;
  const handStartX = (width - totalHandWidth) / 2;

  drawPlayerHand(playerHand, handStartX, HAND_Y_POSITION, HAND_CARD_WIDTH, HAND_CARD_HEIGHT, handSpacing);
  drawDeck(DECK_X, DECK_Y, HAND_CARD_WIDTH, HAND_CARD_HEIGHT, initialGameState ? initialGameState.deck_card_count > 0 ? 3 : 0 : 1); 
  drawDiscardPile(discardTopCard, DISCARD_X, DISCARD_Y, HAND_CARD_WIDTH, HAND_CARD_HEIGHT);
  drawButtonPlaceholders(gameButtons);
}

function mousePressed() {
  if (gameButtons && gameButtons.length > 0) {
    for (const button of gameButtons) {
      if (mouseX >= button.x && mouseX <= button.x + button.width &&
          mouseY >= button.y && mouseY <= button.y + button.height) {
        
        console.log(button.label + " button clicked!");
        // Future: Add specific actions for each button here.
        // For example:
        // if (button.label === 'Draw Card') {
        //   // Call a function to handle drawing a card
        // }
        break; // Assuming buttons don't overlap, stop after finding one.
      }
    }
  }
}

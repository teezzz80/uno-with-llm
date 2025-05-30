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

let playerHand = [
  new UnoCard('red', '1'),
  new UnoCard('green', '7'),
  new UnoCard('blue', 'drawTwo'),
  new UnoCard('yellow', '0'),
  new UnoCard('red', 'skip'),
  new UnoCard('black', 'wild')
  // Add one more for 7 cards if desired: new UnoCard('blue', '3')
];

let discardTopCard; // To hold the card on top of the discard pile
let gameButtons = [];   // To hold button objects

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
  } else {
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
    // 3. Central White Ellipse
    const ellipseWidth = cardWidth * 0.75;
    const ellipseHeight = cardHeight * 0.78; 
    push();
    translate(x + cardWidth / 2, y + cardHeight / 2);
    rotate(tiltAngle);
    fill(255, 255, 255);
    noStroke();
    ellipse(0, 0, ellipseWidth, ellipseHeight);
    pop();

    // 4. Central Symbol/Value Text
    push();
    translate(x + cardWidth / 2, y + cardHeight / 2);
    rotate(tiltAngle);
    
    let centralTextColor, centralStrokeColor;
    if (card.color === 'yellow') { 
        centralTextColor = color(0); 
        centralStrokeColor = color(255); 
    } else {
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

  // 5. Corner Symbols/Value Texts
  let cornerValue = card.value;
  if (isWild) cornerValue = 'W';
  if (isWildDrawFour) cornerValue = 'W+4';
  if (card.value === 'skip') cornerValue = 'S';
  if (card.value === 'reverse') cornerValue = 'R';
  if (card.value === 'drawTwo') cornerValue = '+2';

  const cornerTextSize = cardWidth / 7; 
  const cornerXOffset = cardWidth * 0.12; 
  const cornerYOffset = cardHeight * 0.08; 

  fill(255);
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
  for (let i = 0; i < handArray.length; i++) {
    const card = handArray[i];
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

  discardTopCard = new UnoCard('green', '4'); // Initialize discard pile with a card

  let buttonWidth = 180;
  let buttonHeight = 50; // Slightly smaller buttons
  // Buttons positioned above the hand, to the right
  let firstButtonX = width - (buttonWidth * 3 + 2 * 10) - 40 ; // Start from right edge, move left

  gameButtons = [
    { label: 'Draw Card', x: firstButtonX, y: HAND_Y_POSITION - buttonHeight - 30, width: buttonWidth, height: buttonHeight, color: color(0,150,0), textColor: color(255) },
    { label: 'UNO!', x: firstButtonX + buttonWidth + 10, y: HAND_Y_POSITION - buttonHeight - 30, width: buttonWidth, height: buttonHeight, color: color(255,223,0), textColor: color(0) }, // Yellow UNO button
    { label: 'End Turn', x: firstButtonX + 2*(buttonWidth + 10), y: HAND_Y_POSITION - buttonHeight - 30, width: buttonWidth, height: buttonHeight, color: color(200,0,0), textColor: color(255) }
  ];
}

function draw() {
  background(0, 100, 0); // Green card table background

  // Calculate starting X to center the player's hand
  // Spacing of 10 between cards in hand
  const handSpacing = 10; 
  const totalHandWidth = (playerHand.length * (HAND_CARD_WIDTH + handSpacing)) - handSpacing;
  const handStartX = (width - totalHandWidth) / 2;

  // Draw Player's Hand
  drawPlayerHand(playerHand, handStartX, HAND_Y_POSITION, HAND_CARD_WIDTH, HAND_CARD_HEIGHT, handSpacing);
  
  // Draw Deck
  drawDeck(DECK_X, DECK_Y, HAND_CARD_WIDTH, HAND_CARD_HEIGHT, 3); // Stack of 3 cards for the deck
  
  // Draw Discard Pile
  drawDiscardPile(discardTopCard, DISCARD_X, DISCARD_Y, HAND_CARD_WIDTH, HAND_CARD_HEIGHT);
  
  // Draw Buttons
  drawButtonPlaceholders(gameButtons);
}

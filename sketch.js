class UnoCard {
  constructor(color, value) {
    this.color = color;
    this.value = value;
  }
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

    // Draw four colored segments (example: slightly overlapping rectangles)
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
      // rotate(tiltAngle); // Optional tilt for +4
      fill(255); // White text for +4
      stroke(0); // Black outline
      strokeWeight(cardWidth / 60);
      textAlign(CENTER, CENTER);
      textStyle(BOLD);
      textSize(cardWidth / 3);
      text('+4', 0, 0);
      pop();
    } else { // Regular Wild
      push();
      translate(centerX, centerY);
      // rotate(tiltAngle); // Optional tilt for WILD
      fill(255);
      stroke(0);
      strokeWeight(cardWidth / 70);
      textAlign(CENTER, CENTER);
      textStyle(BOLD);
      textSize(cardWidth / 5); // Smaller "WILD" text
      text('WILD', 0, 0);
      pop();
    }
  } else {
    // 3. Central White Ellipse
    const ellipseWidth = cardWidth * 0.75;
    const ellipseHeight = cardHeight * 0.78; // Adjusted to look more like Uno cards
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
    
    // Determine text color and stroke based on card color
    let centralTextColor, centralStrokeColor;
    if (card.color === 'yellow') { // Special case for yellow cards
        centralTextColor = color(0); // Black text
        centralStrokeColor = color(255); // White outline
    } else {
        centralTextColor = cardColorValue; // Card's color for text
        centralStrokeColor = color(255); // White outline
    }

    fill(centralTextColor);
    stroke(centralStrokeColor);
    strokeWeight(cardWidth / 75); // Proportional stroke weight
    textAlign(CENTER, CENTER);
    textStyle(BOLD);

    let centralValue = card.value;
    let centralTextSize = cardWidth / 2.5; // Default for numbers

    if (card.value === 'skip') {
      centralValue = 'S'; // Using 'S' for Skip
      centralTextSize = cardWidth / 2;
    } else if (card.value === 'reverse') {
      centralValue = 'R'; // Using 'R' for Reverse
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

  const cornerTextSize = cardWidth / 7; // Adjusted for better proportion
  const cornerXOffset = cardWidth * 0.12; // Adjusted for better centering
  const cornerYOffset = cardHeight * 0.08; // Adjusted for better centering

  fill(255);
  noStroke();
  textStyle(BOLD);
  textSize(cornerTextSize);
  textAlign(CENTER, CENTER);

  // Top-Left
  text(cornerValue, x + cornerXOffset, y + cornerYOffset + (cornerTextSize / 3)); // Minor y adjustment for visual centering

  // Bottom-Right
  push();
  translate(x + cardWidth - cornerXOffset, y + cardHeight - cornerYOffset - (cornerTextSize / 3));
  rotate(180);
  text(cornerValue, 0, 0);
  pop();
}

function setup() {
  createCanvas(1200, 800);
  angleMode(DEGREES); // Use degrees for rotation
  textFont('Arial'); // Set default font
}

function draw() {
  background(0, 100, 0); // Green card table background

  // Define card properties
  let cardWidth = 150;
  let cardHeight = 225;
  let initialX = 50;
  let cardY = 100;
  let spacing = cardWidth + 30;

  // Instantiate UnoCard objects
  let blue5Card = new UnoCard('blue', '5');
  let yellowSkipCard = new UnoCard('yellow', 'skip');
  let wildCard = new UnoCard('black', 'wild');
  // let redDrawTwo = new UnoCard('red', 'drawTwo');
  // let greenReverse = new UnoCard('green', 'reverse');
  // let wildDraw4 = new UnoCard('black', 'wildDrawFour');


  // Call drawUnoCard() for each card
  drawUnoCard(blue5Card, initialX, cardY, cardWidth, cardHeight);
  drawUnoCard(yellowSkipCard, initialX + spacing, cardY, cardWidth, cardHeight);
  drawUnoCard(wildCard, initialX + 2 * spacing, cardY, cardWidth, cardHeight);
  // drawUnoCard(redDrawTwo, initialX + 3 * spacing, cardY, cardWidth, cardHeight);
  // drawUnoCard(greenReverse, initialX + 4 * spacing, cardY, cardWidth, cardHeight);
  // drawUnoCard(wildDraw4, initialX + 5 * spacing, cardY, cardWidth, cardHeight);

}

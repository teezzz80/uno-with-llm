function setup() {
  createCanvas(1200, 800);
  angleMode(DEGREES); // Use degrees for rotation
  textFont('Arial'); // Set default font
}

function draw() {
  background(0, 100, 0); // Green card table background

  // Card properties
  let cardWidth = 240;
  let cardHeight = 360;
  let cornerRadius = 20;
  let cardX = (width - cardWidth) / 2; // Center horizontally
  let cardY = 50; // Offset from top
  let cardColor = color(255, 0, 0); // Red

  // Draw card body
  fill(cardColor);
  noStroke();
  rect(cardX, cardY, cardWidth, cardHeight, cornerRadius);

  // Central white ellipse properties
  let ellipseWidth = 180;
  let ellipseHeight = 280;
  let ellipseColor = color(255, 255, 255); // White
  let tiltAngle = 15; // Angle to tilt the ellipse and central number

  // Draw tilted central white ellipse
  push();
  translate(cardX + cardWidth / 2, cardY + cardHeight / 2); // Move to card center
  rotate(tiltAngle);
  fill(ellipseColor);
  noStroke();
  ellipse(0, 0, ellipseWidth, ellipseHeight); // Draw ellipse at new (0,0)
  pop();

  // Draw large central number '7'
  push();
  translate(cardX + cardWidth / 2, cardY + cardHeight / 2); // Move to card center
  rotate(tiltAngle); // Apply the same tilt as the ellipse
  fill(255); // White fill for the number
  stroke(0); // Black stroke for outline
  strokeWeight(6); // Stroke weight for visibility
  textAlign(CENTER, CENTER);
  textStyle(BOLD);
  textSize(120);
  text('7', 0, 0); // Draw number at new (0,0), effectively centered on ellipse
  pop();

  // Small corner numbers properties
  let smallNumberSize = 30;
  let cornerOffset = 25; // How far from the edge the number's center should be

  // Draw top-left small number '7'
  fill(255); // White text
  noStroke(); // No outline for small numbers
  textStyle(BOLD);
  textSize(smallNumberSize);
  textAlign(CENTER, CENTER);
  // Adjusted position to be based on cornerOffset for the center of the text
  text('7', cardX + cornerOffset, cardY + cornerOffset + (smallNumberSize/4)); // Minor y adjustment for visual centering

  // Draw bottom-right small number '7' (rotated)
  push();
  // Translate to the point where the number should be centered
  translate(cardX + cardWidth - cornerOffset, cardY + cardHeight - cornerOffset - (smallNumberSize/4)); // Minor y adjustment
  rotate(180);
  fill(255);
  noStroke();
  textStyle(BOLD);
  textSize(smallNumberSize);
  textAlign(CENTER, CENTER);
  text('7', 0, 0); // Draw number at new (0,0)
  pop();
}

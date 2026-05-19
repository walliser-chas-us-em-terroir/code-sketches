function setup() {
  createCanvas(400, 400);
  noLoop();
}

function draw() {
  for (let y = 0; y < height; y += 50) {
    for (let x = 0; x < width; x += 50) {
      fill((x + y) / 50 % 2 == 0 ? 0 : 255);
      rect(x, y, 50, 50);
    }
  }
}
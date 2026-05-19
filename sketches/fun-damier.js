let taille = 50;
let angle = 0;

function setup() {
  createCanvas(400, 400);
  rectMode(CENTER);
}

function draw() {
  background(220);
  for (let y = 0; y < height; y += taille) {
    for (let x = 0; x < width; x += taille) {
      push();
      translate(x + taille/2, y + taille/2);
      let maxDist = dist(0, 0, width, height);
      let d = dist(x, y, 0, 0);
      let a = 0;
      if (d > maxDist * 0.6) { // seules les dernières cases tournent
        a = angle * ((d - maxDist * 0.6) / (maxDist * 0.4));
      }
      rotate(a);
      fill((x + y) / taille % 2 == 0 ? 0 : 255);
      rect(0, 0, taille, taille);
      pop();
    }
  }
  angle += 0.05;
}
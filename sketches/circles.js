function setup() {
  createCanvas(400, 400);
}

var size = 10;

function draw() {
  noFill();
  circle(200,200,size);
  size += 10;
}
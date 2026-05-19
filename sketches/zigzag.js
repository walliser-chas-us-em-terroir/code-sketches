function setup() {
  createCanvas(400, 400);
}

function draw() {
  background(220);
  
  zigzag(20, 30, 80, 120, 40);
  zigzag(320, 20, 20, 120, 1);
  zigzag(90, 310, 80, 80, 12);

}

function zigzag(x, y, l, h, e){
  //stroke(0);
  //rect(x, y, l, h);
  //stroke(255,0,0);
  strokeWeight(e);
  line(x, y, x+l, y);
  line(x, y+h/2, x+l, y)
  line(x, y+h/2, x+l, y+h/2);
  line(x, y+h, x+l, y+h/2)
  line(x, y+h, x+l, y+h)
}


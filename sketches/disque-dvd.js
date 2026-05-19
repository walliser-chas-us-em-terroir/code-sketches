let posX = 63.4;
let posY = 3.4;
let posR = posY * posY;

let size = 20;

let vitX = 4;
let vitY = 3;
let vitR = 20;


function setup() {
  frameRate(60);
  createCanvas(400, 400);
}

function draw() {
  
  //background(220);
  
  stroke(posR, 00, 255);
  fill(posR, 004, 004)
  
  posR += vitR;
  if( posR >= 255 || posR <= 0){
    vitR = vitR * -1;
  }
  
  posX += vitX;
  posY += vitY;
  
  
  if( posX >= width-size || posX <= 0) {
    vitX = vitX * -1;
  }
  
  if( posY >= height-size || posY <= 0) {
    vitY = vitY * -1;
  }
  
  circle(posX, posY, size)
  
}


function keyPressed(){
  if( key === "s"){
    save("dessin.png");
  }
}
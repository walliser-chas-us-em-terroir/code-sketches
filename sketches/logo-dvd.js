let logo;

function preload() {
  logo = loadImage('dvd.png');
}

let bouncy = {
  size: 64,
  posX: 10,
  posY: 15,
  vitX: 1.2,
  vitY: 0.9,
  name: "un chien",

  update: function(){
    this.posX = this.posX + this.vitX;
    this.posY += this.vitY;

    if(this.posX + this.size > width || this.posX < 0){
      this.vitX = this.vitX * -1;
    }

    if(this.posY + this.size > height || this.posY < 0){
      this.vitY *= -1;
    }

    noStroke();
    image(logo, this.posX, this.posY, this.size, this.size*0.67);
    text(this.name, this.posX, this.posY -4);
  }
};

function setup (){
  createCanvas(400, 400);
  logo.loadPixels();
  for (let i = 0; i < logo.pixels.length; i += 4) {
    if (logo.pixels[i] > 240 && logo.pixels[i+1] > 240 && logo.pixels[i+2] > 240) {
      logo.pixels[i+3] = 0;
    }
  }
  logo.updatePixels();
}

let chaton = Object.create(bouncy);
chaton.name = "un bon";
chaton.vitX = 1.5;

let machin = Object.create(bouncy);
machin.name = "fusilléééééé";
machin.vitY = -2;

function draw(){
  background(220);
  bouncy.update();
  chaton.update();
  machin.update();
}
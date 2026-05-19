let cols = 10;
let rows = 10;
let colors =[];


function setup() {
  
  createCanvas(300, 300);
  
  colors = make2Darray(cols, rows);
  
  for( i=0; i<cols; i++){
  for( j=0; j<rows; j++){
    colors[i][j] = random(255);
    console.log( colors[i][j] );
  }//j
}//i
  
background(51);

//dessiner
  
  for( let a=0; a<cols; a++){
    for( let b=0; b<rows; b++){
      let x = a * 30;
      let y = b * 30;
      fill( colors[a][b] );
      stroke(9);
      rect(x,y, 30, 30);
  }
}
}


//usine de papier quadrillé...
function make2Darray(cols, rows){
  var arr = new Array(cols);
  for( var i = 0; i < arr.length; i++){
    arr[i] = new Array(rows);
  }
  return arr;
}



function draw() {}



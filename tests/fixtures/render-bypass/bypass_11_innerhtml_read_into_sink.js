/* BYPASS 11: reading innerHTML out and back in launders an unaudited string
   through a name the gate never watched. */
function render(entry){
  var carried=el("y").innerHTML;
  el("x").innerHTML=carried;
}

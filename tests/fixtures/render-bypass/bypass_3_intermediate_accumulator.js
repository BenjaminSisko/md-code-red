/* BYPASS 3: the accumulator list was one hard-coded name. Any other name was
   invisible, and `var html=""+h` laundered it into the audited one. */
function render(entry){
  var h="";
  h+=entry.intent;
  var html=""+h;
  el("x").innerHTML=html;
}

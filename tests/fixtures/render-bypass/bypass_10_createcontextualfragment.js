/* BYPASS 10: the same parse, one API further away. */
function render(entry){
  var frag=document.createRange().createContextualFragment("<p>"+entry.intent+"</p>");
  el("x").appendChild(frag);
}

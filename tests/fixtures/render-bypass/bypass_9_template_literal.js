/* BYPASS 9: a template literal interpolates, which is the whole point of the
   gate; it must never count as "a literal". */
function render(entry){
  el("x").innerHTML=`<p>${entry.intent}</p>`;
}

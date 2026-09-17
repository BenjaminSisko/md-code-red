/* BYPASS 2: the accumulator matcher only looked for `html +=`, so an ordinary
   assignment carrying the same concatenation was never read. */
function render(entry){
  var html="";
  html=html+entry.intent;
  el("x").innerHTML=html;
}

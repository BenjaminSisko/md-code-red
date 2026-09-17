/* SAFE. The shape the whole product renders through: a literal-or-esc()
   accumulator assigned into one innerHTML sink. This fixture runs FIRST — a
   checker that has never been seen to PASS on healthy code is as useless as one
   that has never been seen to fail. */
function render(entry){
  var html="";
  html+="<h2>"+esc(entry.intent)+"</h2>";
  html+="<p class=\""+escapeAttr(entry.tool)+"\">"+esc(entry.notes||"")+"</p>";
  el("x").innerHTML=html;
}

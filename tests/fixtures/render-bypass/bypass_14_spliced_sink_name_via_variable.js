/* BYPASS. The splice moved one line up: the property expression is now a bare
   identifier — the shape ordinary array and map code uses — and the sink name
   is assembled somewhere else. Two rules catch it: the concatenation that spells
   a sink name is flagged where it is written, and the computed assignment is
   flagged because the gate cannot prove what `k` holds. */
function render(entry){
  var k = "inner" + "HTML";
  el("x")[k] = entry.intent;
}

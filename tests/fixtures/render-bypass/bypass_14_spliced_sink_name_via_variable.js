/* BYPASS. The splice moved one line up: the property expression is now a bare
   identifier — the shape ordinary array and map code uses, which the gate must
   keep allowing — and the sink name is assembled somewhere else. Caught where
   the splice is WRITTEN rather than where it is used, by two rules that meet
   here: the assignments to `k` are followed and their literal pieces fused, and
   the concatenation that spells a sink name is refused on its own line. */
function render(entry){
  var k = "inner" + "HTML";
  el("x")[k] = entry.intent;
}

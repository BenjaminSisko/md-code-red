/* BYPASS. The splice spread over two statements, so no single expression ever
   contains both halves of the name. The fusion rule that catches bypass_14
   reads one concatenation at a time and sees only "inner" and "HTML" apart.
   Caught instead by following the assignments to the identifier used as the
   property — the same derivation the accumulator rule already does, pointed at
   a property name rather than at a value. */
function render(entry){
  var k = "inner";
  k += "HTML";
  el("x")[k] = entry.intent;
}

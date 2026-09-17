/* BYPASS. Marcus Reed's MCR-SEC-014 reproduction, verbatim in shape: the sink
   name never appears as a literal, so no regex over the source can see it. The
   answer is not to search harder for the name — it is to refuse a computed
   property assignment whose property expression the gate cannot read. */
function render(entry){
  el("x")["inner"+"HTML"] = entry.intent;
}

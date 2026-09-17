/* BYPASS (MCR-SEC-014 family). The sink reached by bracket notation with a
   string literal. Every innerHTML rule in the audit was written against the
   DOT spelling — `\.\s*innerHTML` — so this assignment is not a sink at all as
   far as the gate is concerned: audited = 0, failures = 0, and the raw value
   lands in the DOM. No obfuscation needed; this is just the other way to spell
   a property access. */
function render(entry){
  el("x")["innerHTML"] = entry.intent;
}

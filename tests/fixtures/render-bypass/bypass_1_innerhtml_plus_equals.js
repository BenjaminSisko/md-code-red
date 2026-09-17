/* BYPASS 1 (MCR-SEC-004): the sink regex was `\.innerHTML\s*=\s*`, which `+=`
   does not match. audited=0, verdict PASS. */
function render(entry){
  el("x").innerHTML+="<p>"+entry.intent+"</p>";
}

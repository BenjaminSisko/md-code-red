/* BYPASS 5: outerHTML is the same sink under another name. */
function render(entry){
  el("x").outerHTML="<p>"+entry.intent+"</p>";
}

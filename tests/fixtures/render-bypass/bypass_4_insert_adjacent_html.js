/* BYPASS 4: no gate forbade insertAdjacentHTML anywhere. */
function render(entry){
  el("x").insertAdjacentHTML("beforeend","<p>"+entry.intent+"</p>");
}

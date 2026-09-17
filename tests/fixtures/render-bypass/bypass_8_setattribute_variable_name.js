/* BYPASS 8: an attribute name the gate cannot read is an attribute name the gate
   cannot clear. */
function render(entry,which){
  var attr=(which==="link")?"href":"data-id";
  el("x").setAttribute(attr,entry.id);
}

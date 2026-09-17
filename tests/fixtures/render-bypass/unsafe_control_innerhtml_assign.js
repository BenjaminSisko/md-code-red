/* UNSAFE — Marcus's control case. The gate fired on this one before the fix too;
   it is here so the fixture set contains the case that always worked. */
function render(entry){
  el("x").innerHTML="<p>"+entry.intent+"</p>";
}

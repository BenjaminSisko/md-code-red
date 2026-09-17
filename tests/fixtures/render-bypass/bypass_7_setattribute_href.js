/* BYPASS 7: setAttribute() can turn a content string into a javascript: URL
   without ever touching innerHTML. */
function render(entry){
  var a=el("x");
  a.setAttribute("href",entry.source.url_or_man);
}

/* SAFE. The legitimate computed assignments this product actually writes —
   `out[fields[i].name] = ...` in fieldTypeMap(), `out.resolved[f.name] = ...`
   in validateSpec() — plus an array index and a numeric one. A rule against
   computed member assignment that flagged these would be a rule nobody could
   keep, so the gate reads the property expression instead of banning the form:
   an identifier, a number, or a dotted/indexed chain with no string literal and
   no concatenation in it cannot be spelling a sink name in the source. */
function collect(fields, values){
  var out = {}, seen = [], i;
  for(i = 0; i < fields.length; i++){
    out[fields[i].name] = fields[i].type;
    seen[i] = fields[i].name;
  }
  out.resolved = {};
  out.resolved[fields[0].name] = values[fields[0].name];
  seen[seen.length] = "done";
  return out;
}

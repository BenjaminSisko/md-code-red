#!/usr/bin/env node
/* shift_crosscheck_driver.js — drive the SHIPPED assembler over a batch of
 * template shapes and report, for each run, only whether a command came out.
 *
 * MCR-SEC-018 / MCR-SEC-013, condition E3. tests/test_positional_crosscheck.py
 * owns the question ("which of these runs MUST return null?") and this file
 * owns nothing but the answer. The split is deliberate: the expectation is
 * computed in Python from extract/schema.py's own presence model, and the
 * assembler is lifted here through tests/hostile_harness.js's purity-checked
 * extractor, so neither side can quietly restate the other's rule.
 *
 * stdin:  {"fields": [...], "shapes": [[tok,...],...], "versions": ["7",...],
 *          "combos": [{...values},...], "detail": false}
 * stdout: {"results": [0|1, ...]}  — or, with "detail": true, the command
 *         string (or null) per run, for building a failure message.
 *
 * Run order is shapes -> versions -> combos, and Python rebuilds the same
 * index, so the two sides agree on which run a result belongs to.
 */

var fs = require("fs");
var path = require("path");
var harness = require(path.join(__dirname, "hostile_harness.js"));

function main() {
  var job = JSON.parse(fs.readFileSync(0, "utf8"));
  var A = harness.extractAssembler(path.join(__dirname, "..", "template.html")).api;
  var results = [];
  for (var s = 0; s < job.shapes.length; s++) {
    for (var v = 0; v < job.versions.length; v++) {
      for (var c = 0; c < job.combos.length; c++) {
        var spec = { id: "crosscheck-" + s, tool: "crosscheck", blast: "green",
                     fields: job.fields, template: job.shapes[s] };
        var res = null;
        try {
          res = A.assembleCommand(spec, job.versions[v], job.combos[c], { patterns: [] });
        } catch (e) {
          results.push(job.detail ? ("THREW: " + e.message) : 2);
          continue;
        }
        if (job.detail) results.push(res === null ? null : res.command);
        else results.push(res === null ? 0 : 1);
      }
    }
  }
  process.stdout.write(JSON.stringify({ results: results }));
}

main();

#!/usr/bin/env node
/* test_search_index.js — CR-T-29. Times buildIndex()/queryIndex() against the
 * FULL embedded dataset of the shipped artifact.
 *
 *   node tests/test_search_index.js [path/to/template.html|dist/md-code-red_*.html] [--json]
 *
 * Lifts the MCR-INDEX block verbatim out of the given file, the same way
 * tests/hostile_harness.js lifts MCR-ASSEMBLER — so the code this test times
 * is the code that ships, not a re-implementation. The dataset it runs
 * against is the real data island of the target file (dist/ when a build
 * exists, template.html's placeholder otherwise), not a synthetic fixture:
 * "<100ms on the full dataset" is a claim about THIS build's real 1,492 STIG
 * rules, 200 CCI mappings and 44 flag dictionaries, not a small fixture.
 */
"use strict";

var fs = require("fs");
var path = require("path");

var REPO = path.resolve(__dirname, "..");
var BEGIN = "MCR-INDEX-BEGIN";
var END = "MCR-INDEX-END";

function extractBlock(file, begin, end) {
  var src = fs.readFileSync(file, "utf8");
  var a = src.indexOf(begin);
  if (a < 0) throw new Error("no " + begin + " marker in " + file);
  var from = src.indexOf("*/", a);
  if (from < 0) throw new Error("the " + begin + " comment is unterminated in " + file);
  from += 2;
  var b = src.indexOf(end, from);
  if (b < 0) throw new Error("no " + end + " marker after " + begin + " in " + file);
  var to = src.lastIndexOf("/*", b);
  if (to < from) throw new Error("malformed " + begin + "/" + end + " markers in " + file);
  return src.slice(from, to);
}

function loadDatasets(file) {
  var src = fs.readFileSync(file, "utf8");
  var m = src.match(/<script id="mcr-data" type="application\/json">([\s\S]*?)<\/script>/);
  if (!m) throw new Error("no mcr-data island in " + file + " — run python3 build.py first");
  var data = JSON.parse(m[1]);
  return {
    TOOLS: data.tools, COMMANDS: data.commands, RULES: data.rules,
    FLAGS: data.flags, CCI_NIST: data.cci_nist
  };
}

function main() {
  var args = process.argv.slice(2);
  var asJson = args.indexOf("--json") >= 0;
  var target = args.filter(function (a) { return a !== "--json"; })[0];
  if (!target) {
    var distDir = path.join(REPO, "dist");
    var cands = fs.existsSync(distDir)
      ? fs.readdirSync(distDir).filter(function (f) {
          return f.indexOf("md-code-red_") === 0 && f.slice(-5) === ".html";
        }).sort()
      : [];
    target = cands.length ? path.join(distDir, cands[cands.length - 1]) : path.join(REPO, "template.html");
  }

  var block = extractBlock(target, BEGIN, END);
  var factory = new Function("\"use strict\";\n" + block + "\nreturn {buildIndex:buildIndex,queryIndex:queryIndex};");
  var mod = factory();

  var datasets = loadDatasets(target);

  var t0 = process.hrtime.bigint();
  var index = mod.buildIndex(datasets);
  var t1 = process.hrtime.bigint();
  var buildMs = Number(t1 - t0) / 1e6;

  var queries = ["ssh", "AC-6", "CCI-000366", "RHEL-08-010000", "firewall", "zone", "audit"];
  var queryMs = [];
  var i, results = [];
  for (i = 0; i < queries.length; i++) {
    var q0 = process.hrtime.bigint();
    var r = mod.queryIndex(index, queries[i]);
    var q1 = process.hrtime.bigint();
    var ms = Number(q1 - q0) / 1e6;
    queryMs.push(ms);
    results.push({ query: queries[i], total: r.total, groups: r.groups.length, ms: ms });
  }
  var worstQuery = Math.max.apply(null, queryMs);

  var failures = [];
  if (!index.length) failures.push("buildIndex() produced an empty index over a non-empty dataset");
  if (buildMs >= 100) failures.push("buildIndex() took " + buildMs.toFixed(2) + "ms, over the 100ms budget");
  if (worstQuery >= 100) failures.push("slowest queryIndex() call took " + worstQuery.toFixed(2) + "ms, over the 100ms budget");
  // a no-match state must be explicit (empty groups, not an exception or a false hit)
  var noMatch = mod.queryIndex(index, "zzzzz_no_such_thing_zzzzz");
  if (noMatch.groups.length !== 0 || noMatch.total !== 0) {
    failures.push("a query with no possible match returned a non-empty result instead of the explicit no-match state");
  }

  var report = {
    target: path.relative(REPO, target),
    index_size: index.length,
    build_ms: buildMs,
    query_results: results,
    worst_query_ms: worstQuery,
    no_match_explicit: (noMatch.groups.length === 0 && noMatch.total === 0),
    failures: failures
  };

  if (asJson) {
    process.stdout.write(JSON.stringify(report) + "\n");
  } else {
    console.log("CR-T-29 search index timing — " + report.target);
    console.log("  index size: " + report.index_size + " records");
    console.log("  buildIndex(): " + buildMs.toFixed(3) + "ms (budget: <100ms)");
    results.forEach(function (r) {
      console.log("  query " + JSON.stringify(r.query) + ": " + r.ms.toFixed(3) +
                  "ms, " + r.total + " hit(s) in " + r.groups + " group(s)");
    });
    console.log("  worst query: " + worstQuery.toFixed(3) + "ms");
    console.log("  no-match state explicit: " + report.no_match_explicit);
    if (failures.length) {
      console.log("FAIL:");
      failures.forEach(function (f) { console.log("  - " + f); });
    } else {
      console.log("PASS");
    }
  }
  process.exit(failures.length ? 1 : 0);
}

main();

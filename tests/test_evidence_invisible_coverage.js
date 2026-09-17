#!/usr/bin/env node
/* test_evidence_invisible_coverage.js — H2 (Marcus Reed). Every codepoint
 * INVISIBLE_RE (MCR-ASSEMBLER, the same gate MCR-SEC-004 applies to curated
 * FIELD VALUES) rejects must also be neutralised by the evidence exporter's
 * own line-safety treatment (evidenceHeaderSafe()/evidenceLineSafe(),
 * MCR-EVIDENCE) — ONE shared range table, not two hand-maintained copies
 * that can silently drift apart. H2's own finding: the evidence safener's
 * first cut (G2) was a SEPARATE, hand-rolled numeric range table that
 * already missed U+061C (Arabic Letter Mark), U+00AD (soft hyphen),
 * U+206A-U+206F (deprecated text-direction/digit-shaping controls — it only
 * went to U+2069), and U+FE0F (a variation selector — it covered none of
 * U+FE00-U+FE0F).
 *
 * Rather than hand-copy INVISIBLE_RE's codepoint list into this test (the
 * same mistake that produced the drift in the first place), this LIFTS
 * INVISIBLE_RE itself out of the built file — the ACTUAL regex object the
 * shipped MCR-ASSEMBLER uses — and enumerates every BMP codepoint
 * (U+0000-U+FFFF, surrogates excluded) against it. Whatever INVISIBLE_RE
 * rejects TODAY is what this test demands the evidence safener neutralise
 * TODAY: the two range tables cannot silently diverge again without this
 * test failing, because there is exactly one definition of "rejected",
 * read fresh from the shipped file every run, never retyped here.
 *
 *   node tests/test_evidence_invisible_coverage.js [path/to/template.html|dist/md-code-red_*.html] [--json]
 */
"use strict";

var fs = require("fs");
var path = require("path");

var REPO = path.resolve(__dirname, "..");

function extractBlock(src, begin, end, file) {
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

function main() {
  var args = process.argv.slice(2);
  var asJson = args.indexOf("--json") >= 0;
  var target = args.filter(function (a) { return a !== "--json"; })[0] || path.join(REPO, "template.html");
  var src = fs.readFileSync(target, "utf8");

  var assembler = extractBlock(src, "MCR-ASSEMBLER-BEGIN", "MCR-ASSEMBLER-END", target);
  var evidence = extractBlock(src, "MCR-EVIDENCE-BEGIN", "MCR-EVIDENCE-END", target);

  var factory = new Function(
    "\"use strict\";\n" + assembler + "\n" + evidence + "\n" +
    "return {INVISIBLE_RE:INVISIBLE_RE, evidenceLineSafe:evidenceLineSafe};"
  );
  var mod = factory();
  var INVISIBLE_RE = mod.INVISIBLE_RE;
  var evidenceLineSafe = mod.evidenceLineSafe;

  var failures = [];
  var rejectedCount = 0;
  for (var code = 0x0000; code <= 0xFFFF; code++) {
    if (code >= 0xD800 && code <= 0xDFFF) continue; // lone surrogate — not a real character
    var ch = String.fromCharCode(code);
    if (!INVISIBLE_RE.test(ch)) continue;
    INVISIBLE_RE.lastIndex = 0; // INVISIBLE_RE has no /g flag, but be defensive
    rejectedCount++;
    var out = evidenceLineSafe("before" + ch + "after");
    if (out.indexOf(ch) >= 0) {
      failures.push("U+" + code.toString(16).toUpperCase().padStart(4, "0") +
                    " is rejected by INVISIBLE_RE but survives evidenceLineSafe()");
    }
  }

  if (rejectedCount === 0) {
    failures.push("INVISIBLE_RE rejected nothing in the whole BMP — the regex is broken or empty, " +
                  "and this test proved nothing");
  }

  var report = { target: path.relative(REPO, target), rejected_count: rejectedCount, failures: failures };
  if (asJson) {
    process.stdout.write(JSON.stringify(report) + "\n");
  } else {
    console.log("H2 evidence-safener / INVISIBLE_RE coverage — " + report.target);
    console.log("INVISIBLE_RE rejects " + rejectedCount + " BMP codepoint(s)");
    if (failures.length) {
      console.log("FAIL (" + failures.length + "):");
      failures.forEach(function (f) { console.log("  - " + f); });
    } else {
      console.log("PASS: evidenceLineSafe() neutralises every one of them");
    }
  }
  process.exit(failures.length ? 1 : 0);
}

main();

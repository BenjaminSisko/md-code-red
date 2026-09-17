#!/usr/bin/env node
/* test_evidence_export.js — CR-T-28. Determinism of the plain-text evidence
 * exporter.
 *
 *   node tests/test_evidence_export.js [path/to/template.html|dist/md-code-red_*.html] [--json]
 *
 * Lifts the MCR-EVIDENCE block (formatEvidenceText(), pure — see the block's
 * own header comment in template.html) out of the given file, the same way
 * tests/hostile_harness.js lifts MCR-ASSEMBLER. Calls it twice with the same
 * fixture input except the operator date, and asserts the two outputs are
 * byte-identical once the one line that is allowed to differ (the operator
 * date line) is stripped — the property threat-model-v1 §8 requires ("read
 * from the same rendered-state object as the screen, never recomputed").
 * Also checks the "not captured" honesty path (no `res`, no capture record)
 * never fabricates a value.
 */
"use strict";

var fs = require("fs");
var path = require("path");
var assert = require("assert");

var REPO = path.resolve(__dirname, "..");
var BEGIN = "MCR-EVIDENCE-BEGIN";
var END = "MCR-EVIDENCE-END";

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
  /* The formatter must stay pure — the whole reason it can be tested this
     way and the whole reason threat-model-v1 §8 can be believed. */
  var banned = ["document", "window.", "localStorage", "sessionStorage", "DATASETS", "STATE.", "innerHTML"];
  for (var i = 0; i < banned.length; i++) {
    if (block.indexOf(banned[i]) >= 0) {
      throw new Error("MCR-EVIDENCE block references '" + banned[i] +
                      "' — it must stay pure or this test proves nothing about determinism");
    }
  }
  return block;
}

function loadFormatter(file) {
  var block = extractBlock(file, BEGIN, END);
  var factory = new Function("\"use strict\";\n" + block + "\nreturn {formatEvidenceText:formatEvidenceText};");
  return factory().formatEvidenceText;
}

function fixtureOpts(operatorDate) {
  return {
    res: {
      version: "8", blast: "green", command: "systemctl is-active firewalld",
      flags: [{ flag: "is-active", explain: null }]
    },
    entry: { intent: "check firewalld", tool: "firewall-cmd",
             source: { title: "man firewall-cmd(1)", url_or_man: "firewall-cmd(1)", version: "0.9.3", retrieved_on: "2026-09-01" } },
    stigRow: { stig_id: "RHEL-08-040030", rhel_version: "8", cci: ["CCI-000366"], nist: ["CM-6 b"] },
    rule: { i: "RHEL-08-040030", t: "The SSH daemon must not allow authentication using RSA rules.",
            c: "II", cci: ["CCI-000366"], n: ["CM-6 b"],
            chk: "Verify the firewall is active.\n\n$ sudo systemctl is-active firewalld",
            fix: "Enable firewalld: # systemctl enable --now firewalld" },
    appVersion: "v1.0.0-dev", appBuildDate: "2026-09-17",
    contentFingerprint: "deadbeef".repeat(8),
    stigVersion: "V2R8", benchmarkDate: "01 Jul 2026",
    source: { title: "man firewall-cmd(1)", url_or_man: "firewall-cmd(1)", version: "0.9.3", retrieved_on: "2026-09-01" },
    operatorDate: operatorDate
  };
}

function stripOperatorDateLine(text) {
  return text.split("\n").filter(function (line) {
    return line.indexOf("Operator date:") !== 0;
  }).join("\n");
}

function main() {
  var args = process.argv.slice(2);
  var asJson = args.indexOf("--json") >= 0;
  var target = args.filter(function (a) { return a !== "--json"; })[0] || path.join(REPO, "template.html");

  var formatEvidenceText = loadFormatter(target);
  var failures = [];

  var textA = formatEvidenceText(fixtureOpts("2026-09-17"));
  var textB = formatEvidenceText(fixtureOpts("2026-10-25"));

  try {
    assert.strictEqual(stripOperatorDateLine(textA), stripOperatorDateLine(textB),
      "two exports of the same entry, only the operator date line differing, must be byte-identical");
  } catch (e) { failures.push(e.message); }

  try {
    assert.notStrictEqual(textA, textB, "the operator date line itself must actually differ between calls");
  } catch (e) { failures.push(e.message); }

  // required fields present, verbatim from the input, never recomputed
  [
    ["STIG ID: RHEL-08-040030", "STIG ID"],
    ["CAT: II", "CAT"],
    ["CCI: CCI-000366", "CCI"],
    ["NIST SP 800-53 controls: CM-6 b", "NIST controls"],
    ["Assembled command (RHEL 8, blast green):", "assembled-command header"],
    ["systemctl is-active firewalld", "the assembled command itself"],
    ["Content fingerprint (sha256 of the embedded data island): " + "deadbeef".repeat(8), "content fingerprint"],
    ["STIG version: V2R8  benchmark date: 01 Jul 2026", "STIG version/benchmark date"]
  ].forEach(function (pair) {
    if (textA.indexOf(pair[0]) < 0) failures.push("evidence text is missing required line for " + pair[1] + ": " + pair[0]);
  });

  // the honest "not captured" path — no capture record on the STIG row
  var noCapText = formatEvidenceText(fixtureOpts("2026-09-17"));
  if (noCapText.indexOf("Expected output: not captured yet") < 0) {
    failures.push("no expected_output on the stig row must render the honest 'not captured' line, not a fabricated value");
  }

  // res:null must render an honest line, never a silently-blank or guessed command
  var noResOpts = fixtureOpts("2026-09-17");
  noResOpts.res = null;
  var noResText = formatEvidenceText(noResOpts);
  if (noResText.indexOf("Assembled command: not available") < 0) {
    failures.push("a null res must render 'Assembled command: not available', never guess or omit the field silently");
  }

  var report = { target: path.relative(REPO, target), byte_identical_except_date: failures.length === 0, failures: failures };
  if (asJson) {
    process.stdout.write(JSON.stringify(report) + "\n");
  } else {
    console.log("CR-T-28 evidence export determinism — " + report.target);
    if (failures.length) {
      console.log("FAIL:");
      failures.forEach(function (f) { console.log("  - " + f); });
    } else {
      console.log("PASS: two exports of the same entry are byte-identical except the operator date line");
    }
  }
  process.exit(failures.length ? 1 : 0);
}

main();

#!/usr/bin/env node
/* test_evidence_export.js — CR-T-28. Determinism of the plain-text evidence
 * exporter.
 *
 *   node tests/test_evidence_export.js [path/to/template.html|dist/md-code-red_*.html] [--json]
 *
 * Lifts MCR-ASSEMBLER and MCR-EVIDENCE (formatEvidenceText(), pure — see the
 * block's own header comment in template.html) out of the given file
 * together, the same way tests/test_evidence_export_real.js and
 * tests/test_evidence_invisible_coverage.js already do. Both blocks, not
 * MCR-EVIDENCE alone, since H2 (Marcus Reed) made evidenceHeaderSafe() share
 * MCR-ASSEMBLER's own INVISIBLE_RE_G/HEADER_UNSAFE_G range tables rather than
 * keep a second hand-rolled copy that could drift — MCR-EVIDENCE is no
 * longer self-sufficient in isolation, on purpose (see the shared-table
 * comment at MCR-EVIDENCE-BEGIN in template.html for why that trade was
 * made). Calls it twice with the same fixture input except the operator
 * date, and asserts the two outputs are byte-identical once the one line
 * that is allowed to differ (the operator date line) is stripped — the
 * property threat-model-v1 §8 requires ("read from the same rendered-state
 * object as the screen, never recomputed"). Also checks the "not captured"
 * honesty path (no `res`, no capture record) never fabricates a value.
 */
"use strict";

var fs = require("fs");
var path = require("path");
var assert = require("assert");

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

function loadFormatter(file) {
  var src = fs.readFileSync(file, "utf8");
  var assembler = extractBlock(src, "MCR-ASSEMBLER-BEGIN", "MCR-ASSEMBLER-END", file);
  var evidence = extractBlock(src, "MCR-EVIDENCE-BEGIN", "MCR-EVIDENCE-END", file);
  var block = assembler + "\n" + evidence;
  /* The formatter must stay pure — the whole reason it can be tested this
     way and the whole reason threat-model-v1 §8 can be believed. Checked
     over BOTH blocks together: MCR-ASSEMBLER is documented PURE too
     (tests/hostile_harness.js's own purity check), so this is a stronger
     statement than checking MCR-EVIDENCE alone ever was. */
  var banned = ["document", "window.", "localStorage", "sessionStorage", "DATASETS", "STATE.", "innerHTML"];
  for (var i = 0; i < banned.length; i++) {
    if (block.indexOf(banned[i]) >= 0) {
      throw new Error("MCR-ASSEMBLER/MCR-EVIDENCE reference '" + banned[i] +
                      "' — both must stay pure or this test proves nothing about determinism");
    }
  }
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
    ["Content fingerprint (sha256 of every embedded data island): " + "deadbeef".repeat(8), "content fingerprint"],
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

  // G2 (Marcus Reed Panels review, PANEL-002): a hostile rule title/check text must
  // not carry a bidi override or a raw NUL into the evidence export — the block's
  // <pre> preview and the copied string are the same string (STATE._evidenceText),
  // and this text crosses trust boundary 5 into an SCTM/ATO package. esc() only
  // neutralises HTML metacharacters; it was never a sanitiser and stays out of this
  // fix. formatEvidenceText() is plain TEXT, not markup, so '<', '"' and '\'' must
  // still come through as literal characters — only invisible/reordering/NUL bytes
  // are the ones this line-safety treatment refuses to carry.
  var hostileOpts = fixtureOpts("2026-09-17");
  hostileOpts.rule = {
    i: "RHEL-08-040030",
    t: "The SSH daemon must not allow authentication using RSA rules\u202E \u200E(reversed?)",
    c: "II", cci: ["CCI-000366"], n: ["CM-6 b"],
    chk: "Verify the firewall is active.\n\n$ sudo systemctl is-active firewalld\u0000\n\nactive",
    fix: "Enable firewalld: # systemctl enable --now firewalld \u2014 note the <unit> \"firewalld.service\" and don't forget it's a one-shot"
  };
  var hostileText = formatEvidenceText(hostileOpts);
  if (hostileText.indexOf("\u202E") >= 0) {
    failures.push("U+202E RIGHT-TO-LEFT OVERRIDE survived from the rule title into the evidence export");
  }
  if (hostileText.indexOf("\u200E") >= 0) {
    failures.push("U+200E LEFT-TO-RIGHT MARK survived from the rule title into the evidence export");
  }
  if (hostileText.indexOf("\u0000") >= 0) {
    failures.push("a raw NUL survived from the check text into the evidence export");
  }
  ["<", "\"", "'"].forEach(function (ch) {
    if (hostileText.indexOf(ch) < 0) {
      failures.push("literal '" + ch + "' did not survive into the evidence export — this is plain " +
                    "text, not HTML, and must not be escaped or stripped");
    }
  });
  if (hostileText.indexOf("<unit> \"firewalld.service\"") < 0) {
    failures.push("the fix text's literal angle-bracket/quote content did not survive verbatim " +
                  "into the evidence export");
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

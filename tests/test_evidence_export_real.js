#!/usr/bin/env node
/* test_evidence_export_real.js — G3 (Marcus Reed's Panels review, "Ruling on
 * the reported citation oddity"). A CR-T-28 report circulated a sample export
 * citing "man firewall-cmd(1) ... retrieved 2026-09-01" for
 * firewalld-service-active. That line does not exist at any revision of this
 * repository: content/commands.json's real `source` for that entry has always
 * been the DISA STIG pin, retrieved_on 2026-09-17. The string traces to
 * tests/test_evidence_export.js's OWN hand-written determinism fixture
 * (fixtureOpts()) -- a synthetic illustration built to test that two calls
 * are byte-identical, never meant to represent real content -- which the
 * report pasted as if it were a real run. The Delivery Contract says
 * artefacts, not claims: a report sample must be produced by the shipped
 * code from committed content.
 *
 * This test is the artefact. It builds the REAL RESULT for
 * firewalld-service-active on RHEL 9 the same way the running app does --
 * entryById() + assembleCommand() + withCopyPayloads() (MCR-ASSEMBLER, lifted
 * verbatim, the same way tests/hostile_harness.js lifts it) over the REAL
 * data island of the given built file, then formats it with the REAL,
 * unmodified formatEvidenceText() (MCR-EVIDENCE, lifted verbatim) -- and
 * snapshots the result against tests/fixtures/evidence/firewalld-service-
 * active.rhel9.txt, which was captured this same way. The one line allowed to
 * differ is "Operator date:", exactly like tests/test_evidence_export.js's
 * own determinism check, because it is computed from the real clock the same
 * way currentResult()'s caller (renderEvidenceModal()) computes it today.
 *
 *   node tests/test_evidence_export_real.js [path/to/template.html|dist/md-code-red_*.html] [--json]
 */
"use strict";

var fs = require("fs");
var path = require("path");

var REPO = path.resolve(__dirname, "..");
var FIXTURE = path.join(REPO, "tests", "fixtures", "evidence", "firewalld-service-active.rhel9.txt");
var ENTRY_ID = "firewalld-service-active";
var VERSION = "9";

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

function extractFn(src, name, file) {
  var re = new RegExp("function " + name + "\\([^)]*\\)\\{");
  var m = re.exec(src);
  if (!m) throw new Error("no function " + name + " found in " + file);
  var i = src.indexOf("{", m.index), depth = 0, end = -1;
  for (; i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}") { depth--; if (depth === 0) { end = i + 1; break; } }
  }
  if (end < 0) throw new Error("could not balance braces for " + name + " in " + file);
  return src.slice(m.index, end);
}

function stripOperatorDateLine(text) {
  return text.split("\n").filter(function (line) {
    return line.indexOf("Operator date:") !== 0;
  }).join("\n");
}

function buildRealExport(file) {
  var src = fs.readFileSync(file, "utf8");

  var assembler = extractBlock(src, "MCR-ASSEMBLER-BEGIN", "MCR-ASSEMBLER-END", file);
  var evidence = extractBlock(src, "MCR-EVIDENCE-BEGIN", "MCR-EVIDENCE-END", file);
  var lookups = [
    extractFn(src, "entryById", file),
    extractFn(src, "stigRowsFor", file),
    extractFn(src, "catFor", file),
    extractFn(src, "ruleFor", file),
    extractFn(src, "nistForCci", file),
    extractFn(src, "commentHeaderLines", file),
    extractFn(src, "withCopyPayloads", file)
  ].join("\n");

  var dm = /<script id="mcr-data" type="application\/json">([\s\S]*?)<\/script>/.exec(src);
  if (!dm) throw new Error("no mcr-data island found in " + file + " -- run python3 build.py first");
  var DATA = JSON.parse(dm[1]);
  var DATASETS = {
    META: DATA.meta, COMMANDS: DATA.commands, TOOLS: DATA.tools, DANGEROUS: DATA.dangerous,
    GLOSSARY: DATA.glossary, RULES: DATA.rules, FLAGS: DATA.flags, CCI_NIST: DATA.cci_nist,
    EXPECTED: DATA.expected_output, INDEX_SEED: DATA.index_seed
  };
  var PATTERNS = (DATA.dangerous && DATA.dangerous.patterns) || [];
  var STATE = { version: VERSION };

  var appVersionM = /var APP_VERSION="([^"]*)"/.exec(src);
  var appBuildDateM = /var APP_BUILD_DATE="([^"]*)"/.exec(src);
  var appNameM = /var APP_NAME="([^"]*)"/.exec(src);
  var fingerprintM = /var CONTENT_FINGERPRINT="([^"]*)"/.exec(src);

  var factory = new Function(
    "DATASETS", "STATE", "PATTERNS", "APP_NAME", "APP_VERSION",
    "\"use strict\";\n" + assembler + "\n" + lookups + "\n" + evidence + "\n" +
    "return {assembleCommand:assembleCommand, withCopyPayloads:withCopyPayloads,\n" +
    "  entryById:entryById, stigRowsFor:stigRowsFor, ruleFor:ruleFor, formatEvidenceText:formatEvidenceText};"
  );
  var mod = factory(DATASETS, STATE, PATTERNS,
                    appNameM ? appNameM[1] : "MD CODE RED", appVersionM ? appVersionM[1] : "");

  var entry = mod.entryById(ENTRY_ID);
  if (!entry) throw new Error(ENTRY_ID + " not found in the real content/commands.json island");

  var res = mod.assembleCommand(entry, VERSION, {}, { patterns: PATTERNS });
  if (!res) throw new Error("assembleCommand returned null for " + ENTRY_ID + " on RHEL " + VERSION);
  res = mod.withCopyPayloads(res, entry);

  var rows = mod.stigRowsFor(entry);
  var stigRow = rows.length ? rows[0] : null;
  var rule = stigRow ? mod.ruleFor(stigRow.stig_id, VERSION) : null;
  var stigMeta = ((DATASETS.RULES || {})[VERSION] || {})._meta || {};

  var today = new Date();
  var mm = String(today.getMonth() + 1); if (mm.length < 2) mm = "0" + mm;
  var dd = String(today.getDate()); if (dd.length < 2) dd = "0" + dd;
  var operatorDate = today.getFullYear() + "-" + mm + "-" + dd;

  return mod.formatEvidenceText({
    res: res, entry: entry, stigRow: stigRow, rule: rule,
    appVersion: appVersionM ? appVersionM[1] : "",
    appBuildDate: appBuildDateM ? appBuildDateM[1] : "",
    contentFingerprint: fingerprintM ? fingerprintM[1] : "",
    stigVersion: stigMeta.version || "", benchmarkDate: stigMeta.benchmark_date || "",
    source: (entry && entry.source) || null,
    operatorDate: operatorDate
  });
}

function main() {
  var args = process.argv.slice(2);
  var asJson = args.indexOf("--json") >= 0;
  var target = args.filter(function (a) { return a !== "--json"; })[0];
  if (!target) {
    /* Same resolution as tests/test_search_index.js: this test needs the REAL
       data island, which only a build produces, so it prefers dist/ and falls
       back to template.html (where it will fail honestly with "no mcr-data
       island found" rather than testing a placeholder). */
    var distDir = path.join(REPO, "dist");
    var cands = fs.existsSync(distDir)
      ? fs.readdirSync(distDir).filter(function (f) {
          return f.indexOf("md-code-red_") === 0 && f.slice(-5) === ".html";
        }).sort()
      : [];
    target = cands.length ? path.join(distDir, cands[cands.length - 1]) : path.join(REPO, "template.html");
  }

  var failures = [];
  var actual = null;
  try {
    actual = buildRealExport(target);
  } catch (e) {
    failures.push("could not build the real export: " + e.message);
  }

  var expected = null;
  if (!fs.existsSync(FIXTURE)) {
    failures.push("no snapshot fixture at " + path.relative(REPO, FIXTURE) +
                  " -- this test proves nothing without one");
  } else {
    expected = fs.readFileSync(FIXTURE, "utf8").replace(/\n$/, "");
  }

  if (actual !== null && expected !== null) {
    var a = stripOperatorDateLine(actual), b = stripOperatorDateLine(expected);
    if (a !== b) {
      failures.push("the real export for " + ENTRY_ID + " RHEL " + VERSION +
                    " no longer matches the committed snapshot (operator date line excluded). " +
                    "Either the fix regressed, or the snapshot is stale and needs regenerating " +
                    "from the built artifact, on purpose, by a human who checked why it changed.");
    }
    // The provenance line G3 exists to police: the shipped code must never be
    // able to produce the hand-written sample's citation.
    if (actual.indexOf("man firewall-cmd(1)") >= 0 || actual.indexOf("2026-09-01") >= 0) {
      failures.push("the real export reproduced the hand-written sample's citation " +
                    "('man firewall-cmd(1)' / '2026-09-01') -- content/commands.json's real " +
                    "source for this entry must never read that");
    }
  }

  var report = { target: path.relative(REPO, target), failures: failures };
  if (asJson) {
    process.stdout.write(JSON.stringify(report) + "\n");
  } else {
    console.log("G3 real evidence export snapshot — " + ENTRY_ID + " RHEL " + VERSION + " — " + report.target);
    if (failures.length) {
      console.log("FAIL:");
      failures.forEach(function (f) { console.log("  - " + f); });
    } else {
      console.log("PASS: the real export matches the committed snapshot (operator date excluded), " +
                  "and never reproduces the hand-written sample's citation");
    }
  }
  process.exit(failures.length ? 1 : 0);
}

main();

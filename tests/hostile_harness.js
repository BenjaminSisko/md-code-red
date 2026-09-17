#!/usr/bin/env node
/* hostile_harness.js — CI merge-gate #4 (threat-model-v1 §11 item 4, §12 item 1).
 *
 *   node tests/hostile_harness.js [path/to/template.html|dist/md-code-red_*.html] [--json]
 *
 * Lifts the MCR-ASSEMBLER block verbatim out of the given file and runs every
 * vector in tests/fixtures/hostile-inputs.json against every field type, in
 * both --flag=VALUE and positional shapes, on all four RHEL releases, plus the
 * composed firewalld rich-rule path and the version-gating path.
 *
 * The code under test is the shipped code: qa.py Q18 points this harness at the
 * built artifact, so a difference between template.html and dist/ cannot hide
 * here. Nothing is stubbed, re-implemented, or paraphrased in Python — there is
 * one assembler in this repo and this runs it.
 *
 * Every (field type, vector) pair must land in exactly one of two states:
 *   REJECTED     assembleCommand() returned null.
 *   QUOTED-SAFE  the value occurs in the command only inside single quotes, the
 *                unquoted skeleton equals the benign command's skeleton, and
 *                the unquoted remainder holds no shell metacharacter.
 * Anything else is a FAIL and exits non-zero.
 *
 * The harness never executes /bin/sh against a vector: proving the quoting by
 * running it would execute attacker text on precisely the build where the
 * quoting is broken. It tokenises instead, under POSIX single-quote rules.
 */
"use strict";

var fs = require("fs");
var path = require("path");

var REPO = path.resolve(__dirname, "..");
var BEGIN = "MCR-ASSEMBLER-BEGIN";
var END = "MCR-ASSEMBLER-END";
var VERSIONS = ["7", "8", "9", "10"];

/* ---------------------------------------------------------------- extraction */

function extractAssembler(file) {
  var src = fs.readFileSync(file, "utf8");
  var a = src.indexOf(BEGIN);
  if (a < 0) throw new Error("no " + BEGIN + " marker in " + file);
  /* Both markers live inside block comments, so the code is what lies between
     the end of the opening comment and the start of the closing one. The END
     marker is searched for AFTER the opening comment closes, because that
     comment's own prose names it. */
  var from = src.indexOf("*/", a);
  if (from < 0) throw new Error("the " + BEGIN + " comment is unterminated in " + file);
  from += 2;
  var b = src.indexOf(END, from);
  if (b < 0) throw new Error("no " + END + " marker after " + BEGIN + " in " + file);
  var to = src.lastIndexOf("/*", b);
  if (to < from) throw new Error("malformed assembler markers in " + file);
  var block = src.slice(from, to);
  /* The block must stay pure. If a DOM or data-island reference ever lands in
     it, this harness would either crash or, worse, quietly test a stub. */
  var banned = ["document", "window.", "localStorage", "sessionStorage",
                "DATASETS", "STATE.", "innerHTML"];
  for (var i = 0; i < banned.length; i++) {
    if (block.indexOf(banned[i]) >= 0) {
      throw new Error("assembler block references '" + banned[i] +
                      "' — it must stay pure, or this gate tests nothing");
    }
  }
  var factory = new Function(
    "\"use strict\";\n" + block + "\n" +
    "return {shQuote:shQuote,yamlQuote:yamlQuote,validateField:validateField," +
    "validateSpec:validateSpec,assembleCommand:assembleCommand," +
    "composeRichRule:composeRichRule,blastFor:blastFor,FIELD_TYPES:FIELD_TYPES};");
  return { api: factory(), bytes: block.length };
}

/* --------------------------------------------------------------- tokenising */

/* A POSIX-ish word splitter, which is what a shell would do with this string.
   Single quotes protect everything until the next quote; outside them a
   backslash escapes exactly one character (shQuote's embedded-quote idiom
   'a'\''b' is one word: quoted, escaped-quote, quoted). Each word records the
   text a shell would still interpret — the part NOT protected by quotes and
   NOT backslash-escaped — which is the only text an injected value could ever
   act through. */
function tokenize(cmd) {
  var words = [], cur = "", bare = "", quoted = false, started = false, inQ = false, i = 0;
  function flush() {
    if (started) words.push({ raw: cur, bare: bare, quoted: quoted });
    cur = ""; bare = ""; quoted = false; started = false;
  }
  while (i < cmd.length) {
    var c = cmd.charAt(i);
    if (inQ) {
      cur += c;
      if (c === "'") inQ = false;
      i++; started = true; continue;
    }
    if (c === "\\") {
      if (i + 1 >= cmd.length) return null;      /* trailing backslash: malformed */
      cur += c + cmd.charAt(i + 1);
      i += 2; started = true; continue;          /* escaped char is inert, not 'bare' */
    }
    if (c === "'") { inQ = true; quoted = true; cur += c; i++; started = true; continue; }
    if (c === " " || c === "\t") { flush(); i++; continue; }
    if (c === "\n" || c === "\r") return null;   /* a raw newline is never legitimate here */
    cur += c; bare += c; i++; started = true;
  }
  if (inQ) return null;                          /* unbalanced quote: quoting is broken */
  flush();
  return words;
}

/* The shape a shell sees: every quoted payload collapses to one placeholder, so
   two commands that differ only INSIDE quotes compare equal, and any value that
   changed the command's structure shows up immediately. */
function skeleton(words) {
  var out = [];
  for (var i = 0; i < words.length; i++) {
    out.push(words[i].quoted ? words[i].bare + "@" : words[i].raw);
  }
  return out.join(" ");
}

function bareText(words) {
  var out = "";
  for (var i = 0; i < words.length; i++) out += words[i].bare + " ";
  return out;
}

var UNQUOTED_OK = /^[A-Za-z0-9_./=:@%+,\- ]*$/;

/* ------------------------------------------------------------------- specs */

function flagSpec(type, def, versions) {
  var field = { name: "v", type: type, required: true, versions: versions || VERSIONS };
  if (def.options) field.options = def.options;
  return {
    id: "harness-flag-" + type, tool: "harness", blast: "green",
    fields: [field],
    template: [{ lit: "probe" }, { flag: "--value", field: "v" }]
  };
}
function argSpec(type, def, versions) {
  var field = { name: "v", type: type, required: true, versions: versions || VERSIONS };
  if (def.options) field.options = def.options;
  return {
    id: "harness-arg-" + type, tool: "harness", blast: "green",
    fields: [field],
    template: [{ lit: "probe" }, { lit: "--" }, { field: "v" }]
  };
}
function spacedFlagSpec(type, def) {
  var field = { name: "v", type: type, required: true, versions: VERSIONS };
  if (def.options) field.options = def.options;
  return {
    id: "harness-spaced-" + type, tool: "harness", blast: "green",
    fields: [field],
    template: [{ lit: "probe" }, { flag: "--value", eq: false, field: "v" }]
  };
}
/* The highest-risk field class in the threat model: a rich rule whose legitimate
   syntax overlaps shell syntax. Composed from validated sub-fields only. */
function richRuleSpec(hostileField, hostileType) {
  var fields = [
    { name: "family", type: "family", required: true, versions: VERSIONS },
    { name: "source", type: "cidr", required: true, versions: VERSIONS },
    { name: "port", type: "portrange", required: true, versions: VERSIONS },
    { name: "proto", type: "protocol", required: true, versions: VERSIONS },
    { name: "act", type: "action", required: true, versions: VERSIONS }
  ];
  for (var i = 0; i < fields.length; i++) {
    if (fields[i].name === hostileField) fields[i].type = hostileType || fields[i].type;
  }
  return {
    id: "harness-richrule", tool: "firewall-cmd", blast: "green",
    fields: fields,
    template: [
      { lit: "firewall-cmd" },
      {
        flag: "--add-rich-rule",
        richRule: { family: "family", source: "source", port: "port", protocol: "proto", action: "act" }
      },
      { lit: "--permanent" }
    ]
  };
}

/* -------------------------------------------------------------------- run */

function main() {
  var target = process.argv[2] || path.join(REPO, "template.html");
  var asJson = process.argv.indexOf("--json") >= 0;
  var loaded = extractAssembler(target);
  var A = loaded.api;
  var fx = JSON.parse(fs.readFileSync(path.join(REPO, "tests", "fixtures", "hostile-inputs.json"), "utf8"));
  var types = Object.keys(fx.field_types);
  var vectors = fx.vectors;

  var stats = { checks: 0, rejected: 0, quoted: 0, failures: [], byClass: {}, byType: {} };

  function note(cls, outcome) {
    if (!stats.byClass[cls]) stats.byClass[cls] = { rejected: 0, quoted: 0 };
    stats.byClass[cls][outcome]++;
  }

  function check(label, cls, spec, version, values, value, expect) {
    stats.checks++;
    var res;
    try {
      res = A.assembleCommand(spec, version, values, { patterns: [] });
    } catch (e) {
      stats.failures.push(label + ": assembler threw " + e.message);
      return;
    }
    if (res === null) {
      if (expect !== "reject") {
        stats.failures.push(label + ": rejected, but this value is legitimate for this field type " +
                            "and must assemble into a quoted token");
        return;
      }
      stats.rejected++; note(cls, "rejected"); return;
    }
    if (expect === "reject") {
      stats.failures.push(label + ": accepted a value its field type's allow-list must refuse — " +
                          JSON.stringify(res.command) + " (quoting may still hold; the grammar does not)");
      return;
    }
    if (!res || typeof res.command !== "string") {
      stats.failures.push(label + ": returned a non-null result with no command string");
      return;
    }
    var words = tokenize(res.command);
    if (words === null) {
      stats.failures.push(label + ": command does not tokenise as balanced shell words — "
        + JSON.stringify(res.command));
      return;
    }
    /* nothing the shell would still interpret may carry any of the value */
    var bare = bareText(words);
    if (!UNQUOTED_OK.test(bare)) {
      stats.failures.push(label + ": shell metacharacter left unquoted in "
        + JSON.stringify(bare) + " (from " + JSON.stringify(res.command) + ")");
      return;
    }
    if (value !== "" && bare.indexOf(value) >= 0) {
      stats.failures.push(label + ": the value itself reached unquoted text in " + JSON.stringify(res.command));
      return;
    }
    /* the command's shape must be exactly what the benign control produces */
    var benignValues = {}, k;
    for (k in values) if (Object.prototype.hasOwnProperty.call(values, k)) benignValues[k] = values[k];
    benignValues[spec._hostileField] = spec._benign;
    var ref = A.assembleCommand(spec, version, benignValues, { patterns: [] });
    if (ref === null) {
      stats.failures.push(label + ": the benign control value was itself rejected");
      return;
    }
    var refWords = tokenize(ref.command);
    if (refWords === null || skeleton(words) !== skeleton(refWords)) {
      stats.failures.push(label + ": shell-visible shape differs from the benign control — "
        + JSON.stringify(skeleton(words)) + " vs "
        + JSON.stringify(refWords ? skeleton(refWords) : "(control does not tokenise)"));
      return;
    }
    stats.quoted++;
    note(cls, "quoted");
  }

  /* ---- every field type x every vector x every version x three shapes ---- */
  for (var t = 0; t < types.length; t++) {
    var type = types[t];
    var def = fx.field_types[type];
    stats.byType[type] = { rejected: 0, quoted: 0 };
    for (var v = 0; v < vectors.length; v++) {
      var vec = vectors[v];
      for (var r = 0; r < VERSIONS.length; r++) {
        var version = VERSIONS[r];
        var shapes = [flagSpec(type, def), argSpec(type, def), spacedFlagSpec(type, def)];
        for (var s = 0; s < shapes.length; s++) {
          var spec = shapes[s];
          spec._hostileField = "v";
          spec._benign = def.benign;
          var before = { r: stats.rejected, q: stats.quoted };
          /* every field type except the one free-text type is a closed grammar,
             so the required outcome there is rejection, full stop. */
          check(spec.id + " / " + vec.id + " / RHEL " + version, vec["class"],
                spec, version, { v: vec.value }, vec.value,
                type === "comment" ? vec.free_text : "reject");
          if (stats.rejected > before.r) stats.byType[type].rejected++;
          else if (stats.quoted > before.q) stats.byType[type].quoted++;
        }
      }
    }
  }

  /* ---- the rich-rule path: hostile text into each validated sub-field ---- */
  var richBase = { family: "ipv4", source: "10.0.0.0/8", port: "8443", proto: "tcp", act: "accept" };
  var richFields = ["family", "source", "port", "proto", "act"];
  for (var rf = 0; rf < richFields.length; rf++) {
    for (var rv = 0; rv < vectors.length; rv++) {
      for (var rr = 0; rr < VERSIONS.length; rr++) {
        var rspec = richRuleSpec(null, null);
        rspec._hostileField = richFields[rf];
        rspec._benign = richBase[richFields[rf]];
        var vals = {};
        for (var kk in richBase) if (Object.prototype.hasOwnProperty.call(richBase, kk)) vals[kk] = richBase[kk];
        vals[richFields[rf]] = vectors[rv].value;
        /* every rich-rule sub-field is a closed grammar: nothing hostile may compose */
        check("richrule[" + richFields[rf] + "] / " + vectors[rv].id + " / RHEL " + VERSIONS[rr],
              vectors[rv]["class"], rspec, VERSIONS[rr], vals, vectors[rv].value, "reject");
      }
    }
  }

  /* ---- positive control -------------------------------------------------
     A validator that rejects everything would pass every assertion above while
     making the product useless, so each field type's benign value must
     assemble, on every release, in every argument shape. Check the healthy case
     before believing the signal. */
  var inv = [], controls = 0;
  for (var pt = 0; pt < types.length; pt++) {
    var pdef = fx.field_types[types[pt]];
    for (var pr = 0; pr < VERSIONS.length; pr++) {
      var pshapes = [flagSpec(types[pt], pdef), argSpec(types[pt], pdef), spacedFlagSpec(types[pt], pdef)];
      for (var ps = 0; ps < pshapes.length; ps++) {
        controls++;
        var pres = A.assembleCommand(pshapes[ps], VERSIONS[pr], { v: pdef.benign }, { patterns: [] });
        if (pres === null) {
          inv.push("positive control: benign " + types[pt] + " value " + JSON.stringify(pdef.benign) +
                   " was rejected on RHEL " + VERSIONS[pr] + " (" + pshapes[ps].id + ")");
        } else if (pres.command.indexOf("'" + pdef.benign + "'") < 0) {
          inv.push("positive control: benign " + types[pt] + " value is not present as a single-quoted " +
                   "token in " + JSON.stringify(pres.command));
        }
      }
    }
  }
  /* ---- negative control: the CHECKER itself must be able to fail ---------
     A tokeniser that called everything safe would also pass, so hand it two
     commands it must reject. */
  var broken = tokenize("probe --value=" + "$(whoami)");
  if (broken === null || UNQUOTED_OK.test(bareText(broken))) {
    inv.push("negative control: the tokeniser accepted an unquoted $(whoami) as safe");
  }
  var brokenShape = tokenize("probe --value='x' ; id");
  if (brokenShape !== null && skeleton(brokenShape) === skeleton(tokenize("probe --value='x'"))) {
    inv.push("negative control: the shape comparison did not notice an appended ; id");
  }
  if (A.shQuote("it's") !== "'it'\\''s'") inv.push("shQuote() does not use the POSIX '\\'' idiom");
  if (A.yamlQuote("it's") !== "'it''s'") inv.push("yamlQuote() does not use the YAML '' idiom");
  if (A.shQuote("x") === A.yamlQuote("it's")) inv.push("shQuote and yamlQuote are not distinct");
  if (A.shQuote("plain") !== "'plain'") inv.push("shQuote() has a bare-value bypass — quoting must be uniform");

  /* a required field left empty must yield null on every version */
  for (var iv = 0; iv < VERSIONS.length; iv++) {
    var emptySpec = flagSpec("zone", fx.field_types.zone);
    if (A.assembleCommand(emptySpec, VERSIONS[iv], {}, { patterns: [] }) !== null) {
      inv.push("a missing required field produced a command on RHEL " + VERSIONS[iv]);
    }
  }
  /* a field gated out of a version can never appear in that version's command */
  var gated = flagSpec("zone", fx.field_types.zone, ["9", "10"]);
  gated.fields[0].required = false;
  for (var gv = 0; gv < VERSIONS.length; gv++) {
    var g = A.assembleCommand(gated, VERSIONS[gv], { v: "public" }, { patterns: [] });
    var present = g !== null && g.command.indexOf("public") >= 0;
    var allowed = VERSIONS[gv] === "9" || VERSIONS[gv] === "10";
    if (present !== allowed) {
      inv.push("version gating wrong on RHEL " + VERSIONS[gv] + ": value " +
               (present ? "reached" : "did not reach") + " the command");
    }
  }
  /* an enum option gated out of a version cannot be selected on that version */
  var optSpec = flagSpec("enum", { benign: "alpha", options: [{ value: "alpha", versions: VERSIONS },
                                                              { value: "bravo", versions: ["10"] }] });
  for (var ov = 0; ov < VERSIONS.length; ov++) {
    var o = A.assembleCommand(optSpec, VERSIONS[ov], { v: "bravo" }, { patterns: [] });
    if ((o !== null) !== (VERSIONS[ov] === "10")) {
      inv.push("a version-gated enum option was selectable on RHEL " + VERSIONS[ov]);
    }
  }
  /* blast: the destructive table is matched post-assembly, and blast:red stands alone */
  var dz = flagSpec("comment", fx.field_types.comment);
  var red = A.assembleCommand(dz, "9", { v: "rm -rf /srv" },
                              { patterns: [{ id: "dp", match: "rm -rf", label: "l", why: "w", blast_floor: "red" }] });
  if (!red || red.blast !== "red") inv.push("a destructive pattern in the assembled command did not raise blast to red");
  var ownRed = A.assembleCommand({ id: "x", blast: "red", fields: [], template: [{ lit: "true" }] }, "9", {}, { patterns: [] });
  if (!ownRed || ownRed.blast !== "red") inv.push("a content entry's own blast:red did not survive assembly");

  for (var q = 0; q < inv.length; q++) stats.failures.push("invariant: " + inv[q]);

  var report = {
    target: path.relative(REPO, target),
    assembler_bytes: loaded.bytes,
    field_types: types.length,
    vectors: vectors.length,
    versions: VERSIONS.length,
    checks: stats.checks,
    rejected: stats.rejected,
    quoted_safe: stats.quoted,
    positive_controls: controls,
    invariants: 4 + VERSIONS.length * 3 + 2 + 2,
    failures: stats.failures
  };
  if (asJson) {
    process.stdout.write(JSON.stringify(report, null, 1) + "\n");
  } else {
    console.log("hostile-input harness — " + report.target + " (" + loaded.bytes + " bytes of assembler)");
    console.log("  " + types.length + " field types x " + vectors.length + " vectors x " +
                VERSIONS.length + " releases x 3 argument shapes, plus 5 rich-rule sub-fields");
    console.log("  " + stats.checks + " checks: " + stats.rejected + " rejected (null), " +
                stats.quoted + " quoted-safe, " + stats.failures.length + " FAILED");
    console.log("  " + controls + " positive controls (benign value per type/release/shape) and " +
                report.invariants + " invariants");
    var classes = Object.keys(stats.byClass).sort();
    for (var c = 0; c < classes.length; c++) {
      console.log("    " + classes[c] + ": " + stats.byClass[classes[c]].rejected + " rejected, " +
                  stats.byClass[classes[c]].quoted + " quoted-safe");
    }
    for (var ff = 0; ff < stats.failures.length; ff++) console.log("  FAIL: " + stats.failures[ff]);
  }
  process.exit(stats.failures.length ? 1 : 0);
}

main();

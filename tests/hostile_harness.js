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
    "composeRichRule:composeRichRule,blastFor:blastFor,FIELD_TYPES:FIELD_TYPES," +
    "RICHRULE_SLOT_TYPES:RICHRULE_SLOT_TYPES,fieldTypeMap:fieldTypeMap};");
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
    rich_rule_oracles: stats.oracles,
    half_formed_checks: halfFormed,
    rich_rule_slot_types_refused: richCounts.refusedType,
    rich_rule_slot_types_allowed: richCounts.allowedType,
    positive_controls: controls,
    /* quoting idioms (4) + empty-required, version gating and gated enums
       (3 per release) + 2 tokeniser negative controls + 2 rich-rule-oracle
       negative controls + 2 blast invariants + the MCR-SEC-001 regression
       (1 vector check + 1 per release + 1 typed) */
    invariants: 4 + VERSIONS.length * 3 + 2 + 2 + 2 + (2 + VERSIONS.length),
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

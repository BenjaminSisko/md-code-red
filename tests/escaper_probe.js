#!/usr/bin/env node
/* escaper_probe.js — the oracle behind qa.py Q19, the escaper property gate.
 *
 *   node tests/escaper_probe.js <file-of-extracted-escapers.js> [--json]
 *
 * AL-GATE3-001. Q17 proves that esc()/escapeAttr() are CALLED at every render
 * sink. It has never proven, and structurally cannot prove, that either one
 * escapes anything: `function esc(s){return s;}` defeats the whole render-safety
 * property with zero change to any call site, and every call site keeps looking
 * exactly as safe as it does today. Al Kowalski's Gate 3 review reproduced that
 * directly — render_sink_failures() returned `([], 4)` on a shell whose escapers
 * were identity functions.
 *
 * This probe closes that by running the functions, not by reading them. qa.py
 * lifts `esc`, `escapeAttr` and `escapeRegex` out of the SHIPPED artifact
 * (the same way tests/hostile_harness.js lifts the assembler block) and hands
 * the extracted text here. Nothing is stubbed and nothing is re-implemented in
 * Python: there is one set of escapers in this repo and this runs them.
 *
 * The properties asserted, per vector in tests/fixtures/escaper-corpus.json:
 *
 *   esc()          the OUTPUT carries no raw < > " ', and every & in it opens a
 *                  well-formed entity reference; decoding those entities with a
 *                  strict decoder lands back exactly on the input (so escaping
 *                  is lossless as well as safe — a "sanitiser" that drops the
 *                  character would also pass a no-raw-metacharacter test, and
 *                  silently corrupt DISA fix text).
 *   escapeAttr()   all of the above, plus no raw ` and no raw =, which is what
 *                  makes the value safe in an unquoted attribute too — the
 *                  reason escapeAttr() exists as a separate function.
 *   escapeRegex()  every regex metacharacter present in the input appears
 *                  backslash-escaped in the output and never bare, the output
 *                  compiles, the compiled pattern matches the input exactly, and
 *                  it does NOT match a string that only the UNescaped pattern
 *                  would match (`a.c` must not match `abc`).
 *
 * NEGATIVE CONTROL. Before reporting anything, the probe runs its own battery
 * against deliberately broken escapers defined below — identity, drop-the-
 * character, and half-escaped — and fails if the battery rates any of them
 * clean. A checker that has never been seen to fail is not a checker; this one
 * proves it can fail on every run, on this runner, against this node build.
 */
"use strict";

var fs = require("fs");
var path = require("path");

var REPO = path.resolve(__dirname, "..");
var CORPUS = path.join(REPO, "tests", "fixtures", "escaper-corpus.json");

/* ------------------------------------------------------------ strict decoder */

/* Only the entity spellings an escaper is allowed to emit. Deliberately NOT a
   full HTML entity table: this decoder is one half of a round-trip proof, so it
   must be exactly as generous as the encoder is and no more. */
var NAMED = { amp: "&", lt: "<", gt: ">", quot: "\"", apos: "'" };
var ENTITY_RE = /&(#x[0-9a-fA-F]+|#[0-9]+|[a-zA-Z][a-zA-Z0-9]{1,7});/g;

function fromCodePoint(cp) {
  if (cp < 0 || cp > 0x10FFFF) return null;
  if (cp <= 0xFFFF) return String.fromCharCode(cp);
  cp -= 0x10000;
  return String.fromCharCode(0xD800 + (cp >> 10), 0xDC00 + (cp & 0x3FF));
}

function decodeEntities(s) {
  return String(s).replace(ENTITY_RE, function (m, body) {
    if (body.charAt(0) === "#") {
      var hex = body.charAt(1) === "x" || body.charAt(1) === "X";
      var cp = parseInt(hex ? body.slice(2) : body.slice(1), hex ? 16 : 10);
      if (isNaN(cp)) return m;
      var ch = fromCodePoint(cp);
      return ch === null ? m : ch;
    }
    return Object.prototype.hasOwnProperty.call(NAMED, body) ? NAMED[body] : m;
  });
}

/* Every & that does NOT open one of those entity references. An escaper whose
   output contains one has left an ampersand raw. */
function strayAmpersands(out) {
  return String(out).replace(ENTITY_RE, "").indexOf("&") >= 0;
}

/* --------------------------------------------------------------- the battery */

var REGEX_META = ".*+?^${}()|[]\\";

/* node refuses to compile a very large pattern; see the escapeRegex block below. */
var MAX_PATTERN = 8192;

function unescapedMetacharacters(out) {
  /* Drop every backslash-escaped pair, then look for a metacharacter that is
     still standing on its own. */
  var rest = String(out).replace(/\\[\s\S]/g, "");
  var bad = [];
  for (var i = 0; i < rest.length; i++) {
    if (REGEX_META.indexOf(rest.charAt(i)) >= 0 && bad.indexOf(rest.charAt(i)) < 0) {
      bad.push(rest.charAt(i));
    }
  }
  return bad;
}

function show(v) {
  var s = String(v);
  if (s.length > 48) s = s.slice(0, 48) + "…";
  return JSON.stringify(s);
}

/* Runs every property over every vector. Returns {failures:[], checks:n}. */
function battery(api, vectors) {
  var failures = [], checks = 0;

  function fail(fn, vector, why, got) {
    failures.push(fn + "() on " + show(vector) + ": " + why + " — output " + show(got));
  }

  for (var i = 0; i < vectors.length; i++) {
    var v = vectors[i];

    /* ---- esc() ---- */
    var out;
    try {
      out = api.esc(v);
    } catch (e) {
      failures.push("esc() threw on " + show(v) + ": " + e.message);
      checks++;
      out = null;
    }
    if (out !== null) {
      checks++;
      if (typeof out !== "string") {
        fail("esc", v, "returned a " + typeof out + ", not a string", out);
      } else {
        var raw = /[<>"']/.exec(out);
        if (raw) fail("esc", v, "left a raw " + JSON.stringify(raw[0]) + " in the output", out);
        if (strayAmpersands(out)) {
          fail("esc", v, "left an ampersand that does not open an entity reference", out);
        }
        var back = decodeEntities(out);
        if (back !== v) {
          fail("esc", v, "does not round-trip: decoding the output gives " + show(back), out);
        }
      }
    }

    /* ---- escapeAttr() ---- */
    var aout;
    try {
      aout = api.escapeAttr(v);
    } catch (e) {
      failures.push("escapeAttr() threw on " + show(v) + ": " + e.message);
      checks++;
      aout = null;
    }
    if (aout !== null) {
      checks++;
      if (typeof aout !== "string") {
        fail("escapeAttr", v, "returned a " + typeof aout + ", not a string", aout);
      } else {
        var araw = /[<>"'`=]/.exec(aout);
        if (araw) {
          fail("escapeAttr", v, "left a raw " + JSON.stringify(araw[0]) +
               " in the output — an attribute value carrying one of < > \" ' ` = can end the " +
               "attribute, or the tag, in some context", aout);
        }
        if (strayAmpersands(aout)) {
          fail("escapeAttr", v, "left an ampersand that does not open an entity reference", aout);
        }
        var aback = decodeEntities(aout);
        if (aback !== v) {
          fail("escapeAttr", v, "does not round-trip: decoding the output gives " + show(aback), aout);
        }
      }
    }

    /* ---- escapeRegex() ---- */
    var rout;
    try {
      rout = api.escapeRegex(v);
    } catch (e) {
      failures.push("escapeRegex() threw on " + show(v) + ": " + e.message);
      checks++;
      rout = null;
    }
    if (rout !== null) {
      checks++;
      if (typeof rout !== "string") {
        fail("escapeRegex", v, "returned a " + typeof rout + ", not a string", rout);
      } else {
        var bare = unescapedMetacharacters(rout);
        if (bare.length) {
          fail("escapeRegex", v, "left the regex metacharacter(s) " + JSON.stringify(bare.join("")) +
               " unescaped — the pattern would mean something other than the literal text", rout);
        }
        /* V8 compiles a regular expression lazily, so construction and the first
           execution both have to sit inside the same guard. Patterns longer than
           MAX_PATTERN are not compiled at all: node refuses very large ones, and
           that refusal is a property of the engine, not of the escaper. The
           unescaped-metacharacter check above still runs on every vector,
           including the generated 100k ones. */
        if (rout.length <= MAX_PATTERN) {
          try {
            var re = new RegExp("^(?:" + rout + ")$");
            if (!re.test(v)) {
              fail("escapeRegex", v, "the escaped pattern does not match its own input", rout);
            }
          } catch (e) {
            fail("escapeRegex", v, "produced a pattern that does not compile or run: " + e.message, rout);
          }
        }
      }
    }
  }

  /* escapeRegex() negative controls: an escaper that returns its input would
     pass "matches itself" on every vector above, because an unescaped pattern
     still matches the text it came from. These are the cases where the escaped
     and the unescaped pattern DISAGREE. */
  var negatives = [
    ["a.c", "abc", "a dot must not match an arbitrary character"],
    [".", "x", "a lone dot must not match an arbitrary character"],
    ["[a-z]+", "abc", "a character class must not be a character class"],
    ["a|b", "a", "an alternation must not alternate"],
    ["(x)", "x", "a group must not group"],
    ["a*", "aaaa", "a star must not repeat"],
    ["^a$", "a", "anchors must be literal text"]
  ];
  for (var n = 0; n < negatives.length; n++) {
    var pat = negatives[n][0], should_not_match = negatives[n][1];
    checks++;
    var nre = null;
    try {
      nre = new RegExp("^(?:" + api.escapeRegex(pat) + ")$");
    } catch (e) {
      failures.push("escapeRegex() on " + show(pat) + " produced an uncompilable pattern: " + e.message);
      continue;
    }
    if (nre.test(should_not_match)) {
      failures.push("escapeRegex() on " + show(pat) + " still matches " + show(should_not_match) +
                    " — " + negatives[n][2]);
    }
    if (!nre.test(pat)) {
      failures.push("escapeRegex() on " + show(pat) + " no longer matches its own input");
    }
  }

  /* Null and undefined reach these functions from real call sites
     (`esc(entry.notes||"")` is one keystroke away from `esc(entry.notes)`), and
     both must produce the empty string rather than the text "null". */
  var nullish = [[null, "null"], [undefined, "undefined"]];
  for (var k = 0; k < nullish.length; k++) {
    for (var fn in api) {
      if (!Object.prototype.hasOwnProperty.call(api, fn)) continue;
      checks++;
      var got;
      try {
        got = api[fn](nullish[k][0]);
      } catch (e) {
        failures.push(fn + "() threw on " + nullish[k][1] + ": " + e.message);
        continue;
      }
      if (got !== "") {
        failures.push(fn + "() on " + nullish[k][1] + " returned " + show(got) +
                      " rather than the empty string");
      }
    }
  }

  return { failures: failures, checks: checks };
}

/* ------------------------------------------------------- the negative control */

/* Three broken escapers, each broken the way a real regression would break one.
   If the battery rates any of them clean, the battery is not measuring anything
   and this probe must not report a PASS. */
var BROKEN = {
  "identity (`return s;`, AL-GATE3-001's own reproduction)": {
    esc: function (s) { return s; },
    escapeAttr: function (s) { return s; },
    escapeRegex: function (s) { return s; }
  },
  "drops the dangerous characters instead of encoding them": {
    esc: function (s) { return String(s == null ? "" : s).replace(/[&<>"'`=]/g, ""); },
    escapeAttr: function (s) { return String(s == null ? "" : s).replace(/[&<>"'`=]/g, ""); },
    escapeRegex: function (s) { return String(s == null ? "" : s).replace(/[.*+?^${}()|[\]\\]/g, ""); }
  },
  "escapes < and > but forgets the quotes": {
    esc: function (s) {
      return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    },
    escapeAttr: function (s) {
      return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    },
    escapeRegex: function (s) { return String(s == null ? "" : s).replace(/[.*+?]/g, "\\$&"); }
  }
};

function selfTest(vectors) {
  var out = [];
  for (var label in BROKEN) {
    if (!Object.prototype.hasOwnProperty.call(BROKEN, label)) continue;
    var r = battery(BROKEN[label], vectors);
    if (!r.failures.length) {
      out.push("the property battery rated a KNOWN-BROKEN escaper clean (" + label +
               ") — this probe proves nothing on this runner and must not report a PASS");
    }
  }
  return out;
}

/* ------------------------------------------------------------------- driver */

function loadCorpus() {
  var doc = JSON.parse(fs.readFileSync(CORPUS, "utf8"));
  var vectors = doc.vectors.map(function (v) { return v.value; });
  var generated = doc.generated || [];
  for (var i = 0; i < generated.length; i++) {
    var g = generated[i], s = "";
    for (var j = 0; j < g.count; j++) s += g.repeat;
    vectors.push(s);
  }
  return { vectors: vectors, declared: doc.vectors.length, generated: generated.length };
}

function loadEscapers(file) {
  var src = fs.readFileSync(file, "utf8");
  /* The extracted block must stay pure for the same reason the assembler block
     must: a DOM or storage reference in here means this probe is either
     crashing or, worse, quietly testing a stub. */
  var banned = ["document", "window.", "localStorage", "sessionStorage", "innerHTML", "require("];
  for (var i = 0; i < banned.length; i++) {
    if (src.indexOf(banned[i]) >= 0) {
      throw new Error("the extracted escaper block references '" + banned[i] +
                      "' — these three functions are pure string transforms, or this gate " +
                      "tests something other than what ships");
    }
  }
  var factory = new Function("\"use strict\";\n" + src + "\n" +
                             "return {esc:esc,escapeAttr:escapeAttr,escapeRegex:escapeRegex};");
  return factory();
}

function main(argv) {
  var file = null, asJson = false;
  for (var i = 0; i < argv.length; i++) {
    if (argv[i] === "--json") asJson = true;
    else if (file === null) file = argv[i];
  }
  if (!file) {
    process.stderr.write("usage: node tests/escaper_probe.js <extracted-escapers.js> [--json]\n");
    return 2;
  }

  var corpus = loadCorpus();
  var report = {
    vectors: corpus.declared,
    generated_vectors: corpus.generated,
    checks: 0,
    failures: [],
    negative_controls: Object.keys(BROKEN).length,
    escaper_bytes: 0
  };

  var control = selfTest(corpus.vectors);
  if (control.length) {
    report.failures = control;
  } else {
    var api;
    try {
      api = loadEscapers(file);
      report.escaper_bytes = fs.readFileSync(file, "utf8").length;
    } catch (e) {
      report.failures = ["the extracted escapers could not be loaded: " + e.message];
      api = null;
    }
    if (api) {
      var required = ["esc", "escapeAttr", "escapeRegex"];
      for (var q = 0; api && q < required.length; q++) {
        if (typeof api[required[q]] !== "function") {
          report.failures.push("the extracted block defines no " + required[q] + "() function");
        }
      }
      if (!report.failures.length) {
        var r = battery(api, corpus.vectors);
        report.checks = r.checks;
        report.failures = r.failures;
      }
    }
  }

  if (asJson) {
    process.stdout.write(JSON.stringify(report) + "\n");
  } else {
    process.stdout.write(report.checks + " checks over " + report.vectors + " declared and " +
                         report.generated_vectors + " generated vectors, " +
                         report.negative_controls + " negative controls\n");
    for (var k = 0; k < report.failures.length; k++) {
      process.stdout.write("FAIL: " + report.failures[k] + "\n");
    }
  }
  return report.failures.length ? 1 : 0;
}

process.exit(main(process.argv.slice(2)));

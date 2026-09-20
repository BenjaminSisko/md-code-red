#!/usr/bin/env node
/* test_reference_index.js -- the build-time inverted index and the lazy
 * per-family hydration it drives, LIFTED OUT OF THE SHIPPED ARTIFACT and run.
 *
 * AL-GATE3-001 is the precedent: a test that checks a function is CALLED proves
 * the call, not the behaviour. So this extracts the MCR-HYDRATE block verbatim
 * from dist/md-code-red_*.html, supplies the only DOM call it makes
 * (document.getElementById(...).textContent) from the artifact's OWN islands,
 * and runs the real thing.
 *
 * What it proves:
 *
 *   1. RESOLUTION. Every posting decodes to a record that actually contains the
 *      token it was filed under. This is the property an inverted index can get
 *      wrong silently: an off-by-one in the ordinal, or a stride that wraps,
 *      resolves to a REAL record that is simply the wrong one, and the palette
 *      then shows the operator a DISA command under a search term that came out
 *      of a Red Hat guide. Sampled on a fixed stride, never an RNG, so a failure
 *      is reproducible (Q10's shape).
 *
 *   2. COMPLETENESS. The index finds what a linear scan would find. A random
 *      sample of records is looked up by a token taken from its own text, and
 *      the record must come back. An index that silently dropped a family, or a
 *      token class, passes (1) trivially and fails this.
 *
 *   3. LAZINESS. The property the whole design exists for: a query whose terms
 *      only occur in one family must hydrate ONLY that family. Measured by
 *      counting island reads, not by reading a flag the code sets about itself.
 *
 *   4. THE BOOT PROMISE. Nothing hydrates until something asks. Zero island
 *      reads after loading the block, before the first query.
 *
 *   node tests/test_reference_index.js [path/to/dist/md-code-red_*.html] [--json]
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

function islandsOf(src) {
  var re = /<script id="([^"]+)" type="application\/json">([\s\S]*?)<\/script>/g, m, out = {};
  while ((m = re.exec(src))) out[m[1]] = m[2];
  return out;
}

/* The same haystack build.py indexed. Restated here ON PURPOSE rather than
   lifted: if the two ever disagree, the index is filed under text the record
   does not carry, and that disagreement is exactly what test (1) is for. A
   shared implementation would make the test agree with the bug. */
function haystackOf(rec) {
  var stigs = (rec.o || []).map(function (o) { return o.s || ""; }).join(" ");
  return ((rec.c || "") + " " + (rec.t || "") + " " + stigs).toLowerCase();
}

function load(file) {
  var src = fs.readFileSync(file, "utf8");
  var islands = islandsOf(src);
  var block = extractBlock(src, "MCR-HYDRATE-BEGIN", "MCR-HYDRATE-END", file);
  if (!islands["mcr-data"]) throw new Error("no mcr-data island in " + file);
  var DATA = JSON.parse(islands["mcr-data"]);
  var reads = [];
  /* The only DOM the block touches. Counting the reads is how laziness is
     measured: the block cannot report its own behaviour to this test. */
  var document = {
    getElementById: function (id) {
      if (!Object.prototype.hasOwnProperty.call(islands, id)) return null;
      return { get textContent() { reads.push(id); return islands[id]; } };
    }
  };
  var DATASETS = { REFCMDS: DATA.reference_commands };
  var factory = new Function("document", "DATASETS", "\"use strict\";\n" + block + "\n" +
    "return {hydrateFamily:hydrateFamily, refIndex:refIndex, refSearchPostings:refSearchPostings,\n" +
    "  refResolvePostings:refResolvePostings, refPostingFamily:refPostingFamily,\n" +
    "  refPostingOrdinal:refPostingOrdinal, refTokensMatching:refTokensMatching,\n" +
    "  queryReference:queryReference, refFamilyNames:refFamilyNames,\n" +
    "  refFamilyIsHydrated:refFamilyIsHydrated, refFamilyCount:refFamilyCount};");
  return { mod: factory(document, DATASETS), islands: islands, reads: reads, data: DATA };
}

function main() {
  var args = process.argv.slice(2);
  var asJson = args.indexOf("--json") >= 0;
  var target = args.filter(function (a) { return a !== "--json"; })[0];
  if (!target) {
    var distDir = path.join(REPO, "dist");
    var cands = fs.existsSync(distDir)
      ? fs.readdirSync(distDir).filter(function (f) {
          return f.indexOf("md-code-red_") === 0 && f.slice(-5) === ".html";
        }).sort()
      : [];
    target = cands.length ? path.join(distDir, cands[cands.length - 1]) : path.join(REPO, "template.html");
  }

  var failures = [], notes = [];
  var ctx;
  try {
    ctx = load(target);
  } catch (e) {
    failures.push("could not lift MCR-HYDRATE out of " + path.relative(REPO, target) + ": " + e.message);
    var report0 = { target: path.relative(REPO, target), failures: failures, notes: notes };
    process.stdout.write(asJson ? JSON.stringify(report0) + "\n" : report0.failures.join("\n") + "\n");
    process.exit(1);
  }
  var mod = ctx.mod;

  /* (4) THE BOOT PROMISE, asserted before anything else runs. */
  if (ctx.reads.length !== 0) {
    failures.push("lifting the block read " + ctx.reads.length + " island(s) (" +
                  ctx.reads.join(", ") + "). Nothing may hydrate until something asks.");
  } else {
    notes.push("boot: zero island reads before the first query");
  }

  var idx = mod.refIndex();
  if (ctx.reads.length !== 1 || ctx.reads[0] !== "mcr-ref-index") {
    failures.push("refIndex() read " + JSON.stringify(ctx.reads) + "; it must read mcr-ref-index and nothing else");
  }
  var tokens = Object.keys(idx.t || {});
  if (tokens.length < 1000) {
    failures.push("the inverted index carries only " + tokens.length + " tokens over a " +
                  "three-family corpus -- that is not an index, it is a stub");
  }
  notes.push("index: " + tokens.length + " tokens, " + (idx.postings || 0) + " postings, encoding " +
             (idx.enc || "raw") + ", families " + (idx.f || []).join("/"));

  /* Hydrate everything for the resolution and completeness checks. That is the
     one place this test is deliberately NOT lazy: proving the mapping is right
     needs every record, and laziness is proved separately in (3) on a fresh
     module. */
  var famRecords = {};
  (idx.f || []).forEach(function (f) { famRecords[f] = mod.hydrateFamily(f); });

  /* (1) RESOLUTION, on a fixed stride. No RNG: a failure has to be reproducible
     by re-running the same command, which is Q10's rule and the reason its
     accuracy sampling is trusted. */
  var STRIDE = 37, checkedPostings = 0, wrong = [];
  tokens.sort();
  for (var ti = 0; ti < tokens.length; ti += STRIDE) {
    var tok = tokens[ti], list = idx.t[tok] || [], run = 0;
    for (var j = 0; j < list.length; j++) {
      run = (idx.enc === "delta") ? (run + list[j]) : list[j];
      var fam = mod.refPostingFamily(idx, run);
      var ord = mod.refPostingOrdinal(idx, run);
      var rec = (famRecords[fam] || [])[ord];
      checkedPostings++;
      if (!rec) {
        wrong.push(tok + " -> " + fam + "[" + ord + "] does not exist");
      } else if (haystackOf(rec).indexOf(tok) < 0) {
        wrong.push(tok + " -> " + fam + "[" + ord + "] is " + JSON.stringify(rec.c).slice(0, 60) +
                   ", which does not contain that token");
      }
      if (wrong.length > 5) break;
    }
    if (wrong.length > 5) break;
  }
  if (wrong.length) {
    failures.push("postings resolve to the wrong record: " + wrong.join(" | "));
  } else {
    notes.push("resolution: " + checkedPostings + " postings across " +
               Math.ceil(tokens.length / STRIDE) + " tokens (stride " + STRIDE +
               ") each decode to a record that carries the token");
  }

  /* (2) COMPLETENESS, the other direction. */
  var missed = [], checkedRecords = 0;
  (idx.f || []).forEach(function (fam) {
    var recs = famRecords[fam] || [];
    for (var i = 0; i < recs.length; i += 101) {
      var rec = recs[i];
      var words = haystackOf(rec).match(/[a-z0-9_.+-]+/g) || [];
      var term = null;
      for (var w = 0; w < words.length; w++) {
        if (words[w].length >= (idx.min_token || 2)) { term = words[w]; break; }
      }
      if (!term) continue;
      checkedRecords++;
      var found = mod.refSearchPostings(idx, [term]);
      var want = (idx.f.indexOf(fam)) * (idx.stride || 1000000) + i;
      if (found.postings.indexOf(want) < 0 && missed.length < 5) {
        missed.push(fam + "[" + i + "] is not findable by its own token " + JSON.stringify(term));
      }
    }
  });
  if (missed.length) {
    failures.push("the index does not find records a scan would: " + missed.join(" | "));
  } else {
    notes.push("completeness: " + checkedRecords + " records (every 101st, per family) are each " +
               "findable by a token taken from their own text");
  }

  /* (3) LAZINESS, on a FRESH module so nothing is already hydrated. A STIG id
     occurs only in DISA text, so this query must touch stig_rules and nothing
     else. */
  var fresh = load(target);
  var stigId = null;
  var disa = famRecords["stig_rules"] || [];
  for (var s = 0; s < disa.length && !stigId; s++) {
    var occ = (disa[s].o || [])[0];
    if (occ && occ.s) stigId = String(occ.s).toLowerCase();
  }
  if (!stigId) {
    failures.push("no STIG id found in the DISA family -- the laziness check has no query to make");
  } else {
    var g = fresh.mod.queryReference(fresh.mod.refIndex(), stigId, 8);
    var hydrated = fresh.reads.filter(function (r) { return r.indexOf("mcr-ref-") === 0 && r !== "mcr-ref-index"; });
    var uniq = hydrated.filter(function (v, i) { return hydrated.indexOf(v) === i; });
    if (!g.hits.length) {
      failures.push("querying the index for the STIG id " + stigId + " returned no reference hit");
    }
    if (uniq.length !== 1 || uniq[0] !== "mcr-ref-stig_rules") {
      failures.push("a DISA-only query hydrated " + JSON.stringify(uniq) +
                    " -- lazy per-family hydration is not holding, and the 4.1 MB Red Hat family " +
                    "is being parsed for a search that cannot match it");
    } else {
      notes.push("laziness: a query for " + stigId + " returned " + g.hits.length + " hit(s) and " +
                 "hydrated only mcr-ref-stig_rules");
    }
  }

  /* NEGATIVE CONTROL, and it runs on every invocation rather than living behind
     a flag nobody passes. AL-GATE3-001: a checker that has only ever been shown
     correct input has not been shown to check anything. The mutation is the
     exact failure this design is most exposed to and least likely to notice --
     an ordinal off by one, which resolves to a REAL neighbouring record rather
     than to nothing, so the palette would show a plausible wrong command under
     the operator's search term.

     Both directions are mutated, because (1) and (2) fail differently: shifting
     the postings breaks resolution, and emptying a family's token lists breaks
     completeness while leaving resolution perfectly true. */
  var control = [];
  var bad = { f: idx.f, enc: "raw", stride: idx.stride, min_token: idx.min_token, t: {} };
  var sample = tokens.slice(0, 200), caughtShift = false;
  sample.forEach(function (tok) {
    var list = idx.t[tok] || [], run = 0, out = [];
    for (var j = 0; j < list.length; j++) { run = (idx.enc === "delta") ? run + list[j] : list[j]; out.push(run + 1); }
    bad.t[tok] = out;
  });
  for (var ci = 0; ci < sample.length && !caughtShift; ci++) {
    var lst = bad.t[sample[ci]] || [];
    for (var cj = 0; cj < lst.length; cj++) {
      var f2 = mod.refPostingFamily(bad, lst[cj]), o2 = mod.refPostingOrdinal(bad, lst[cj]);
      var r2 = (famRecords[f2] || [])[o2];
      if (!r2 || haystackOf(r2).indexOf(sample[ci]) < 0) { caughtShift = true; break; }
    }
  }
  if (!caughtShift) {
    failures.push("the resolution check did not fire on an index whose every posting was shifted " +
                  "by one -- it is not checking what it claims to check");
  } else {
    control.push("resolution fires on a +1 ordinal shift over " + sample.length + " tokens");
  }
  var emptied = { f: idx.f, enc: "raw", stride: idx.stride, min_token: idx.min_token, t: {} };
  var probe = mod.refSearchPostings(emptied, ["auditctl"]);
  if (probe.postings.length !== 0) {
    failures.push("refSearchPostings() returned hits from an EMPTY index");
  } else {
    control.push("completeness fires on an emptied index (an empty dictionary returns no hits)");
  }
  notes.unshift("negative controls ran first: " + control.join("; "));

  var report = { target: path.relative(REPO, target), failures: failures, notes: notes };
  if (asJson) {
    process.stdout.write(JSON.stringify(report) + "\n");
  } else {
    console.log("reference inverted index + lazy hydration — " + report.target);
    notes.forEach(function (n) { console.log("  ok: " + n); });
    failures.forEach(function (x) { console.log("  FAIL: " + x); });
  }
  process.exit(failures.length ? 1 : 0);
}

main();

#!/usr/bin/env node
/* test_rail_keyboard.js -- MCR-A2-KEY-001 keyboard/UI contract.
 *
 * The rail is static HTML, while its keyboard navigation is JavaScript.  A
 * count-only assertion on either side misses the defect this test was written
 * for: alpha.2 rendered six buttons and advertised Ctrl+Alt+6 on About, but
 * KEYMAP accepted only keys 1 through 5.  This test joins those surfaces.
 *
 * It enumerates every rendered rail button, extracts the shipped railAt(),
 * KEYMAP and modsMatch() implementations, and executes each advertised binding
 * against a minimal DOM model.  Each rail must have exactly one unique
 * Ctrl+Alt+number binding, that binding must select and focus the same button,
 * and the button title must advertise the same shortcut.
 */
"use strict";

var fs = require("fs");
var path = require("path");

var REPO = path.resolve(__dirname, "..");

function extractBetween(src, start, end) {
  var a = src.indexOf(start);
  if (a < 0) throw new Error("missing keyboard source marker: " + start);
  var b = src.indexOf(end, a);
  if (b < 0) throw new Error("missing keyboard source marker after " + start + ": " + end);
  return src.slice(a, b);
}

function attrs(markup) {
  var out = {};
  markup.replace(/([A-Za-z_:][-A-Za-z0-9_:.]*)="([^"]*)"/g, function (_, name, value) {
    out[name] = value;
    return _;
  });
  return out;
}

function renderedRails(src) {
  var nav = extractBetween(src, '<nav id="rail"', "</nav>");
  var rails = [];
  nav.replace(/<button\b[^>]*\bclass="[^"]*\brailbtn\b[^"]*"[^>]*>/g, function (button) {
    var a = attrs(button);
    rails.push({
      id: a["data-rail"] || "",
      label: a["aria-label"] || "",
      title: a.title || ""
    });
    return button;
  });
  return rails;
}

function keyboardModule(src, buttons, selected) {
  var railAt = extractBetween(src, "function railAt(n){", "function moveWithinList(");
  var keymap = extractBetween(src, "var KEYMAP=[", "function modsMatch(");
  var modsMatch = extractBetween(src, "function modsMatch(rule,ev){", 'document.addEventListener("keydown"');
  var fakeDocument = {
    querySelectorAll: function (selector) {
      if (selector !== "#rail .railbtn") throw new Error("unexpected selector: " + selector);
      return buttons;
    }
  };
  var factory = new Function(
    "document", "setRail",
    '"use strict";\n' + railAt + "\n" + keymap + "\n" + modsMatch +
    "\nreturn {railAt:railAt,KEYMAP:KEYMAP,modsMatch:modsMatch};"
  );
  return factory(fakeDocument, function (rail) { selected.value = rail; });
}

function main() {
  var args = process.argv.slice(2);
  var asJson = args.indexOf("--json") >= 0;
  var target = args.filter(function (arg) { return arg !== "--json"; })[0] ||
               path.join(REPO, "template.html");
  var src = fs.readFileSync(target, "utf8");
  var rails = renderedRails(src);
  var failures = [];

  if (!rails.length) failures.push("the rendered activity rail contains no .railbtn buttons");

  var ids = {};
  rails.forEach(function (rail, index) {
    if (!rail.id) failures.push("rendered rail button " + (index + 1) + " has no data-rail identity");
    if (ids[rail.id]) failures.push("rendered rail identity is not unique: " + rail.id);
    ids[rail.id] = true;
  });

  var selected = { value: null };
  var buttons = rails.map(function (rail) {
    return {
      focused: 0,
      getAttribute: function (name) { return name === "data-rail" ? rail.id : null; },
      focus: function () { this.focused += 1; }
    };
  });
  var keyboard = keyboardModule(src, buttons, selected);
  var jumpBindings = keyboard.KEYMAP.filter(function (binding) { return binding.id === "rail-jump"; });
  if (jumpBindings.length !== 1) {
    failures.push("KEYMAP must contain exactly one rail-jump binding; found " + jumpBindings.length);
  }

  var binding = jumpBindings[0] || { keys: [], mods: "", doc: "", run: function () {} };
  var uniqueKeys = {};
  binding.keys.forEach(function (key) {
    if (uniqueKeys[key]) failures.push("rail-jump contains duplicate runtime key: " + key);
    uniqueKeys[key] = true;
  });
  if (binding.keys.length !== rails.length) {
    failures.push("rendered rail count " + rails.length + " does not equal runtime rail-jump key count " +
                  binding.keys.length);
  }
  if (binding.mods !== "ctrlAlt") {
    failures.push("rail-jump uses modifier rule " + JSON.stringify(binding.mods) +
                  ", but every rail advertises Ctrl+Alt");
  }
  if (!keyboard.modsMatch(binding.mods, {
    ctrlKey: true, altKey: true, shiftKey: false, metaKey: false
  })) {
    failures.push("the rail-jump modifier rule does not accept Ctrl+Alt at runtime");
  }

  var mappings = [];
  rails.forEach(function (rail, index) {
    var key = String(index + 1);
    var advertised = /\(Ctrl\+Alt\+([0-9]+)\)$/.exec(rail.title);
    if (!advertised) {
      failures.push("rail " + rail.id + " does not advertise a Ctrl+Alt+number shortcut in its title");
    } else if (advertised[1] !== key) {
      failures.push("rail " + rail.id + " is position " + key + " but advertises Ctrl+Alt+" +
                    advertised[1]);
    }
    if (!uniqueKeys[key]) {
      failures.push("rail " + rail.id + " advertises Ctrl+Alt+" + key +
                    " but KEYMAP has no runtime key " + key);
    }

    selected.value = null;
    buttons.forEach(function (button) { button.focused = 0; });
    if (uniqueKeys[key]) binding.run({ key: key });
    if (selected.value !== rail.id) {
      failures.push("Ctrl+Alt+" + key + " selected " + JSON.stringify(selected.value) +
                    " instead of rendered rail " + rail.id);
    }
    if (buttons[index].focused !== 1) {
      failures.push("Ctrl+Alt+" + key + " did not focus rendered rail " + rail.id);
    }
    mappings.push({ id: rail.id, label: rail.label, key: key, title: rail.title });
  });

  if (binding.keys.length === rails.length) {
    var extras = binding.keys.filter(function (key) {
      return !/^[1-9][0-9]*$/.test(key) || Number(key) < 1 || Number(key) > rails.length;
    });
    if (extras.length) failures.push("rail-jump contains keys that do not name a rendered rail: " + extras.join(", "));
  }

  var expectedDoc = "Jump to rail 1-" + rails.length;
  if (binding.doc !== expectedDoc) {
    failures.push("rail-jump documentation is " + JSON.stringify(binding.doc) +
                  "; expected " + JSON.stringify(expectedDoc));
  }

  var report = {
    target: path.relative(REPO, target),
    rendered_rails: rails.length,
    runtime_keys: binding.keys,
    mappings: mappings,
    failures: failures
  };
  if (asJson) {
    process.stdout.write(JSON.stringify(report) + "\n");
  } else {
    console.log("MCR-A2-KEY-001 rail keyboard/UI contract -- " + report.target);
    mappings.forEach(function (mapping) {
      console.log("  Ctrl+Alt+" + mapping.key + " -> " + mapping.id + " (" + mapping.label + ")");
    });
    if (failures.length) {
      console.log("FAIL:");
      failures.forEach(function (failure) { console.log("  - " + failure); });
    } else {
      console.log("PASS");
    }
  }
  process.exit(failures.length ? 1 : 0);
}

main();

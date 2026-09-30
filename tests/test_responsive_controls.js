#!/usr/bin/env node
/* Direct UI contract for the alpha.6 responsive shell controls.
 *
 * This executes the shipped action router and status/palette focus helpers
 * against a deliberately small DOM model. Source-only string assertions would
 * prove that labels exist, but not that a click reaches the intended action,
 * pressed state follows body state, or replacing the status bar keeps focus.
 */
"use strict";

var fs = require("fs");
var path = require("path");

var REPO = path.resolve(__dirname, "..");

function extractBetween(src, start, end) {
  var a = src.indexOf(start);
  if (a < 0) throw new Error("missing source marker: " + start);
  var b = src.indexOf(end, a);
  if (b < 0) throw new Error("missing source marker after " + start + ": " + end);
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

function actionRouterContract(src, failures) {
  var code = extractBetween(src, "function routeChromeAction(action){", "/* ============ one delegated click router");
  var calls = [];
  var route = new Function(
    "openPalette", "togglePanel", "THEME",
    '"use strict";\n' + code + "\nreturn routeChromeAction;"
  )(
    function () { calls.push("palette"); },
    function (which) { calls.push("panel:" + which); },
    {toggle: function () { calls.push("theme"); }}
  );
  [
    ["palette", true, "palette"],
    ["panel-sidebar", true, "panel:sidebar"],
    ["panel-inspector", true, "panel:inspector"],
    ["theme", true, "theme"],
    ["copy", false, null]
  ].forEach(function (row) {
    calls.length = 0;
    var handled = route(row[0]);
    if (handled !== row[1]) failures.push("route " + row[0] + " returned " + handled);
    if ((calls[0] || null) !== row[2]) failures.push("route " + row[0] + " called " + JSON.stringify(calls));
  });
  if (src.indexOf("if(routeChromeAction(action)) return;") < 0) {
    failures.push("delegated click router does not call routeChromeAction");
  }
}

function statusContract(src, failures) {
  var code = extractBetween(src, "function focusedStatusAction(){", "/* ============ CR-T-29");
  var doc = {activeElement: null};
  var bodyAttrs = {"data-sidebar": "on", "data-inspector": "on"};
  doc.body = {
    getAttribute: function (name) { return bodyAttrs[name] || null; }
  };

  function makeButton(markup, text) {
    var a = attrs(markup);
    return {
      attrs: a,
      text: text.replace(/<[^>]+>/g, ""),
      focusCount: 0,
      getAttribute: function (name) { return this.attrs[name] || null; },
      focus: function () { this.focusCount += 1; doc.activeElement = this; }
    };
  }

  var status = {
    nodes: [],
    contains: function (node) { return this.nodes.indexOf(node) >= 0; },
    querySelectorAll: function (selector) {
      if (selector !== "[data-action]") throw new Error("unexpected selector " + selector);
      return this.nodes;
    }
  };
  Object.defineProperty(status, "innerHTML", {
    set: function (html) {
      this.html = html;
      this.nodes = [];
      var re = /(<button\b[^>]*>)([\s\S]*?)<\/button>/g;
      var match;
      while ((match = re.exec(html))) this.nodes.push(makeButton(match[1], match[2]));
    },
    get: function () { return this.html || ""; }
  });

  function el(id) {
    if (id !== "statusbar") throw new Error("unexpected element " + id);
    return status;
  }
  doc.activeElement = doc.body;
  var themeMode = "light";
  var api = new Function(
    "document", "el", "STATE", "stigReleaseLabel", "esc", "escapeAttr",
    "APP_NAME", "APP_VERSION", "APP_BUILD_DATE", "APP_CLASSIFICATION",
    "entryById", "verificationStatusForVersion", "THEME",
    '"use strict";\n' + code +
    "\nreturn {renderStatusBar:renderStatusBar,focusedStatusAction:focusedStatusAction};"
  )(
    doc, el, {toast: "", version: "9", entryId: null},
    function () { return "STIG V2R9"; }, function (v) { return String(v); },
    function (v) { return String(v); }, "MD CODE RED", "test", "2026-09-30", "LAB",
    function () { return null; }, function () { return {}; },
    {resolved: function () { return themeMode; }}
  );

  function byAction(action) {
    return status.nodes.filter(function (node) { return node.attrs["data-action"] === action; })[0];
  }

  api.renderStatusBar();
  var sidebar = byAction("panel-sidebar");
  var inspector = byAction("panel-inspector");
  if (!sidebar || !inspector || !byAction("theme")) failures.push("status controls did not render");
  if (sidebar && (sidebar.attrs["aria-pressed"] !== "true" || sidebar.text.indexOf("Navigator: On") < 0)) {
    failures.push("sidebar on state is not synchronized in text and aria-pressed");
  }
  if (sidebar && sidebar.attrs["aria-label"].indexOf(sidebar.text) < 0) {
    failures.push("sidebar accessible name does not contain its visible label");
  }
  if (inspector && (inspector.attrs["aria-pressed"] !== "true" || inspector.text.indexOf("Inspector: On") < 0)) {
    failures.push("inspector on state is not synchronized in text and aria-pressed");
  }
  if (inspector && inspector.attrs["aria-label"].indexOf(inspector.text) < 0) {
    failures.push("inspector accessible name does not contain its visible label");
  }

  sidebar.focus();
  bodyAttrs["data-sidebar"] = "off";
  api.renderStatusBar();
  var sidebarAfter = byAction("panel-sidebar");
  if (doc.activeElement !== sidebarAfter || sidebarAfter.focusCount !== 1) {
    failures.push("sidebar control did not retain focus across status rerender");
  }
  if (sidebarAfter.attrs["aria-pressed"] !== "false" || sidebarAfter.text.indexOf("Navigator: Off") < 0) {
    failures.push("sidebar off state is not synchronized in text and aria-pressed");
  }

  byAction("panel-inspector").focus();
  bodyAttrs["data-inspector"] = "off";
  api.renderStatusBar();
  var inspectorAfter = byAction("panel-inspector");
  if (doc.activeElement !== inspectorAfter || inspectorAfter.attrs["aria-pressed"] !== "false" ||
      inspectorAfter.text.indexOf("Inspector: Off") < 0) {
    failures.push("inspector off state/focus did not survive status rerender");
  }

  byAction("theme").focus();
  themeMode = "dark";
  api.renderStatusBar();
  var themeAfter = byAction("theme");
  if (doc.activeElement !== themeAfter || themeAfter.text.indexOf("Theme: Dark") < 0) {
    failures.push("theme state/focus did not survive status rerender");
  }
  if (themeAfter.attrs["aria-label"].indexOf(themeAfter.text) < 0) {
    failures.push("theme accessible name does not contain its visible label");
  }
}

function paletteFocusContract(src, failures) {
  var code = extractBetween(src, "function openPalette(){", "/* A search-index hit");
  var opener = {focusCount: 0, focus: function () { this.focusCount += 1; }};
  var search = {focusCount: 0, focus: function () { this.focusCount += 1; }};
  var input = {
    value: "", focusCount: 0, attrs: {},
    focus: function () { this.focusCount += 1; },
    setAttribute: function (name, value) { this.attrs[name] = String(value); },
    removeAttribute: function (name) { delete this.attrs[name]; }
  };
  var palette = {hidden: true};
  var doc = {
    activeElement: opener,
    body: {},
    documentElement: {contains: function (node) { return node === opener; }},
    querySelector: function (selector) { return selector === ".quicksearch" ? search : null; }
  };
  function el(id) { return id === "palette" ? palette : input; }
  var STATE = {paletteOpen: false, paletteSel: -1};
  var api = new Function(
    "document", "el", "STATE", "renderPalette", "PALETTE_OPENER",
    '"use strict";\n' + code + "\nreturn {openPalette:openPalette,closePalette:closePalette};"
  )(doc, el, STATE, function () {}, null);

  api.openPalette();
  api.closePalette();
  if (opener.focusCount !== 1) failures.push("palette cancel did not restore its opener");

  doc.activeElement = opener;
  api.openPalette();
  api.closePalette(false);
  if (opener.focusCount !== 1) failures.push("palette activation path incorrectly restored old focus");
}

function main() {
  var target = process.argv[2] || path.join(REPO, "template.html");
  var src = fs.readFileSync(target, "utf8");
  var failures = [];
  actionRouterContract(src, failures);
  statusContract(src, failures);
  paletteFocusContract(src, failures);
  process.stdout.write(JSON.stringify({target: path.relative(REPO, target), failures: failures}) + "\n");
  process.exit(failures.length ? 1 : 0);
}

main();

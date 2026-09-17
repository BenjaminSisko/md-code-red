# Code Standards & Security Patterns

Every line of code in MD CODE RED must follow these mandatory patterns. Violations block build and merge.

---

## 1. Output Encoding at Every Render Boundary

**Mandatory.** Every value rendered into the DOM must be escaped per its context.

### Functions (Required in every build)

```javascript
function esc(str) {
  // HTML entity encoding: < > & " '
  return String(str).replace(/[&<>"']/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[ch]));
}

function escapeHtml(str) { /* alias for esc() */ }
function escapeAttr(str) { /* use in href, data-*, style attribute values */ }
function escapeRegex(str) { /* for use in dynamic RegExp() calls */ }
```

### Usage

- **HTML content:** `element.textContent = esc(userValue)`; never `.innerHTML`
- **Attributes:** `element.setAttribute('title', escapeAttr(userValue))`
- **URLs:** `element.href = sanitizeUrl(userValue)` (no javascript: scheme)
- **Regex patterns:** `new RegExp(escapeRegex(userPattern))`
- **Properties are written out, not computed** — `el.innerHTML = …`, never
  `el["innerHTML"] = …` and never a property name assembled from pieces. A
  computed property assignment is allowed only where the gate can read the
  property expression: an identifier, a number, or a dotted/indexed chain
  (`out[fields[i].name] = …` is fine, and is real code in `template.html`).

### What Q17 does and does not prove (MCR-SEC-014, condition D2)

Q17's render-sink inventory is an **accident-prevention** gate: it exists so the
next render path somebody writes by hand during CR-T-25/26/27/30 cannot become
an XSS path by mistake, in code `CODEOWNERS` reviews before it merges.

It reads the source. It catches every sink spelling this product could plausibly
grow — `.innerHTML` assigned or read, `+=`, derived accumulators to a fixed
point, `insertAdjacentHTML`, `outerHTML`, `document.write`,
`createContextualFragment`, `srcdoc`, `setAttribute` with a dangerous or
unreadable name, and (since MCR-SEC-014) bracketed sink names and sink names
fused out of string literals inline, through a variable, or across statements.

It is **not a sandbox**. A property name produced at run time from something that
is not a string literal — characters from a code-point array, a value read out of
the content island — is invisible to any scan of the source, and no regex gate
can see it. That residual is stated here, and printed by the gate itself in its
PASS output, rather than being left implicit: a gate described as unbypassable is
worse than one whose limits are written down, because the first one stops being
questioned.

---

## 2. Input Validation at Boundaries

**Mandatory.** Validate at form submission and before any operation.

- Required fields must not be empty
- RHEL version must be in [7, 8, 9, 10]
- STIG IDs must match pattern `RHEL-\d{2}-\d{6}`
- No command template is rendered until all required fields are filled

---

## 3. No Inline Event Handlers

**Mandatory.** No `onclick=""`, `onchange=""`, etc. in HTML. Use `addEventListener()` only.

### Correct
```javascript
button.addEventListener('click', (e) => { /* handler */ });
```

### Incorrect (forbidden)
```html
<button onclick="doThing()">Click</button>
```

---

## 4. Store Raw, Render Safe

**Mandatory.** Raw data (JSON entries, user input) stored unescaped; escaped only at render time.

### Correct
```javascript
// Store raw
const entry = { tool: 'firewall-cmd', desc: 'Add a <rule>' };
// Render safe
element.textContent = esc(entry.desc);
```

### Incorrect (forbidden)
```javascript
// Pre-escape in storage (breaks search, export)
const entry = { desc: 'Add a &lt;rule&gt;' };
```

---

## 5. Air-Gap Rules

**Mandatory.** Every line of code must support offline-only operation.

### Forbidden
- No `fetch()`, `XMLHttpRequest()`, or WebSocket connections
- No external `<link rel="stylesheet" href="https://...">`
- No external `<script src="https://...">`
- No CDN references (cdnjs, googleapis, jsdelivr, unpkg)
- No image external URLs (embed as data:image/png;base64,...)

### Exceptions
- URLs in comments or string literals are OK if they're never executed
- Internal URLs like `#command-123` are OK

---

## 6. Version & Build Metadata Block

**Mandatory.** Every build must include this block immediately after `<!DOCTYPE html>`.

```html
<!DOCTYPE html>
<!-- MD CODE RED
     APP_VERSION: 0.1.0-sketch
     APP_BUILD_DATE: 2026-09-17
     APP_NAME: MD CODE RED — RHEL Admin Toolkit
     RHEL_VERSIONS: 7, 8, 9, 10
     BUILD_CLEAN: YES
     AIR_GAP_VERIFIED: YES (when built)
-->
```

---

## 7. Constants at Top Level

**Mandatory.** Accessible to QA and build verification scripts.

```javascript
const APP_VERSION = '0.1.0-sketch';
const APP_BUILD_DATE = '2026-09-17';
const APP_NAME = 'MD CODE RED';
const RHEL_VERSIONS = [7, 8, 9, 10];
const FEATURE_FLAGS = {
  commandBuilder: true,
  stigExport: true,
  ansibleGenerator: false, // P1 feature
};
```

---

## 8. Content Schema Validation

**Mandatory.** Every content entry must have these fields and pass validation before build.

```javascript
// Minimum entry schema
{
  id: 'cmd-systemctl-enable',           // Unique ID
  tool: 'systemctl',                    // Tool name
  rhel: [7, 8, 9, 10],                  // Supported versions (subset OK)
  action: 'Enable service on boot',     // One-line description
  command: 'systemctl enable SERVICE',  // Command template
  flags: [                              // Required flags
    { flag: 'SERVICE', desc: 'Service name (e.g., sshd)' }
  ],
  optional: [],                         // Optional parameters
  stigIds: ['RHEL-09-xxxxxx'],         // If compliance-related
  nistControls: ['AC-17', 'CM-6'],    // If compliance-related
  expectedOutput: '...',                // Expected result
  source: {
    title: 'Red Hat RHEL 9 Admin Guide',
    url: 'https://access.redhat.com/...',
    verified: '2026-09-10',
    verifiedBy: 'SME Name'
  }
}
```

---

## 9. Testing & QA Gates

**Mandatory.** All code passes before merge.

- **Syntax:** `node --check` on final file
- **Air-gap:** Grep for `http`, `fetch`, `cdn` — must be zero
- **Encoding:** Spot-check 10 commands for proper escaping
- **Storage:** Verify localStorage only, no server calls

---

## Violations

Any deviation from these standards blocks:
- Pull request merge
- Build assembly
- QA sign-off
- Release

Report violations to Zee (Engineering) and Marcus (Security). Repeat violations trigger security review.

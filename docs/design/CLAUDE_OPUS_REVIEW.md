# Independent Claude Opus Review — PR #17

**Review date:** 2026-09-30
**Reviewer runtime:** Claude Code 2.1.233
**Requested model:** Opus, maximum effort
**Verified model:** `claude-opus-5-5`
**Scope:** Read-only review of `codex/alpha6-responsive-ux` at commit `510c9a0` against `main`
**Repository:** `BenjaminSisko/md-code-red`

> This file preserves the independent review output. The reviewer was restricted from editing, writing, committing, pushing, or posting comments.

# PR #17 final review: `codex/alpha6-responsive-ux` @ 510c9a0 vs `main`

## 1. Executive verdict: REQUEST CHANGES

The fixes needed are small. The layout-state cascade and the release archival are correct. The problem is that the new toggle buttons drop keyboard focus every time someone uses them, which is the main accessibility claim this PR makes. The new shortcut hint also fails text contrast, and no tests cover any of the new UI. I'd approve once the three pre-merge items in §7 land.

## 2. Findings

| # | Sev | Location | Evidence | User impact | Remediation |
|---|---|---|---|---|---|
| H1 | **High** | `template.html:5149-5158`, `5420`, `5486-5487`, `3594` | `renderStatusBar()` rebuilds the whole status bar with `el("statusbar").innerHTML=parts.join("")`. This PR makes `togglePanel()` call it (5420) and sends the new status-bar buttons there (5486-5487). Pressing Enter or Space on **Navigator**, **Inspector** or **Theme** deletes the focused button, so focus falls back to `<body>`. The Theme button already did this before the PR; the PR copies the pattern onto two new controls. | Keyboard and screen-reader users lose their place after every toggle. The new `aria-pressed` state is never announced on the button they pressed, so the claim in CHANGELOG and USER_GUIDE that the pressed state tells you whether the panel is open doesn't hold for them. In practice this is a WCAG 2.4.3 failure. | Change the three buttons in place (`setAttribute("aria-pressed",…)`, `textContent`). Or: before the innerHTML write, save the `data-action` of the focused element inside `#statusbar`, and afterwards refocus the matching button. Add a regression test. |
| M1 | Medium | `template.html:119`, `111-112` (tokens at `27`, `43`/`51`) | The new `.quicksearch kbd` hint ("Ctrl K", 10px) uses `--text-muted` #8494ab on `--bg-editor` #f6f8fa, about 2.9:1. Dark mode (#71717a on #0a0e15) is about 4.0:1. The new `.railbrand small` tagline (9px) is about 3.1:1 light and 3.7:1 dark; it may count as part of the logo, which is exempt. | New text fails WCAG 1.4.3, and the 9–10px sizes make it worse. On touch devices the "Ctrl K" hint means nothing. | Use `--text-secondary` (about 6:1) at 11px or more. Hide the `kbd` at ≤720px. Darkening `--text-muted` app-wide is a separate follow-up, since that problem predates this PR. |
| M2 | Medium | `tests/`, `qa.py`, `tools/` | Searching all three for `skiplink`, `quicksearch`, `panel-sidebar`, `panel-inspector`, `panelbtn`, `railbrand`, `max-width:720` and `Search all` finds nothing. The only test change is a regenerated evidence fixture. | The recorded 402 tests and 26 gates don't exercise any of the new UI, which is how H1 got through. The grid-state matrix and action routing have no protection against future changes. | Add tests for: (a) every `data-action` has a route; (b) `aria-pressed` matches `body[data-*]` after each toggle; (c) focus stays on the button after a toggle; (d) the skip-link target is `<main>`; (e) in each grid-state rule, the number of rows equals the number of rows in the template areas. |
| M3 | Medium | `template.html:304` (sticky rail), `339`→`366` | At ≤720px `#rail` is `position:sticky; top:0; z-index:20` and about 52px tall. There is no `scroll-padding` or `scroll-margin` anywhere in the file. The skip-link jump puts the top of `#editor` (blast banner, title) at the top of the screen, under the rail. Shift+Tab scrolling has the same problem. | Likely fails WCAG 2.2 **2.4.11 Focus Not Obscured (Minimum)** on phones. The missing CSS is proven; the actual overlap needs a browser to confirm. | Add `@media (max-width:720px){html{scroll-padding-top:64px}}` and confirm on a device. |
| M4 | Medium | `template.html:5254-5260`, `348` | `closePalette()` always focuses the first button in `#editor-card`, not the element that opened the palette. The new visible **Search all** button therefore never gets focus back after Escape. | Keyboard users land somewhere unexpected in the editor. On mobile the page also scrolls away from the rail. This breaks the standard dialog pattern of returning focus to the opener. The logic predates the PR, but the PR makes Search all a main entry point. | Save `document.activeElement` in `openPalette()` and restore it on Escape/cancel. Keep the editor-card target only for when a result is chosen. |
| L1 | Low | `template.html:110` | `.railbrand strong span{color:var(--danger)}` | The logo red uses the same color token as destructive and critical warnings. A red element that is always on screen teaches users to ignore red, and any later change to the danger color also changes the logo. | Add a separate `--brand` token and keep `--danger` for danger only. |
| L2 | Low | `template.html:162`, `5150-5155` | Only the text and border color change when a panel button is pressed. The Theme button shows its state in text ("Theme: Dark"). The accessible name "Show or hide the command navigator" contains the visible word "Navigator" but doesn't start with it. | Relies on color alone (WCAG 1.4.1 risk, softened because the panel itself appears or disappears). In Windows forced-colors mode the pressed state becomes invisible. The Theme and panel buttons use different patterns. | Show "Navigator: On/Off" or add bold text or a check mark. Rename to "Navigator panel". |
| L3 | Low | `template.html:345` | `aria-label` on a plain `<div>` with no role; ARIA 1.2 prohibits this. The document has no `<h1>` anywhere. | Some assistive tech ignores the label, and axe reports `aria-prohibited-attr`. The page has no top-level heading. | Remove the `aria-label` and make the brand the page's `<h1>` (it can look the same). |
| L4 | Low | `template.html:339` vs `366`; print `328-334` | The skip link says "command workspace" but the landmark is named "Editor". `#editor` has no `tabindex="-1"`. The print CSS doesn't hide `.skiplink`. | Screen-reader users hear two names for the same place. | Use one name for both. Add `tabindex="-1"` to `#editor` and hide `.skiplink` in print. |
| L5 | Low | `template.html:304-312`, `318-319` | On phones the rail scrolls sideways with no visual hint that there is more, and the brand takes at least 116px. The Navigator and Inspector buttons sit at the very bottom of the single-column page. | Phone users may not find the rail destinations that start off-screen. Hiding the 42vh navigator means scrolling past the whole page first. | Shrink or drop the brand at ≤720px, add an edge fade, and move the panel toggles into the sticky rail on mobile. |
| L6 | Low | `template.html:135`, `312` | The current-rail tint is hard-coded as `rgba(180,83,9,.10)`, the light-theme accent color. | In dark mode the tint is a muddy brown unrelated to `--accent` #f59e0b. | Make it a token and redefine it in the dark theme blocks. |
| L7 | Low | `releases/README.md:14` | The row says the alpha.5 provenance is "preserved byte-for-byte" under the immutable tag. But `git diff -M v1.0.0-alpha.5 HEAD` shows `provenance.json` differs by one line (it was stamped after the tag, in 78ac717). The alpha.2 row describes the same situation accurately. | The provenance record states something that isn't literally true. | Reuse the alpha.2 wording ("post-tag-stamped … from `main`"). |
| L8 | Low | `README.md:14`; `docs/USER_GUIDE.md` front matter | `Last built: 2026-09-22`, but `build.py:39` is `2026-09-30`. USER_GUIDE was edited but `last_verified` still says `2026-09-22`. | Docs disagree with the build, and no QA gate catches it. | Update the dates or generate them from `release-facts.json`. |

**Note on typography:** `--font-ui` (`template.html:31`) replaces the system font stack. Windows and macOS will now render Trebuchet MS, while RHEL will render Liberation Sans. Instructor screenshots will differ from what students see. I'm not raising this as a defect.

## 3. Strengths

- **Layout states are correct.** At ≤1024px all four sidebar/inspector on/off combinations are defined (`template.html:75-88`), and each has as many rows as its template areas. At ≤720px all four are overridden (`298-302`) by selectors of equal specificity that come later in the file, so they win. The tablet "empty inspector row" bug is actually fixed.
- **No routing conflicts.** The new action names are unique, and `data-action="palette"` appears only at `348`. The routes for acknowledgement (`ack`, `ref-ack`) and copy are untouched.
- **New rail items don't interfere.** `renderRail()` (`3927-3931`) and the Ctrl+Alt+N shortcut (`5570`) both select only `#rail .railbtn`, so the new brand and search elements are never overwritten or counted as rail destinations.
- **Air-gap and security are unchanged.** No `url()` or `@font-face` was added; fonts are local family names only. The CSP (`19`) is unchanged. The new attributes are inserted through `escapeAttr`, keeping the audited sink shape.
- **Real touch-target gains:** 40px rail buttons, 36px status buttons, and 40px toolbar buttons at the phone breakpoints.

## 4. Verified facts

- The archived alpha.5 HTML and its `.sha256` sidecar are **byte-identical to tag `v1.0.0-alpha.5`** (e299102): git reports them as 100% renames with zero changed lines.
- The dev artifact's sidecar and provenance file agree: sha256 `f0f6b372…59eb`, 8,897,770 bytes. The artifact contains the new markup (skip link at `dist/…alpha.6-dev.html:339`) and the title `v1.0.0-alpha.6-dev`.
- The content fingerprint changed (`41fb7c…` → `004b46…`), and that is expected: `build.py:105-106` puts the version and build date into a hashed payload (`460`).
- There is no `hashchange` or `location.hash` handling anywhere, so the `#editor` skip-link fragment can't disturb app state.
- The evidence modal (z-index 60) and palette (50) sit above the sticky rail (20).

## 5. Assumptions and limitations

- The sandbox blocked `shasum` and `git tag`, so I couldn't recompute the SHA-256 digests myself. Integrity rests on git's byte-identity against the tag and on the sidecar and provenance agreeing.
- Contrast ratios are hand-calculated from the CSS color tokens using the WCAG formula, roughly ±0.1.
- I did no live browser or assistive-technology testing. H1 and M4 are proven by reading the code; M3 and L5 are risks until checked in a browser.
- I accepted the recorded QA, unit-test and hostile-harness results and did not read the embedded data.
- Three accessibility problems predate this PR and are out of scope, but will affect any AT testing:
  - The whole `#editor-card` is a polite live region (`368`), so screen readers may read too much on every update.
  - Toasts aren't announced, because `#statusbar` is `contentinfo` rather than a live region (`394`, `3613-3616`).
  - The palette's Tab trap wasn't audited.

## 6. Browser and assistive-technology checks

1. **H1:** Firefox ESR with NVDA, and Chrome with JAWS. Tab to Navigator and press Space. Expected: focus stays on the button and "toggle button, not pressed" is announced. Currently focus goes to the document. Repeat for Inspector and Theme.
2. **M3:** iPhone Safari with VoiceOver at 390×844. Activate the skip link: is the blast banner or title hidden under the rail? Then Shift+Tab back through the editor controls.
3. **M4:** Tap or click Search all, then press Escape. Focus should return to Search all.
4. **Reflow:** Chrome at 320px, and at 1280px with 400% zoom. At ≤720px `#editor` is `overflow:visible` (`314`). Code blocks scroll on their own (`177`, `189`, `226`), but `.compare` tables (`293`) have no scroll wrapper and may make the whole page scroll sideways.
5. **Tablet matrix:** At 768×1024 and 1024×768, try all four Ctrl+B / Ctrl+I combinations. Check for empty tracks or rows and that sticky positioning isn't used here.
6. **Zoom at 200% on a 1280px screen** (switches to the phone layout): does the sticky rail plus the 42vh navigator leave enough room for the editor?
7. **Windows forced colors / high contrast:** can you still see the Navigator/Inspector pressed state (L2) and the current rail item?
8. **Speech input** (Dragon, macOS Voice Control): say "click Navigator" and "click Search all".
9. **Print from Chromium on A4:** the printable width (about 718px) triggers the ≤720px rules. Confirm the output matches alpha.5 and the skip link doesn't print.
10. **Touch:** swiping the rail sideways must not trigger the browser's back-swipe (`overscroll-behavior-x:contain`) on iOS Safari or Android Chrome.

## 7. Merge recommendation

**Before merging:**
1. Fix H1 so focus stays on the Navigator, Inspector and Theme buttons.
2. Fix M1: switch the shortcut hint to `--text-secondary` and enlarge the 9–10px text.
3. Add the M2 minimum: tests for `aria-pressed` sync, focus retention, and every `data-action` having a route.

**Follow-ups (before tagging alpha.6, not blocking this dev merge):**
- M3: add `scroll-padding` and run check 2.
- M4: return palette focus to its opener.
- L1–L6: separate brand token, pressed-state design, heading and landmark naming, mobile rail and toggle placement, dark-mode tint.
- L7 and L8: fix the doc wording and dates. These are one-line edits and could go into the same fix commit.

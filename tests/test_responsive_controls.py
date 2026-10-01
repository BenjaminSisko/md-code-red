#!/usr/bin/env python3
"""Accessibility contract for the alpha.6 responsive application shell."""

import json
import os
import re
import shutil
import subprocess
import unittest


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(REPO, "template.html")
SCRIPT = os.path.join(REPO, "tests", "test_responsive_controls.js")


def contrast(foreground, background):
    def luminance(value):
        value = value.lstrip("#")
        rgb = [int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)]
        linear = [
            channel / 12.92
            if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
            for channel in rgb
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    first, second = luminance(foreground), luminance(background)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


class ResponsiveControlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(TEMPLATE, encoding="utf-8") as handle:
            cls.source = handle.read()

    def test_runtime_routes_pressed_state_and_focus(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node is required to execute the shipped UI helpers")
        proc = subprocess.run(
            [node, SCRIPT, TEMPLATE],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        try:
            report = json.loads(proc.stdout.decode("utf-8"))
        except ValueError as exc:
            self.fail(
                "responsive control harness returned no JSON: %s\n%s"
                % (exc, proc.stderr.decode("utf-8", "replace"))
            )
        self.assertEqual(report["failures"], [])
        self.assertEqual(proc.returncode, 0)

    def test_shell_has_one_h1_and_specific_landmarks(self):
        self.assertEqual(len(re.findall(r"<h1\b", self.source)), 1)
        for marker in (
            'aria-label="Primary navigation"',
            'aria-label="Command navigator"',
            'aria-label="Command workspace" tabindex="-1"',
            'aria-label="Command safety and evidence"',
            'aria-label="Application status and controls"',
        ):
            self.assertIn(marker, self.source)

    def test_skip_target_accounts_for_sticky_navigation_and_print(self):
        mobile = self.source[self.source.index("@media (max-width:720px)") :]
        self.assertRegex(mobile, r"#editor\{[^}]*scroll-margin-top:132px")
        print_css = self.source[self.source.index("@media print") :]
        self.assertRegex(print_css, r"\.skiplink,#rail,#sidebar")

    def test_brand_and_selected_tint_are_semantic_theme_tokens(self):
        self.assertIn("--brand:#991b1b; --selected-fill:rgba(180,83,9,.10);", self.source)
        self.assertGreaterEqual(
            self.source.count("--brand:#f87171; --selected-fill:rgba(245,158,11,.14);"),
            2,
        )
        self.assertIn(".railbrand h1 span{color:var(--brand);}", self.source)
        self.assertIn("background:linear-gradient(90deg,var(--selected-fill),transparent 75%)", self.source)
        self.assertIn(".railbtn[aria-current=\"true\"]{background:var(--selected-fill);}", self.source)

    def test_new_brand_and_discovery_text_meet_normal_text_contrast(self):
        # These are the actual light/dark token pairs used by the brand,
        # tagline and visible search shortcut. The assertions document the
        # minimum instead of treating a color-name check as an accessibility
        # test.
        for foreground, background in (
            ("#991b1b", "#ffffff"),
            ("#f87171", "#18181b"),
            ("#51607a", "#ffffff"),
            ("#51607a", "#f6f8fa"),
            ("#a1a1aa", "#18181b"),
            ("#a1a1aa", "#0a0e15"),
            ("#53657d", "#ffffff"),
            ("#53657d", "#f6f8fa"),
            ("#a1a1aa", "#09090b"),
        ):
            self.assertGreaterEqual(contrast(foreground, background), 4.5)
        self.assertRegex(
            self.source,
            r"\.railbrand small\{[^}]*color:var\(--text-secondary\)[^}]*font-size:11px",
        )
        self.assertRegex(self.source, r"\.quicksearch\{[^}]*font-size:13px")
        self.assertRegex(
            self.source,
            r"\.quicksearch kbd\{[^}]*font-size:11px; color:var\(--text-secondary\)",
        )

    def test_focus_tokens_meet_non_text_contrast(self):
        self.assertGreaterEqual(contrast("#a16207", "#ffffff"), 3.0)
        self.assertGreaterEqual(contrast("#fbbf24", "#18181b"), 3.0)
        self.assertGreaterEqual(contrast("#047857", "#ffffff"), 4.5)
        self.assertIn(
            'id=\\"gen-announcement\\" class=\\"sr-only\\" '
            'aria-live=\\"polite\\" aria-atomic=\\"true\\"',
            self.source,
        )
        gen_result = self.source.split('id=\\"gen-result\\"', 1)[1].split(">", 1)[0]
        self.assertNotIn("aria-live", gen_result)

    def test_panel_state_is_exposed_without_color(self):
        self.assertIn('"\\">Navigator: "+esc(sidebarOn?"On":"Off")', self.source)
        self.assertIn('"\\">Inspector: "+esc(inspectorOn?"On":"Off")', self.source)
        self.assertIn(".panelbtn[aria-pressed=\"true\"]", self.source)

    def test_form_changes_refresh_inspector_and_status_verification(self):
        handler = re.search(
            r"function onFieldChange\(ev\)\{(?P<body>[\s\S]*?)\n\}", self.source
        )
        self.assertIsNotNone(handler)
        body = handler.group("body")
        self.assertIn("renderInspector();", body)
        self.assertIn("renderStatusBar();", body)


if __name__ == "__main__":
    unittest.main()

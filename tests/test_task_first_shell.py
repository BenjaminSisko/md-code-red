#!/usr/bin/env python3
"""Contracts for the task-centered Home and focused command workspace."""

from pathlib import Path
import re
import unittest
import qa


REPO = Path(__file__).resolve().parents[1]
SRC = (REPO / "template.html").read_text(encoding="utf-8")


def function_body(name):
    text, error = qa.extract_js_function(SRC, name)
    if error:
        raise AssertionError(error)
    return text


class TaskFirstShellTests(unittest.TestCase):
    def test_home_is_the_default_and_first_keyboard_destination(self):
        self.assertIn('rail:"favorites"', SRC)
        nav = SRC[SRC.index('<nav id="rail"'):SRC.index("</nav>")]
        rails = re.findall(r'class="railbtn" data-rail="([^"]+)"', nav)
        self.assertEqual(rails[0], "favorites")
        self.assertIn('aria-label="Home" title="Home (Ctrl+Alt+1)"', nav)

    def test_home_offers_reviewed_outcomes_and_explains_the_library_boundary(self):
        home = function_body("renderHome")
        for text in (
            "What do you need to do?",
            "Common RHEL tasks",
            "Operate a host",
            "Automate a change",
            "Learn and teach",
            "Reviewed catalog",
            "Reference Library",
        ):
            self.assertIn(text, home)
        self.assertIn("gen-lsblk-inspect-storage", home)

    def test_build_catalog_does_not_render_mined_reference_rows(self):
        build = function_body("renderToolList")
        self.assertNotIn("refCommandsForTool", build)
        self.assertNotIn('data-ref=\\"', build)
        library = function_body("renderReferenceSidebar")
        self.assertIn('data-ref=\\"', library)

    def test_guided_builder_has_stages_fields_and_command_review(self):
        editor = function_body("renderGeneratorEditor")
        self.assertIn("1 Configure", editor)
        self.assertIn("2 Review", editor)
        self.assertIn("3 Verify", editor)
        self.assertIn('class=\\"builderfields\\"', editor)
        self.assertIn('class=\\"commandreview\\"', editor)
        result = function_body("renderGeneratorResult")
        self.assertIn("Command preview", result)
        self.assertIn("Copy command", result)
        self.assertIn("Review runbook: Preflight, Run, Verify, Recover", result)

    def test_field_teaching_is_progressively_disclosed(self):
        form = function_body("renderGeneratorForm")
        self.assertIn("Why this field?", form)
        self.assertIn("<details>", form)
        self.assertIn("teaching.meaning", form)

    def test_mobile_navigation_wraps_and_command_review_precedes_fields(self):
        mobile = SRC[SRC.index("@media (max-width:720px)"):SRC.index("@media (max-width:440px)")]
        self.assertIn("flex-wrap:wrap", mobile)
        self.assertIn("overflow-x:visible", mobile)
        self.assertIn('body[data-selection-open="true"]', mobile)
        self.assertIn('grid-template-areas:"rail" "editor" "sidebar" "inspector" "status"', mobile)
        self.assertIn(".commandreview{order:1", mobile)
        self.assertIn(".builderfields{order:2", mobile)
        render_all = function_body("renderAll")
        self.assertIn('setAttribute("data-selection-open"', render_all)

    def test_search_and_evidence_overlays_expose_focus_contracts(self):
        self.assertRegex(SRC, r'id="palette-input"[^>]*role="combobox"')
        self.assertIn('aria-autocomplete="list"', SRC)
        self.assertIn('aria-activedescendant', function_body("renderPalette"))
        self.assertIn("setEvidenceBackgroundInert(true)", function_body("exportEvidence"))
        self.assertIn("setEvidenceBackgroundInert(false)", function_body("closeEvidenceModal"))
        self.assertIn("EVIDENCE_OPENER", function_body("closeEvidenceModal"))


if __name__ == "__main__":
    unittest.main()

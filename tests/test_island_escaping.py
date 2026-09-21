#!/usr/bin/env python3
"""test_island_escaping.py — the data island cannot break out of its <script> (MCR-SEC-007).

Run with either:
    python3 -m unittest discover -s tests
    python3 tests/test_island_escaping.py

The inherited escaping was `payload.replace("</", "<\\/")`. That closes
`</script>` and nothing else: a payload carrying `<!--` followed by `<script`
(neither has a slash) puts the HTML tokeniser into script-data-double-escaped
state, where `</script>` stops terminating the element. The island's closing tag,
the app script after it, and the "Not built yet" fallback inside that script are
then all swallowed as text — the page stops at "Reading the embedded content
island." with no error, which on a jump box mid-task is a denial of use.

DISA XCCDF fix text is embedded verbatim, so `<!--<script` is a content value
away, not an attack away.

The control runs first: the real build must still produce a parsing island.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import build  # noqa: E402
import qa     # noqa: E402

HOSTILE = "<!--<script>alert(1)</script>--> and a bare </script> for good measure"


class EscapeIslandIsReversible(unittest.TestCase):
    """Control first: escaping that loses data would be a worse bug than the one it fixes."""

    def test_round_trip_through_json(self):
        payload = {"rule": {"fix": HOSTILE}, "note": "a > b and a < b"}
        text = build.escape_island(json.dumps(payload, ensure_ascii=False))
        self.assertEqual(payload, json.loads(text), "escaping changed the parsed value")

    def test_no_html_significant_character_survives(self):
        text = build.escape_island(json.dumps({"fix": HOSTILE}, ensure_ascii=False))
        for bad in ("<", ">", "</script", "<!--", "-->", "<script"):
            self.assertNotIn(bad, text, "%r survived the island escaping" % bad)


class TheGateCanFail(unittest.TestCase):
    """A gate that has never been seen to fail is not a gate."""

    def test_an_unescaped_island_fails_the_q1_assertion(self):
        unescaped = json.dumps({"fix": HOSTILE}, ensure_ascii=False)
        failures = qa.island_escape_failures(unescaped)
        self.assertTrue(failures, "a raw '<' in the island was not flagged")
        self.assertIn("MCR-SEC-007", " ".join(failures))

    def test_the_old_escaping_still_fails_the_assertion(self):
        """The exact rule this finding replaced: `</` only."""
        old = json.dumps({"fix": HOSTILE}, ensure_ascii=False).replace("</", "<\\/")
        self.assertTrue(qa.island_escape_failures(old),
                        "the pre-MCR-SEC-007 escaping was rated clean; the assertion is not "
                        "measuring what the finding was about")

    def test_a_properly_escaped_island_is_clean(self):
        good = build.escape_island(json.dumps({"fix": HOSTILE}, ensure_ascii=False))
        self.assertEqual([], qa.island_escape_failures(good))


class ABuildWithHostileContentStillWorks(unittest.TestCase):
    """End to end: `<!--<script` in a rule's text must produce a working artifact."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="mcr-island-")
        shutil.copy(os.path.join(REPO, "build.py"), cls.tmp)
        shutil.copy(os.path.join(REPO, "template.html"), cls.tmp)
        os.makedirs(os.path.join(cls.tmp, "extract"))
        shutil.copy(os.path.join(REPO, "extract", "schema.py"), os.path.join(cls.tmp, "extract"))
        shutil.copytree(os.path.join(REPO, "content"), os.path.join(cls.tmp, "content"))

        # plant the hostile sequence in a rule's title, which is embedded verbatim
        rules_path = os.path.join(cls.tmp, "content", "rules_rhel9.json")
        with open(rules_path, encoding="utf-8") as f:
            rules = json.load(f)
        rules["rules"][0]["t"] = rules["rules"][0]["t"] + " " + HOSTILE
        cls.planted = rules["rules"][0]["t"]
        with open(rules_path, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False)

        proc = subprocess.run([sys.executable, os.path.join(cls.tmp, "build.py")], cwd=cls.tmp,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        cls.rc = proc.returncode
        cls.out = proc.stdout.decode("utf-8", "replace")
        dist = os.path.join(cls.tmp, "dist")
        artifacts = ([name for name in os.listdir(dist) if name.endswith(".html")]
                     if os.path.isdir(dist) else [])
        cls.artifact = os.path.join(dist, artifacts[0]) if len(artifacts) == 1 else None

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_build_succeeded(self):
        self.assertEqual(0, self.rc, "build failed on hostile content:\n" + self.out)

    def test_the_artifact_has_one_closing_script_per_opening_one(self):
        with open(self.artifact, encoding="utf-8") as f:
            html = f.read()
        self.assertEqual(html.count("<script"), html.count("</script>"),
                         "the island swallowed a script boundary")
        island = re.search(r'<script id="mcr-data" type="application/json">(.*?)</script>',
                           html, re.S).group(1)
        self.assertEqual([], qa.island_escape_failures(island))
        data = json.loads(island)
        titles = [r["t"] for r in data["rules"]["9"]["rules"]]
        self.assertIn(self.planted, titles,
                      "the hostile text did not survive as DATA — escaping must be reversible, "
                      "not lossy")


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""test_dist_integrity.py -- AL-GATE3-001-class fail-open in qa.py's artifact
selection.

DECISION_LOG 2026-09-17/18 records three incidents from the same root cause:
find_artifact() globbed dist/ for anything named `md-code-red_*.html` and
took whichever name sorted last. Twice that produced a false FAIL (a stale
v1.0.0-dev sidecar sorted after the real build and got gated instead of it).
The third time is the dangerous direction, never yet caught by a test: a
stale artifact -- left behind by a hand copy, an old branch, a sidecar
export -- that happens to sort last AND carries the CURRENT version string
would pass Q1's five-way version check exactly as well as the fresh build
does, because Q1 only checks that the file it was HANDED is internally
consistent. It never asks whether that file is the one build.py just wrote.
That is the fail-open AL-GATE3-001 named, and CI has never watched it fail.

This file proves two things the old glob-and-sort-last code could not:

1. find_artifact() returns the exact file build.py's own APP_VERSION names
   -- never whatever a directory listing happens to sort last -- so a stale
   file cannot be selected no matter how it is named or how new it looks.
2. dist_integrity_failures() refuses to let qa.py proceed at all when
   dist/ holds anything else shaped like an artifact or sidecar, or when
   the correctly-named artifact is older than something it should have been
   built from -- named, with a message telling the operator to clean it,
   not a silent pass.

qa.REPO / qa.DIST / qa.CONTENT are patched at a scratch directory per case
(same idiom as tests/test_q16_receipts.py's qa.REPO patch), so these run in
milliseconds against no real build.

Run with either:
    python3 -m pytest tests/test_dist_integrity.py
    python3 tests/test_dist_integrity.py
"""

import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import qa  # noqa: E402

APP_VERSION = "v1.0.0-alpha.1"

BUILD_PY_STUB = (
    'APP_NAME = "MD CODE RED"\n'
    'APP_VERSION = "%s"\n'
    'CLASSIFICATION = "UNCLASSIFIED"\n'
) % APP_VERSION


class DistIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.mkdtemp(prefix="mcr-dist-integrity-")
        self.addCleanup(shutil.rmtree, self.scratch, ignore_errors=True)
        self.dist = os.path.join(self.scratch, "dist")
        self.content = os.path.join(self.scratch, "content")
        os.makedirs(self.dist)
        os.makedirs(self.content)
        with open(os.path.join(self.scratch, "build.py"), "w", encoding="utf-8") as f:
            f.write(BUILD_PY_STUB)
        with open(os.path.join(self.scratch, "template.html"), "w", encoding="utf-8") as f:
            f.write("<html>/*__DATA__*/</html>")
        for name, target in (("REPO", self.scratch), ("DIST", self.dist), ("CONTENT", self.content)):
            p = mock.patch.object(qa, name, target)
            p.start()
            self.addCleanup(p.stop)

    def _write(self, name, text, mtime=None):
        path = os.path.join(self.dist, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        if mtime is not None:
            os.utime(path, (mtime, mtime))
        return path

    # -- the fail-open itself -------------------------------------------

    def test_stale_artifact_carrying_the_current_version_does_not_win(self):
        """The DECISION_LOG 2026-09-17 finding: a stale sidecar file, named
        so it sorts AFTER the real artifact and ALSO carries the current
        version string (exactly the hand-copied '*.main.html' shape the CEO
        hit), must never be what selection hands back -- even though
        nothing about its own filename looks wrong in isolation, and even
        though the old code's `sorted(...)[-1]` picks it every time."""
        fresh_name = "md-code-red_%s.html" % APP_VERSION
        stale_name = "md-code-red_%s.main.html" % APP_VERSION
        # Confirms the attack shape: alphabetically, the stale sidecar sorts
        # after the real artifact ("...alpha.1.html" vs "...alpha.1.main.html"
        # -- 'm' > 'h' right after the shared "alpha.1." prefix), which is
        # exactly what let the old sorted(...)[-1] pick it.
        self.assertGreater(stale_name, fresh_name)
        now = time.time()
        fresh_path = self._write(
            fresh_name,
            'FRESH_BUILD_MARKER var APP_VERSION="%s"' % APP_VERSION,
            mtime=now,
        )
        self._write(
            stale_name,
            'STALE_CONTENT_FROM_AN_OLD_BRANCH var APP_VERSION="%s"' % APP_VERSION,
            mtime=now - 3600,
        )

        artifact = qa.find_artifact()

        self.assertEqual(
            artifact, fresh_path,
            "find_artifact() selected %r instead of the fresh build %r -- a stale "
            "artifact carrying the current version string was validated instead of "
            "what build.py just produced (AL-GATE3-001 fail-open)"
            % (artifact, fresh_path),
        )

    # -- dirty dist/ is refused, named, before gating proceeds -----------

    def test_dirty_dist_is_refused_by_name(self):
        self._write("md-code-red_%s.html" % APP_VERSION, "FRESH")
        stray = "md-code-red_v1.0.0-dev.main.html"
        self._write(stray, "OLD DEV BUILD")

        failures = qa.dist_integrity_failures()

        self.assertTrue(failures, "a stray dist/ file produced no failures")
        self.assertTrue(
            any(stray in msg for msg in failures),
            "no failure named the stray file %r: %r" % (stray, failures),
        )

    def test_stray_sidecar_is_refused_even_with_no_extra_html(self):
        self._write("md-code-red_%s.html" % APP_VERSION, "FRESH")
        stray_sidecar = "md-code-red_v1.0.0-dev.html.sha256"
        self._write(stray_sidecar, "deadbeef  md-code-red_v1.0.0-dev.html\n")

        failures = qa.dist_integrity_failures()

        self.assertTrue(
            any(stray_sidecar in msg for msg in failures),
            "no failure named the stray sidecar %r: %r" % (stray_sidecar, failures),
        )

    def test_clean_dist_produces_no_failures(self):
        self._write("md-code-red_%s.html" % APP_VERSION, "FRESH")

        self.assertEqual(qa.dist_integrity_failures(), [])

    def test_the_artifacts_own_sidecars_are_not_strays(self):
        """build.py writes <artifact>.sha256 right next to the artifact, and
        make_provenance.py writes <version>.provenance.json -- neither is a
        stray; a fix that flagged the build's own paperwork as dirty would
        make every real build FAIL, which is worse than the bug it closes."""
        self._write("md-code-red_%s.html" % APP_VERSION, "FRESH")
        self._write("md-code-red_%s.html.sha256" % APP_VERSION, "deadbeef  md-code-red.html\n")
        self._write("md-code-red_%s.provenance.json" % APP_VERSION, "{}")

        self.assertEqual(qa.dist_integrity_failures(), [])

    # -- a correctly-named but stale artifact is refused by mtime ---------

    def test_stale_mtime_is_refused(self):
        content_file = os.path.join(self.content, "commands.json")
        with open(content_file, "w", encoding="utf-8") as f:
            f.write("{}")
        old = time.time() - 3600
        artifact_path = self._write("md-code-red_%s.html" % APP_VERSION, "OLD BUILD", mtime=old)
        # Touch the content input AFTER the artifact was "built" -- the
        # artifact now predates something build.py should have baked in.
        os.utime(content_file, None)

        failures = qa.dist_integrity_failures()

        self.assertTrue(
            any("older" in msg.lower() or "predates" in msg.lower() for msg in failures),
            "a stale-but-correctly-named artifact was not refused: %r" % (failures,),
        )
        # And the artifact is still the one selection hands back -- staleness
        # is a build_ctx()-level refusal to proceed, not a different pick.
        self.assertEqual(qa.find_artifact(), artifact_path)


if __name__ == "__main__":
    unittest.main()

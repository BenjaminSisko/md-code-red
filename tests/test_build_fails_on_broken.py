#!/usr/bin/env python3
"""build.py must fail loud on broken content — and must still build the real content.

Run with either:
    python3 -m pytest tests/
    python3 tests/test_build_fails_on_broken.py

Stdlib only, no pytest required. Each case copies template.html, build.py and the
real content/ into a scratch tree, overlays one deliberately broken commands.json
from tests/fixtures/broken-content/, and asserts the build exits non-zero with the
message that names the actual defect. The healthy control runs first: a failing
test that has never been seen to pass on good input proves nothing.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(REPO, "tests", "fixtures", "broken-content")

# fixture file -> a substring that must appear in the failure output
CASES = [
    ("commands_missing_rhel_key.json", "rhel_versions missing RHEL key(s) 7"),
    ("commands_dangling_stig.json", "does not resolve to a record in rules_rhel9.json"),
    ("commands_missing_provenance.json", "missing provenance field source.url_or_man"),
    ("commands_verified_without_receipt.json", "verified['10'] is set but has no 'on'"),
    ("commands_unavailable_empty_reason.json", "unavailable has an empty reason"),
    ("commands_same_as_cycle.json", "same_as cycle"),
    # MCR-SEC-003: a header-bound string that is not single-line fails the BUILD,
    # so it can never reach the clipboard comment header in the first place.
    ("commands_multiline_intent.json", "intent contains the control character U+000D"),
    # MCR-SEC-006: template flag and lit tokens reach the command line unquoted, so
    # the generator/spec shape is validated at build time as well as at run time.
    ("commands_spec_flag_injection.json", "is not an option token"),
    ("commands_spec_lit_injection.json", "reaches the command line unquoted"),
]


def scratch_repo(tmp, broken=None):
    """A minimal buildable tree: build.py + extract/schema.py + template.html + content/.

    extract/schema.py comes along because build.py imports the schema from there
    rather than carrying its own copy (CR-T-06). Nothing else in extract/ is
    needed: the build reads content/, never stig-src/.
    """
    shutil.copy(os.path.join(REPO, "build.py"), tmp)
    shutil.copy(os.path.join(REPO, "template.html"), tmp)
    os.makedirs(os.path.join(tmp, "extract"))
    shutil.copy(os.path.join(REPO, "extract", "schema.py"), os.path.join(tmp, "extract"))
    shutil.copytree(os.path.join(REPO, "content"), os.path.join(tmp, "content"))
    if broken:
        shutil.copy(os.path.join(FIXTURES, broken), os.path.join(tmp, "content", "commands.json"))
    return tmp


def run_build(tmp):
    proc = subprocess.run([sys.executable, os.path.join(tmp, "build.py")], cwd=tmp,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


class BuildValidation(unittest.TestCase):

    def test_00_real_content_builds(self):
        """Control: the real content/ must build cleanly in the same scratch harness."""
        tmp = tempfile.mkdtemp(prefix="mcr-ok-")
        try:
            scratch_repo(tmp)
            code, out = run_build(tmp)
            self.assertEqual(code, 0, "real content failed to build:\n" + out)
            self.assertTrue(
                os.path.exists(os.path.join(tmp, "dist")),
                "build produced no dist/ directory:\n" + out)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_broken_fixtures_fail_the_build(self):
        for fixture, expect in CASES:
            with self.subTest(fixture=fixture):
                tmp = tempfile.mkdtemp(prefix="mcr-broken-")
                try:
                    scratch_repo(tmp, broken=fixture)
                    code, out = run_build(tmp)
                    self.assertNotEqual(code, 0, "%s built successfully; it must not:\n%s" % (fixture, out))
                    self.assertIn(expect, out,
                                  "%s failed for the wrong reason; expected %r in:\n%s"
                                  % (fixture, expect, out))
                finally:
                    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)

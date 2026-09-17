#!/usr/bin/env python3
"""test_provenance_manifest.py -- REL-2026-09-18-001 item 4.

extract/make_provenance.py emits dist/md-code-red_<version>.provenance.json
claiming, among other things, the built artifact's own sha256 and content
fingerprint. A provenance manifest whose own headline claims do not match the
artifact it describes is worse than no manifest -- it would be trusted and
wrong. This test runs the real script against the real built artifact (same
idiom as test_evidence_export_real.py: shell out to the real tool over real
committed content, never re-implement it) and checks the two claims that
matter most independently, the same way qa.py's build_ctx() would: re-hash
the artifact file and the bytes inside its own <script id="mcr-data"> island,
and compare both to what the manifest says.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(REPO, "dist")
SCRIPT = os.path.join(REPO, "extract", "make_provenance.py")


def find_artifact():
    if not os.path.isdir(DIST):
        return None
    cands = sorted(f for f in os.listdir(DIST) if f.startswith("md-code-red_") and f.endswith(".html"))
    return os.path.join(DIST, cands[-1]) if cands else None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def content_fingerprint(artifact_path):
    with open(artifact_path, encoding="utf-8") as f:
        html = f.read()
    m = re.search(r'<script id="mcr-data" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        raise AssertionError("no mcr-data island found in %s" % artifact_path)
    return hashlib.sha256(m.group(1).encode("utf-8")).hexdigest()


class ProvenanceManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        artifact = find_artifact()
        if not artifact:
            raise unittest.SkipTest("no dist/md-code-red_*.html -- run python3 build.py first "
                                    "(the manifest is generated FROM a build, it does not build "
                                    "anything itself)")
        cls.artifact_path = artifact
        cls.expected_sha256 = sha256_file(artifact)
        cls.expected_fingerprint = content_fingerprint(artifact)

        manifest_path = os.path.join(
            DIST, os.path.basename(artifact).replace(".html", ".provenance.json"))
        proc = subprocess.run([sys.executable, SCRIPT],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO)
        cls.rc = proc.returncode
        cls.stderr = proc.stderr.decode("utf-8", "replace")
        cls.manifest_path = manifest_path
        if os.path.exists(manifest_path):
            with open(manifest_path, encoding="utf-8") as f:
                cls.manifest = json.load(f)
        else:
            cls.manifest = None

    def test_script_succeeds_and_writes_the_manifest(self):
        self.assertEqual(self.rc, 0, self.stderr)
        self.assertIsNotNone(self.manifest, "make_provenance.py did not write %s"
                             % os.path.relpath(self.manifest_path, REPO))

    def test_manifest_artifact_sha256_matches_the_built_artifact(self):
        self.assertEqual(self.manifest["artifact"]["sha256"], self.expected_sha256)
        self.assertEqual(self.manifest["artifact"]["filename"], os.path.basename(self.artifact_path))

    def test_manifest_content_fingerprint_matches_the_data_island(self):
        self.assertEqual(self.manifest["content_fingerprint"], self.expected_fingerprint)

    def test_manifest_reports_a_git_commit_field(self):
        # Not reproducible before the tag exists (this worktree's HEAD is a
        # release-branch commit, not the merge commit that gets tagged) -- the
        # placeholder is the documented, honest default. The field must exist
        # and must not be silently empty.
        self.assertTrue(self.manifest.get("git_commit"))

    def test_manifest_is_deterministic_except_the_commit_field(self):
        # make_provenance.py always writes to the same path (derived from
        # build.py's APP_VERSION), so this second invocation overwrites the
        # exact file setUpClass already wrote and that other test methods in
        # this class read. Restore the original bytes afterward no matter
        # what -- a test that leaves dist/*.provenance.json mutated with a
        # throwaway "deadbeef..." commit hash would poison the working tree
        # for whatever runs next (a later gate, or `git add` at commit time),
        # which is exactly the kind of self-inflicted drift this repo's own
        # gates (Q21) exist to catch.
        with open(self.manifest_path, "rb") as f:
            original_bytes = f.read()
        try:
            proc = subprocess.run([sys.executable, SCRIPT, "--commit", "deadbeef" * 5],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
            with open(self.manifest_path, encoding="utf-8") as f:
                second = json.load(f)
            first = dict(self.manifest)
            first.pop("git_commit")
            second.pop("git_commit")
            self.assertEqual(first, second,
                             "two runs of make_provenance.py against the same build produced "
                             "different output in a field other than git_commit")
        finally:
            with open(self.manifest_path, "wb") as f:
                f.write(original_bytes)


if __name__ == "__main__":
    unittest.main()

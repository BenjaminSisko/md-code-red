#!/usr/bin/env python3
"""Focused regression tests for release identity and provenance guidance."""

import importlib.util
import hashlib
import json
import os
import re
import shutil
import subprocess
import unittest


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "extract", "make_provenance.py")

spec = importlib.util.spec_from_file_location("make_provenance", SCRIPT)
make_provenance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make_provenance)


def canonical_placeholder_provenance(current_blob, baseline_blob, head="HEAD"):
    """Validate the one permitted post-review manifest stamp and normalize it.

    The release procedure learns the immutable tag-target SHA only after merge.
    That later commit may therefore replace TAG_COMMIT_PLACEHOLDER, but it may
    not change the artifact, sources, review lineage, or release-workstation
    toolchain that the candidate review bound.
    """
    try:
        current=json.loads(current_blob)
        baseline=json.loads(baseline_blob)
    except (TypeError,json.JSONDecodeError) as exc:
        raise ValueError("provenance must be valid JSON") from exc
    if not isinstance(current,dict) or not isinstance(baseline,dict):
        raise ValueError("provenance must be a JSON object")
    commit=current.get("git_commit")
    if commit!=make_provenance.PLACEHOLDER_COMMIT:
        if not isinstance(commit,str) or not re.fullmatch(r"[0-9a-f]{40}",commit):
            raise ValueError("git_commit must be the placeholder or a full lowercase SHA")
        exists=subprocess.run(
            ["git","cat-file","-e",commit+"^{commit}"],cwd=REPO,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        )
        if exists.returncode!=0:
            raise ValueError("stamped git_commit does not resolve to a commit")
        ancestor=subprocess.run(
            ["git","merge-base","--is-ancestor",commit,head],cwd=REPO,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        )
        if ancestor.returncode!=0:
            raise ValueError("stamped git_commit is not an ancestor of the release tree")
    current["git_commit"]=make_provenance.PLACEHOLDER_COMMIT
    baseline["git_commit"]=make_provenance.PLACEHOLDER_COMMIT
    if current!=baseline:
        raise ValueError("stamped provenance changed fields other than git_commit")
    return (json.dumps(current,indent=1,sort_keys=True,ensure_ascii=True)+"\n").encode("utf-8")


class ReleaseReadinessTests(unittest.TestCase):
    def test_review_lineage_is_derived_from_the_requested_version(self):
        version = "v9.8.7-test.6"
        lineage = make_provenance.review_lineage(version)

        self.assertEqual(lineage["release_version"], version)
        self.assertIn(version, lineage["change_record"])
        self.assertEqual(
            lineage["required_release_evidence"],
            [
                "docs/BQP_SUMMARY_%s.md" % version,
                "docs/QA_REPORT_%s.md" % version,
                "docs/SECURITY_REVIEW_%s.md" % version,
                "docs/RELEASE_REPORT_%s.md" % version,
            ],
        )

    def test_review_lineage_does_not_claim_a_historical_release_review(self):
        lineage = make_provenance.review_lineage("v9.8.7-test.6")
        rendered = repr(lineage)

        self.assertNotIn("alpha3_", rendered)
        self.assertNotIn("MCR-A2-KEY-001", rendered)
        self.assertNotIn("46507926500ea92aa8904c6a9d69698e2d3ba705", rendered)
        self.assertIn("must be recorded", lineage["independent_review"])
        self.assertIn("does not itself assert", lineage["independent_review"])

    def test_missing_artifact_guidance_uses_safe_dist_cleanup(self):
        with self.assertRaises(SystemExit) as caught:
            make_provenance.find_artifact("version-that-does-not-exist")

        message = str(caught.exception)
        self.assertIn("git clean -fdx dist", message)
        self.assertNotIn("rm -rf", message)

    def test_bqp_summary_names_the_current_artifact_bytes(self):
        version="v1.0.0-alpha.6"
        artifact=os.path.join(REPO,"dist","md-code-red_%s.html" % version)
        sidecar=artifact+".sha256"
        provenance=os.path.join(REPO,"dist","md-code-red_%s.provenance.json" % version)
        summary_path=os.path.join(REPO,"docs","BQP_SUMMARY_%s.md" % version)
        with open(artifact,"rb") as fh:
            blob=fh.read()
        with open(sidecar,"rb") as fh:
            sidecar_blob=fh.read()
        with open(provenance,"rb") as fh:
            provenance_blob=fh.read()
        provenance_rel=os.path.relpath(provenance,REPO)
        with open(os.path.join(REPO,"docs","qa","QA_RESULTS_%s-rc.json" % version),
                  encoding="utf-8") as fh:
            implementation_source=json.load(fh)["meta"]["commit"]
        baseline=subprocess.run(
            ["git","show",implementation_source+":"+provenance_rel],cwd=REPO,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,
        ).stdout
        normalized_provenance=canonical_placeholder_provenance(
            provenance_blob,baseline)
        with open(summary_path,encoding="utf-8") as fh:
            summary=fh.read()
        fingerprint=re.search(
            rb"Content fingerprint \(SHA-256 of every data island\): ([0-9a-f]{64})",blob)
        self.assertIsNotNone(fingerprint)
        for expected in (
            format(len(blob),","),
            hashlib.sha256(blob).hexdigest(),
            fingerprint.group(1).decode("ascii"),
            hashlib.sha256(sidecar_blob).hexdigest(),
            hashlib.sha256(normalized_provenance).hexdigest(),
        ):
            self.assertIn(expected,summary)

    def test_html_report_cites_only_recorded_browser_assertions(self):
        base=os.path.join(REPO,"docs","qa")
        with open(os.path.join(base,"QA_RESULTS_v1.0.0-alpha.6-rc.json"),encoding="utf-8") as fh:
            standalone=json.load(fh)
        with open(os.path.join(base,"QA_RESULTS_v1.0.0-alpha.6-rc-http.json"),encoding="utf-8") as fh:
            http=json.load(fh)
        with open(os.path.join(base,"QA_REPORT_v1.0.0-alpha.6-rc.html"),encoding="utf-8") as fh:
            report=fh.read()
        recorded={row["id"] for row in standalone["results"]}|{row["id"] for row in http["results"]}
        cited=set(re.findall(r"TC-[A-Za-z0-9_-]+",report))
        self.assertEqual(cited-recorded,set(),"HTML report cites nonexistent browser assertions")

    def test_browser_results_and_release_docs_bind_to_current_candidate(self):
        version="v1.0.0-alpha.6"
        artifact=os.path.join(REPO,"dist","md-code-red_%s.html" % version)
        with open(artifact,"rb") as fh:
            blob=fh.read()
        artifact_hash=hashlib.sha256(blob).hexdigest()
        fingerprint=re.search(
            rb"Content fingerprint \(SHA-256 of every data island\): ([0-9a-f]{64})",blob)
        self.assertIsNotNone(fingerprint)
        fingerprint=fingerprint.group(1).decode("ascii")
        modes=[]
        implementation_sources=[]
        for suffix in ("", "-http"):
            path=os.path.join(REPO,"docs","qa",
                              "QA_RESULTS_%s-rc%s.json" % (version,suffix))
            with open(path,encoding="utf-8") as fh:
                result=json.load(fh)
            self.assertEqual(result["meta"].get("artifactBytes"),len(blob),path)
            self.assertEqual(result["meta"].get("artifactSha256"),artifact_hash,path)
            self.assertEqual(result["meta"].get("contentFingerprint"),fingerprint,path)
            self.assertEqual(result["summary"]["total"],len(result["results"]),path)
            self.assertEqual(result["summary"]["pass"],len(result["results"]),path)
            self.assertEqual(result["summary"]["fail"],0,path)
            self.assertEqual(result["exceptions"],[],path)
            self.assertEqual(result["consoleErrors"],[],path)
            self.assertTrue(all(row["status"]=="PASS" for row in result["results"]),path)
            modes.append({row["id"] for row in result["results"]})
            implementation_sources.append(result["meta"].get("commit"))
        self.assertEqual(modes[0],modes[1],"browser modes did not run the same assertion IDs")
        self.assertEqual(len(set(implementation_sources)),1,
                         "browser modes name different implementation commits")
        implementation_source=implementation_sources[0] or ""
        self.assertRegex(implementation_source,r"^[0-9a-f]{40}$")
        subprocess.run(["git","cat-file","-e",implementation_source+"^{commit}"],
                       cwd=REPO,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        protected=("template.html","content","extract","build.py","qa.py","tools/qa",
                   "tests","dist",":(exclude)dist/*.provenance.json",
                   ".forgejo/workflows")
        unchanged=subprocess.run(
            ["git","diff","--quiet",implementation_source+"..HEAD","--",*protected],
            cwd=REPO,
        )
        self.assertEqual(unchanged.returncode,0,
                         "implementation files changed after the browser-evidence commit")
        working=subprocess.run(
            ["git","status","--porcelain","--untracked-files=all","--",*protected],
            cwd=REPO,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=True,
        )
        self.assertEqual(working.stdout,"",
                         "protected implementation paths have uncommitted changes:\n"+
                         working.stdout)
        provenance_rel="dist/md-code-red_%s.provenance.json" % version
        provenance_path=os.path.join(REPO,provenance_rel)
        provenance_working=subprocess.run(
            ["git","status","--porcelain","--untracked-files=all","--",provenance_rel],
            cwd=REPO,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=True,
        )
        self.assertEqual(
            provenance_working.stdout,"",
            "the placeholder or stamped provenance must be committed before release gates run",
        )
        with open(provenance_path,"rb") as fh:
            current_provenance=fh.read()
        baseline_provenance=subprocess.run(
            ["git","show",implementation_source+":"+provenance_rel],cwd=REPO,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,
        ).stdout
        canonical_placeholder_provenance(current_provenance,baseline_provenance)
        stamped=json.loads(current_provenance)
        stamped["git_commit"]=subprocess.run(
            ["git","rev-parse","HEAD"],cwd=REPO,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,text=True,check=True,
        ).stdout.strip()
        stamped_blob=(json.dumps(stamped,indent=1,sort_keys=True,ensure_ascii=True)+"\n").encode("utf-8")
        self.assertEqual(
            canonical_placeholder_provenance(stamped_blob,baseline_provenance),
            canonical_placeholder_provenance(current_provenance,baseline_provenance),
            "a documented post-merge git_commit stamp must preserve candidate provenance",
        )
        drifted=json.loads(stamped_blob)
        drifted["toolchain"]["python3"]="0.0-review-drift"
        with self.assertRaisesRegex(ValueError,"other than git_commit"):
            canonical_placeholder_provenance(
                (json.dumps(drifted)+"\n").encode("utf-8"),baseline_provenance)
        nonancestor=json.loads(stamped_blob)
        nonancestor["git_commit"]="0"*40
        with self.assertRaisesRegex(ValueError,"does not resolve"):
            canonical_placeholder_provenance(
                (json.dumps(nonancestor)+"\n").encode("utf-8"),baseline_provenance)
        required=("BQP_SUMMARY_","QA_REPORT_","SECURITY_REVIEW_","RELEASE_REPORT_")
        suite=unittest.defaultTestLoader.discover(
            os.path.join(REPO,"tests"),pattern="test*.py")
        unit_count=suite.countTestCases()
        node=shutil.which("node")
        self.assertIsNotNone(node,"Node is required to derive current harness totals")
        harness=subprocess.run(
            [node,os.path.join(REPO,"tests","hostile_harness.js"),artifact,"--json"],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=True)
        hostile=json.loads(harness.stdout)
        browser_total=len(result["results"])
        verification_line=(
            "Verification totals: %s unit tests; %s hostile-input checks; "
            "%s pipeline checks; %s rendered-browser records in each delivery mode "
            "(896 pass/fail assertions and 2 performance observations)."
            % (format(unit_count,","),format(hostile["checks"],","),
               format(hostile["pipeline_checks"],","),format(browser_total,","))
        )
        for prefix in required:
            path=os.path.join(REPO,"docs",prefix+version+".md")
            with open(path,encoding="utf-8") as fh:
                text=fh.read()
            self.assertEqual(
                text.count(verification_line),1,
                "%s lacks exactly one canonical verification-total line" % path,
            )
            for expected in (format(len(blob),","),artifact_hash,fingerprint,
                             implementation_source):
                self.assertIn(expected,text,
                              "%s is missing release traceability value %s" % (path,expected))


if __name__ == "__main__":
    unittest.main()

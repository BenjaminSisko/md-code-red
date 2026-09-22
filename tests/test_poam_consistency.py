#!/usr/bin/env python3
"""Keep POAM facts that are mechanically derivable aligned with the catalog.

The POAM still contains human decisions which tests must not invent: owners,
acceptance, closure, and scheduling remain documentary authority.  These tests
cover only counts and states already represented by repository data.
"""

import json
import pathlib
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
POAM = (REPO / "docs" / "POAM.md").read_text(encoding="utf-8")


class PoamRepositoryFacts(unittest.TestCase):

    def test_rhel9_capture_and_receipt_claims_match_content(self):
        flags9 = json.loads((REPO / "content" / "flags_rhel9.json").read_text(
            encoding="utf-8"))
        clis = flags9["clis"]
        available = sum(bool(cli.get("available")) for cli in clis.values())
        flag_rows = sum(len(cli.get("flags", [])) for cli in clis.values())

        commands = json.loads((REPO / "content" / "commands.json").read_text(
            encoding="utf-8"))["entries"]
        receipts = [
            (entry["id"], version)
            for entry in commands
            for version, receipt in entry.get("verified", {}).items()
            if isinstance(receipt, dict)
        ]
        rhel9_receipts = [receipt for receipt in receipts if receipt[1] == "9"]

        self.assertIn(
            f"{len(clis)}-tool flag dictionary", POAM,
            "POAM must report the current RHEL 9 dictionary size",
        )
        self.assertIn(
            f"{available} tools available, {flag_rows:,} extracted flag rows", POAM,
            "POAM must report the current RHEL 9 capture coverage",
        )
        self.assertIn(
            f"none of the build's {len(receipts)} QA-reviewed", POAM,
            "POAM must distinguish command receipts from flag captures",
        )
        self.assertEqual([], rhel9_receipts, "update POAM when RHEL 9 gains a receipt")

    def test_flag_curation_denominator_matches_all_release_dictionaries(self):
        total = 0
        curated = 0
        for version in ("7", "8", "9", "10"):
            data = json.loads((REPO / "content" / f"flags_rhel{version}.json").read_text(
                encoding="utf-8"))
            for cli in data["clis"].values():
                flags = cli.get("flags", [])
                total += len(flags)
                curated += sum(bool(flag.get("explain")) for flag in flags)

        self.assertIn(f"{curated} of {total:,} flag-dictionary entries", POAM)

    def test_retired_q20_finding_is_not_listed_as_open(self):
        open_findings = POAM.split("## Open Findings", 1)[1].split(
            "### Example Entry", 1)[0]
        self.assertNotIn("MCR-SEC-020", open_findings)
        self.assertIn("| MCR-SEC-020 |", POAM)
        self.assertIn("**Retired 2026-09-20**", POAM)

    def test_ssp_example_reflects_automated_remediation_without_claiming_closure(self):
        self.assertIn(
            "| SSP-001 | MEDIUM | Input Validation | Zee | "
            "Remediated (awaiting formal closure) |", POAM
        )
        self.assertNotIn("| SSP-001 | MEDIUM | Input Validation | Zee | Open |", POAM)
        self.assertIn(
            "No named security reviewer has recorded formal closure",
            " ".join(POAM.split()),
        )

    def test_unapproved_skeleton_deadlines_are_not_live_targets(self):
        self.assertNotIn("Target: 2026-09-30", POAM)
        self.assertNotIn("Target: 2026-10-31", POAM)


if __name__ == "__main__":
    unittest.main(verbosity=2)

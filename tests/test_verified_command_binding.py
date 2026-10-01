#!/usr/bin/env python3
"""Build-time binding between host receipts and the exact shipped command."""

import json
import os
import unittest

import build


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class VerifiedCommandBindingTests(unittest.TestCase):
    def test_every_embedded_receipt_carries_its_capture_command(self):
        data = build.load_content()
        build.validate(data)
        assembled = build.assemble(data)
        receipts = 0
        for entry in assembled["commands"]["entries"]:
            for version, receipt in (entry.get("verified") or {}).items():
                if not isinstance(receipt, dict):
                    continue
                receipts += 1
                capture_path = os.path.join(ROOT, receipt["capture"])
                with open(capture_path, encoding="utf-8") as handle:
                    capture = json.load(handle)
                self.assertEqual(entry["id"], capture["entry_id"])
                self.assertEqual(version, str(capture["rhel_version"]))
                self.assertEqual(capture["command_as_run"], receipt["command_as_run"])
        self.assertEqual(18, receipts)


if __name__ == "__main__":
    unittest.main()

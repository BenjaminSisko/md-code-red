#!/usr/bin/env python3
"""Q24: execute the shipped governing-quotation eligibility boundary."""
import json
import os
import subprocess
import unittest

import qa

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(REPO, "template.html"), encoding="utf-8") as fh:
    SRC = fh.read()


def quote_function():
    body, err = qa.extract_js_function(SRC, "referenceEvidenceQuote")
    if err:
        raise AssertionError(err)
    return body


def run_js(records, mutate=False):
    safety = "function evidenceLineSafe(x){return x+'changed';}" if mutate else \
             "function evidenceLineSafe(x){return x;}"
    program = "\n".join([
        safety,
        "function refCitationLine(o,m){return 'DISA RHEL '+o.v+' STIG, '+o.s+' ('+o.f+' text, line '+o.l+')';}",
        quote_function(),
        "const rows=" + json.dumps(records, ensure_ascii=True) + ";",
        "console.log(JSON.stringify(rows.map(r=>referenceEvidenceQuote(r,{}))));",
    ])
    proc = subprocess.run(["node", "-e", program], cwd=REPO, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode:
        raise AssertionError(proc.stderr)
    return json.loads(proc.stdout)


class GoverningReferenceEvidence(unittest.TestCase):
    def setUp(self):
        self.base = {"authority": "governing", "verbatim_span": True, "trunc": False,
                     "c": "systemctl is-active firewalld",
                     "o": [{"v": "9", "s": "RHEL-09-251015", "f": "check", "l": 17}]}

    def test_byte_exact_governing_span_exports_as_a_quotation(self):
        out = run_js([self.base])[0]
        self.assertIn(self.base["c"], out)
        self.assertIn("GOVERNING SOURCE QUOTATION", out)
        self.assertIn("RHEL-09-251015", out)

    def test_every_ineligible_shape_is_refused(self):
        rows = []
        for key, value in (("authority", "documentary"), ("verbatim_span", False),
                           ("trunc", True), ("o", [])):
            row = dict(self.base)
            row[key] = value
            rows.append(row)
        self.assertEqual([None, None, None, None], run_js(rows))

    def test_a_line_safety_change_refuses_instead_of_rewriting_source_bytes(self):
        self.assertEqual([None], run_js([self.base], mutate=True))


if __name__ == "__main__":
    unittest.main()

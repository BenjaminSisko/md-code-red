#!/usr/bin/env python3
"""test_positional_crosscheck.py — the exhaustive argument-shift cross-check.

Condition E3 of Marcus Reed's D4 review: after changing the positional
discriminator from a DECLARED one (a `flag` key beside `lit`) to a DERIVED one
(a `lit` matching FLAG_TOKEN_RE is an option), re-run the exhaustive shape
sweep he ran against the D1 fix — extended with option-shaped literals, which
are the shapes the change is about.

What it proves, and what it does not:

  It enumerates every template of 2, 3 and 4 tokens over a kind set that covers
  every shape the product can write — plain literals, conditional argument
  literals, unconditional and conditional OPTION-shaped literals, required and
  optional positional fields, and short and long flag tokens — keeps the ones
  extract/schema.py accepts, and drives the SHIPPED assembler over every one of
  them on all four releases in every supplied/absent combination of the
  droppable fields.

  A VIOLATION is the MCR-SEC-002/013 hazard stated directly: a positional token
  vanishes, a positional token AFTER it survives, and the assembler still
  returns a command — so argument n+1 has been promoted into slot n and
  `chown 'apache' '/var/www'` has silently become `chown '/var/www'`.

  The expectation is computed here, from extract/schema.py's own
  positional_indexes() and token_gate(), and the answer comes from
  template.html's assembler lifted through the harness's purity-checked
  extractor. Neither side restates the other's rule, which is the only way this
  is a cross-check rather than a transcript.

Node is optional in this repo (qa.py's JS gate says so too); without it this
test skips rather than failing a runner that cannot run it.
"""

import itertools
import json
import os
import shutil
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "extract"))
sys.path.insert(0, REPO)

import schema  # noqa: E402

DRIVER = os.path.join(REPO, "tests", "shift_crosscheck_driver.js")

# Four fields, one per droppability shape the assembler distinguishes.
FIELDS = [
    {"name": "m", "type": "integer", "required": False},
    {"name": "p", "type": "path", "required": True},
    {"name": "o", "type": "service", "required": False},
    {"name": "z", "type": "zone", "required": False},
]
FIELDS_BY_NAME = {f["name"]: f for f in FIELDS}

# The eight token kinds. Four carry a literal, because the literal path is what
# MCR-SEC-013, MCR-SEC-018 and MCR-SEC-022 were all about; the other four are
# the field and flag shapes a literal has to coexist with.
KINDS = [
    {"lit": "chmod"},                                   # 0 unconditional literal
    {"lit": "0644", "requires": "m"},                   # 1 conditional ARGUMENT literal
    {"lit": "-P"},                                      # 2 unconditional OPTION literal
    {"lit": "-P", "requires": "m"},                     # 3 conditional OPTION literal
    {"field": "p"},                                     # 4 required positional field
    {"field": "o", "optional": True},                   # 5 optional positional field
    {"flag": "-L", "field": "o", "optional": True},     # 6 optional short flag token
    {"flag": "--zone", "field": "z", "optional": True}, # 7 optional long flag token
]

VALUES = {"m": "7", "p": "/etc/foo", "o": "ssh", "z": "public"}
DROPPABLE = ("m", "o", "z")          # p is required and always supplied


def combos():
    """Every supplied/absent combination of the droppable fields."""
    out = []
    for bits in itertools.product((True, False), repeat=len(DROPPABLE)):
        vals = {"p": VALUES["p"]}
        for name, supplied in zip(DROPPABLE, bits):
            if supplied:
                vals[name] = VALUES[name]
        out.append(vals)
    return out


def token_present(tok, supplied):
    """Mirror of the assembler's tokenPresent() for this fixed field set."""
    req = tok.get("requires")
    if req is not None and req not in supplied:
        return False
    field = tok.get("field")
    if field is None:
        return True
    return field in supplied


def expect_null(template, supplied):
    """Does the assembler have to answer null for this shape and value set?

    Three reasons, in the assembler's own order: a required field with no value,
    every token vanishing (there is no empty command), and the shift rule.
    """
    if "p" not in supplied:
        return True
    positional = set(schema.positional_indexes(template))
    present = [i for i, t in enumerate(template) if token_present(t, supplied)]
    if not present:
        return True
    for i, tok in enumerate(template):
        if token_present(tok, supplied):
            continue
        if i not in positional:
            continue
        for j in range(i + 1, len(template)):
            if j in positional and token_present(template[j], supplied):
                return True
    return False


def accepted_shapes():
    out = []
    for n in (2, 3, 4):
        for combo in itertools.product(range(len(KINDS)), repeat=n):
            template = [dict(KINDS[i]) for i in combo]
            if not any("lit" in t for t in template):
                continue                       # the literal path is what is under test
            if schema.spec_template_errors("shape", template, FIELDS_BY_NAME):
                continue                       # the build refuses it; the run time never sees it
            out.append(template)
    return out


def run_driver(shapes, versions, value_sets, detail=False):
    job = {"fields": FIELDS, "shapes": shapes, "versions": versions,
           "combos": value_sets, "detail": detail}
    proc = subprocess.run([shutil.which("node"), DRIVER], input=json.dumps(job).encode("utf-8"),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise AssertionError("shift_crosscheck_driver.js failed:\n"
                             + proc.stderr.decode("utf-8", "replace"))
    return json.loads(proc.stdout.decode("utf-8"))["results"]


@unittest.skipUnless(shutil.which("node"), "node is not installed on this runner")
class ExhaustiveShiftCrossCheck(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.shapes = accepted_shapes()
        cls.versions = list(schema.VERSIONS)
        cls.combos = combos()
        cls.results = run_driver(cls.shapes, cls.versions, cls.combos)

    def _index(self, s, v, c):
        return (s * len(self.versions) + v) * len(self.combos) + c

    def test_the_sweep_is_large_enough_to_mean_something(self):
        """A cross-check over three shapes proves nothing; state the size."""
        self.assertGreater(len(self.shapes), 1000,
                           "the accepted-shape set collapsed — the schema is refusing almost "
                           "everything, and a sweep over what is left is not a cross-check")
        self.assertEqual(len(self.results),
                         len(self.shapes) * len(self.versions) * len(self.combos))

    def test_no_shape_shifts_an_argument(self):
        """The finding itself: no run may drop a positional and still answer."""
        violations = []
        for s, template in enumerate(self.shapes):
            for v in range(len(self.versions)):
                for c, supplied in enumerate(self.combos):
                    got = self.results[self._index(s, v, c)]
                    self.assertNotEqual(2, got, "the assembler threw on %r" % (template,))
                    want_null = expect_null(template, supplied)
                    if want_null and got == 1:
                        violations.append((template, self.versions[v], supplied, "assembled"))
                    elif not want_null and got == 0:
                        violations.append((template, self.versions[v], supplied, "refused"))
        if violations:
            detail = run_driver([violations[0][0]], [violations[0][1]], [violations[0][2]],
                                detail=True)
            self.fail("%d of %d runs disagree with the shift rule. First:\n"
                      "  template %s\n  RHEL %s, values %s\n  expected %s, assembler produced %r"
                      % (len(violations), len(self.results), json.dumps(violations[0][0]),
                         violations[0][1], json.dumps(violations[0][2]),
                         "null" if violations[0][3] == "assembled" else "a command", detail[0]))

    def test_the_sweep_has_a_healthy_half(self):
        """An assembler that returned null for everything would pass the test above."""
        assembled = sum(1 for r in self.results if r == 1)
        self.assertGreater(assembled, len(self.results) // 10,
                           "almost nothing assembled (%d of %d) — check the healthy case before "
                           "believing the signal" % (assembled, len(self.results)))

    def test_the_two_real_conditional_option_specs_are_accepted(self):
        """E3's named test: the shapes gen-setsebool-set and gen-lvextend-grow write."""
        setsebool = [{"lit": "setsebool"}, {"lit": "-P", "requires": "m"}, {"field": "p"}]
        lvextend = [{"lit": "lvextend"}, {"flag": "-L", "field": "o", "optional": True},
                    {"lit": "-r", "requires": "m"}, {"field": "p"}]
        for template in (setsebool, lvextend):
            self.assertEqual([], schema.spec_template_errors("real", template, FIELDS_BY_NAME),
                             "an option-shaped conditional literal is still refused: %r" % (template,))

    def test_marcus_013_vector_is_still_refused(self):
        """...and the regression to watch for: the same shape with an ARGUMENT literal."""
        template = [{"lit": "chmod"}, {"lit": "0644", "requires": "m"}, {"field": "p"}]
        errs = schema.spec_template_errors("013", template, FIELDS_BY_NAME)
        self.assertTrue(any("conditional POSITIONAL literal" in e for e in errs),
                        "the MCR-SEC-013 vector is no longer refused: %r" % errs)

    def test_a_dual_key_token_is_refused_however_honest(self):
        """MCR-SEC-022: `flag` beside `lit` is gone, including where flag == lit."""
        for lit, flag in (("-P", "-P"), ("0644", "-P"), ("/etc/shadow", "-x")):
            template = [{"lit": "chmod"}, {"lit": lit, "flag": flag, "requires": "m"},
                        {"field": "p"}]
            errs = schema.spec_template_errors("dual", template, FIELDS_BY_NAME)
            self.assertTrue(any("carries both `lit` and `flag`" in e for e in errs),
                            "{lit:%r, flag:%r} was accepted: %r" % (lit, flag, errs))


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""test_ansible_rail.py -- the Ansible rail shows Ansible content, or fails.

Run with either:
    python3 -m unittest discover -s tests
    python3 tests/test_ansible_rail.py

WHY THIS FILE EXISTS. The Founder opened v1.0.0-alpha.1, pressed the Ansible
rail, and got a paragraph beginning "This rail lands with its own task". That
is what "I don't see any git or ansible content" was: not a rendering bug, a
rail wired to a placeholder over a catalog that had no Ansible in it at all.

renderToolList() now slices tools.json by category: the Ansible rail renders
the tools whose category is "ansible", the Command Builder rail renders the
rest. A slice is a silent failure mode -- if the category string drifts on
either side, or the entries stop pointing at those tools, the rail renders an
empty list and says "No tools in this build's content island", which looks
exactly like a build with no content rather than like a bug. These tests are
the tripwire for that, and they are deliberately CONTENT tests (they read
content/*.json, not the built artifact) so they fail at the source rather than
three steps downstream.

They also hold the template to its own copy: the placeholder paragraph the
Founder read must not still claim the Ansible generator is pending work, and
the rail button must still exist to be pressed.
"""
import json
import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMANDS = os.path.join(REPO, "content", "commands.json")
TOOLS = os.path.join(REPO, "content", "tools.json")
TEMPLATE = os.path.join(REPO, "template.html")

ANSIBLE_CATEGORY = "ansible"


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class AnsibleRailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tools = load(TOOLS)["tools"]
        cls.entries = load(COMMANDS)["entries"]
        cls.ansible_tools = [t for t in cls.tools if t.get("category") == ANSIBLE_CATEGORY]
        cls.builder_tools = [t for t in cls.tools if t.get("category") != ANSIBLE_CATEGORY]
        with open(TEMPLATE, encoding="utf-8") as fh:
            cls.template = fh.read()

    def test_the_ansible_slice_is_not_empty(self):
        # AL-GATE3-004 shape: a rail that renders an empty slice passes every
        # other check in this file by having nothing to disagree with.
        self.assertGreater(len(self.ansible_tools), 0,
                           "no tools.json record carries category '%s', so the Ansible rail "
                           "renders 'No tools in this build's content island' -- which is what "
                           "the Founder saw, in a different font" % ANSIBLE_CATEGORY)

    def test_the_builder_slice_is_not_empty_either(self):
        self.assertGreater(len(self.builder_tools), 0,
                           "every tool is categorised 'ansible', so the Command Builder rail is "
                           "now the empty one -- the slice moved the hole, it did not close it")

    def test_every_ansible_tool_has_at_least_one_entry(self):
        by_tool = {}
        for e in self.entries:
            by_tool.setdefault(e.get("tool"), []).append(e.get("id"))
        empty = sorted(t["id"] for t in self.ansible_tools if not by_tool.get(t["id"]))
        self.assertEqual(empty, [],
                         "these Ansible tools render in the rail and open to 'No catalogued "
                         "command for this tool yet': %s. A rail of empty tools is a rail with "
                         "no content, one click further in" % ", ".join(empty))

    def test_ansible_entries_file_under_ansible_tools(self):
        # The ported Ansible catalog has to be REACHABLE from the rail: every
        # a-* entry's tool must be in the Ansible slice, or the entry ships in
        # the island and the rail cannot open it.
        ansible_ids = set(t["id"] for t in self.ansible_tools)
        ported = [e for e in self.entries if str(e.get("id", "")).startswith("a-")]
        self.assertGreater(len(ported), 0, "no ported Ansible entries in content/commands.json")
        misfiled = sorted(e["id"] for e in ported if e.get("tool") not in ansible_ids)
        self.assertEqual(misfiled, [],
                         "these Ansible entries file under a tool the Ansible rail does not "
                         "render, so the rail cannot reach them: %s" % ", ".join(misfiled))

    def test_every_ansible_tool_is_available_on_every_release(self):
        # An ansible-* invocation is governed by the control node's ansible-core
        # version, not by the RHEL release of the hosts it reaches. A version
        # gate here would grey out the whole rail on a release for a reason that
        # is not true of it.
        bad = []
        for t in self.ansible_tools:
            for v in ("7", "8", "9", "10"):
                if not ((t.get("availability") or {}).get(v) or {}).get("available"):
                    bad.append("%s/RHEL %s" % (t["id"], v))
        self.assertEqual(bad, [],
                         "these Ansible tools are gated off a RHEL release: %s. The control "
                         "node's ansible-core version governs these commands, not the release "
                         "of the hosts they reach" % ", ".join(bad))

    def test_the_rail_is_still_reachable_and_no_longer_promises_itself(self):
        self.assertIn('data-rail="ansible"', self.template,
                      "the Ansible rail button is gone from the static markup")
        self.assertIn('STATE.rail==="ansible"', self.template,
                      "renderToolList() no longer special-cases the Ansible rail, so it falls "
                      "back to the 'lands with its own task' placeholder")
        self.assertNotIn("the Ansible generator (CR-T-25)", self.template,
                         "the sidebar placeholder still tells the reader the Ansible generator "
                         "is pending work -- it is the sentence the Founder read")

    def test_playbook_offers_task_selection_checkboxes(self):
        playbook = next(e for e in self.entries if e.get("id") == "gen-ansible-playbook")
        checkboxes = {
            f["name"]: f for f in playbook.get("fields", [])
            if f.get("control") == "checkbox"
        }
        self.assertEqual(set(checkboxes), {"refresh_cache", "manage_service"})
        for name, field in checkboxes.items():
            self.assertEqual(field.get("type"), "enum", name)
            self.assertEqual(field.get("options"), ["yes"], name)
            self.assertFalse(field.get("required", False), name)

        lines = playbook.get("doc", {}).get("lines", [])
        gates = {line.get("requires") for line in lines if line.get("requires")}
        self.assertTrue(set(checkboxes).issubset(gates),
                        "each task checkbox must gate at least one declared YAML line")

    def test_checkbox_control_is_rendered_and_unchecked_means_absent(self):
        self.assertIn('field.control==="checkbox"', self.template)
        self.assertIn('type="checkbox"', self.template)
        self.assertIn('!f.checked', self.template)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Build-time contract for generator task-selection checkboxes."""
import unittest

from extract import schema


def errors(field):
    return schema.spec_fields_errors("spec", [field], set())


class CheckboxFieldSchemaTests(unittest.TestCase):
    def test_optional_yes_enum_is_the_only_valid_checkbox_shape(self):
        self.assertEqual(errors({
            "name": "refresh_cache", "type": "enum", "required": False,
            "options": ["yes"], "control": "checkbox",
        }), [])

    def test_checkbox_cannot_carry_an_author_chosen_payload(self):
        got = errors({
            "name": "task", "type": "enum", "required": False,
            "options": ["run arbitrary task"], "control": "checkbox",
        })
        self.assertTrue(any("sole option is 'yes'" in e for e in got), got)

    def test_checkbox_cannot_be_required(self):
        got = errors({
            "name": "task", "type": "enum", "required": True,
            "options": ["yes"], "control": "checkbox",
        })
        self.assertTrue(any("optional enum" in e for e in got), got)

    def test_checkbox_cannot_bypass_the_enum_validator(self):
        got = errors({
            "name": "task", "type": "comment", "required": False,
            "control": "checkbox",
        })
        self.assertTrue(any("optional enum" in e for e in got), got)


if __name__ == "__main__":
    unittest.main()

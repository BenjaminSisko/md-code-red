#!/usr/bin/env python3
import importlib.util
import contextlib
import io
import json
import os
import tempfile
import unittest
from types import SimpleNamespace

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "tools", "execution_receipt.py")
spec = importlib.util.spec_from_file_location("execution_receipt", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExecutionReceiptTests(unittest.TestCase):
    def receipt(self):
        command = "systemctl status sshd.service\n"
        stdout = "Active: active (running)\n"
        stderr = ""
        return {
            "schema": module.SCHEMA,
            "tool_version": "v1.0.0-alpha.4",
            "entry_id": "firewalld-service-active",
            "rhel_version": "9",
            "target": "asset-123",
            "operator": "Example Operator",
            "executed_at": "2026-09-22T14:00:00-04:00",
            "ticket": "CHG-123",
            "command": command,
            "command_sha256": module.digest_bytes(command.encode()),
            "artifact_sha256": "a" * 64,
            "content_fingerprint": "b" * 64,
            "exit_code": 0,
            "stdout": stdout,
            "stdout_sha256": module.digest_bytes(stdout.encode()),
            "stderr": stderr,
            "stderr_sha256": module.digest_bytes(stderr.encode()),
            "verification": "PASS: service is active",
            "attestation": {
                "command_was_executed": True,
                "outputs_are_actual": True,
                "statement": "I ran the recorded command and captured these outputs."
            }
        }

    def test_complete_receipt_passes(self):
        self.assertEqual(module.validate(self.receipt()), [])

    def test_changed_command_or_output_fails_hash_binding(self):
        receipt = self.receipt()
        receipt["command"] += " # changed"
        receipt["stdout"] += "changed"
        errors = module.validate(receipt)
        self.assertTrue(any("command_sha256" in item for item in errors))
        self.assertTrue(any("stdout_sha256" in item for item in errors))

    def test_attestation_cannot_be_omitted_or_false(self):
        receipt = self.receipt()
        receipt["attestation"]["outputs_are_actual"] = False
        self.assertTrue(any("outputs_are_actual" in item for item in module.validate(receipt)))

    def test_artifact_is_checked_when_supplied(self):
        receipt = self.receipt()
        with tempfile.NamedTemporaryFile() as artifact:
            artifact.write(b"artifact")
            artifact.flush()
            self.assertTrue(any("artifact_sha256" in item
                                for item in module.validate(receipt, artifact.name)))

    def test_schema_closure_integer_type_and_fingerprint_binding(self):
        receipt = self.receipt()
        receipt["undeclared"] = "refused"
        receipt["attestation"]["undeclared"] = True
        receipt["exit_code"] = True
        errors = module.validate(receipt)
        self.assertTrue(any("undeclared top-level" in item for item in errors), errors)
        self.assertTrue(any("undeclared attestation" in item for item in errors), errors)
        self.assertTrue(any("exit_code must be an integer" in item for item in errors), errors)

        receipt = self.receipt()
        artifact = (b'<script>var APP_VERSION="v1.0.0-alpha.4";'
                    b'var CONTENT_FINGERPRINT="' + b'c' * 64 + b'";</script>')
        with tempfile.NamedTemporaryFile() as handle:
            handle.write(artifact)
            handle.flush()
            receipt["artifact_sha256"] = module.digest_bytes(artifact)
            errors = module.validate(receipt, handle.name)
        self.assertTrue(any("content_fingerprint does not match" in item for item in errors), errors)

    def test_import_stores_validated_receipt_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "receipt.json")
            store = os.path.join(directory, "store")
            with open(source, "w", encoding="utf-8") as handle:
                json.dump(self.receipt(), handle)
            args = SimpleNamespace(receipt=source, store=store, artifact=None)
            with contextlib.redirect_stdout(io.StringIO()):
                module.import_command(args)
            imported = []
            for root, _dirs, files in os.walk(store):
                imported.extend(os.path.join(root, name) for name in files)
            self.assertEqual(len(imported), 1)
            with self.assertRaises(FileExistsError):
                with contextlib.redirect_stdout(io.StringIO()):
                    module.import_command(args)


if __name__ == "__main__":
    unittest.main()

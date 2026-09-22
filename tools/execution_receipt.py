#!/usr/bin/env python3
"""Create and validate MD CODE RED execution receipts.

This tool records an execution that already happened. It never executes the
command. That separation prevents a receipt helper from becoming an implicit
remote-execution feature.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys

SCHEMA = "md-code-red/execution-receipt/v1"
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def text_file(path):
    return read_bytes(path).decode("utf-8", "replace")


def validate(receipt, artifact_path=None):
    errors = []
    required = (
        "schema", "tool_version", "entry_id", "rhel_version", "target", "operator", "executed_at",
        "ticket", "command", "command_sha256", "artifact_sha256",
        "content_fingerprint", "exit_code", "stdout", "stdout_sha256",
        "stderr", "stderr_sha256", "verification", "attestation",
    )
    for key in required:
        if key not in receipt:
            errors.append("missing %s" % key)
    if errors:
        return errors
    if receipt["schema"] != SCHEMA:
        errors.append("schema must be %s" % SCHEMA)
    for key in ("tool_version", "entry_id", "target", "operator", "ticket", "verification"):
        if not isinstance(receipt[key], str) or not receipt[key].strip():
            errors.append("%s must be a non-empty string" % key)
    if receipt["rhel_version"] not in ("7", "8", "9", "10"):
        errors.append("rhel_version must be 7, 8, 9, or 10")
    try:
        parsed = dt.datetime.fromisoformat(receipt["executed_at"].replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            errors.append("executed_at must include a timezone")
    except (TypeError, ValueError):
        errors.append("executed_at must be an ISO-8601 timestamp")
    if not isinstance(receipt["exit_code"], int):
        errors.append("exit_code must be an integer")
    for key in ("command_sha256", "artifact_sha256", "content_fingerprint",
                "stdout_sha256", "stderr_sha256"):
        if not isinstance(receipt[key], str) or not SHA256.fullmatch(receipt[key]):
            errors.append("%s must be a lowercase SHA-256 digest" % key)
    if isinstance(receipt["command"], str):
        if digest_bytes(receipt["command"].encode("utf-8")) != receipt["command_sha256"]:
            errors.append("command_sha256 does not match command")
    else:
        errors.append("command must be a string")
    for field in ("stdout", "stderr"):
        if not isinstance(receipt[field], str):
            errors.append("%s must be a string" % field)
        elif digest_bytes(receipt[field].encode("utf-8")) != receipt[field + "_sha256"]:
            errors.append("%s_sha256 does not match %s" % (field, field))
    att = receipt["attestation"]
    if not isinstance(att, dict):
        errors.append("attestation must be an object")
    else:
        if att.get("command_was_executed") is not True:
            errors.append("attestation.command_was_executed must be true")
        if att.get("outputs_are_actual") is not True:
            errors.append("attestation.outputs_are_actual must be true")
        if not isinstance(att.get("statement"), str) or not att["statement"].strip():
            errors.append("attestation.statement must be non-empty")
    if artifact_path:
        actual = digest_bytes(read_bytes(artifact_path))
        if actual != receipt["artifact_sha256"]:
            errors.append("artifact_sha256 does not match %s" % artifact_path)
    return errors


def create(args):
    command = text_file(args.command_file)
    stdout = text_file(args.stdout_file)
    stderr = text_file(args.stderr_file)
    receipt = {
        "schema": SCHEMA,
        "tool_version": args.tool_version,
        "entry_id": args.entry_id,
        "rhel_version": args.rhel_version,
        "target": args.target,
        "operator": args.operator,
        "executed_at": args.executed_at,
        "ticket": args.ticket,
        "command": command,
        "command_sha256": digest_bytes(command.encode("utf-8")),
        "artifact_sha256": digest_bytes(read_bytes(args.artifact)),
        "content_fingerprint": args.content_fingerprint,
        "exit_code": args.exit_code,
        "stdout": stdout,
        "stdout_sha256": digest_bytes(stdout.encode("utf-8")),
        "stderr": stderr,
        "stderr_sha256": digest_bytes(stderr.encode("utf-8")),
        "verification": args.verification,
        "attestation": {
            "command_was_executed": True,
            "outputs_are_actual": True,
            "statement": args.attestation,
        },
    }
    errors = validate(receipt, args.artifact)
    if errors:
        raise SystemExit("receipt refused: " + "; ".join(errors))
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
    else:
        sys.stdout.write(rendered)


def validate_command(args):
    with open(args.receipt, encoding="utf-8") as handle:
        receipt = json.load(handle)
    errors = validate(receipt, args.artifact)
    if errors:
        for error in errors:
            print("INVALID:", error, file=sys.stderr)
        return 1
    print("VALID: execution receipt binds command, outputs, target, operator, artifact, and verification")
    return 0


def import_command(args):
    with open(args.receipt, encoding="utf-8") as handle:
        receipt = json.load(handle)
    errors = validate(receipt, args.artifact)
    if errors:
        raise SystemExit("receipt refused: " + "; ".join(errors))
    safe_target = re.sub(r"[^A-Za-z0-9._-]", "_", receipt["target"]).strip("._-")
    safe_entry = re.sub(r"[^A-Za-z0-9._-]", "_", receipt["entry_id"]).strip("._-")
    if not safe_target or not safe_entry:
        raise SystemExit("receipt refused: target or entry_id has no safe filename characters")
    stamp = re.sub(r"[^0-9]", "", receipt["executed_at"])[:14]
    filename = "%s-%s-%s.json" % (stamp, safe_entry, receipt["command_sha256"][:12])
    destination_dir = os.path.join(args.store, "rhel" + receipt["rhel_version"], safe_target)
    os.makedirs(destination_dir, exist_ok=True)
    destination = os.path.join(destination_dir, filename)
    with open(destination, "x", encoding="utf-8", newline="\n") as output:
        json.dump(receipt, output, indent=2, sort_keys=True)
        output.write("\n")
    print("IMPORTED", destination)


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="action", required=True)
    make = sub.add_parser("create", help="create a receipt from already captured files")
    make.add_argument("--artifact", required=True)
    make.add_argument("--tool-version", required=True)
    make.add_argument("--entry-id", required=True)
    make.add_argument("--rhel-version", choices=("7", "8", "9", "10"), required=True)
    make.add_argument("--content-fingerprint", required=True)
    make.add_argument("--target", required=True)
    make.add_argument("--operator", required=True)
    make.add_argument("--executed-at", required=True)
    make.add_argument("--ticket", required=True)
    make.add_argument("--command-file", required=True)
    make.add_argument("--stdout-file", required=True)
    make.add_argument("--stderr-file", required=True)
    make.add_argument("--exit-code", required=True, type=int)
    make.add_argument("--verification", required=True)
    make.add_argument("--attestation", required=True)
    make.add_argument("--output")
    make.set_defaults(func=create)
    check = sub.add_parser("validate", help="validate a receipt and optionally its artifact")
    check.add_argument("receipt")
    check.add_argument("--artifact")
    check.set_defaults(func=validate_command)
    importer = sub.add_parser("import", help="validate and store a receipt without overwriting evidence")
    importer.add_argument("receipt")
    importer.add_argument("--store", required=True)
    importer.add_argument("--artifact")
    importer.set_defaults(func=import_command)
    return root


def main():
    args = parser().parse_args()
    result = args.func(args)
    return 0 if result is None else result


if __name__ == "__main__":
    raise SystemExit(main())

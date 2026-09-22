# Execution Evidence

The in-browser **Export command and control reference** action exports a deterministic command
and control reference. It contains the selected command, its source and its
expected-output state. It does not prove that anyone ran the command, and it is
not an execution receipt.

An execution receipt binds an actual run to its target, operator, timestamp,
change ticket, exit code, actual standard output and error, verification result,
exact command hash, artifact SHA-256 and content fingerprint. The v1 format is
defined by `content-src/execution-receipt.schema.json` and enforced without
third-party packages by `tools/execution_receipt.py`.

The helper never runs a command. Capture the command and its outputs under the
receiving organization's approved procedure, then create a receipt from those
files:

```text
python3 tools/execution_receipt.py create \
  --artifact dist/md-code-red_v1.0.0-alpha.5.html \
  --tool-version v1.0.0-alpha.5 \
  --entry-id firewalld-service-active \
  --rhel-version 9 \
  --content-fingerprint <64-lowercase-hex-digest> \
  --target <inventory-id-or-hostname> \
  --operator <named-operator> \
  --executed-at 2026-09-22T14:00:00-04:00 \
  --ticket <change-or-ticket-id> \
  --command-file command.txt \
  --stdout-file stdout.txt \
  --stderr-file stderr.txt \
  --exit-code 0 \
  --verification "PASS: observed state matched the stated verification" \
  --attestation "I ran the recorded command on the recorded target; these are its actual outputs." \
  --output receipt.json
```

Validate internal hashes and, when available, the original artifact:

```text
python3 tools/execution_receipt.py validate receipt.json \
  --artifact dist/md-code-red_v1.0.0-alpha.5.html
```

After review, import the receipt into an evidence store. Import validates every
binding, creates a release/target-specific filename, and refuses to overwrite an
existing receipt:

```text
python3 tools/execution_receipt.py import receipt.json \
  --artifact dist/md-code-red_v1.0.0-alpha.5.html \
  --store <approved-evidence-directory>
```

The receipt may contain sensitive host output. Review and redact it under the
local evidence policy before distribution. Any redaction changes the output and
therefore requires a new receipt that states the redaction in `verification`;
never alter a receipt while retaining its old hashes.

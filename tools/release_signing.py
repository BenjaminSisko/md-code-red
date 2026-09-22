#!/usr/bin/env python3
"""Prepare, sign, and verify a release checksum manifest.

Signing requires an explicit GPG key fingerprint. The repository does not
choose, create, or imply an authorized publisher identity.
"""

import argparse
import hashlib
import os
import subprocess
import sys


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def prepare(args):
    rows = []
    for path in sorted(args.artifacts, key=lambda value: os.path.basename(value)):
        name = os.path.basename(path)
        if "\n" in name or "\r" in name or name in ("", ".", ".."):
            raise SystemExit("unsafe artifact basename: %r" % name)
        rows.append("%s  %s" % (sha256(path), name))
    with open(args.output, "w", encoding="ascii", newline="\n") as handle:
        handle.write("\n".join(rows) + "\n")
    print("WROTE %s (%d artifact digests; unsigned until a detached signature is created)" %
          (args.output, len(rows)))


def sign(args):
    if not args.key_fingerprint or len(args.key_fingerprint.replace(" ", "")) < 16:
        raise SystemExit("an explicit authorized GPG key fingerprint is required")
    output = args.output or args.manifest + ".asc"
    command = ["gpg", "--batch", "--yes", "--armor", "--detach-sign",
               "--local-user", args.key_fingerprint, "--output", output, args.manifest]
    subprocess.run(command, check=True)
    print("SIGNED %s with requested key %s" % (args.manifest, args.key_fingerprint))


def verify(args):
    base = os.path.dirname(os.path.abspath(args.manifest))
    with open(args.manifest, encoding="ascii") as handle:
        rows = [line.rstrip("\n") for line in handle if line.strip()]
    errors = []
    for row in rows:
        if len(row) < 67 or row[64:66] != "  ":
            errors.append("malformed manifest row: %r" % row)
            continue
        expected, name = row[:64], row[66:]
        if os.path.basename(name) != name:
            errors.append("manifest names must be basenames: %s" % name)
            continue
        path = os.path.join(base, name)
        if not os.path.isfile(path):
            errors.append("missing artifact: %s" % name)
        elif sha256(path) != expected:
            errors.append("digest mismatch: %s" % name)
    if args.signature:
        result = subprocess.run(["gpg", "--status-fd", "1", "--verify",
                                 args.signature, args.manifest], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            errors.append("detached signature verification failed")
        elif "[GNUPG:] VALIDSIG " not in result.stdout:
            errors.append("GPG did not report a valid signature fingerprint")
    else:
        errors.append("no detached signature supplied; digests alone do not authenticate a publisher")
    if errors:
        for error in errors:
            print("INVALID:", error, file=sys.stderr)
        return 1
    print("VALID: detached signature and %d artifact digest(s) verified" % len(rows))
    return 0


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("artifacts", nargs="+")
    prep.add_argument("--output", required=True)
    prep.set_defaults(func=prepare)
    signer = sub.add_parser("sign")
    signer.add_argument("manifest")
    signer.add_argument("--key-fingerprint", required=True)
    signer.add_argument("--output")
    signer.set_defaults(func=sign)
    check = sub.add_parser("verify")
    check.add_argument("manifest")
    check.add_argument("--signature")
    check.set_defaults(func=verify)
    return root


def main():
    args = parser().parse_args()
    value = args.func(args)
    return 0 if value is None else value


if __name__ == "__main__":
    raise SystemExit(main())

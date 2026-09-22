#!/usr/bin/env python3
"""Report the real-host matrix or perform an eligibility-only local probe."""

import argparse
import json
import os
import platform

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATRIX = os.path.join(REPO, "content-src", "real-host-validation-matrix.json")


def load():
    with open(MATRIX, encoding="utf-8") as handle:
        return json.load(handle)


def receipt_counts():
    with open(os.path.join(REPO, "content", "commands.json"), encoding="utf-8") as handle:
        entries = json.load(handle)["entries"]
    return {version: sum(isinstance(entry.get("verified", {}).get(version), dict)
                         for entry in entries)
            for version in ("7", "8", "9", "10")}


def report(_args):
    data = load()
    print("RHEL  Support posture                         Receipts  Status")
    for release, row in data["releases"].items():
        print("%-5s %-39s %-9s %s" %
              (release, row["support_posture"][:39], row["verified_receipts"],
               row.get("matrix_status", row["host_access"])))


def check(_args):
    data = load()
    actual = receipt_counts()
    errors = []
    for release, count in actual.items():
        recorded = data["releases"][release]["verified_receipts"]
        if recorded != count:
            errors.append("RHEL %s records %s receipts; commands.json has %s" %
                          (release, recorded, count))
    if errors:
        for error in errors:
            print("STALE:", error)
        return 1
    print("PASS: validation matrix receipt counts match commands.json")
    return 0


def probe_local(_args):
    """Read identity only. Never treats a non-RHEL machine as RHEL evidence."""
    observed = {"platform": platform.platform(), "eligible": False, "reason": ""}
    release = ""
    if os.path.exists("/etc/redhat-release"):
        with open("/etc/redhat-release", encoding="utf-8", errors="replace") as handle:
            release = handle.read().strip()
    observed["redhat_release"] = release or None
    if release.startswith("Red Hat Enterprise Linux release "):
        major = release.split("release ", 1)[1].split(".", 1)[0].split(" ", 1)[0]
        observed["eligible"] = major in ("8", "9", "10")
        observed["reason"] = ("eligible RHEL %s identity; matrix commands still require named operator capture and independent review" % major
                              if observed["eligible"] else "RHEL release is outside the active 8/9/10 matrix")
    else:
        observed["reason"] = "local system is not an eligible RHEL 8/9/10 validation host; no commands were run"
    print(json.dumps(observed, indent=2, sort_keys=True))
    return 0 if observed["eligible"] else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    show = sub.add_parser("report")
    show.set_defaults(func=report)
    checker = sub.add_parser("check")
    checker.set_defaults(func=check)
    probe = sub.add_parser("probe-local")
    probe.set_defaults(func=probe_local)
    args = parser.parse_args()
    value = args.func(args)
    return 0 if value is None else value


if __name__ == "__main__":
    raise SystemExit(main())

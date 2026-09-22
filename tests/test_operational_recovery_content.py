#!/usr/bin/env python3
"""Regression coverage for the Linux-administrator operational review."""
import json
import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(REPO, "content", "commands.json"), encoding="utf-8") as f:
    ENTRIES = {row["id"]: row for row in json.load(f)["entries"]}


class OperationalRecoveryContent(unittest.TestCase):
    def test_rich_rule_generators_bind_zone_and_remove_exact_rule(self):
        for eid in ("gen-fw-open-port", "gen-fw-allow-service"):
            row = ENTRIES[eid]
            fields = {field["name"]: field for field in row["fields"]}
            self.assertTrue(fields["zone"]["required"], eid)
            self.assertEqual("root", row.get("privilege"), eid)
            self.assertIn("--zone", [part.get("flag") for part in row["template"]], eid)
            self.assertIn("--remove-rich-rule", row["undo"], eid)
            self.assertIn("<exact generated rule>", row["undo"], eid)
            self.assertIn("--reload", row["undo"], eid)
            self.assertIn("permanent", row["verify"], eid)
            self.assertIn("runtime", row["verify"], eid)
            combined = " ".join((row.get("notes", ""), row["undo"])).lower()
            self.assertNotIn("reverse action", combined, eid)
            self.assertNotIn("edit /etc/firewalld", combined, eid)

    def test_recovery_never_claims_reverse_action_recreates_pre_state(self):
        for eid in ("gen-dnf-package", "gen-yum-package"):
            row = ENTRIES[eid]
            self.assertIn("transaction ID", row["undo"], eid)
            self.assertIn("does not recreate", row["undo"], eid)
            self.assertEqual("root", row.get("privilege"), eid)
        row = ENTRIES["gen-systemctl-manage"]
        self.assertIn("captured pre-state", row["undo"])
        self.assertIn("no automatic inverse", row["undo"])

    def test_network_change_does_not_claim_dns_or_fake_dhcp_rollback(self):
        row = ENTRIES["gen-nmcli-static-ipv4"]
        self.assertNotIn("DNS method", row["intent"])
        self.assertIn("does not configure DNS", row["notes"])
        self.assertIn("complete saved NetworkManager connection profile", row["undo"])
        self.assertIn("out-of-band", row["undo"])
        self.assertNotIn("returns the connection to DHCP", row["undo"])

    def test_storage_recovery_is_explicitly_destructive(self):
        for eid in ("gen-pvcreate-initialize", "gen-vgcreate-new-vg"):
            row = ENTRIES[eid]
            self.assertEqual("root", row.get("privilege"), eid)
            self.assertIn("lsblk", row["notes"], eid)
            self.assertIn("backup", (row["notes"] + row["undo"]).lower(), eid)
        self.assertIn("cannot restore", ENTRIES["gen-lvcreate-new-lv"]["undo"])
        self.assertIn("no safe undo", ENTRIES["gen-lvextend-grow"]["undo"])

    def test_single_commands_make_no_multi_step_promise(self):
        expectations = {
            "r-nfs-mount": ("current boot", "does not establish persistence"),
            "r-journal-cap": ("Reclaim journal disk space once", "does not impose a permanent cap"),
            "r-localrepo": ("Create or refresh repository metadata", "does not create a .repo"),
        }
        for eid, (intent, verify) in expectations.items():
            row = ENTRIES[eid]
            self.assertIn(intent, row["intent"], eid)
            self.assertIn(verify, row["verify"], eid)

    def test_known_administrative_invocations_declare_root(self):
        required = {
            "gen-fw-set-default-zone", "gen-fw-open-port", "gen-fw-allow-service",
            "gen-nmcli-static-ipv4", "gen-pvcreate-initialize", "gen-vgcreate-new-vg",
            "gen-lvcreate-new-lv", "gen-lvextend-grow", "gen-useradd-create",
            "gen-usermod-add-group", "gen-systemctl-manage", "gen-dnf-package",
            "gen-yum-package", "gen-setsebool-set", "gen-semanage-port-add",
            "gen-chage-set-aging", "gen-auditctl-watch", "r-lvextend", "r-fw-add",
            "r-dnf-install", "r-dnf-history", "r-enable-now", "r-daemon-reload",
            "r-sys-edit", "r-restorecon", "r-semanage-fcontext", "r-setsebool",
            "r-usermod-ag", "r-journal-cap", "mount-attach-filesystem",
            "umount-detach-filesystem", "chown-ownership", "r-nfs-mount", "r-localrepo",
        }
        missing = sorted(eid for eid in required if ENTRIES[eid].get("privilege") != "root")
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()

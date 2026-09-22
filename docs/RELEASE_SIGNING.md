# Release Signing and Offline Verification

The published alpha.4 tag and the alpha.5 candidate are unsigned. Their SHA-256
values detect a file change but do not authenticate the publisher. This
repository does not contain an authorized signing key or assert that one exists.

When the release owner provisions and publishes an authorized GPG signing key,
prepare a deterministic manifest from the exact release assets:

```text
python3 tools/release_signing.py prepare \
  dist/md-code-red_v1.0.0-alpha.5.html \
  dist/md-code-red_v1.0.0-alpha.5.html.sha256 \
  dist/md-code-red_v1.0.0-alpha.5.provenance.json \
  --output dist/SHA256SUMS
```

The output is still unsigned. The authorized release owner signs it by naming
the full published 40- or 64-hex-character key fingerprint explicitly:

```text
python3 tools/release_signing.py sign dist/SHA256SUMS \
  --key-fingerprint <full-authorized-GPG-fingerprint>
```

Transfer the artifacts, `SHA256SUMS`, `SHA256SUMS.asc`, and the public key by
the approved offline path. The receiver must obtain the expected key
fingerprint through a separately trusted channel, import the public key, and
compare the complete fingerprint before verification:

```text
gpg --show-keys --with-fingerprint publisher-public-key.asc
gpg --import publisher-public-key.asc
python3 tools/release_signing.py verify SHA256SUMS \
  --signature SHA256SUMS.asc
```

Verification fails when an artifact differs, a file is missing, the detached
signature is invalid, or no signature is supplied. A successful result proves
that the imported key signed the manifest and that the listed files match it;
the receiving organization remains responsible for deciding whether that key
fingerprint is an authorized publisher identity.

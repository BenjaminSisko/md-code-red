# Deploy Receipt Template -- MD CODE RED

Filled out by the receiving admin at every handoff of a versioned artifact to
a host census entry, per ADR-001 section 9 (rollback = the previous versioned
file, or none). One receipt per (artifact, host) pair. Copy this template,
fill in the blanks, and file the copy under the release's own record in
`08_Release_Operations/MD_CODE_RED/` (SALM-internal) or the receiving
enclave's own records -- this repo ships the template, not the filled-in
receipts, which are evidence about a deployment, not about the code.

Draft origin: Taylor Webb's readiness assessment (REL-2026-09-18-001, item 12).
Format confirmation against the v2-process environment ladder is Avery
Quinn's, per that assessment -- treat this as usable-today, not yet canonical.

```
DEPLOY RECEIPT -- MD CODE RED

Version:                 <e.g. v1.0.0-alpha.1>
Artifact:                dist/md-code-red_<version>.html
Artifact sha256:         <sha256 from the .sha256 sidecar, verified by the
                          receiving admin, not copied from a claim>
Sidecar verified:        <sha256sum -c against the .sha256 file -- yes/no>
Content fingerprint:     <from the artifact's own About panel -- recomputable
                          from the file alone, verified against the release
                          page's recorded value>
Provenance manifest:     dist/md-code-red_<version>.provenance.json
                          (git_commit field -- should read the real tagged
                          commit, never TAG_COMMIT_PLACEHOLDER, on anything
                          actually deployed)
Signature status:        UNSIGNED -- sha256 integrity only, unless and until
                          a signing key is provisioned (readiness item 5).
                          Neither the sha256 nor the content fingerprint
                          proves who built the file.
                          If signed, record the detached signature filename,
                          full verified signer fingerprint, and verification
                          result from docs/RELEASE_SIGNING.md.
Built from commit:       <exact git sha of the tagged release>
Built by:                <person / CI run ID that produced the artifact>
Host census ID:          <the receiving host's own census/inventory ID --
                          Home Lab vault device page, or the receiving
                          organization's equivalent>
Deployed to:             <hostname or asset tag, and path on that host>
Deployed by:             <receiving admin name>
Deployed on:             <date>
Handoff method:          <file share / removable media / other, per the
                          receiving enclave's policy>
Environment rung:        dev [build+CI] -> test [named hosts + browsers] ->
                          <this rung -- pilot enclave / production / other>
Verifier:                <name of the person who independently checked the
                          sha256 and content fingerprint before use -- should
                          not be the same person as "Deployed by" alone;
                          two-person verification for anything past dev/test>
Known limitations acknowledged:
                          <copy the release's "Known limitations" section
                          from docs/CHANGELOG.md by reference (version and
                          heading), not by retyping it here where it can
                          drift out of sync>
Rollback:                <the previous versioned file at this host, by
                          filename and sha256 -- or "N/A, first deployment
                          of this tool to this host" for a first install.
                          Never leave this field blank; a blank rollback
                          field reads as an oversight, not as the correct
                          answer for a first deployment.>
Post-deploy check:       <admin opened the file in the required browser,
                          confirmed the About panel's version and content
                          fingerprint match this receipt, confirmed zero
                          network activity in devtools (air-gap sanity
                          check) -- yes/no, with any exception noted>
Receipt filed by:        <name, role, date>
```

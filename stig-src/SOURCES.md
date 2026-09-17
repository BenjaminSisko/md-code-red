# Pinned STIG sources — MD CODE RED

Source of record for every RULES record the build embeds. Nothing else is. Re-pin only through a
dep-bump PR that updates this file, the XML, and SHA256SUMS together (ADR-001 §7, Cardinal Rule).

| RHEL | Version | Benchmark date (release-info) | Zip downloaded | Zip SHA-256 | Status |
|---|---|---|---|---|---|
| 7 | V3R15 | 24 Jul 2024 | https://dl.dod.cyber.mil/wp-content/uploads/stigs/zip/U_RHEL_7_V3R15_STIG.zip | 89cf7d04b1ca6536b51cad2fe7ff5b729c9022a77522156f8a9c7b6967e6c52f | SUNSET at DISA; frozen terminal version. In project only while RHEL 7 can be validated (Founder, 2026-09-17). |
| 8 | V2R8 | 01 Jul 2026 | https://dl.dod.cyber.mil/wp-content/uploads/stigs/zip/U_RHEL_8_V2R8_STIG.zip | 5180ff6be545c306950f2041330e0cba835b148529e3c51c55c386f95c363a8c | current |
| 9 | V2R9 | 01 Jul 2026 | https://dl.dod.cyber.mil/wp-content/uploads/stigs/zip/U_RHEL_9_V2R9_STIG.zip | 1875de2543d01695c5a346c51888cc336113e9199bfe6726d74a08de286ca1ae | current |
| 10 | V1R2 | 01 Jul 2026 | https://dl.dod.cyber.mil/wp-content/uploads/stigs/zip/U_RHEL_10_V1R2_STIG.zip | d050b93c00d3c2cf8b0adec4a852f27bd827720cc4510ce32f3368006ad63ac3 | current (Draft V1R0.1 of 2026-09-02 in comment, not authoritative) |
| CCI | 2025-01-23 (publishdate in XML) | | https://dl.dod.cyber.mil/wp-content/uploads/stigs/zip/U_CCI_List.zip | 077cbb6d2ae5f8fdbaaf416d87a34a8621767cdba490f3283feb0c5c35892700 | current |

Downloaded 2026-09-17 by Eli Cross on Founder authorization (DECISION_LOG 2026-09-17). Individual XML
hashes in SHA256SUMS. Refresh rule: first week of each quarter, re-check the DISA library for RHEL 8/9/10;
RHEL 7 re-checked semi-annually only for removal from the library.

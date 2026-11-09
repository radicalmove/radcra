# Unified Sphere update rehearsal

Goal: prepare one extension for both LEARN and UCO and verify the existing Sphere data on a private PostgreSQL clone. Keep the live pilot, release pointers, and Store submission unchanged.

- [x] Use the existing isolated Sphere worktree. Preserve its migration lineage and run the backend and extension suites.
- [x] Rehearse using a transaction-consistent read-only dump on the existing server. Restore only into a temporary PostgreSQL cluster with no TCP listener. Compare the original rows (all columns except intentional course-identity normalization) before and after migration, then exercise copied account permissions and comment visibility. Never send email or export the dump from the server.
- [ ] Build a versioned candidate with both Moodle hosts, the original pilot public key, and one service URL. Verify the manifest and ZIP without installing or publishing it.
- [ ] Record counts, permission checks and the exact package location. Stop and remove only the rehearsal cluster and its private scratch files.

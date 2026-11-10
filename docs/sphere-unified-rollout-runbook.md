# Sphere 0.6.17: rollout and rollback plan

Status on 10 November 2026 (NZ): **hold production rollout**. This is a plan, not approval to run a deployment. Leave the existing UCO pilot and Chrome Web Store submission unchanged.

## Evidence and blockers

- The private PostgreSQL rehearsal preserved 19 users, 15 memberships and 158 comments. It verified UCO and LEARN role isolation and reuse of one account on both sites.
- Gmail accepted all three staging messages, and the reviewer confirmed all three appeared in their inbox. This was an isolated flow; it did not send to any other reviewer.
- A read-only audit confirmed that the six approved UCO reviewers flagged by the rehearsal are beta testers with reserved/test addresses. The broader audit found 13 such addresses across all accounts, including archived and non-UCO accounts; none had an active session. Some own comments or have memberships. Leave every account and its history intact. If a real reviewer is identified, confirm a deliverable address with them and retain the original account ID when arranging a correction.
- The native timer's missing script was restored. A one-shot timer invoked the same backup service successfully without restarting Sphere. The usual daily timer remains enabled. The resulting private bundle, `20261110T003802.221021Z-native`, was encrypted on the Sphere host and copied to the operator Mac. A restore using **only that encrypted copy** passed checksum, schema and attachment checks in a temporary PostgreSQL cluster without a TCP listener: schema `20261107_15`, 19 users, 10 courses, 15 memberships, 158 comments, and no attachments. The disposable restore was removed.
- The original `REVIEWER_ACCESS_ENABLED` switch still affects all courses. The staged server patch adds `REVIEWER_ACCESS_LEARN_TRIAL_EMAIL`: one invited address on the exact LEARN origin and course number 3598. Keep the global flag off. Startup rejects configuring both modes. Uninvited submissions do not queue mail or consume the trial's request quota. Legacy UCO sign-in and mail dispatch are unchanged. The live switch was off and no LEARN course was registered at the audit.
- The scoped patch passed 292 backend tests and a read-only PostgreSQL-copy rehearsal. The latter preserved 19 users, 15 memberships and 158 comments, exercised all 13 approved UCO memberships, and approved the same account on LEARN without changing its UCO role. Trial mail was captured, not sent. The current extension candidate needs no binary change for this backend setting. No production rollout has taken place.

## Before booking a maintenance window

1. Check the latest daily backup result and refresh the tested encrypted off-host copy before the window. The repaired job produces a private checksummed PostgreSQL dump and matching attachments archive using one read-only snapshot. A Mac-held encrypted copy has been restored successfully; off-host transfers are not scheduled. Keep a separately protected recovery copy of the encryption key before relying on the Mac as the sole recovery destination.
2. In an isolated deployment, smoke-test the browser build against the scoped backend with the chosen invited reviewer and CRJU160 before release. The staged backend tests cover approval, confirmation, exchange, legacy UCO access, cross-course denial, and allowed mail dispatch. Keep the existing 0.6.17 rehearsal artifact unchanged.
3. Inventory the running unit files, notification worker, source, virtual environment, and environment configuration. The live checkout contains local changes; preserve its exact contents and secrets separately rather than assuming its Git commit reproduces production. Stage the new service in a separate release directory. Obtain approval for the window, proposed reviewers, and operator performing recovery.

## Approved window only

1. Pause the mail timer and let any active send finish. Freeze application writes. Take and validate a fresh matched database/attachments backup and record the live revision and baseline counts. Stop if any backup or restore validation fails.
2. Apply the rehearsed migrations using the explicitly checked production target. Start the candidate with LEARN disabled and mail paused. Check health, migration head, row counts and CRJU160 permissions/comment reads. Keep general write traffic closed until this gate passes.
3. After the baseline passes, enable only LEARN course 3598 for the first invited reviewer. Check sign-in, course-specific permissions, and a controlled comment; verify CRJU160 again. Resume authorised mail processing only after checking the pending queue and recipient scope. Do not change the Store submission or publish the candidate in this window.

For the trial, explicitly register the exact LEARN course, set `REVIEWER_ACCESS_LEARN_TRIAL_EMAIL` to the agreed reviewer, and configure the existing reviewer mail secret, admin inbox, sender and HTTPS origin on the staged app and worker. Keep `REVIEWER_ACCESS_ENABLED=false`. To pause, remove the invited address from both processes' configuration; this blocks the trial's queued mail, proof exchange, existing sessions and renewal without deleting history. To revoke an individual permanently, also revoke their course membership before any reactivation.

## Rollback decision

- Stop immediately for a migration error, unexpected row change, CRJU160 access regression, cross-course visibility, or mail to the wrong recipient. Freeze writes and stop the worker. Record the stage and timestamps.
- Before reopening writes, if recovery is needed, restore the matched pre-change database and attachments into a separate verified target, then point the exact prior release and configuration at that target. Check schema `20261107_15`, health and CRJU160 access before reopening writes. Do not overwrite the failed database; retain it privately for diagnosis.
- After reopening writes, first disable LEARN and pause its mail. Preserve a snapshot of the current database and attachments. Do not silently restore the old snapshot and discard new UCO or LEARN activity. Compare changes and agree on reconciliation or a forward fix before switching back. Migration 16's downgrade rejects repeated numeric Moodle IDs across hosts; do not force it or delete courses to make it pass.

## Off-host recovery record

- Ciphertext on the Mac: `~/.local/state/sphere-offhost/20261110T003802.221021Z-native.tar.gpg` (mode 0600).
- Ciphertext SHA-256: `e2ad8eb2f250bc7b29e971890b56a9e3325fe40fbf39d69ce2d88217e17ce90c`.
- Dedicated GnuPG keyring: `~/.config/sphere-offhost-gnupg` (mode 0700, protected at rest by the Mac's FileVault). Public fingerprint: `7B537479F3CF4C85F86F121C2ACAFA04DC55B39D`. The private key was not sent to the Sphere host or copied elsewhere. Loss of this Mac and the keyring would make the archive unrecoverable.
- To refresh, validate the selected native bundle's SHA256SUMS on the Sphere host. Stream a tar of exactly `database.dump`, `attachments.tar.gz`, `manifest.json` and `SHA256SUMS` through GnuPG using the dedicated public key **on the source host**, then transfer the ciphertext over SSH. Verify GnuPG decryption on the Mac before keeping the file. Use a fresh versioned filename; do not overwrite the last verified copy.
- To rehearse recovery, decrypt with the Mac keyring, validate the four archived files and their checksums, and restore only into a disposable PostgreSQL instance. Compare its Alembic revision, row counts, and attachment references against the bundle. The test streamed the decrypted data over SSH to a disposable Unix-socket-only cluster, not the live database. Never extract a plaintext backup into a shared or synced directory.

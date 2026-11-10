# Sphere 0.6.17: rollout and rollback plan

Status on 10 November 2026 (NZ): **hold production rollout**. This is a plan, not approval to run a deployment. Leave the existing UCO pilot and Chrome Web Store submission unchanged.

## Evidence and blockers

- The private PostgreSQL rehearsal preserved 19 users, 15 memberships and 158 comments. It verified UCO and LEARN role isolation and reuse of one account on both sites.
- Gmail accepted all three staging messages, and the reviewer confirmed all three appeared in their inbox. This was an isolated flow; it did not send to any other reviewer.
- A read-only audit confirmed that the six approved UCO reviewers flagged by the rehearsal are beta testers with reserved/test addresses. The broader audit found 13 such addresses across all accounts, including archived and non-UCO accounts; none had an active session. Some own comments or have memberships. Leave every account and its history intact. If a real reviewer is identified, confirm a deliverable address with them and retain the original account ID when arranging a correction.
- The native timer's missing script was restored. A one-shot timer invoked the same backup service successfully without restarting Sphere. The resulting private on-host bundle, `20261110T003802.221021Z-native`, passed checksums and an actual restore into a temporary PostgreSQL cluster without a TCP listener: schema `20261107_15`, 19 users, 10 courses, 15 memberships, 158 comments, and no attachments. Five automated checks covered valid, missing, symlinked, incorrectly sized, and unsafe attachment paths. The usual daily timer remains enabled. No backup was sent off-host.
- The candidate's `REVIEWER_ACCESS_ENABLED` switch affects registration and sign-in across the system, not just LEARN. Do not enable it as a one-course trial. Prepare and test an explicitly scoped LEARN allowlist with an invitation or reviewer allowlist; verify request, confirmation, exchange and mail dispatch all respect the scope, and that CRJU160 retains its current access flow. Verify abusive or uninvited requests cannot exhaust shared mail capacity. The live switch was off and no LEARN course was registered at the audit.

## Before booking a maintenance window

1. Check the latest daily backup result, retain a recoverable encrypted copy at an approved off-host destination, and verify its restore. The repaired job now produces a private checksummed PostgreSQL dump and matching attachments archive using one read-only snapshot. Local recovery has been proven; off-host storage still needs a destination and verification.
2. Rehearse the scoped LEARN activation against a restored copy and the existing browser builds. Cover existing CRJU160 sign-in, comment display and session renewal, one invited LEARN reviewer with a shared account, different roles on each site, wrong-course denial, and mail sent only to authorised recipients. Build a new candidate if code changes; do not overwrite the 0.6.17 rehearsal artifact.
3. Inventory the running unit files, notification worker, source, virtual environment, and environment configuration. The live checkout contains local changes; preserve its exact contents and secrets separately rather than assuming its Git commit reproduces production. Stage the new service in a separate release directory. Obtain approval for the window, proposed reviewers, and operator performing recovery.

## Approved window only

1. Pause the mail timer and let any active send finish. Freeze application writes. Take and validate a fresh matched database/attachments backup and record the live revision and baseline counts. Stop if any backup or restore validation fails.
2. Apply the rehearsed migrations using the explicitly checked production target. Start the candidate with LEARN disabled and mail paused. Check health, migration head, row counts and CRJU160 permissions/comment reads. Keep general write traffic closed until this gate passes.
3. After the baseline passes, enable only LEARN course 3598 for the first invited reviewer. Check sign-in, course-specific permissions, and a controlled comment; verify CRJU160 again. Resume authorised mail processing only after checking the pending queue and recipient scope. Do not change the Store submission or publish the candidate in this window.

## Rollback decision

- Stop immediately for a migration error, unexpected row change, CRJU160 access regression, cross-course visibility, or mail to the wrong recipient. Freeze writes and stop the worker. Record the stage and timestamps.
- Before reopening writes, if recovery is needed, restore the matched pre-change database and attachments into a separate verified target, then point the exact prior release and configuration at that target. Check schema `20261107_15`, health and CRJU160 access before reopening writes. Do not overwrite the failed database; retain it privately for diagnosis.
- After reopening writes, first disable LEARN and pause its mail. Preserve a snapshot of the current database and attachments. Do not silently restore the old snapshot and discard new UCO or LEARN activity. Compare changes and agree on reconciliation or a forward fix before switching back. Migration 16's downgrade rejects repeated numeric Moodle IDs across hosts; do not force it or delete courses to make it pass.

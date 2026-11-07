# Demo recovery implementation plan

> Execute inline with superpowers:executing-plans. User approved demo-only recovery hardening and restart testing; do not change the live CRJU160 pilot.

**Goal:** Keep the separate Store-review demo recoverable after process failures, logout and reboot without touching the live service.

**Architecture:** Retain the existing isolated PHP/MariaDB and Python/SQLite services, paths and ports. Set both demo units to Restart=always, RestartSec=5s and StartLimitIntervalSec=0. Use Wants rather than Requires for the gateway's Moodle dependency, preserving startup ordering without stopping the gateway when PHP fails. Enable both demo units under the lingering user manager. Leave the live unit, its process, database, code and public port-443 mapping alone.

**Files:** deploy/reviewer-demo/sphere-review-demo.service; deploy/reviewer-demo/sphere-review-demo-moodle.service; tests/test_demo_recovery_units.py.

- [x] Add unit-configuration regression tests and observe failure against the current configuration.
- [x] Apply only the three recovery settings and dependency adjustment; rerun tests.
- [x] Capture the live service PID/start time/unit hash and Funnel mapping; back up only the two existing demo unit files.
- [x] Copy the tested units to the Mac mini, validate with systemd-analyze, reload the user manager, enable both units and restart only the demo units.
- [x] Verify public demo login and API health, then terminate each demo main process separately and confirm automatic recovery. Confirm PHP recovery does not change the gateway PID.
- [x] Compare live PID/start time/unit hash and public mapping before/after; check live health. Do not reboot the Mac or restart shared services.
- [x] Record evidence and commit/push only the recovery files and this plan. No extension or Store package change.

**Limits:** This improves process recovery, not protection against power, network, disk or host failure. Do not alter global power settings or add unrelated monitoring/backup changes.

## Verified deployment, 8 November 2026

- Three configuration tests failed before implementation, then all three passed. The plan received a read-only safety review with no blockers.
- Both demo units pass systemd-analyze verification, are enabled, and report Restart=always, RestartUSec=5s and StartLimitIntervalUSec=0. Linger=yes was already configured and remains unchanged; MariaDB and Tailscale were already enabled/active.
- Controlled demo-only restart succeeded. A subsequent SIGKILL to the demo PHP main process recovered automatically (PID 3047077 to 3047132, NRestarts=1), while gateway PID 3047078 stayed running. A SIGKILL to the demo gateway recovered automatically (PID 3047078 to 3047163, NRestarts=1).
- Public demo API returns healthy and its Moodle login returns HTTP 200 after recovery. Live public API also returns healthy.
- Live moodle-review.service remains PID 3016164, active since 6 November 2026 23:48:04 UTC, with unchanged unit hash 47427cf580d614dc64ed1b86702b8e1ca8efec0de3401d303e4a82d12301a32f. Public routing remains 443 to 8017 and demo 8443 to 8023. A raw output comparison initially differed only because Tailscale reordered its comment header; comparison of actual routes passed.
- Original demo unit files and before/after evidence are retained at /home/fldadmin/sphere-review-demo/recovery-backup-20261108. No live unit, application, database, shared-service restart, host reboot, extension package or Store submission change was made.

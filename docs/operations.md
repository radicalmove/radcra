# Pilot operations

The RADCRA pilot API remains loopback-only on the Ubuntu Mac mini. The current live service is the user-managed `moodle-review.service`, which listens on `127.0.0.1:8017`; PostgreSQL has no host port. Tailscale Funnel terminates public HTTPS and proxies only to that loopback service. Do not expose the API port directly or add a separate public listener.

Before deployment obtain the Tailnet DNS name, confirm Tailscale HTTPS, choose encrypted off-host backup storage, and obtain stable Chrome/Edge IDs and administrator identity. Clone to `/home/fldadmin/beta-testing-app`, create `.env`, replace every placeholder with separate random secrets, and `chmod 600 .env`.

```sh
docker compose --env-file .env -f deploy/docker-compose.yml config
bash -n deploy/scripts/*.sh
```

Install the service unit, enable/start it, and confirm with `ss -lnt` that the API port is loopback-only. For the current live pilot, check the installed CLI syntax with `tailscale funnel --help`, then normally run:

```sh
tailscale funnel --yes --bg --https=443 http://127.0.0.1:8017
tailscale funnel status
```

Use the stable `https://<machine>.<tailnet>.ts.net` as `SERVICE_ORIGIN`. Funnel means reviewers do not need Tailscale installed: the `*.ts.net` hostname is reachable over normal HTTPS after public DNS has propagated. The service must still enforce application authentication and authorization. Check both public health and anonymous API rejection:

```sh
curl -fsS https://<machine>.<tailnet>.ts.net/health
curl -sS -o /dev/null -w '%{http_code}\n' https://<machine>.<tailnet>.ts.net/api/comments
```

The expected results are `{"status":"ok"}` and `401` or `403`. The `tailscale serve` command is tailnet-only; use it only when every user is meant to have Tailscale access. Funnel and Serve share the HTTPS listener, so the most recent command determines whether the endpoint is public or tailnet-only.

When a managed network cannot resolve the Tailscale hostname, a temporary Cloudflare Quick Tunnel can proxy the same loopback service without installing software on reviewers' computers:

```sh
systemd-run --user --unit=moodle-review-quick-tunnel --property=Restart=no \\
  /usr/bin/cloudflared tunnel --url http://127.0.0.1:8017 --no-autoupdate
journalctl --user -u moodle-review-quick-tunnel --no-pager -n 50
```

Use the `https://...trycloudflare.com` URL printed by `cloudflared` as `SERVICE_ORIGIN`, then build a new extension package with that exact URL. This is a temporary testing route: the URL changes if the tunnel process is restarted or the machine reboots, and the extension must be rebuilt for the new URL. Do not use Quick Tunnels as the permanent production route.

## Course registration and reviewer access

Register each Moodle course deliberately, in this order:

1. Open the intended Moodle course, not just a page from another course.
2. Wait for the extension to finish checking course access readiness.
3. While signed in as an Admin or LD/DCD, use the explicit **Register this course for review** action and confirm it.
4. Only after registration succeeds, open `/admin/users`, select that course, and create reviewer invitations or manage course memberships.

Merely visiting a course never registers it. The course lookup/resolve step only identifies an already registered course or reports that it is unregistered; it does not create or register a course. Course registration makes the Moodle course available for review. It is separate from reviewer membership statuses such as `Approved`, `Rejected`, and `Revoked`, which describe a particular user's access to that course and are managed after registration.

Account archiving is a separate lifecycle. In `/admin/users`, deleting an account archives it rather than destroying it: the user is signed out and loses access. The deleted-account area lists and restores the account; comments and review history remain available through the course review/comments area. Archived accounts cannot sign in until restored. This account state is distinct from both course registration and a membership's `Approved`, `Rejected`, or `Revoked` status.

## Articulate Rise Connected Packages

Versions 0.5.29 and later support the exact externally hosted frame used by the supplied Articulate Rise Connected Package launcher: `https://packages.articulateusercontent.com`. No wildcard Articulate subdomain or unrelated frame host is approved. If a different host appears in a future package, observe and review it before changing the allowlist.

When a reviewer opens a Connected Package, the toolbar may show **Allow SCORM review access**. Selecting it opens Chrome's permission prompt for the exact Articulate host. A granted permission persists for that Chrome profile and extension installation, although the reviewer may need to reload the Moodle activity once immediately after granting it. Denying the prompt is safe: no fallback toolbar is injected into the inaccessible frame, and the reviewer can retry the permission action later.

Never record, copy, or share a Connected Package launcher's `#token` value in comments, screenshots, support logs, or documentation. Versions 0.5.29 and later strip launcher-token fragments from review page identities, embedded locators, worker events, and API payloads. Treat any launcher URL containing a token as sensitive even after this safeguard.

Connected Packages load mutable content hosted by Articulate rather than a fixed uploaded SCORM archive. If Articulate content is changed after comments are saved, lesson structure, text, or layout changes may prevent an old highlight or visual marker from recovering at its original anchor. The comment thread remains associated with the Moodle review, but the reviewer may need to locate the revised content manually.

## Backup and restore

Run `deploy/scripts/backup-postgres.sh` from the root-owned timer. The coordinated backup creates a brief maintenance window: it takes the lock, stops only the API, dumps the still-running database and archives attachments, then restarts the API even if backup creation fails. It is not an online snapshot. The script also uses umask 077, checksums, atomic rename, and retention. Credentials remain in the mode-0600 env file and container environment, not command arguments.

Install and enable the supplied nightly timer exactly as follows:

```sh
sudo install -o root -g root -m 0644 deploy/systemd/moodle-review-backup.service /etc/systemd/system/moodle-review-backup.service
sudo install -o root -g root -m 0644 deploy/systemd/moodle-review-backup.timer /etc/systemd/system/moodle-review-backup.timer
sudo install -o root -g root -m 0755 deploy/scripts/backup-postgres.sh /home/fldadmin/beta-testing-app/deploy/scripts/backup-postgres.sh
sudo systemctl daemon-reload
sudo systemctl enable --now moodle-review-backup.timer
systemctl list-timers moodle-review-backup.timer
```

`verify-pilot.sh` validates archive paths and checksums, restores the custom dump into a uniquely named disposable database in the existing PostgreSQL container, queries the restored `users` table, then always drops that database. It separately extracts attachments into a disposable directory, checks readability, and cleans it up. An empty attachments directory is valid. It never restores into the production database. A live restore requires approval, outage, a pre-restore backup, matching DB and attachment archives, migrations, and health checks.

Run `VERIFY_EMAIL=... VERIFY_PASSWORD=... deploy/scripts/verify-pilot.sh https://<machine>.<tailnet>.ts.net [archive]` using an existing approved pilot account. Do not place credentials in positional arguments or logs. The check verifies authenticated dashboard access, unauthenticated API rejection, exact Alembic head equality, and (when supplied) a disposable restore. Docker was unavailable in the packaging environment, so run the exact Compose config command and disposable restore on Ubuntu before sign-off.

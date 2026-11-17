# Sphere admin polish and publishing repair

Released 18 November 2026 NZ time. User approved the compact branded header and requested implementation without mockups.

## Public website

- The failed workflow lacked `SPHERE_PAGES_REPOSITORY_TOKEN`. Replaced that unused dependency with a dedicated write-enabled SSH deployment key for the target repository only, consistent with [GitHub's deploy-key guidance](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys).
- Target deploy-key ID: `170231744`, title `Sphere public site publishing (radcra Actions)`. Private half is stored only as the source repository Actions secret `SPHERE_PAGES_DEPLOY_KEY`; the temporary local key and host-file copies were removed after successful authentication testing. No personal OAuth token was copied into Actions.
- Workflow uses strict host verification against GitHub's HTTPS metadata, temporary mode-0600 key storage and exit cleanup; checkout credentials are not persisted. Existing target path ownership remains `sphere` and `radcra` only. Concurrent publish jobs are serialized.
- Feature-branch proof run [44155915920](https://github.com/radicalmove/radcra/actions/runs/44155915920) passed and pushed target commit `43929ab641a9a7af17751bff5c4252b96e606c44`. GitHub Pages reported that commit built successfully; public Sphere and support URLs returned HTTP 200.
- Publication-only repair is on `main` at `f30d310eee9ea6f2b01d303cd2106a46e6ad5c8b`; it contains only the workflow and its regression test. Its automatic [main run 44156186226](https://github.com/radicalmove/radcra/actions/runs/44156186226) also passed. No unrelated local website-copy edits were published.

## Admin presentation

- Commit `1c0cd5f` provides a shared Sphere logo/banner/navigation shell, white cards on a pale-blue surface, readable status labels and role names, larger consistently spaced controls, pending requests first, and scroll-contained tables.
- Reviewer transfers now use the same admin shell, with side-by-side course information on desktop and stacked information on phones. Confirmation requirements, CSRF fields and form actions remain unchanged.
- Only four production presentation files changed: `admin.css`, `admin/shell.html`, `admin/users.html`, `admin/course_migration.html`. No handler, database model, schema, permission or mail-policy changes were included.
- Fresh full backend suite: **330 passed**, one existing Starlette/httpx deprecation warning. Two browser access/transfer/email-proof/extension-reconnection tests passed. Two additional desktop/mobile (1280px and 390px) browser tests passed, including pending requests, long names/emails, disclosure tables, no document overflow and natural checkbox sizing. Screenshots were visually inspected; status wrapping and adjacent action spacing were corrected and retested. All browser data/mail were synthetic loopback fixtures.
- Independent review reported no actionable blockers before deployment. Reviewer safeguards included private temporary credential storage and retaining both prior service override configurations.

## Live release verification

- Current release: `/home/fldadmin/sphere-admin-release.kwwv6cEp/server` on fld-mini. Prior release `/home/fldadmin/sphere-course-release.lJ2wGYsi/server` retained. New `99-sphere-admin-polish.conf` working-directory overrides apply to both app and mail worker; prior override copies retained privately in the release directory.
- Read-only pre/post checks matched user/course/membership/comment/location/reply/share/audit fingerprints and every approved user's UCO roles and visible comment IDs. Schema remains `20261118_18`; LEARN3598 remains the sole enabled course.
- Both deployed templates rendered against real data in a read-only transaction. Actual HTTPS health, CSS and logo endpoints returned 200; unauthenticated admin access returned 401. Live checks did not create an admin login session, new reviewer, real email or comment.
- App health passed after restart. Notification timer resumed, and its next automatic run from the new release completed with success/exit0. Backup timer remains enabled. No database migration or new data restore was required for this presentation-only release.
- To roll back this presentation change, move both new working-directory overrides aside, reload user systemd units and restart the app; restore both processes to the retained prior release. No data downgrade is needed.
- Chrome Store 0.6.17, extension installation and unrelated pending extension/help/site edits remain unchanged.

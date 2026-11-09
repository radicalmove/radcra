# Sphere 0.6.17 unified upgrade candidate

Not deployed. One extension ID and one backend for UCO Moodle and LEARN. Roles and feedback are scoped to each course; Moodle origin is part of course identity.

## Database rehearsal

The read-only PostgreSQL snapshot stayed on the existing host and was restored into a private temporary cluster with no TCP listener. The upgrade ran from `20261107_15` through `20261110_17`. Row fingerprints matched before and after migration for all existing data columns except the intentionally normalized course number and origin, which were validated separately. This included 19 users, 10 courses, 15 memberships, 158 comments, 158 locations, 13 replies, 272 status events, 598 sessions and 428 device-credential rows. The clone and dump were automatically removed.

All 13 approved UCO memberships exercised returned their recorded roles and, collectively, 146 distinct visible comments. They could not use those sessions to access LEARN. Equal numeric course IDs on opposite sites resolved to different Sphere courses. A copied UCO reviewer gained separately approved LEARN access using their existing account ID; their UCO role was unchanged.

No active unscoped non-admin extension sessions were present at snapshot time. Six copied reviewer accounts had non-mail-eligible addresses; their rows and memberships were retained, but they cannot use email confirmation with those addresses. No email was sent.

Backend: 284 tests passed. Extension: 538 tests passed, 9 skipped; TypeScript checking passed.

## Candidate build

Use the existing pilot's public manifest key, the existing Sphere HTTPS service origin, and both exact content-script patterns: `https://my.uconline.ac.nz/*` and `https://learn.canterbury.ac.nz/*`. Keep the reviewed Articulate optional permission. Build in production mode with the commit SHA; write only to a new versioned candidate directory, leaving `current`, the live service and the Store unchanged.

Do not install or circulate the candidate as a live update yet. Review the non-mail-eligible accounts, the configuration for real email, and the rollout/rollback procedure first. The rehearsal did not verify real SMTP or change the Chrome Store submission.

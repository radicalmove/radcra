# LEARN 3598 real access-request test

18 November 2026 NZ time. User authorized a real SME request for `rcadavies@gmail.com`, admin notification, approval and email confirmation. No unrelated account or course grants were authorized or made.

## Passed against the live service

- Signed in to the actual admin UI with the browser's saved admin login. Requested access in the same Chrome profile using Name, Email and requested role SME, without a reviewer password.
- Pending requests increased from 0 to 1. It showed the existing account and an advisory requested SME role, with email unverified. No automatic approval occurred.
- The existing scheduled mail timer, not a manual send, delivered `Sphere: Course access request`. Verified the actual message in the recipient Gmail inbox at 08:31 NZ: correct name, address, LEARN3598, requested SME role and `/admin` link. Sender was Sphere Notifications.
- Approved through the normal admin form with the actual course role set to SME. Pending requests returned to 0; the LEARN course reviewer table showed SME/approved.
- The scheduled worker delivered `Sphere: Course access approved` at 08:34 NZ. Verified the actual inbox message, assigned SME role, course link, same-profile and 20-minute confirmation instructions.
- Opened that email's link in the requesting Chrome profile and selected Confirm email. Sphere displayed `Email verified. You already have access to this course.` with the exact LEARN3598 link and Check access instruction. Took a browser screenshot of that success page.
- Read-only database checks confirmed: one existing account reused (19 total users), global role still beta_tester, a separately approved SME membership only for LEARN3598, confirmed course-onboarding challenge, all its mail flags drained, and no extension exchange yet. Comments remain 158; no test comment or unrelated account was created.
- Public Tailscale Funnel is enabled for the live HTTPS service; the hostname is not limited to devices joined to the tailnet. App, mail timer and backup timer are enabled for startup, and user lingering is enabled. This verifies configuration and current health, not a newly repeated power-failure recovery test.

## Store browser gate, subsequently completed

Initially Sphere did not appear on LEARN or on a freshly opened UCO page in the selected Chrome profile. The user supplied a Chrome extensions screenshot identifying the manually loaded Sphere **0.6.12**, extension ID beginning `omcaf…`, rather than Store item `mohajifpffgbmkelnpdibcebmjpjngak`.

Browser automation was denied access to Chrome's internal extension-management page and to the Store page. No alternate internal API or filesystem-profile bypass was used. The user installed the official Store copy manually. After installation, a page screenshot revealed the first-run notice; the DOM-only snapshot had not included Sphere's shadow UI. Used supported native accessibility controls on the Moodle page to continue testing that UI. No extension-settings action was automated.

- Actual Store0.6.17 appeared on LEARN, and its first-run privacy notice was acknowledged. Sign in → Check access exchanged the already-confirmed request and showed `Test user · Subject Matter Expert`, `Connected`, version0.6.17. This is the existing test account's retained display name, not a duplicate account.
- Navigated to the real LEARN Page activity1260925 and reloaded it; the SME identity and Connected state persisted. Read-only backend verification confirmed the challenge was exchanged, all its mail flags cleared, the global account role stayed beta_tester and the course role stayed SME.
- Switched to real UCO CRJU160 and used the existing administrator login via Admin sign-in. The Store copy displayed Richard Davies/Administrator/Connected and the eight existing unresolved comments, including their original markers. No comments were posted, resolved or deleted.
- Admin sign-in intentionally stores a global course-team session, which takes precedence over reviewer sessions (`background.ts:courseTeamToken`, `resolveCourse`, `client`). Returning to LEARN therefore shows the existing administrator identity until signing out of admin mode. This is an explicit authenticated mode switch, not a change to the SME membership. Added this distinction to the getting-started instructions.
- The live request → admin email → approval → confirmation email → confirmation → Store Check access → Connected flow has now passed. Chrome remains in administrator mode after the UCO regression check; the underlying email reviewer has separately approved SME membership on LEARN3598. No Store upload or publishing change was made.

## Sharing instructions prepared

The existing pending installation/help documentation was reviewed, completed and committed. Public homepage/download now point reviewers to the Store, not nonexistent release ZIPs. Public support includes the passwordless request/approval/confirmation/Check access sequence, same-profile requirement, mail delay, expired-link recovery, missing-panel steps and old-pilot-to-Store guidance. Privacy wording and URL contracts were preserved; the old metadata feed is explicitly labelled legacy pilot metadata.

All **68** root release/deployment/public-site tests passed using the project virtual environment and its pinned Pillow12 build dependency on PATH. Updated the obsolete root workflow assertions to match the already-verified dedicated SSH deployment key. Source commit `37c200d`; guidance-only main commit `b5f05270ad63aa6cfb8da6608cc45a1909b4154b`. Automatic publication run [44160989940](https://github.com/radicalmove/radcra/actions/runs/44160989940) succeeded, final Pages build `d9c0e43` reported built, and the public support page served the new instructions. A follow-up clarifies removing the old pilot only after validating the Store copy and explains administrator mode.

Comment notification delivery is still the existing pilot configuration. This test verifies access-request/approval emails on LEARN, not a new general all-course comment-notification rollout or compatibility with every Moodle activity type.

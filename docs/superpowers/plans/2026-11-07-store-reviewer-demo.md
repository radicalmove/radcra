# Store reviewer demo implementation plan

**Goal:** Give Google a working, isolated Moodle/Sphere review environment without changing CRJU160, the existing test Moodle, or submitting the draft.

**Architecture:** Install a fresh Moodle database and data directory from the existing code, not a copy of existing course/user data. A separate gateway on public HTTPS port 8443 serves the demo Moodle and its own Sphere API; the existing public port 443 mapping is unchanged. Compile this exact demo origin into the extension. Namespace sessions by service so demo credentials never go to the live API. The demo API provides password-gated, course-scoped reviewer access and blocks administration and registration routes. No email queue is enabled. Credentials stay outside Git and are entered only into Google's confidential Test instructions.

**Tech stack:** Moodle PHP CLI, MariaDB, Python/FastAPI, SQLite, systemd user services, Tailscale Funnel, TypeScript, Chrome.

- [x] Add routing/isolation tests, then implement exact-origin demo routing and separately stored demo sign-ins.
- [x] Add demo API tests for password gating, one-use course-bound codes, protected administration, and isolated seeded courses. Implement only the demo wrapper.
- [x] Install empty Moodle/demo databases in new directories, create two sample courses and a restricted Moodle user, and start new loopback services. Enable only the new Funnel ports; do not change the existing port-443 mapping.
- [x] Test the actual extension from a clean Chrome profile against the demo, including comments, navigation, resolution and course switching.
- [ ] Package a new Store-only version, fill listing/privacy fields, set Unlisted, and add confidential reviewer instructions. Pause before policy certifications that need the user's confirmation; never submit for review.

## Verification and operational notes

The public clean-profile Chrome test exercises Moodle login, separate password-gated Sphere access for both dummy courses, highlight creation, navigation, reply, resolution and return to the first course. Server suite: 214 passing. Extension suite: 535 passing, nine intentionally skipped; the additional narrow-path manifest regression test also passes. Store packaging/site checks: 23 passing.

Use a fresh Chrome profile for Store review. Cookies are hostname-scoped, not port-scoped: although the gateway discards non-demo cookies before forwarding and the demo Moodle uses its own cookie name, an existing browser profile could send same-host pilot cookies to the gateway. Extension access credentials are separately namespaced and routed by exact origin. The demo contains no copied user/course data and sends no email (`noemailever` plus disabled PHP sendmail).

The public information-site repository was absent and its existing links returned 404. A static-only `radicalmove.github.io` repository was created to serve the existing Sphere information, privacy and support pages. No pilot extension release or live course deployment is part of this change.

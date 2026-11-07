# Multi-course reviewer access implementation plan

**Goal:** Reopen any previously approved course in the same Chrome profile without another email link.

**Design:** Keep reviewer device credentials in trusted local storage and access tokens in session storage, both keyed by the confirmed server course ID. Resolve that ID from the Moodle course identity before sending authenticated requests. Preserve legacy single-course access on upgrade, keep administrator authentication separate, and clear all local sign-ins on explicit sign-out or policy reset. Server-side membership and permissions remain authoritative.

- [x] Reproduce switching in a fresh persistent Chrome profile against two isolated course fixtures. Assert course-specific requests and rerun after restarting Chrome.
- [x] Add scoped storage, migration, renewal and clearing tests. Route resolution and all comment operations through the right token.
- [x] Run the unit and browser regressions and type checking. Do not deploy or touch the CRJU160 pilot or Store draft.

From `extension/`, run the local browser fixture with:

```sh
REVIEW_SERVICE_ORIGIN=http://127.0.0.1:48139 npm run build
SPHERE_COURSE_SWITCH_FIXTURE=1 npx playwright test e2e/reviewer-course-switching.spec.ts
```

Set `SPHERE_EXTENSION_TEST_CHROME` to an installed Chrome for Testing executable if the Playwright default is unavailable. The test provisions two approved fixture memberships without sending email or connecting to a live service.

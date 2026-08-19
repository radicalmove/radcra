# Chrome Web Store listing — private beta

Use this exact copy for the private trusted-testers item.

## Listing fields

**Name:** `Sphere - Course Review App (BETA)`

**Short description:** `Review configured Moodle course pages with contextual comments and markers.`

**Category recommendation:** Productivity (Education if Productivity is unavailable).

**Detailed description:**

> **THIS EXTENSION IS FOR BETA TESTING.** Sphere helps authorised course-team reviewers record, discuss, navigate to, and resolve contextual feedback on configured Moodle pages and optionally approved Rise/SCORM content. Comments show the author's first name before the quoted excerpt, while the full display name remains available to assistive technology. The toolbar's chevron control clearly exposes Minimise comments and Expand comments states. Sphere never changes Moodle content.
>
> Sphere handles reviewer name, email, role, and approval status; authentication, session, reconnect, and device credentials; course/page URLs and activity/SCORM identifiers, titles, and current location; comments, replies, statuses, timestamps, selected text, visual anchors, and optional screenshots and attachments submitted only at the reviewer's request; and browser/build, navigation, reliability, and error diagnostics. Authorised course-team members may read course-review content. Service operator staff do not routinely read it and may access specific data only on explicit user request about that data, for security or abuse, or legal obligation. Internal operational or improvement use is limited to aggregated and anonymised data.
>
> GitHub Pages receives ordinary request metadata: IP address, user agent, request time, and requested path. Sphere sends it no Moodle content, review content, credentials, or tokens. See https://radicalmove.github.io/sphere/privacy/ and https://radicalmove.github.io/sphere/support/.

**Single purpose:** `Help an authorised reviewer record, discuss, navigate, and resolve contextual feedback on configured Moodle course pages.`

## Permission and host justifications

| Permission/host | Justification |
| --- | --- |
| `identity` | Opens the approved reviewer authentication flow and validates its exact callback. |
| `storage` | Stores bounded session/access and reconnect state and optional-host coordination, panel preferences, update-check state, and policy acknowledgement. |
| `scripting` | Registers and injects the packaged content script only on approved optional embedded hosts. |
| `webNavigation` | Observes trusted top-level navigation and enumerates the current-tab frame hierarchy. |
| configured Moodle host patterns | Runs Sphere only on approved Moodle origins; no `<all_urls>` access. |
| configured HTTPS review-service origin | Sends authenticated course-review operations to the configured service. |
| `https://radicalmove.github.io/sphere/*` | Reads strictly validated `latest.json` version metadata. It reads no Moodle content or credentials and cannot supply executable behaviour. |
| optional Rise/SCORM host patterns | Requested by user action only for an approved embedded activity; denial preserves the parent-page path. |

No `downloads`, `<all_urls>`, or private-key permission is requested.

## Privacy dashboard choices

| Dashboard category | Choice | Declaration |
| --- | --- | --- |
| Personally identifiable information | Yes | reviewer name, email, role, approval and membership identifiers |
| Health information | No | not requested; educational course content is Website content |
| Financial and payment information | No | not collected |
| Authentication information | Yes | short-lived tokens and reconnect/device credentials |
| Personal communications | Yes | comments, replies, statuses and intentionally attached files |
| Location | No | not collected |
| Web history | Yes | configured Moodle/course/page/SCORM URLs used for context navigation |
| User activity | Yes | review actions and bounded navigation/reliability diagnostics |
| Website content | Yes | selected text, titles, visual anchors, requested screenshots and course context |

**Remote code:** `No`. Sphere neither downloads nor executes remote code; GitHub metadata never controls executable behaviour.

Certify every Limited Use statement: data is not sold; is not used or transferred outside the single purpose; is not used or transferred for creditworthiness or lending; is not used for personalised advertising; and transfers and human access are limited to disclosed permitted cases. Sphere complies with the Chrome Web Store User Data Policy, including Limited Use.

**Homepage:** https://radicalmove.github.io/sphere/

**Privacy:** https://radicalmove.github.io/sphere/privacy/

**Support:** https://radicalmove.github.io/sphere/support/

**Update metadata:** https://radicalmove.github.io/sphere/latest.json

Distribute only to approved private trusted testers. Supply reviewer credentials and private URLs only in Store Test instructions or another approved private channel. Upload the exact root-level `sphere-web-store-v0.6.0.zip`; compare the Store Item ID and public key with the accepted pilot identity before submission. Use the generated Sphere promo tile and a genuine current product screenshot; do not fabricate Store evidence.

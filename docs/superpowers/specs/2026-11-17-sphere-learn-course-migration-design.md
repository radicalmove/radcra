# Sphere: normal LEARN access and course migration

## Outcome

Use the existing Sphere extension and accounts on both UCO Moodle and LEARN. Replace the single-course LEARN trial with administrator-controlled email onboarding per LEARN course. Treat the Moodle migration and the Sphere migration as separate operations: copying a Moodle course does not grant Sphere access or establish a mapping.

## Register and enable a LEARN course

Register a confirmed LEARN course using its canonical Moodle URL and numeric ID, scoped to the exact LEARN origin. Registration alone does not open reviewer requests. A Sphere administrator explicitly enables email onboarding for that course; the default is off. Keep the global switch off and preserve the UCO invitation, reconnect, and notification flows.

An unapproved reviewer submits their name, email and requested role. The administrator assigns the actual course role before the reviewer can confirm their email and connect that browser. An already approved reviewer can use their existing account; a new Chrome profile still requires email proof. The course setting and membership must be enforced in the server and mail worker, not just in the extension UI. Disabling enrollment stops new requests; revoking a membership is the separate way to remove already-approved access. The existing 3598 trial remains unchanged until its transition is explicitly tested and approved.

## Carry approved reviewer roles across

The administrator supplies the original UCO URL and copied LEARN URL. Sphere validates both origins and resolves both registered courses by origin plus numeric ID. Never infer a match from course titles or equal numeric IDs. Show a preview of eligible approved reviewers and their proposed roles; apply only the entries and roles the administrator confirms.

Reuse the existing user ID and grant a separate LEARN membership. Exclude archived and unapproved accounts, suspended or pending memberships, and administrator privileges. Do not silently overwrite an existing target membership or undo a revocation; report those entries for manual review. Recheck eligibility when applying, record who approved the transfer, and make retries safe. Do not copy passwords, sessions, device credentials, invitation codes or pending requests.

## Comments and notifications

Keep historical comments, attachments, anchors and history attached to UCO. New LEARN comments belong to the LEARN course. Do not represent the two histories as automatically synced. Moving comments later requires a separate decision and verified destination anchors. Use captured email in staging and do not send batch migration announcements or emails upon creating or previewing a mapping.

## Verification and rollout

1. Test two different LEARN courses, including one with the same numeric ID as a UCO course. Verify opt-in, same-account sign-in, new-profile email proof, course-scoped access, and no mail for disabled courses.
2. Rehearse a mapping on a private database copy. Verify approved, pending, revoked, archived, already-present and changed-after-preview cases. Check that each original UCO role and all UCO comments remain unchanged. Repeat the apply operation to verify it creates no duplicates.
3. Test with the published Chrome build against an isolated server. Verify UCO and LEARN after switching between courses, including the existing 3598 trial. Review any extension copy or package changes separately before Store submission.
4. In production, enable only explicitly approved mappings and courses after a backup and staging sign-off. Roll out in batches and check UCO after each batch. Do not enable courses, copy memberships, migrate comments or change the Store as part of approving this design.

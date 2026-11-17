# Sphere administration polish and publishing repair

The user approved the compact branded-header approach and requested implementation without mockups. These are two independent, bounded changes.

## Administration presentation

Reuse the existing local Sphere logo, blue/white branding and system-font stack. A shared admin shell provides the logo/wordmark, a compact blue banner, navigation to course access, reviewer transfers and the review dashboard, a skip link and a quiet footer. Clearly indicate the active navigation item. Preserve existing route names, permissions, CSRF, form field names, approval rules and actions.

The course-access page retains pending requests first, with readable request cards and a clear empty state. Keep course selection and invitations grouped; put account archiving/restoration in secondary disclosure sections. Use consistent button heights, form spacing, status chips and table headers. Destructive actions remain visually distinct. The migration page uses the same full-width shell instead of the narrow login card, with readable source/target information and explicit confirmations unchanged. Scope styles to admin pages; do not restyle reviewer login or extension screens. Support keyboard focus, small screens and horizontally scrollable data tables without page overflow. No external fonts, images, scripts or new JavaScript.

## Public-site publication

The missing `SPHERE_PAGES_REPOSITORY_TOKEN` prevented the GitHub Actions workflow from updating the external public-site repository. Replace that absent broad credential with a dedicated write-enabled SSH deployment key restricted to `radicalmove/radicalmove.github.io`. Store only its public half as a target deploy key and its private half in the source repository Actions secret `SPHERE_PAGES_DEPLOY_KEY`; never expose either private key or personal OAuth credentials in code/logs. Use verified GitHub host keys from its HTTPS metadata API and strict SSH host checking. Keep target write paths limited to the existing `sphere` and `radcra` directories; preserve all other target content.

Verify cloning and a successful workflow dispatch of the committed source, then confirm the target deployment and public pages. Publish only the existing committed site content, not unrelated pending copy edits. The Chrome Store and extension artifacts remain unchanged. Deploy the presentation-only backend changes as a separate retained release with health and existing-data checks; no schema update is needed.

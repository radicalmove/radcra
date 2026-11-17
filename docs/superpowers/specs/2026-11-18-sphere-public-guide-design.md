# Sphere public installation and access guide

The user approved one detailed guide with a jump menu, numbered steps, expected results and separate troubleshooting, plus clearer homepage/install links. No mockups are needed.

## Presentation

Reuse Sphere's existing logo and high-contrast blue/white palette. Add one self-hosted stylesheet and local logo asset for the homepage, install page and support guide. Use semantic headings, a skip link, visible focus, readable line lengths and responsive cards. On desktop the guide has a sticky section menu; on phones navigation flows above the article with no page overflow. No JavaScript, trackers, forms, remote fonts or new services.

## Content

Keep `/sphere/support/#getting-started` working as the main start-of-guide anchor. Provide clear navigation for installation, first-time requests, confirmation/connection, returning reviewers/new computers, old Sphere/RADCRA pilots, role visibility, course teams, troubleshooting and privacy/support. Number actions and place concise expected-result notes alongside them. Be explicit that Moodle access, Sphere approval, email confirmation and browser connection are separate steps.

Email-approved courses use Name/Email/requested role, admin approval, an email confirmation in the same Chrome profile within20minutes, then Check access. Scheduled mail may take a few minutes. Returning approved users should sign in, not create duplicate requests; a different Chrome profile or computer may need a fresh link. Administrator sign-in is a separate global mode. Legacy UCO invitation/code routes may differ; contact the course team rather than claiming all courses use email onboarding.

Old-copy instructions: install the Store copy, disable the unpacked copy, connect and verify the expected comments, then remove only the old copy. Explain that server-held comments/approvals remain but old local extension state is removed. Do not claim automatic duplicate detection/removal exists.

Role descriptions must follow current service rules: beta testers see their own threads; SMEs also see SME-authored threads and threads shared with them; LD/DCDs manage course feedback/status; administrators use global admin mode. No new rights are implied by choosing a requested role. Retain privacy disclosure wording and the existing six URL contracts, compatibility fixtures and metadata schema. Never publish private course URLs, credentials or user screenshots.

## Verification and release

Add regression checks for guide sections, internal anchors, local assets and absent scripts. Run root tests, desktop/phone headless browser layout and keyboard checks, and visually inspect screenshots. Use a temporary loopback static server only. Review, commit and push only guide assets/pages/tests/docs; preserve the pending extension Help edit. Integrate only the website/doc change into main and verify successful Actions and final GitHub Pages build plus live page content/assets. Do not rebuild/upload the extension or deploy/restart the backend.

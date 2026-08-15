# Chrome Web Store pre-submission checklist — RADCRA 0.5.37

- [ ] Rename the GitHub repository to `radcra`, update the local `origin` remote, push the reviewed tag/commit, enable GitHub Pages deployment through Actions, and confirm https://github.com/radicalmove/radcra.
- [ ] Verify unauthenticated HTTPS responses for homepage, privacy, support, and latest JSON: https://radicalmove.github.io/radcra/, `/privacy/`, `/support/`, and `/latest.json`.
- [ ] Set `MOODLE_HOST_PATTERNS` and `OPTIONAL_FRAME_PATTERNS` from the approved deployment configuration; set `REVIEW_SERVICE_ORIGIN` from the live HTTPS service; use `EXTENSION_PUBLIC_KEY` securely derived from `EXTENSION_PRIVATE_KEY_PEM` and compared with the accepted pilot identity; and use `BUILD_COMMIT` automatically derived from the exact tagged GitHub commit. Keep the secret out of files, logs, artifacts, and Pages.
- [ ] Generate the exact ZIP `radcra-web-store-v0.5.37.zip` from the tagged commit, verify manifest-at-root, checksum, production origins, key identity, contents, and a clean-profile load/smoke test.
- [ ] Enter the exact listing and all nine Privacy dashboard selections, Remote code No, and every Limited Use certification.
- [ ] Choose private trusted testers only and supply reviewer credentials/private test URLs solely in Store Test instructions or another approved private channel.
- [ ] Upload the exact ZIP, compare the Chrome Web Store Item ID and public key against the accepted pilot identity, and stop on any mismatch.
- [ ] Upload the required 128 px icon, compliant screenshot(s), and promotional tile; inspect all assets at dashboard size.
- [ ] Paste the listing, privacy/support/homepage URLs, distribution, and reviewer instructions exactly; run the reviewer guide against the submitted package/account.
- [ ] Select deferred publishing for the first review. Do not publish or invite testers until explicit release approval.

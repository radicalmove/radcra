# Sphere Chrome Web Store artwork

`sphere-promo-440x280.png` is the generated 440×280 promotional tile for the Sphere listing. Upload it only to the matching Chrome Web Store promotional-image field; extension icons remain in `extension/public/icons/`.

Before every upload, regenerate the artwork from the repository scripts, visually compare it with the committed image, and confirm its dimensions and text. Sanitize the upload set by removing screenshots, metadata exports, drafts, hidden files, unrelated logos, university branding, Google branding, user information, and internal review notes. Upload only the final PNG files requested by the Store form.

Source and provenance details are recorded in `source/README.md`.

## Manual screenshot gate

`sphere-screenshot-1280x800.png` must be captured manually from the real, current Sphere 0.6.0 product. The image must show the Sphere overlay and a contextual marker or comment at exactly 1280×800 pixels. Do not fabricate the interface, substitute an older-version screenshot, or reuse test-fixture artwork.

Before committing or uploading the screenshot, confirm that it contains no credentials, browser-profile details, student records, private email addresses, tokens, invitation details, or private URLs. Arrange the page to keep private information out of the capture where possible; any sanitisation must preserve the genuine overlay and contextual-review behaviour.

Keep the Store screenshot as listing artwork beside the promotional tile. It is a separate Chrome Web Store upload and must never be copied into the extension directory or Web Store ZIP. Until an authorised capture is available, omit the file: fixture-mode readiness remains green and reports `manual_screenshot_required: true`, while submission readiness remains blocked on the screenshot gate.

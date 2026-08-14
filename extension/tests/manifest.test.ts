import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import test from "node:test";
import { loadBuildConfig } from "../src/build-config.ts";

const extensionName = "RADCRA — Course Review (BETA)";
const extensionDescription = "Review configured Moodle course pages with comments, highlights, and review markers. THIS EXTENSION IS FOR BETA TESTING.";
const updateMetadataHostPermission = "https://radicalmove.github.io/Beta-testing-app/*";

function assertRgbaPng(path: URL, expectedSize: number): void {
  const png = readFileSync(path);
  assert.deepEqual([...png.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
  assert.equal(png.readUInt32BE(16), expectedSize);
  assert.equal(png.readUInt32BE(20), expectedSize);
  assert.equal(png[25], 6, "icon must use RGBA PNG colour type");
}

test("generated manifest keeps optional hosts out of static injection", () => {
  execFileSync(process.execPath, ["./node_modules/vite/bin/vite.js", "build"], { stdio: "pipe" });
  const manifest = JSON.parse(readFileSync(new URL("../dist/manifest.json", import.meta.url), "utf8"));
  const expected = loadBuildConfig(process.env);

  assert.deepEqual(manifest.content_scripts[0].matches, expected.moodlePatterns);
  assert.deepEqual(manifest.optional_host_permissions, expected.optionalPatterns);
  assert.equal(manifest.content_scripts[0].all_frames, true);
  assert.equal(manifest.content_scripts[0].match_about_blank, true);
  assert.equal(manifest.content_scripts[0].match_origin_as_fallback, true);
  assert.deepEqual(manifest.background, { service_worker: "background.js" });
  assert.equal(JSON.stringify(manifest).includes("<all_urls>"), false);
  assert.deepEqual(manifest.permissions.sort(), ["identity", "scripting", "storage", "webNavigation"]);
  assert.equal(manifest.name, extensionName);
  assert.equal(manifest.description, extensionDescription);
  assert.match(manifest.description, /THIS EXTENSION IS FOR BETA TESTING/);
  assert.deepEqual(manifest.icons, {
    16: "icons/icon16.png",
    48: "icons/icon48.png",
    128: "icons/icon128.png",
  });
  assert.ok(manifest.host_permissions.includes(updateMetadataHostPermission));
  for (const size of [16, 48, 128]) {
    assertRgbaPng(new URL(`../public/icons/icon${size}.png`, import.meta.url), size);
    assertRgbaPng(new URL(`../dist/icons/icon${size}.png`, import.meta.url), size);
  }
});

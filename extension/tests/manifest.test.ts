import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import test from "node:test";
import { inflateSync } from "node:zlib";
import { loadBuildConfig } from "../src/build-config.ts";

const extensionName = "Sphere - Course Review App (BETA)";
const extensionDescription = "Review configured Moodle course pages with comments, highlights, and review markers. THIS EXTENSION IS FOR BETA TESTING.";
const updateMetadataHostPermission = "https://radicalmove.github.io/sphere/*";

function assertRgbaPng(path: URL, expectedSize: number): void {
  const png = readFileSync(path);
  assert.deepEqual([...png.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
  assert.equal(png.readUInt32BE(16), expectedSize);
  assert.equal(png.readUInt32BE(20), expectedSize);
  assert.equal(png[25], 6, "icon must use RGBA PNG colour type");
}

function pngAlphaBounds(path: URL): [number, number, number, number] {
  const png = readFileSync(path);
  const width = png.readUInt32BE(16);
  const height = png.readUInt32BE(20);
  const chunks: Buffer[] = [];
  for (let offset = 8; offset < png.length;) {
    const length = png.readUInt32BE(offset);
    if (png.toString("ascii", offset + 4, offset + 8) === "IDAT") {
      chunks.push(png.subarray(offset + 8, offset + 8 + length));
    }
    offset += length + 12;
  }
  const raw = inflateSync(Buffer.concat(chunks));
  const stride = width * 4;
  const rows: Buffer[] = [];
  let previous = Buffer.alloc(stride);
  const paeth = (a: number, b: number, c: number): number => {
    const p = a + b - c;
    const pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
    return pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
  };
  for (let y = 0; y < height; y++) {
    const filter = raw[y * (stride + 1)];
    const row = Buffer.from(raw.subarray(y * (stride + 1) + 1, (y + 1) * (stride + 1)));
    for (let x = 0; x < stride; x++) {
      const left = x >= 4 ? row[x - 4] : 0;
      const up = previous[x];
      const upperLeft = x >= 4 ? previous[x - 4] : 0;
      if (filter === 1) row[x] = (row[x] + left) & 0xff;
      else if (filter === 2) row[x] = (row[x] + up) & 0xff;
      else if (filter === 3) row[x] = (row[x] + Math.floor((left + up) / 2)) & 0xff;
      else if (filter === 4) row[x] = (row[x] + paeth(left, up, upperLeft)) & 0xff;
      else assert.equal(filter, 0, `unsupported PNG filter ${filter}`);
    }
    rows.push(row);
    previous = row;
  }
  const xs: number[] = [];
  const ys: number[] = [];
  rows.forEach((row, y) => {
    for (let x = 0; x < width; x++) {
      if (row[x * 4 + 3] !== 0) {
        xs.push(x);
        ys.push(y);
      }
    }
  });
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs) + 1, Math.max(...ys) + 1];
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
  assert.deepEqual(manifest.permissions.sort(), ["activeTab", "identity", "scripting", "storage", "webNavigation"]);
  assert.equal(manifest.action.default_popup, "sphere-controls.html");
  assert.equal(manifest.name, extensionName);
  assert.equal(manifest.description, extensionDescription);
  assert.match(manifest.description, /THIS EXTENSION IS FOR BETA TESTING/);
  assert.deepEqual(manifest.icons, {
    16: "icons/icon16.png",
    48: "icons/icon48.png",
    128: "icons/icon128.png",
  });
  assert.ok(manifest.host_permissions.includes(updateMetadataHostPermission));
  assert.doesNotMatch(JSON.stringify(manifest), /radicalmove\.github\.io\/radcra/);
  assert.doesNotMatch(JSON.stringify(manifest), /Beta-testing-app|RADCRA — Course Review \(BETA\)/);
  for (const size of [16, 48, 128]) {
    assertRgbaPng(new URL(`../public/icons/icon${size}.png`, import.meta.url), size);
    assertRgbaPng(new URL(`../dist/icons/icon${size}.png`, import.meta.url), size);
  }
  const bounds = pngAlphaBounds(new URL("../public/icons/icon128.png", import.meta.url));
  assert.ok(
    bounds[0] >= 16 && bounds[1] >= 16 && bounds[2] <= 112 && bounds[3] <= 112,
    `128px icon artwork must fit within (16,16,112,112), got (${bounds.join(",")})`,
  );
});

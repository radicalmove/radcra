import { chromium, expect, test } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";

test("unpacked Sphere pauses and resumes the injected overlay", async () => {
  const extension = process.env.SPHERE_EXTENSION_TEST_DIR ?? fileURLToPath(new URL("../dist", import.meta.url));
  const context = await chromium.launchPersistentContext("", {
    channel: "chromium", executablePath: process.env.SPHERE_EXTENSION_TEST_CHROME ?? chromium.executablePath(), headless: true,
    ignoreDefaultArgs: ["--disable-extensions"],
    args: [`--disable-extensions-except=${extension}`, `--load-extension=${extension}`],
  });
  try {
    const manifest = JSON.parse(readFileSync(`${extension}/manifest.json`, "utf8"));
    const site = new URL(manifest.content_scripts[0].matches[0]).origin;
    const id = createHash("sha256").update(Buffer.from(manifest.key, "base64")).digest("hex").slice(0, 32).replace(/./g, (digit) => String.fromCharCode(97 + parseInt(digit, 16)));
    const controls = await context.newPage();
    await controls.goto(`chrome-extension://${id}/sphere-controls.html`);
    await expect(controls.getByRole("button", { name: "Pause Sphere" })).toBeVisible();
    await context.route(`${site}/**`, (route) => route.fulfill({ contentType: "text/html", body: "<h1>Fixture course</h1>" }));
    const moodle = await context.newPage();
    const errors: string[] = [];
    moodle.on("pageerror", (error) => errors.push(error.message));
    const cdp = await context.newCDPSession(moodle);
    await cdp.send("Runtime.enable");
    cdp.on("Runtime.exceptionThrown", ({ exceptionDetails }) => errors.push(exceptionDetails.exception?.description ?? exceptionDetails.text));
    await moodle.goto(`${site}/course/view.php?id=1`);
    await expect(moodle.getByRole("heading", { name: "Fixture course" })).toBeVisible();
    const overlay = moodle.locator("#moodle-course-review-overlay");
    await expect(overlay).toHaveCount(1).catch(async (error) => {
      const state = await controls.evaluate(async (site) => {
        const api = (globalThis as any).chrome;
        const tabs = await api.tabs.query({ url: `${site}/*` });
        try {
          return await api.scripting.executeScript({ target: { tabId: tabs[0]?.id }, func: () => ({ marker: document.documentElement.getAttribute("data-moodle-review-extension"), storage: Boolean((globalThis as any).chrome.storage) }) });
        } catch (error) { return String(error); }
      }, site);
      throw new Error(`${error.message}\nPage errors: ${errors.join("\n")}\nExtension state: ${JSON.stringify(state)}`);
    });
    await controls.getByRole("button", { name: "Pause Sphere" }).click();
    await expect(overlay).toHaveCount(0);
    await moodle.reload();
    await expect(overlay).toHaveCount(0);
    await controls.getByRole("button", { name: "Resume Sphere" }).click();
    await expect(overlay).toHaveCount(1);
  } finally { await context.close(); }
});

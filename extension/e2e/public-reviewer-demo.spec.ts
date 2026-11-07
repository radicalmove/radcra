import { chromium, expect, test } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { readFile, mkdtemp, rm } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";

const site = "https://fld-mini.tail4ccaba.ts.net:8443";
test("public demo: real Moodle login, course access, highlight, and course switching", async () => {
  test.skip(!process.env.SPHERE_PUBLIC_DEMO_CREDENTIALS, "Requires isolated demo reviewer credentials");
  test.setTimeout(90_000);
  const credentials = JSON.parse(await readFile(process.env.SPHERE_PUBLIC_DEMO_CREDENTIALS!, "utf8"));
  const profile = await mkdtemp(join(tmpdir(), "sphere-public-demo-"));
  const context = await chromium.launchPersistentContext(profile, {
    channel: "chromium",
    executablePath: process.env.SPHERE_EXTENSION_TEST_CHROME ?? chromium.executablePath(),
    headless: true, viewport: { width: 1280, height: 800 },
    ignoreDefaultArgs: ["--disable-extensions"],
    args: [`--disable-extensions-except=${fileURLToPath(new URL("../dist", import.meta.url))}`, `--load-extension=${fileURLToPath(new URL("../dist", import.meta.url))}`],
  });
  context.setDefaultTimeout(12_000);
  context.setDefaultNavigationTimeout(20_000);
  try {
    const page = await context.newPage();
    await page.goto(`${site}/course/view.php?id=2`);
    await page.locator("#username").fill(credentials.moodle_user);
    await page.locator("#password").fill(credentials.moodle_password);
    await page.locator("#loginbtn").click();
    await page.waitForURL(`${site}/course/view.php?id=2`);
    const panel = page.locator("#moodle-course-review-overlay");
    const accept = panel.getByRole("button", { name: "Continue", exact: true });
    await expect(panel).toHaveCount(1);
    await accept.click();
    const connect = async () => {
      await panel.locator('[data-action="authenticate"]').click();
      const popup = context.waitForEvent("page");
      await panel.getByRole("button", { name: "Check access" }).click();
      const auth = await popup;
      await auth.getByLabel("Demo password").fill(credentials.sphere_password);
      await auth.getByRole("button", { name: "Connect to this course" }).click();
      await expect(panel.locator("[data-viewer-line]")).toContainText("Demo Reviewer");
    };
    await connect();
    await page.getByText("This sentence deliberately contains a small spelling eror for reviewers to discuss.", { exact: true }).evaluate((node) => {
      const text = node.firstChild!;
      const range = document.createRange();
      range.selectNodeContents(text);
      getSelection()!.removeAllRanges(); getSelection()!.addRange(range);
      document.dispatchEvent(new Event("selectionchange"));
    });
    await panel.locator('[data-action="add-comment"]').click();
    await panel.locator("textarea").fill("Demo feedback: please correct the spelling of ‘error’.");
    await panel.locator("[data-save]").click();
    await expect(panel.locator('[role="dialog"]')).toHaveCount(0);
    await expect(page.locator("[data-moodle-review-stored-highlight]").last()).toBeAttached();
    await page.goto(`${site}/course/view.php?id=3`);
    await connect();
    await page.goto(`${site}/course/view.php?id=2`);
    await expect(panel.locator("[data-viewer-line]")).toContainText("Demo Reviewer");
    await expect(page.locator("[data-moodle-review-stored-highlight]").last()).toBeAttached();
    await panel.locator('[data-action="panel"]').click();
    await panel.locator('[data-comment-item]').filter({ hasText: "Demo feedback:" }).last().click();
    await expect(panel).toContainText("Demo feedback:");
    const thread = page.locator('[data-thread-popover]');
    await expect(thread).toContainText("Demo feedback:");
    await thread.getByRole('button', { name: 'Reply', exact: true }).click();
    await thread.locator('textarea').fill('Demo reply: checked against the sample text.');
    await thread.getByRole('button', { name: 'Save reply', exact: true }).click();
    await expect(thread).toContainText('Demo reply: checked against the sample text.');
    await thread.getByRole('button', { name: 'Resolve this comment', exact: true }).click();
    await panel.getByRole('button', { name: 'Resolve', exact: true }).click();
    await expect(thread).toContainText('Comment resolved.');
    await expect(thread).toHaveCount(0);
    await panel.locator('[data-comment-filter="resolved"]').click();
    await panel.locator('[data-comment-item]').filter({ hasText: 'Demo feedback:' }).last().click();
    await expect(thread).toContainText('Demo reply: checked against the sample text.');
    if (process.env.SPHERE_DEMO_SCREENSHOT) await page.screenshot({ path: process.env.SPHERE_DEMO_SCREENSHOT });
  } finally {
    await context.close();
    await rm(profile, { recursive: true, force: true });
  }
});

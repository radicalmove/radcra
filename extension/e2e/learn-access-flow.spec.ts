import { chromium, expect, request, test } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { POLICY_VERSION } from "../src/policy-consent.ts";

const service = "https://localhost:48140";
const sites = ["https://learn.canterbury.ac.nz", "https://my.uconline.ac.nz"];
const titles = ["Test Course - Richard D - Demo Course", "UCO isolated identity test"];
const reviewer = "stage-reviewer@example.com";
type Mail = { recipient: string; subject: string; body: string };

test("LEARN staging: admin-first access, confirmation and trusted two-host reconnect", async () => {
  test.skip(!process.env.SPHERE_LEARN_FLOW, "Requires disposable LEARN staging and test build");
  test.setTimeout(120_000);
  const extension = fileURLToPath(new URL("../dist", import.meta.url));
  const manifest = JSON.parse(await readFile(join(extension, "manifest.json"), "utf8"));
  expect(manifest.host_permissions).toEqual([...sites.map(site => `${site}/*`), `${service}/*`, "https://radicalmove.github.io/sphere/*"]);
  const profile = await mkdtemp(join(tmpdir(), "sphere-learn-chrome-"));
  const otherProfile = await mkdtemp(join(tmpdir(), "sphere-learn-new-device-"));
  const inbox = await request.newContext({ baseURL: service, ignoreHTTPSErrors: true });
  const mailbox = async () => {
    const result = await inbox.get("/__staging/inbox");
    expect(result.ok()).toBe(true);
    return result.json() as Promise<{ messages: Mail[]; admin_password: string }>;
  };
  const launch = async (directory = profile) => {
    const context = await chromium.launchPersistentContext(directory, {
      executablePath: process.env.SPHERE_EXTENSION_TEST_CHROME ?? chromium.executablePath(), headless: true,
      ignoreHTTPSErrors: true, ignoreDefaultArgs: ["--disable-extensions"],
      args: ["--ignore-certificate-errors", `--disable-extensions-except=${extension}`, `--load-extension=${extension}`],
    });
    context.setDefaultTimeout(12_000);
    for (const [index, site] of sites.entries()) await context.route(`${site}/**`, route => route.fulfill({
      contentType: "text/html", body: `<html><title>${titles[index]}</title><body class="course-3598"><h1>${titles[index]}</h1><main><p>Dummy staging course content. No live Moodle data.</p></main></body></html>`,
    }));
    return context;
  };
  try {
    let context = await launch();
    try {
      const worker = context.serviceWorkers()[0] ?? await context.waitForEvent("serviceworker");
      await worker.evaluate(async (version) => (globalThis as any).chrome.storage.local.set({ policyAcknowledgement: { version } }), POLICY_VERSION);
      const course = await context.newPage();
      const admin = await context.newPage();
      const panel = course.locator("#moodle-course-review-overlay");
      for (const [index, role, displayRole] of [[0, "sme", "Subject Matter Expert"], [1, "ld_dcd", "Learning Designer"]] as const) {
        await course.goto(`${sites[index]}/course/view.php?id=3598`);
        await panel.locator('[data-action="authenticate"]').click();
        const opened = context.waitForEvent("page");
        await panel.getByRole("button", { name: "Request access", exact: true }).click();
        const page = await opened;
        await expect(page.getByText(titles[index], { exact: true })).toBeVisible();
        await expect(page.locator('input[type="password"]')).toHaveCount(0);
        await page.getByLabel("Name", { exact: true }).fill("Staging Reviewer");
        await page.getByLabel("Email address", { exact: true }).fill(reviewer);
        await page.getByLabel("Requested role").selectOption("beta_tester");
        await page.getByRole("button", { name: "Request access", exact: true }).click();
        await expect(page.getByRole("status")).toContainText(/admin|approval/i);
        const requested = await mailbox();
        expect(requested.messages).toHaveLength(index * 2 + 1);
        expect(requested.messages.at(-1)).toMatchObject({ recipient: "stage-admin@example.com", subject: "Sphere: Course access request" });
        expect(requested.messages.filter(mail => mail.recipient === reviewer)).toHaveLength(index);

        await admin.goto(`${service}/admin`);
        if (index === 0) {
          await admin.getByLabel("Email", { exact: true }).fill("stage-admin@example.com");
          await admin.getByLabel("Password", { exact: true }).fill(requested.admin_password);
          await admin.getByRole("button", { name: "Sign in", exact: true }).click();
        }
        const pending = admin.locator("#pending-requests form").filter({ hasText: titles[index] });
        await expect(pending).toContainText(reviewer);
        await expect(pending).toContainText(/unverified|not.*verified|not.*confirmed/i);
        await pending.getByLabel("Course role").selectOption(role);
        await pending.getByRole("button", { name: "Approve", exact: true }).click();
        const approved = (await mailbox()).messages.at(-1)!;
        expect(approved.recipient).toBe(reviewer);
        expect(approved.body).toContain(`${sites[index]}/course/view.php?id=3598`);
        expect(approved.body).toMatch(role === "sme" ? /SME|subject matter expert/i : /learning designer/i);
        const link = approved.body.match(/https:\/\/localhost:48140\/reviewer-access\/verify#[a-f0-9]+/)?.[0];
        expect(link).toBeTruthy();
        await page.goto(link!);
        await page.getByRole("button", { name: "Confirm email", exact: true }).click();
        await expect(page.getByRole("status")).toContainText(/verified|confirmed/i);
        await expect(page.getByRole("link", { name: "Open course in Moodle" })).toHaveAttribute("href", `${sites[index]}/course/view.php?id=3598`);
        await page.screenshot({ path: `/private/tmp/sphere-learn-confirmed-${index}.png` });
        await page.close();
        await panel.getByRole("button", { name: "Check access", exact: true }).click();
        await expect(panel.locator("[data-viewer-line]")).toContainText(displayRole);
      }
      for (const [index, role] of [[0, "Subject Matter Expert"], [1, "Learning Designer"]] as const) {
        await course.goto(`${sites[index]}/course/view.php?id=3598`);
        await expect(panel.locator("[data-viewer-line]")).toContainText(role);
      }
    } finally { await context.close(); }
    context = await launch();
    try {
      for (const [index, role] of [[0, "Subject Matter Expert"], [1, "Learning Designer"]] as const) {
        const page = await context.newPage();
        await page.goto(`${sites[index]}/course/view.php?id=3598`);
        await expect(page.locator("[data-viewer-line]")).toContainText(role);
      }
      expect((await mailbox()).messages).toHaveLength(4);
    } finally { await context.close(); }
    context = await launch(otherProfile);
    try {
      const worker = context.serviceWorkers()[0] ?? await context.waitForEvent("serviceworker");
      await worker.evaluate(async (version) => (globalThis as any).chrome.storage.local.set({ policyAcknowledgement: { version } }), POLICY_VERSION);
      const course = await context.newPage();
      await course.goto(`${sites[0]}/course/view.php?id=3598`);
      const panel = course.locator("#moodle-course-review-overlay");
      await panel.locator('[data-action="authenticate"]').click();
      await panel.getByLabel("Email address").fill(reviewer);
      const [page] = await Promise.all([
        context.waitForEvent("page", { timeout: 5000 }),
        panel.locator('[data-email-signin]').click(),
      ]);
      await expect(page.getByLabel("Email address")).toHaveValue(reviewer);
      await expect(page.getByLabel("Name", { exact: true })).toHaveCount(0);
      await page.getByRole("button", { name: "Send sign-in link" }).click();
      await expect(page.getByRole("status")).toBeVisible();
      const { messages } = await mailbox();
      expect(messages).toHaveLength(5);
      expect(messages.at(-1)).toMatchObject({ recipient: reviewer, subject: "Sphere: Confirm your email" });
      const link = messages.at(-1)!.body.match(/https:\/\/localhost:48140\/reviewer-access\/verify#[a-f0-9]+/)?.[0];
      expect(link).toBeTruthy();
      await page.goto(link!);
      await page.getByRole("button", { name: "Confirm email", exact: true }).click();
      await expect(page.getByRole("status")).toContainText(/verified|confirmed/i);
      await panel.getByRole("button", { name: "Check access", exact: true }).click();
      await expect(panel.locator("[data-viewer-line]")).toContainText("Subject Matter Expert");
    } finally { await context.close(); }
  } finally {
    await inbox.dispose();
    await rm(profile, { recursive: true, force: true });
    await rm(otherProfile, { recursive: true, force: true });
  }
});

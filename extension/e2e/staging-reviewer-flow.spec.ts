import { chromium, expect, request, test } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const origin = "https://localhost:48140";
const moodle = "https://moodle.example.invalid";
const reviewerEmail = "stage-reviewer@example.com";
const adminEmail = "stage-admin@example.com";
const courseUrl = (index: number) => `${moodle}/course/view.php?id=${901 + index}`;
type Mail = { recipient: string; subject: string; body: string };

test("staging: request, verify, approve, and reconnect to two courses in Chrome", async () => {
  test.skip(!process.env.SPHERE_STAGING_REVIEWER_FLOW, "Requires the isolated staging server and loopback extension build");
  test.setTimeout(90_000);
  const extension = fileURLToPath(new URL("../dist", import.meta.url));
  const manifest = JSON.parse(await readFile(join(extension, "manifest.json"), "utf8"));
  expect(manifest.host_permissions).toEqual([`${moodle}/*`, `${origin}/*`, "https://radicalmove.github.io/sphere/*"]);
  const profile = await mkdtemp(join(tmpdir(), "sphere-staging-chrome-"));
  const inbox = await request.newContext({ baseURL: origin, ignoreHTTPSErrors: true });
  const mailbox = async () => {
    const response = await inbox.get("/__staging/inbox");
    expect(response.ok()).toBe(true);
    return response.json() as Promise<{ messages: Mail[]; admin_password: string }>;
  };
  const launch = async () => {
    const context = await chromium.launchPersistentContext(profile, {
      channel: "chromium",
      executablePath: process.env.SPHERE_EXTENSION_TEST_CHROME ?? chromium.executablePath(),
      headless: true,
      ignoreHTTPSErrors: true,
      ignoreDefaultArgs: ["--disable-extensions"],
      args: ["--ignore-certificate-errors", `--disable-extensions-except=${extension}`, `--load-extension=${extension}`],
    });
    context.setDefaultTimeout(9_000);
    await context.route(`${moodle}/**`, (route) => {
      const id = Number(new URL(route.request().url()).searchParams.get("id"));
      const title = `Staging course ${id === 901 ? "A" : "B"}`;
      return route.fulfill({ contentType: "text/html", body: `<html><title>${title}</title><body class="course-${id}"><h1>${title}</h1></body></html>` });
    });
    return context;
  };
  try {
    let context = await launch();
    try {
      const worker = context.serviceWorkers()[0] ?? await context.waitForEvent("serviceworker");
      await worker.evaluate(async () => (globalThis as any).chrome.storage.local.set({ policyAcknowledgement: { version: "2026-08-14" } }));
      const course = await context.newPage();
      const admin = await context.newPage();
      const panel = course.locator("#moodle-course-review-overlay");
      for (const [index, letter, role, displayRole] of [[0, "A", "sme", "Subject Matter Expert"], [1, "B", "ld_dcd", "Learning Designer"]] as const) {
        await test.step(`Request and approve access to course ${letter}`, async () => {
          await course.goto(courseUrl(index));
          await panel.locator('[data-action="authenticate"]').click();
          const requestTab = context.waitForEvent("page");
          await panel.getByRole("button", { name: "Request access" }).click();
          const page = await requestTab;
          await expect(page.getByText(`Staging course ${letter}`)).toBeVisible();
          await page.getByLabel("Name").fill("Staging Reviewer");
          await page.getByLabel("Email").fill(reviewerEmail);
          await page.getByRole("button", { name: "Email me a link" }).click();
          await expect(page.getByRole("status")).toContainText("Check your email");

          const queued = (await mailbox()).messages;
          expect(queued).toHaveLength(index * 3 + 1);
          expect(queued.at(-1)).toMatchObject({ recipient: reviewerEmail, subject: "Sphere: Confirm your email" });
          const verification = queued.at(-1)!.body.match(/https:\/\/localhost:48140\/reviewer-access\/verify#[a-f0-9]+/)?.[0];
          expect(verification).toBeTruthy();
          await page.goto(verification!);
          await page.getByRole("button", { name: "Confirm email" }).click();
          await expect(page.getByRole("status")).toContainText("Waiting for admin approval");
          await expect(page.getByRole("link", { name: "Open course in Moodle" })).toHaveAttribute("href", courseUrl(index));
          await page.close();

          const requested = await mailbox();
          expect(requested.messages.at(-1)).toMatchObject({ recipient: adminEmail, subject: "Sphere: Course access request" });
          await admin.goto(`${origin}/admin`);
          if (index === 0) {
            await admin.getByLabel("Email").fill(adminEmail);
            await admin.getByLabel("Password").fill(requested.admin_password);
            await admin.getByRole("button", { name: "Sign in", exact: true }).click();
          }
          const pending = admin.locator("#pending-requests form").filter({ hasText: `Staging course ${letter}` });
          await expect(pending).toContainText(reviewerEmail);
          await pending.getByLabel("Course role").selectOption(role);
          await pending.getByRole("button", { name: "Approve" }).click();
          await expect(admin.locator("#pending-requests")).toContainText("No course access requests waiting");

          const approved = (await mailbox()).messages.at(-1);
          expect(approved).toMatchObject({ recipient: reviewerEmail, subject: "Sphere: Course access approved" });
          expect(approved!.body).toContain(courseUrl(index));
          await panel.getByRole("button", { name: "Check access" }).click();
          await expect(panel.locator("[data-viewer-line]")).toContainText(`Staging Reviewer · ${displayRole}`);
        });
      }
      await course.goto(courseUrl(0));
      await expect(panel.locator("[data-viewer-line]")).toContainText("Subject Matter Expert");
      await course.goto(courseUrl(1));
      await expect(panel.locator("[data-viewer-line]")).toContainText("Learning Designer");
    } finally { await context.close(); }

    context = await launch();
    try {
      for (const [index, role] of [[0, "Subject Matter Expert"], [1, "Learning Designer"]] as const) {
        const course = await context.newPage();
        await course.goto(courseUrl(index));
        await expect(course.locator("[data-viewer-line]")).toContainText(role);
      }
      expect((await mailbox()).messages).toHaveLength(6);
    } finally { await context.close(); }
  } finally {
    await inbox.dispose();
    await rm(profile, { recursive: true, force: true });
  }
});

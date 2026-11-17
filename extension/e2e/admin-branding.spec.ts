import { expect, test } from "@playwright/test";

const base = "https://localhost:48144";
test.describe.configure({ mode: "serial" });

for (const width of [1280, 390]) {
  test(`Sphere admin branding and usable layout at ${width}px`, async ({ browser }, testInfo) => {
    test.skip(!process.env.SPHERE_COURSE_STAGING, "Requires loopback synthetic staging");
    test.setTimeout(45000);
    const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width, height: 950 } });
    const requesterContext = await browser.newContext({ ignoreHTTPSErrors: true });
    try {
      const initial = await (await context.request.get(base + "/__staging/inbox")).json();
      const page = await context.newPage();
      await page.goto(base + "/login?next=%2Fadmin");
      await page.getByLabel("Email", { exact: true }).fill("stage-admin@example.com");
      await page.getByLabel("Password", { exact: true }).fill(initial.admin_password);
      await page.getByRole("button", { name: "Sign in", exact: true }).click();
      await page.goto(base + "/admin/users?course_id=" + initial.courses.target);
      const enable = page.getByRole("button", { name: "Enable admin-approved email requests", exact: true });
      if (await enable.count()) await enable.click();
      const requester = await requesterContext.newPage();
      await requester.goto(base + "/reviewer-access/request/" + initial.courses.target);
      await requester.getByLabel("Name", { exact: true }).fill("New subject expert with a long display name for layout testing");
      await requester.getByLabel("Email address", { exact: true }).fill(`long-reviewer-address-for-layout-${width}@example.com`);
      await requester.getByLabel("Requested role").selectOption("sme");
      await requester.getByRole("button", { name: "Request access", exact: true }).click();
      await page.goto(base + "/admin/users?course_id=" + initial.courses.source);
      await expect(page.locator(".admin-brand img")).toBeVisible();
      expect(await page.locator(".admin-brand img").evaluate((image: HTMLImageElement) => image.complete && image.naturalWidth > 0)).toBeTruthy();
      await expect(page.locator("nav [aria-current=page]")).toHaveText("Course access");
      await expect(page.locator("#pending-requests")).toContainText(`long-reviewer-address-for-layout-${width}@example.com`);
      const controls = page.locator("#pending-requests form").filter({ hasText: `long-reviewer-address-for-layout-${width}@example.com` });
      await expect(controls.getByLabel("Course role")).toBeVisible();
      await expect(controls.getByRole("button", { name: "Approve", exact: true })).toBeVisible();
      await page.getByText("Active account administration", { exact: true }).click();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
      await page.screenshot({ path: testInfo.outputPath(`admin-${width}.png`), fullPage: true });
      await page.getByRole("link", { name: "Reviewer transfers", exact: true }).click();
      await expect(page.locator("nav [aria-current=page]")).toHaveText("Reviewer transfers");
      await page.getByLabel("Original UCO course URL").fill("https://my.uconline.ac.nz/course/view.php?id=81");
      await page.getByLabel("Copied LEARN course URL").fill("https://learn.canterbury.ac.nz/course/view.php?id=81");
      await page.getByRole("button", { name: "Preview reviewers", exact: false }).click();
      await expect(page.getByRole("heading", { name: "Review before granting access" })).toBeVisible();
      const checkbox = page.locator('input[name="confirm"]');
      expect((await checkbox.boundingBox())?.width).toBe(20);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
      await page.screenshot({ path: testInfo.outputPath(`transfers-${width}.png`), fullPage: true });
      await page.keyboard.press("Tab");
      expect(await page.evaluate(() => document.activeElement?.tagName)).not.toBe("BODY");
    } finally {
      await requesterContext.close();
      await context.close();
    }
  });
}

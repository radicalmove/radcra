import { expect, test } from "@playwright/test";
import { createHash } from "node:crypto";

const base = "http://127.0.0.1:48146";

for (const width of [1280, 390]) {
  test(`role PDF links and downloads at ${width}px`, async ({ page }, testInfo) => {
    test.skip(!process.env.SPHERE_PUBLIC_GUIDE, "Requires the isolated local static site");
    await page.setViewportSize({ width, height: 950 });
    const manifestResponse = await page.request.get(base + "/guides/manifest.json");
    expect(manifestResponse.ok()).toBeTruthy();
    const manifest = await manifestResponse.json();
    for (const path of ["/download/#guides", "/support/#guides"]) {
      await page.goto(base + path);
      const section = page.locator("#guides");
      await expect(section).toBeInViewport();
      await expect(section.locator('a[type="application/pdf"]')).toHaveCount(4);
      for (const document of manifest.documents) {
        const link = section.locator(`a[href="../guides/${document.file}"]`);
        await expect(link).toBeVisible();
        const response = await page.request.get(new URL(await link.getAttribute("href") ?? "", page.url()).href);
        expect(response.ok()).toBeTruthy();
        expect(response.headers()["content-type"]).toContain("application/pdf");
        const data = await response.body();
        expect(data.subarray(0, 5).toString()).toBe("%PDF-");
        expect(createHash("sha256").update(data).digest("hex")).toBe(document.sha256);
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
      await section.screenshot({ path: testInfo.outputPath(`pdf-guides-${path.includes("download") ? "download" : "support"}-${width}.png`) });
    }
  });

  for (const [path, title] of [["/", "Clear feedback, right where it belongs."], ["/download/", "Install Sphere in Chrome"], ["/support/", "Set up Sphere and start reviewing"]]) {
    test(`public Sphere guide ${path} at ${width}px`, async ({ page }, testInfo) => {
      test.skip(!process.env.SPHERE_PUBLIC_GUIDE, "Requires the isolated local static site");
      await page.setViewportSize({ width, height: 950 });
      const external: string[] = [];
      const failures: string[] = [];
      page.on("request", (request) => { if (!request.url().startsWith(base + "/")) external.push(request.url()); });
      page.on("response", (response) => { if (response.status() >= 400) failures.push(response.url()); });
      await page.goto(base + path, { waitUntil: "networkidle" });
      await expect(page.getByRole("heading", { level: 1, name: title, exact: true })).toBeVisible();
      expect(await page.locator(".brand img").evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBeTruthy();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
      expect(await page.locator("script").count()).toBe(0);
      await page.keyboard.press("Tab");
      await expect(page.locator(".skip-link")).toBeFocused();
      await expect(page.locator(".skip-link")).toBeVisible();
      expect(await page.locator(".skip-link").evaluate((link) => getComputedStyle(link).outlineStyle)).toBe("solid");
      await page.getByRole("heading", { level: 1, name: title, exact: true }).click();
      await page.screenshot({ path: testInfo.outputPath(`page-${width}.png`), fullPage: false });
      expect(external).toEqual([]);
      expect(failures).toEqual([]);
    });
  }

  test(`guide navigation and troubleshooting at ${width}px`, async ({ page }, testInfo) => {
    test.skip(!process.env.SPHERE_PUBLIC_GUIDE, "Requires the isolated local static site");
    await page.setViewportSize({ width, height: 950 });
    await page.goto(base + "/support/", { waitUntil: "networkidle" });
    await page.getByRole("navigation", { name: "Guide sections", exact: true }).getByRole("link", { name: "Confirm and connect", exact: true }).click();
    await expect(page).toHaveURL(base + "/support/#confirm-connect");
    await expect(page.getByRole("heading", { name: "3. Confirm your email and connect", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "3. Confirm your email and connect", exact: true })).toBeInViewport();
    await page.screenshot({ path: testInfo.outputPath(`confirmation-steps-${width}.png`), fullPage: false });
    await page.getByRole("navigation", { name: "Guide sections", exact: true }).getByRole("link", { name: "Troubleshooting", exact: true }).click();
    const faq = page.locator("#email-link");
    await faq.locator("summary").click();
    await expect(faq).toHaveAttribute("open", "");
    await expect(faq).toContainText("request a fresh sign-in link");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    const oldCopy = page.locator("#replace-pilot");
    await expect(oldCopy).toContainText("Now remove the old copy");
    await expect(oldCopy).toContainText("An unsaved draft");
  });
}

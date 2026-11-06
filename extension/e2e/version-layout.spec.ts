import { expect, test } from "@playwright/test";
import { fileURLToPath } from "node:url";

const contentScript = fileURLToPath(new URL("../dist/content.js", import.meta.url));

test("version remains accessible without overlapping review controls at 320 CSS pixels and 200% zoom", async ({ page }) => {
  // At 200% browser zoom a 640px-wide device viewport exposes a 320 CSS px layout viewport.
  await page.setViewportSize({ width: 320, height: 640 });
  await page.route("https://moodle.example.invalid/**", (route) => route.fulfill({ contentType: "text/html", body: "<!doctype html><title>Fixture</title><h1>Law</h1>" }));
  await page.addInitScript(() => {
    (globalThis as any).chrome = { runtime: { id: "fixture-extension", sendMessage(message: any, callback: (response: unknown) => void) {
      if (message.type === "GET_POLICY_STATUS") callback({ ok: true, data: { acknowledged: true } });
      else if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } });
      else if (message.type === "GET_CURRENT_VIEWER") callback({ ok: true, data: { user: { id: "123e4567-e89b-42d3-a456-426614174001", email: "ld@example.test", display_name: "Fixture LD", role: "ld_dcd" } } });
      else callback({ ok: true, data: [] });
    } } };
  });
  await page.goto("https://moodle.example.invalid/course/view.php?id=1");
  await page.addScriptTag({ path: contentScript });
  const host = page.locator("#moodle-course-review-overlay");
  await expect.poll(() => host.evaluate((node: any) => Boolean(node.shadowRoot))).toBe(true);

  await expect(host.locator(".pilot-version")).toBeHidden();
  await expect(host.locator("[data-auth-status]")).toBeHidden();
  await expect(host.locator('[data-action="add-comment"]')).toBeVisible();
  const compactHeight = (await host.locator(".toolbar").boundingBox())!.height;
  await host.getByRole("button", { name: "Expand comments" }).click();
  await expect(host.locator(".pilot-version")).toBeVisible();
  expect((await host.locator(".toolbar").boundingBox())!.height).toBeGreaterThan(compactHeight);
  const layout = await host.evaluate((node: any) => {
    const box = (selector: string) => node.shadowRoot.querySelector(selector).getBoundingClientRect().toJSON();
    return {
      viewport: { width: innerWidth, height: innerHeight },
      boxes: [box(".shell"), box("[data-auth-status]"), box("[data-review-controls]")],
    };
  });
  const boxes = layout.boxes.slice(1);
  for (const box of layout.boxes) {
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(layout.viewport.width);
    expect(box.y).toBeGreaterThanOrEqual(0);
    expect(box.y + box.height).toBeLessThanOrEqual(layout.viewport.height);
  }
  const intersects = (a: any, b: any) => a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y;
  expect(intersects(boxes[0], boxes[1])).toBe(false);
  const minimise = await host.locator('[data-action="panel-minimise"]').boundingBox();
  const version = await host.locator(".pilot-version").boundingBox();
  expect(minimise!.x).toBeGreaterThan(version!.x + version!.width);
  expect(minimise!.y).toBeLessThan(boxes[1].y);
  await expect(host.locator(".toolbar")).toHaveCSS("background-color", "rgb(24, 95, 165)");
  await expect(host.locator(".viewer")).toBeVisible();
  for (const selector of [".course", ".viewer", ".status", ".pilot-version", ".sign-out"]) {
    await expect(host.locator(selector)).toHaveCSS("color", "rgb(255, 255, 255)");
  }

  await host.locator('[data-action="help"]').click();
  await expect(host.getByText("Pilot 0.6.10 · build 0000000")).toBeVisible();
});

test("comment control rows stay distinct and fit even at a narrow zoomed viewport", async ({ page }) => {
  await page.setViewportSize({ width: 760, height: 700 });
  await page.route("https://moodle.example.invalid/**", (route) => route.fulfill({ contentType: "text/html", body: "<!doctype html><title>Fixture</title><h1>Law</h1>" }));
  await page.addInitScript(() => {
    (globalThis as any).chrome = { runtime: { id: "fixture-extension", sendMessage(message: any, callback: (response: unknown) => void) {
      if (message.type === "GET_POLICY_STATUS") callback({ ok: true, data: { acknowledged: true } });
      else if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } });
      else if (message.type === "GET_CURRENT_VIEWER") callback({ ok: true, data: { id: "123e4567-e89b-42d3-a456-426614174001", email: "ld@example.test", display_name: "Fixture LD", role: "ld_dcd" } });
      else callback({ ok: true, data: [] });
    } } };
  });
  await page.goto("https://moodle.example.invalid/course/view.php?id=1");
  await page.addScriptTag({ path: contentScript });
  const host = page.locator("#moodle-course-review-overlay");
  await expect.poll(() => host.evaluate((node: any) => Boolean(node.shadowRoot))).toBe(true);
  await host.locator('[data-action="panel"]').click();

  for (const width of [760, 320]) {
    await page.setViewportSize({ width, height: 700 });
    const rows = await host.evaluate((node) => Array.from(node.shadowRoot!.querySelectorAll(".review-control-line"), (row) =>
      Array.from(row.querySelectorAll("button"), (button) => button.getBoundingClientRect().toJSON())));
    expect(rows.map((row) => row.length)).toEqual([2, 2, 2]);
    for (const [first, second] of rows) {
      expect(first.height).toBeGreaterThanOrEqual(38);
      expect(second.height).toBeGreaterThanOrEqual(38);
      expect(second.right).toBeLessThanOrEqual(width);
      expect(second.left >= first.right + 4 || second.top >= first.bottom + 4).toBe(true);
    }
    expect(rows[1][0].top).toBeGreaterThan(rows[0][1].bottom);
    expect(rows[2][0].top).toBeGreaterThan(rows[1][1].bottom);
  }
});

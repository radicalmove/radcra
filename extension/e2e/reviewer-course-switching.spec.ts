import { chromium, expect, test } from "@playwright/test";
import { createServer } from "node:http";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const port = 48139;
const origin = `http://127.0.0.1:${port}`;
const moodle = "https://moodle.example.invalid";
const ids = ["123e4567-e89b-42d3-a456-426614174001", "123e4567-e89b-42d3-a456-426614174002"];
const roles = ["sme", "ld_dcd"];

test("a clean Chrome profile remembers two approved courses across switching and restart", async () => {
  test.skip(!process.env.SPHERE_COURSE_SWITCH_FIXTURE, "Build with the isolated loopback fixture configuration");
  test.setTimeout(45_000);
  const extension = fileURLToPath(new URL("../dist", import.meta.url));
  const manifest = JSON.parse(await readFile(join(extension, "manifest.json"), "utf8"));
  expect(manifest.host_permissions).toEqual([`${moodle}/*`, `${origin}/*`, "https://radicalmove.github.io/sphere/*"]);
  const profile = await mkdtemp(join(tmpdir(), "sphere-chrome-switch-"));
  const renewals = [0, 0];
  const commentRequests = new Set<number>();
  const wrongTokens: string[] = [];
  let signIns = 0;
  const server = createServer(async (req, res) => {
    const url = new URL(req.url!, origin);
    let raw = "";
    for await (const chunk of req) raw += chunk;
    const body = raw ? JSON.parse(raw) : {};
    const moodleIndex = Number(body.moodle_course_id ?? url.searchParams.get("id")) - 901;
    const index = ids.indexOf(body.course_handle ?? body.course_id ?? url.searchParams.get("course_id") ?? url.pathname.split("/").at(-1));
    const json = (value: unknown, status = 200) => res.writeHead(status, { "Content-Type": "application/json" }).end(JSON.stringify(value));
    const access = (i: number) => ({ state: "approved", role: roles[i], session_token: `token-${i}`, expires_in: 3600, device_credential: `device-${i}-${renewals[i]}` });
    const course = (i: number) => ({ id: ids[i], title: `Fixture course ${i + 1}`, course_url: `${moodle}/course/view.php?id=${901 + i}`, moodle_course_id: String(901 + i), is_confirmed: true });
    if (url.pathname === "/api/access/course") return ids[moodleIndex] ? json({ course_handle: ids[moodleIndex], title: course(moodleIndex).title }) : json({}, 404);
    if (url.pathname === "/api/access/reviewers/sign-in" && index >= 0 && body.membership_id === ids[index]) {
      signIns++;
      return json(access(index));
    }
    if (url.pathname === "/api/access/renew" && index >= 0 && body.device_credential === `device-${index}-${renewals[index]}`) {
      renewals[index]++;
      return json(access(index));
    }
    const selected = url.pathname === "/api/courses/resolve" ? moodleIndex : index;
    if (selected >= 0 && ids[selected] && req.headers.authorization !== `Bearer token-${selected}`) {
      wrongTokens.push(url.pathname);
      return json({ detail: "Wrong course" }, 404);
    }
    if (url.pathname === "/api/courses/resolve" && ids[selected]) return json(course(selected));
    if (url.pathname === "/api/me" && ids[selected]) return json({ course_id: ids[selected], user: { id: ids[selected], email: "fixture@example.test", display_name: `Reviewer ${selected + 1}`, role: roles[selected] } });
    if (url.pathname === "/api/comments" && ids[selected]) { commentRequests.add(selected); return json([]); }
    return json({}, 404);
  });
  const launch = async () => {
    const context = await chromium.launchPersistentContext(profile, {
    channel: "chromium",
    executablePath: process.env.SPHERE_EXTENSION_TEST_CHROME ?? chromium.executablePath(),
    headless: true,
    ignoreDefaultArgs: ["--disable-extensions"],
    args: [`--disable-extensions-except=${extension}`, `--load-extension=${extension}`],
    });
    context.setDefaultTimeout(8_000);
    context.setDefaultNavigationTimeout(8_000);
    await context.route(`${moodle}/**`, (route) => {
      const number = Number(new URL(route.request().url()).searchParams.get("id"));
      return route.fulfill({ contentType: "text/html", body: `<html><title>Fixture course ${number}</title><body class="course-${number}"><h1>Fixture course ${number}</h1></body></html>` });
    });
    return context;
  };
  await new Promise<void>((resolve, reject) => { server.once("error", reject); server.listen(port, "127.0.0.1", resolve); });
  try {
    let context = await launch();
    const open = async (i: number) => {
      const page = await context.newPage();
      await page.goto(`${moodle}/course/view.php?id=${901 + i}`);
      return page;
    };
    try {
      const worker = context.serviceWorkers()[0] ?? await context.waitForEvent("serviceworker");
      await worker.evaluate(async () => (globalThis as any).chrome.storage.local.set({ policyAcknowledgement: { version: "2026-08-14" } }));
      const first = await open(0);
      const approve = async (page: typeof first, i: number) => {
        const panel = page.locator("#moodle-course-review-overlay");
        await expect(panel).toHaveCount(1);
        // Simulate already approved memberships through the extension runtime,
        // without real accounts, mail, or a live pilot server.
        const result = await worker.evaluate(async ({ url, id }) => {
          const chrome = (globalThis as any).chrome;
          const tabs = await chrome.tabs.query({});
          const tabId = tabs.find((tab: { url?: string }) => tab.url === url)?.id;
          const [{ result }] = await chrome.scripting.executeScript({
            target: { tabId }, args: [id],
            func: (course: string) => (globalThis as any).chrome.runtime.sendMessage({ type: "USE_SAVED_REVIEWER", course_handle: course, membership_id: course }),
          });
          return result;
        }, { url: page.url(), id: ids[i] });
        expect(result, JSON.stringify(result)).toMatchObject({ ok: true });
        await page.reload();
        await expect(panel.locator("[data-viewer-line]")).toContainText(`Reviewer ${i + 1}`);
      };
      await test.step("Connect as an SME in course A", () => approve(first, 0));
      const second = await open(1);
      await test.step("Connect as an LD in course B", () => approve(second, 1));
      await first.goto(second.url());
      await expect(first.locator("[data-viewer-line]")).toContainText("Reviewer 2");
      await first.goto(`${moodle}/course/view.php?id=901`);
      await expect(first.locator("[data-viewer-line]")).toContainText("Reviewer 1");
      await second.reload();
      await expect(second.locator("[data-viewer-line]")).toContainText("Reviewer 2");
      expect(renewals, "no renewal while both sessions are active").toEqual([0, 0]);
    } finally { await context.close(); }
    context = await launch();
    try {
      const [first, second] = await Promise.all([open(0), open(1)]);
      await expect(first.locator("[data-viewer-line]")).toContainText("Reviewer 1 · Subject Matter Expert");
      await expect(second.locator("[data-viewer-line]")).toContainText("Reviewer 2 · Learning Designer");
      await expect.poll(() => [...commentRequests].sort()).toEqual([0, 1]);
      expect(renewals.every((count) => count > 0)).toBe(true);
      expect(wrongTokens).toEqual([]);
      expect(signIns).toBe(2);
      await test.step("Sign out and check that neither course reconnects", async () => {
        await first.locator('[data-action="sign-out"]').evaluate((button: HTMLButtonElement) => button.click());
        await expect(first.locator("[data-viewer-line]")).toBeHidden();
        const beforeReload = [...renewals];
        await Promise.all([first.reload(), second.reload()]);
        await expect(first.locator('[data-action="authenticate"]')).toBeEnabled();
        await expect(second.locator('[data-action="authenticate"]')).toBeEnabled();
        expect(renewals).toEqual(beforeReload);
      });
    } finally { await context.close(); }
  } finally {
    await new Promise<void>((resolve) => { server.close(() => resolve()); server.closeAllConnections(); });
    await rm(profile, { recursive: true, force: true });
  }
});

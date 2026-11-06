import { expect, test, type Page } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { StatefulCommentBackend, type FixtureViewer } from "./stateful-comment-backend.ts";

const contentScript = fileURLToPath(new URL("../dist/content.js", import.meta.url));
const courseId = "123e4567-e89b-12d3-a456-426614174000";
const viewers = {
  beta: { role: "beta_tester", userId: "beta-1", email: "beta@example.test" },
  sme: { role: "sme", userId: "sme-author", email: "author@example.test" },
  selectedSme: { role: "sme", userId: "sme-selected", email: "selected@example.test" },
  otherSme: { role: "sme", userId: "sme-other", email: "other@example.test" },
  ld: { role: "ld_dcd", userId: "ld-1", email: "ld@example.test" },
} satisfies Record<string, FixtureViewer>;

async function installRuntime(page: Page, backend: StatefulCommentBackend, calls: string[] = [], screenshot?: () => Promise<string>) {
  await page.exposeFunction("__fixtureRuntime", (message: any) => {
    calls.push(message.type);
    if (message.type === "GET_POLICY_STATUS") return { ok: true, data: { acknowledged: true } };
    if (message.type === "CAPTURE_QUIZ_PREVIEW") return screenshot ? screenshot().then((data) => ({ ok: true, data })) : { ok: false, error: "Chrome permission unavailable" };
    if (message.type === "RESOLVE_COURSE") return { ok: true, data: { id: courseId } };
    if (message.type === "GET_REVIEW_CONTEXT") return { ok: true, data: { course_id: courseId, course_title: "Law course", parent_activity_url: "https://moodle.example.invalid/page/one" } };
    if (message.type === "GET_CURRENT_VIEWER") return { ok: true, data: { id: viewers.ld.userId, email: viewers.ld.email, display_name: "Fixture reviewer", role: "ld_dcd" } };
    if (message.type === "LIST_COURSE_COMMENTS") return { ok: true, data: backend.list("https://moodle.example.invalid/page/one") };
    if (message.type === "CONSUME_COMMENT_NAVIGATION") return { ok: true, data: {} };
    if (message.type === "CREATE_COMMENT") return { ok: true, data: { ...backend.create(message.payload), screenshot_available: message.screenshot_requested === true } };
    return { ok: true, data: {} };
  });
  await page.addInitScript(() => {
    (globalThis as any).chrome = { runtime: { id: "fixture-extension", sendMessage(message: unknown, callback: (response: unknown) => void) {
      (globalThis as any).__fixtureRuntime(message).then(callback);
    } } };
  });
}

async function serve(page: Page) {
  await page.route("https://moodle.example.invalid/**", (route) => route.fulfill({ contentType: "text/html", body: "<!doctype html><title>Fixture</title><h1>Fixture</h1><p id=copy>An important phrase here</p><div id=target style='position:absolute;left:100px;top:180px;width:240px;height:120px'>Pin target</div>" }));
}

async function load(page: Page) {
  await page.goto("https://moodle.example.invalid/page/one");
  await page.addScriptTag({ path: contentScript });
  await expect.poll(() => page.evaluate(() => Boolean(document.querySelector("#moodle-course-review-overlay")?.shadowRoot))).toBe(true);
}

async function compose(page: Page, action: "highlight" | "pin", body: string, category = "general") {
  const host = page.locator("#moodle-course-review-overlay");
  if (action === "highlight") {
    await page.locator("#copy").evaluate((node) => {
      const text = node.firstChild!; const value = text.textContent!; const start = value.indexOf("important phrase");
      const range = document.createRange(); range.setStart(text, start); range.setEnd(text, start + "important phrase".length);
      const selection = getSelection()!; selection.removeAllRanges(); selection.addRange(range);
      document.dispatchEvent(new Event("selectionchange"));
    });
    await host.evaluate((node: any) => node.shadowRoot.querySelector('[data-action="add-comment"]').click());
  } else {
    await host.evaluate((node: any) => node.shadowRoot.querySelector('[data-action="add-comment"]').click());
    await page.locator("#target").click({ position: { x: 120, y: 60 } });
  }
  await expect.poll(() => host.evaluate((node: any) => Boolean(node.shadowRoot.querySelector('[role="dialog"]')))).toBe(true);
  await host.evaluate((node: any, values) => { node.shadowRoot.querySelector("textarea").value = values.body; }, { body, category });
  await host.evaluate((node: any) => node.shadowRoot.querySelector("[data-save]").click());
  await expect.poll(() => host.evaluate((node: any) => Boolean(node.shadowRoot.querySelector('[role="dialog"]')))).toBe(false);
}

async function openThreadText(page: Page, marker: string) {
  await page.locator(marker).click();
  return page.locator("#moodle-course-review-overlay").evaluate((host: any) => host.shadowRoot.textContent as string);
}

test("beta creates a real highlight; reload recovers its beta/LD-only thread and navigation clears it", async ({ page }) => {
  const backend = new StatefulCommentBackend(); backend.setViewer(viewers.beta);
  await serve(page); await installRuntime(page, backend); await load(page);
  await compose(page, "highlight", "Beta highlighted feedback", "learning_design_content_flow");
  const created = backend.list("https://moodle.example.invalid/page/one")[0]!;
  backend.reply(created.id, viewers.sme, "SME reply must stay hidden");

  await page.reload(); await page.addScriptTag({ path: contentScript });
  await expect(page.locator("[data-moodle-review-stored-highlight]")).toBeVisible();
  const thread = await openThreadText(page, "[data-moodle-review-stored-highlight]");
  expect(thread).toContain("Beta highlighted feedback"); expect(thread).not.toContain("SME reply must stay hidden");
  await page.evaluate(() => history.pushState({}, "", "/page/two"));
  await expect(page.locator("[data-moodle-review-stored-highlight]")).toHaveCount(0);
});

test("quiz preview requests a screenshot automatically and still saves when Chrome denies capture", async ({ page }) => {
  const backend = new StatefulCommentBackend(); backend.setViewer(viewers.ld);
  const calls: string[] = [];
  await serve(page); await installRuntime(page, backend, calls);
  await page.goto("https://moodle.example.invalid/mod/quiz/preview.php?cmid=42");
  await page.addScriptTag({ path: contentScript });
  const host = page.locator("#moodle-course-review-overlay");
  await expect(host.locator('[data-action="add-comment"]')).toBeVisible();
  await compose(page, "highlight", "Quiz wording feedback");
  expect(calls.filter((type) => type === "CAPTURE_QUIZ_PREVIEW")).toHaveLength(1);
  expect(calls.filter((type) => type === "CREATE_COMMENT")).toHaveLength(1);
  expect(calls).not.toContain("UPLOAD_SCREENSHOT");
  await expect(host.locator("[data-status-message]")).toContainText("saved without a quiz screenshot");
});

test("Moodle restart-preview form enables automatic screenshot attachment", async ({ page }) => {
  const backend = new StatefulCommentBackend(); backend.setViewer(viewers.ld);
  const calls: string[] = [];
  await serve(page);
  await page.route("https://moodle.example.invalid/mod/quiz/attempt.php?**", (route) => route.fulfill({
    contentType: "text/html",
    body: '<h1>Quiz</h1><nav id="mod_quiz_navblock"><div class="othernav"><form action="/mod/quiz/startattempt.php"><input type="hidden" name="forcenew" value="1"></form></div></nav><div class="que"><span class="qno">3</span><p id="copy">An important phrase here</p></div>',
  }));
  await installRuntime(page, backend, calls, async () => "data:image/png;base64," + (await page.screenshot()).toString("base64"));
  await page.goto("https://moodle.example.invalid/mod/quiz/attempt.php?attempt=5&cmid=42");
  await page.addScriptTag({ path: contentScript });
  await expect(page.locator("#moodle-course-review-overlay").locator('[data-action="add-comment"]')).toBeVisible();
  await compose(page, "highlight", "Review question three");
  expect(calls.filter((type) => ["CAPTURE_QUIZ_PREVIEW", "CREATE_COMMENT", "UPLOAD_SCREENSHOT"].includes(type))).toEqual(["CAPTURE_QUIZ_PREVIEW", "CREATE_COMMENT", "UPLOAD_SCREENSHOT"]);
  expect(backend.list("https://moodle.example.invalid/mod/quiz/view.php?id=42")[0]?.page_title).toContain("question 3");
});

test("edited highlight keeps its marker and the review view exports before and after text", async ({ page }) => {
  const backend = new StatefulCommentBackend(); backend.setViewer(viewers.ld);
  await serve(page);
  let wording = "important phrase";
  await page.route("https://moodle.example.invalid/page/one", (route) => route.fulfill({ contentType: "text/html", body: `<h1>Fixture</h1><p id=copy>Here is a long stable beginning before the ${wording} with a long stable ending afterwards.</p>` }));
  await installRuntime(page, backend);
  await load(page);
  const host = page.locator("#moodle-course-review-overlay");
  await expect(host.locator('[data-action="add-comment"]')).toBeVisible();
  await compose(page, "highlight", "Check the wording");
  wording = "revised wording";
  await page.reload(); await page.addScriptTag({ path: contentScript });
  await expect(page.locator("[data-moodle-review-stored-highlight]")).toBeVisible();
  await expect(host.locator("[data-comment-count]")).toHaveText("1");
  await host.locator('[data-action="panel"]').click();
  await host.locator('[data-comment-scope="page"]').click();
  await expect(host.getByRole("button", { name: /Open comment in context.*Check the wording/ })).toBeVisible({ timeout: 2000 });
  await host.locator('[data-comment-filter="resolved"]').click();
  await expect(host.getByRole("button", { name: /Open comment in context.*Check the wording/ })).toBeHidden();
  await expect(host.locator("[data-comment-count]")).toHaveText("1");
  await host.locator('[data-comment-filter="open"]').click();
  await host.getByRole("button", { name: "View all comments" }).click();
  const workspace = host.getByRole("dialog", { name: "Course review" });
  await expect(workspace).toContainText("Originally highlighted: important phrase");
  await expect(workspace).toContainText("Current text: revised wording");
  await workspace.getByRole("checkbox", { name: "Reviewed this session" }).check();
  const download = page.waitForEvent("download");
  await workspace.getByRole("button", { name: "Export JSON" }).click();
  expect((await download).suggestedFilename()).toBe("sphere-course-review.json");
  await workspace.getByRole("button", { name: "Close" }).click();
});

test("SME creates a real geometric pin and LD/DCD sees its recovered thread after viewer refresh", async ({ page }) => {
  const backend = new StatefulCommentBackend(); backend.setViewer(viewers.sme);
  await serve(page); await installRuntime(page, backend); await load(page);
  await compose(page, "pin", "SME geometric pin");
  expect(backend.list("https://moodle.example.invalid/page/one")[0]?.author.role).toBe("sme");

  backend.setViewer(viewers.ld); await page.reload(); await page.addScriptTag({ path: contentScript });
  await expect(page.locator("[data-moodle-review-stored-pin]")).toHaveAttribute("aria-label", /SME geometric pin/);
  expect(await openThreadText(page, "[data-moodle-review-stored-pin]")).toContain("SME geometric pin");
});

test("dashboard/server selective share transitions an unshared beta comment to selected-SME-only", async ({ page, context }) => {
  const backend = new StatefulCommentBackend(); backend.setViewer(viewers.beta);
  await serve(page); await installRuntime(page, backend); await load(page); await compose(page, "highlight", "Share only with selected SME");
  const commentId = backend.list("https://moodle.example.invalid/page/one")[0]!.id;

  backend.setViewer(viewers.selectedSme);
  const before = await context.newPage(); await serve(before); await installRuntime(before, backend); await load(before);
  await expect(before.locator("[data-moodle-review-stored-highlight]")).toHaveCount(0); await before.close();

  backend.setViewer(viewers.ld);
  backend.share(commentId, viewers.selectedSme.userId); // In production the dashboard calls the server; the extension deliberately has no sharing UI.
  backend.setViewer(viewers.selectedSme);
  const selected = await context.newPage(); await serve(selected); await installRuntime(selected, backend); await load(selected);
  await expect(selected.locator("[data-moodle-review-stored-highlight]")).toBeVisible();
  expect(await openThreadText(selected, "[data-moodle-review-stored-highlight]")).toContain("Share only with selected SME");

  backend.setViewer(viewers.otherSme);
  const unselected = await context.newPage(); await serve(unselected); await installRuntime(unselected, backend); await load(unselected);
  await expect(unselected.locator("[data-moodle-review-stored-highlight]")).toHaveCount(0);
});

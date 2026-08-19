import assert from "node:assert/strict";
import test from "node:test";
import { Window } from "happy-dom";

import { createCommentRenderer } from "../src/comment-renderer.ts";
import type { PageComment } from "../src/background-bridge.ts";
import { sphereTokens } from "../src/ui/sphere-tokens.ts";

const pageUrl = "https://learn.example/mod/page/view.php?id=2";
const otherPageUrl = "https://learn.example/mod/page/view.php?id=3";
const thirdPageUrl = "https://learn.example/mod/page/view.php?id=4";
const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

const comment = (overrides: Partial<PageComment> = {}): PageComment => ({
  id: "00000000-0000-4000-8000-000000000001",
  body: "Move this card",
  category: "general",
  status: "open",
  author: { display_name: "Reviewer", role: "beta_tester" },
  page_url: pageUrl,
  page_title: "Week 2",
  parent_activity_url: null,
  embedded_locator: null,
  anchor_type: "visual_pin",
  selected_quote: null,
  prefix: null,
  suffix: null,
  css_selector: "#target",
  dom_selector: null,
  relative_x: 0.5,
  relative_y: 0.5,
  replies: [],
  status_history: [],
  capabilities: { can_reply: true, can_edit: true, can_change_status: true, can_share_with_sme: false, can_delete: true },
  ...overrides,
});

function setup() {
  const window = new Window({ url: pageUrl });
  const document = window.document as unknown as Document;
  const target = document.createElement("div");
  target.id = "target";
  target.getBoundingClientRect = () => ({ x: 10, y: 20, left: 10, top: 20, right: 210, bottom: 120, width: 200, height: 100, toJSON() {} });
  document.body.append(target);
  return { window, document };
}

test("renders and restores only comments for the renderer's exact page URL", () => {
  const { document } = setup();
  const renderer = createCommentRenderer(document, pageUrl);
  renderer.setComments([comment(), comment({ id: "00000000-0000-4000-8000-000000000002", page_url: otherPageUrl })]);

  assert.equal(document.querySelectorAll("[data-moodle-review-stored-pin]").length, 1);
  const marker = document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]");
  assert.equal(marker?.dataset.moodleReviewStoredPin, comment().id);
  assert.equal(marker?.style.getPropertyValue("--sphere-ink"), "#0C447C");
  assert.equal(marker?.style.getPropertyValue("--sphere-primary"), "#185FA5");
  assert.equal(marker?.style.getPropertyValue("--sphere-radius-container"), "8px");
  assert.equal(document.getElementById("moodle-course-review-overlay"), null);

  renderer.setComments([]);
  assert.equal(document.querySelector("[data-moodle-review-stored-pin]"), null);
});

test("standalone SCORM threads use the established Poppins typography and button weight", () => {
  const { document } = setup();
  const renderer = createCommentRenderer(document, pageUrl);
  const host = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!;
  const css = host.shadowRoot!.querySelector<HTMLStyleElement>("style[data-comment-renderer-styles]")!.textContent!;
  assert.match(host.style.cssText, /font:\s*16px\s*\/\s*1\.5\s+Poppins,\s*system-ui/);
  assert.match(css, /button,textarea,input\{box-sizing:border-box;font:inherit\}/);
  assert.match(css, /button\{[^}]*font-weight:650/);
  assert.doesNotMatch(css, /button,textarea,input\{font:16px\/1\.5 Poppins,Arial,sans-serif\}/);
  renderer.destroy();
});

test("standalone SCORM threads compose the shared Sphere tokens", () => {
  const { document } = setup();
  const renderer = createCommentRenderer(document, pageUrl);
  const host = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!;
  const css = host.shadowRoot!.querySelector<HTMLStyleElement>("style[data-comment-renderer-styles]")!.textContent!;
  assert.match(css, /--sphere-ink:#0C447C/);
  assert.match(css, /--sphere-primary:#185FA5/);
  assert.match(css, /--sphere-action:#378ADD/);
  assert.match(css, /--sphere-danger-deep:#8E2A22/);
  assert.match(css, /--sphere-radius-control:6px/);
  assert.match(css, /fonts\/Poppins-Regular\.ttf/);
  assert.match(sphereTokens, /font-family:Poppins,system-ui/);
  assert.doesNotMatch(css, /#28c4c2|#0b6261|#b8dcdc|#f8fbfb|var\(--review-teal/);
  const definedTokens = new Set(Array.from(css.matchAll(/(--sphere-[a-z0-9-]+):/g), (match) => match[1]));
  for (const token of new Set(Array.from(css.matchAll(/var\((--sphere-[a-z0-9-]+)/g), (match) => match[1]))) {
    assert.ok(definedTokens.has(token), `Sphere token ${token} is referenced without a definition`);
  }
  renderer.destroy();
});

test("replies from the original commenter stay left-aligned while other participants align right", () => {
  const { document } = setup();
  const renderer = createCommentRenderer(document, pageUrl);
  renderer.setComments([comment({
    replies: [
      { id: "00000000-0000-4000-8000-000000000011", body: "Original reviewer follow-up", author: { display_name: "Reviewer", role: "beta_tester" } },
      { id: "00000000-0000-4000-8000-000000000012", body: "Course-team response", author: { display_name: "Learning designer", role: "ld_dcd" } },
    ],
  })]);

  document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!.click();
  const shadow = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;
  const replies = Array.from(shadow.querySelectorAll<HTMLElement>("[data-thread-popover] .thread-message-reply"));
  assert.equal(replies.length, 2);
  assert.ok(replies[0].classList.contains("thread-message-origin-participant"));
  assert.ok(replies[1].classList.contains("thread-message-other-participant"));
  const css = shadow.querySelector("style")!.textContent!;
  assert.match(css, /\.thread-message-origin-participant\{margin-left:0;margin-right:8%/);
  assert.match(css, /\.thread-message-other-participant\{margin-left:8%;margin-right:0/);
  renderer.destroy();
});

test("each participant in a thread receives a distinct reply colour", () => {
  const { document } = setup();
  const renderer = createCommentRenderer(document, pageUrl);
  renderer.setComments([comment({
    replies: [
      { id: "00000000-0000-4000-8000-000000000021", body: "Administrator response", author: { display_name: "Richard Davies", role: "admin" } },
      { id: "00000000-0000-4000-8000-000000000022", body: "SME response", author: { display_name: "Pilot SME", role: "sme" } },
    ],
  })]);

  document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!.click();
  const shadow = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;
  const replies = Array.from(shadow.querySelectorAll<HTMLElement>("[data-thread-popover] .thread-message-reply"));
  assert.equal(replies.length, 2);
  assert.notEqual(replies[0].style.borderLeftColor, replies[1].style.borderLeftColor);
  renderer.destroy();
});

test("nested SCORM scrolling hides offscreen markers and their open threads", async () => {
  const { window, document } = setup();
  const target = document.querySelector<HTMLElement>("#target")!;
  const scroller = document.createElement("div"); scroller.append(target); document.body.append(scroller);
  let top = 20;
  target.getBoundingClientRect = () => ({ x: 10, y: top, left: 10, top, right: 210, bottom: top + 100, width: 200, height: 100, toJSON() {} });
  const renderer = createCommentRenderer(document, pageUrl);
  renderer.setComments([comment()]);
  const marker = document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!;
  marker.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;
  const popover = root.querySelector<HTMLElement>("[data-thread-popover]")!;
  assert.equal(marker.hidden, false);
  assert.equal(popover.hidden, false);

  top = -160;
  scroller.dispatchEvent(new window.Event("scroll") as unknown as Event);
  await new Promise<void>((resolve) => window.requestAnimationFrame(() => resolve()));
  assert.equal(marker.hidden, true);
  assert.equal(popover.hidden, true);

  top = 20;
  scroller.dispatchEvent(new window.Event("scroll") as unknown as Event);
  await new Promise<void>((resolve) => window.requestAnimationFrame(() => resolve()));
  assert.equal(marker.hidden, false);
  assert.equal(popover.hidden, false);
});

test("opens a contextual thread beside its marker and toggles it closed", () => {
  const { document } = setup();
  const renderer = createCommentRenderer(document, pageUrl);
  renderer.setComments([comment()]);
  const marker = document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!;

  marker.click();
  const rendererHost = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!;
  assert.ok(rendererHost.shadowRoot?.querySelector("[data-thread-popover]"));
  assert.equal(marker.getAttribute("aria-expanded"), "true");

  marker.click();
  assert.equal(rendererHost.shadowRoot?.querySelector("[data-thread-popover]"), null);
  assert.equal(marker.getAttribute("aria-expanded"), "false");
});

test("thread focus preserves the SCORM anchor scroll position", () => {
  const { window, document } = setup();
  let threadFocusOptions: FocusOptions | undefined;
  window.HTMLElement.prototype.focus = function (options?: FocusOptions) {
    if (this.hasAttribute("data-thread-popover")) threadFocusOptions = options;
  };
  const renderer = createCommentRenderer(document, pageUrl);
  renderer.setComments([comment()]);

  document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!.click();

  assert.deepEqual(threadFocusOptions, { preventScroll: true });
  renderer.destroy();
});

test("contextual thread moves left when the expanded comments panel occupies the right side", () => {
  const { window, document } = setup();
  Object.defineProperty(window, "innerWidth", { configurable: true, value: 1200 });
  Object.defineProperty(window, "innerHeight", { configurable: true, value: 800 });
  const overlay = document.createElement("div"); overlay.id = "moodle-course-review-overlay";
  const overlayRoot = overlay.attachShadow({ mode: "open" }); const shell = document.createElement("section"); shell.className = "shell";
  shell.getBoundingClientRect = () => ({ x: 840, y: 40, left: 840, top: 40, right: 1190, bottom: 780, width: 350, height: 740, toJSON() {} });
  overlayRoot.append(shell); document.body.append(overlay);
  const renderer = createCommentRenderer(document, pageUrl); renderer.setComments([comment()]);
  const marker = document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!;
  marker.getBoundingClientRect = () => ({ x: 780, y: 220, left: 780, top: 220, right: 818, bottom: 258, width: 38, height: 38, toJSON() {} });
  marker.click();
  const popover = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!.querySelector<HTMLElement>("[data-thread-popover]")!;
  assert.ok(Number.parseFloat(popover.style.left) + 360 <= 832);
  renderer.destroy();
});

test("contextual threads preserve edit, reply, delete, and status callbacks", async () => {
  const { document } = setup();
  const calls: string[] = [];
  const renderer = createCommentRenderer(document, pageUrl, {
    editThread: async () => { calls.push("edit"); },
    replyThread: async () => { calls.push("reply"); },
    deleteThread: async () => { calls.push("delete"); },
    changeStatus: async () => { calls.push("status"); },
  });
  renderer.setComments([comment()]);
  document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;

  root.querySelector<HTMLElement>('[aria-label="Edit original comment"]')!.click();
  const editor = root.querySelector<HTMLTextAreaElement>("[data-edit-composer] textarea")!;
  editor.value = "Updated";
  root.querySelector<HTMLElement>("[data-edit-composer] button")!.click();
  await Promise.resolve();

  root.querySelector<HTMLElement>("[data-reply-toggle]")!.click();
  root.querySelector<HTMLTextAreaElement>("[data-reply-composer] textarea")!.value = "Reply";
  root.querySelector<HTMLElement>("[data-save-reply]")!.click();
  await Promise.resolve();

  root.querySelector<HTMLElement>('[aria-label="Resolve this comment"]')!.click();
  await Promise.resolve();
  root.querySelector<HTMLElement>('[aria-label="Delete thread"]')!.click();
  await Promise.resolve();

  assert.deepEqual(calls, ["edit", "reply", "status", "delete"]);
});

test("contextual thread controls use the established button styles", () => {
  const { document } = setup();
  const renderer = createCommentRenderer(document, pageUrl, {
    editThread: async () => {}, replyThread: async () => {},
    deleteThread: async () => {}, changeStatus: async () => {},
  });
  renderer.setComments([comment()]);
  document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;

  const edit = root.querySelector<HTMLElement>('[aria-label="Edit original comment"]')!;
  assert.ok(edit.classList.contains("thread-edit"));
  assert.equal(edit.title, "Edit comment");
  assert.ok(edit.querySelector('[data-review-icon="edit"]'));
  assert.equal(edit.textContent?.includes("✎"), false);
  assert.equal(edit.getAttribute("aria-pressed"), null);
  edit.click();
  assert.equal(edit.getAttribute("aria-pressed"), "true");
  edit.click();
  assert.equal(edit.getAttribute("aria-pressed"), "false");
  assert.ok(root.querySelector("[data-reply-toggle]")?.classList.contains("thread-reply"));
  const resolve = root.querySelector<HTMLElement>('[aria-label="Resolve this comment"]')!;
  assert.equal(resolve.textContent, "");
  assert.ok(resolve.querySelector("svg"));
  assert.ok(resolve.querySelector(".status-hover-tick"));
  assert.equal(resolve.querySelector("[data-review-icon]"), null);
  const remove = root.querySelector<HTMLElement>('[aria-label="Delete thread"]')!;
  assert.ok(remove.classList.contains("thread-delete"));
  assert.equal(remove.title, "Delete comment thread");
  assert.ok(remove.querySelector('[data-review-icon="delete"]'));
  assert.match(root.querySelector("style")!.textContent!, /\.thread-delete\{[^}]*background:var\(--sphere-danger\)/);
  assert.match(root.querySelector("style")!.textContent!, /\.thread-delete:hover\{border-color:var\(--sphere-danger\);background:#fff;color:var\(--sphere-danger\)\}/);
  assert.match(root.querySelector("style")!.textContent!, /button\.resolve-toggle\{right:50px;margin:0;border:2px solid var\(--sphere-ink\);border-radius:2px;background:#fff\}/);
  assert.match(root.querySelector("style")!.textContent!, /button\.resolve-toggle:hover \.status-hover-tick/);
  assert.match(document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")?.title ?? "", /Open comment/);
});

test("SME sharing uses a full-width action, resolved-style toggles, and an external save control", async () => {
  const { document } = setup();
  const renderer = createCommentRenderer(document, pageUrl, {
    manageSme: async () => ({
      available_recipients: [{ id: "sme-1", display_name: "Pilot SME" }],
      selected_user_ids: [],
    }),
  });
  renderer.setComments([comment({ capabilities: { ...comment().capabilities, can_share_with_sme: true } })]);
  document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;

  root.querySelector<HTMLButtonElement>(".thread-share-sme")!.click();
  await settle();

  const share = root.querySelector<HTMLElement>(".thread-share-sme")!;
  const access = root.querySelector<HTMLElement>("[data-sme-chooser]")!;
  const chooser = access.querySelector<HTMLElement>(".thread-sme-chooser")!;
  const toggle = root.querySelector<HTMLButtonElement>(".thread-sme-toggle")!;
  const save = root.querySelector<HTMLElement>(".thread-sme-save")!;
  assert.equal(share.parentElement?.previousElementSibling?.getAttribute("data-thread-navigation"), "true");
  assert.ok(toggle.querySelector(".status-hover-tick"));
  toggle.click();
  assert.equal(toggle.getAttribute("aria-pressed"), "true");
  assert.ok(toggle.querySelector(".status-resolved-tick"));
  assert.equal(chooser.contains(save), false);
  assert.equal(save.parentElement, access);
  assert.match(root.querySelector("style")!.textContent!, /\.thread-share-sme\{grid-column:1\/-1/);
  assert.doesNotMatch(root.querySelector("style")!.textContent!, /\.thread-sme-chooser\{[^}]*overflow:/);
});

test("contextual thread uses whole-course open numbering and the requested action layout", () => {
  const { document } = setup();
  const renderer = createCommentRenderer(document, pageUrl, {
    editThread: async () => {}, replyThread: async () => {},
    deleteThread: async () => {}, changeStatus: async () => {},
  });
  renderer.setComments([
    comment({ id: "00000000-0000-4000-8000-000000000010", page_url: otherPageUrl, page_title: "Week 1", body: "Earlier" }),
    comment({ id: "00000000-0000-4000-8000-000000000011", status: "resolved", body: "Resolved" }),
    comment({ id: "00000000-0000-4000-8000-000000000012", body: "Current" }),
    comment({ id: "00000000-0000-4000-8000-000000000013", page_url: thirdPageUrl, page_title: "Week 3", body: "Later" }),
  ]);
  document.querySelector<HTMLElement>('[data-moodle-review-stored-pin="00000000-0000-4000-8000-000000000012"]')!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;

  assert.equal(root.querySelector<HTMLElement>("[data-thread-position]")?.textContent, "Comment 2 of 3");
  assert.deepEqual(
    Array.from(root.querySelectorAll<HTMLElement>("[data-thread-top-actions] > button")).map((button) => button.getAttribute("aria-label")),
    ["Edit original comment", "Resolve this comment", "Delete thread"],
  );
  assert.deepEqual(
    Array.from(root.querySelectorAll<HTMLElement>("[data-thread-navigation] > button")).map((button) => button.textContent),
    ["Previous", "Reply", "Next"],
  );
  for (const control of Array.from(root.querySelectorAll<HTMLElement>(".thread-previous, .thread-reply, .thread-next"))) {
    assert.equal(control.querySelector("svg"), null);
  }
  assert.match(root.querySelector("style")!.textContent!, /\.thread-edit\{[^}]*right:92px[^}]*border:2px solid var\(--sphere-action\)/);
  assert.match(root.querySelector("style")!.textContent!, /\.thread-navigation\{display:grid;grid-template-columns:repeat\(3,minmax\(0,1fr\)\)/);
});

test("previous and next navigate through open comments across the whole course", async () => {
  const { document } = setup();
  const navigations: Array<[string, string]> = [];
  const current = comment({ id: "00000000-0000-4000-8000-000000000022", page_title: "Week 2", body: "Current" });
  const renderer = createCommentRenderer(document, pageUrl, {
    replyThread: async () => {},
    navigateToComment: async (id, url) => { navigations.push([id, url]); },
  });
  renderer.setComments([
    comment({ id: "00000000-0000-4000-8000-000000000021", page_url: otherPageUrl, page_title: "Week 1", body: "Previous" }),
    current,
    comment({ id: "00000000-0000-4000-8000-000000000023", status: "resolved", page_title: "Week 2", body: "Skip me" }),
    comment({ id: "00000000-0000-4000-8000-000000000024", page_url: thirdPageUrl, page_title: "Week 3", body: "Next" }),
  ]);
  document.querySelector<HTMLElement>(`[data-moodle-review-stored-pin="${current.id}"]`)!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;

  root.querySelector<HTMLButtonElement>('[data-thread-navigation] [data-direction="previous"]')!.click();
  await settle();
  root.querySelector<HTMLButtonElement>('[data-thread-navigation] [data-direction="next"]')!.click();
  await settle();

  assert.deepEqual(navigations, [
    ["00000000-0000-4000-8000-000000000021", otherPageUrl],
    ["00000000-0000-4000-8000-000000000024", thirdPageUrl],
  ]);
});

test("previous and next follow anchor order on the current page and scroll into context", async () => {
  const { document } = setup();
  const positions = [["early", 20], ["middle", 120], ["late", 220]] as const;
  const scrolls: Array<[string, ScrollIntoViewOptions]> = [];
  for (const [id, top] of positions) {
    const target = document.createElement("div"); target.id = id;
    target.getBoundingClientRect = () => ({ x: 10, y: top, left: 10, top, right: 110, bottom: top + 40, width: 100, height: 40, toJSON() {} });
    target.scrollIntoView = ((options?: boolean | ScrollIntoViewOptions) => { if (options && typeof options !== "boolean") scrolls.push([id, options]); }) as typeof target.scrollIntoView;
    document.body.append(target);
  }
  const early = comment({ id: "00000000-0000-4000-8000-000000000031", body: "Early", css_selector: "#early" });
  const middle = comment({ id: "00000000-0000-4000-8000-000000000032", body: "Middle", css_selector: "#middle" });
  const late = comment({ id: "00000000-0000-4000-8000-000000000033", body: "Late", css_selector: "#late" });
  const renderer = createCommentRenderer(document, pageUrl, { replyThread: async () => {} });
  renderer.setComments([late, middle, early]);
  document.querySelector<HTMLElement>(`[data-moodle-review-stored-pin="${middle.id}"]`)!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;

  root.querySelector<HTMLButtonElement>('[data-thread-navigation] [data-direction="previous"]')!.click();
  await settle();

  assert.equal(root.querySelector<HTMLElement>("[data-thread-popover] div")?.textContent, "Early");
  assert.equal(root.querySelector<HTMLElement>("[data-thread-position]")?.textContent, "Comment 1 of 3");
  assert.deepEqual(scrolls, [["early", { block: "center", inline: "center", behavior: "smooth" }]]);
});

test("Moodle context uses native centred scrolling for a recovered text highlight", () => {
  const { window, document } = setup();
  const paragraph = document.createElement("p"); paragraph.textContent = "Before Moodle target after"; document.body.append(paragraph);
  let elementScroll: ScrollIntoViewOptions | undefined;
  paragraph.scrollIntoView = ((options?: boolean | ScrollIntoViewOptions) => { if (options && typeof options !== "boolean") elementScroll = options; }) as typeof paragraph.scrollIntoView;
  let windowScrolls = 0;
  window.scrollBy = (() => { windowScrolls += 1; }) as typeof window.scrollBy;
  const targetComment = comment({ anchor_type: "text_highlight", selected_quote: "Moodle target", prefix: "Before ", suffix: " after", css_selector: null, relative_x: null, relative_y: null });
  const renderer = createCommentRenderer(document, pageUrl); renderer.setComments([targetComment]);

  const completed = renderer.takeToContext(targetComment.id);

  renderer.destroy();
  assert.equal(completed, true);
  assert.deepEqual(elementScroll, { block: "center", behavior: "smooth" });
  assert.equal(windowScrolls, 0);
});

test("Moodle context uses native centred scrolling for a recovered visual pin", () => {
  const { window, document } = setup();
  const target = document.querySelector<HTMLElement>("#target")!;
  target.getBoundingClientRect = () => ({ x: 0, y: -1200, left: 0, top: -1200, right: 1000, bottom: 800, width: 1000, height: 2000, toJSON() {} });
  let elementScroll: ScrollIntoViewOptions | undefined;
  target.scrollIntoView = ((options?: boolean | ScrollIntoViewOptions) => { if (options && typeof options !== "boolean") elementScroll = options; }) as typeof target.scrollIntoView;
  let windowScrolls = 0;
  window.scrollBy = (() => { windowScrolls += 1; }) as typeof window.scrollBy;
  const renderer = createCommentRenderer(document, pageUrl);
  const targetComment = comment({ relative_x: 0.5, relative_y: 0.1 });
  renderer.setComments([targetComment]);

  assert.equal(renderer.takeToContext(targetComment.id), true, "top-level Moodle must not wait for an embedded retry cycle");

  assert.deepEqual(elementScroll, { block: "center", inline: "center", behavior: "smooth" });
  assert.equal(windowScrolls, 0);
  renderer.destroy();
});

test("Moodle context does not complete when its stored anchor no longer resolves", () => {
  const { document } = setup();
  const renderer = createCommentRenderer(document, pageUrl); renderer.setComments([comment()]);
  document.querySelector("#target")!.remove();

  const completed = renderer.takeToContext(comment().id);
  const recovery = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!.querySelector<HTMLElement>("[data-recovery-status]")?.textContent;
  renderer.destroy();
  assert.equal(completed, false);
  assert.match(recovery ?? "", /original content could not be found/i);
});

test("SCORM text context settles at centre before completing and clamps its popover inside the viewport", async () => {
  const { window, document } = setup();
  Object.defineProperty(window, "top", { configurable: true, value: {} });
  Object.defineProperty(window, "innerHeight", { configurable: true, value: 500 });
  const scroller = document.createElement("div");
  scroller.style.overflowY = "auto";
  Object.defineProperties(scroller, { clientHeight: { value: 400 }, scrollHeight: { value: 2000 } });
  scroller.getBoundingClientRect = () => ({ x: 0, y: 50, left: 0, top: 50, right: 800, bottom: 450, width: 800, height: 400, toJSON() {} });
  const paragraph = document.createElement("p"); paragraph.textContent = "Before centred target after"; scroller.append(paragraph); document.body.append(scroller);
  let rangeTop = 390;
  const originalCreateRange = document.createRange.bind(document);
  document.createRange = (() => {
    const range = originalCreateRange();
    range.getBoundingClientRect = () => ({ x: 100, y: rangeTop, left: 100, top: rangeTop, right: 240, bottom: rangeTop + 20, width: 140, height: 20, toJSON() {} });
    range.getClientRects = () => [range.getBoundingClientRect()] as unknown as DOMRectList;
    return range;
  }) as typeof document.createRange;
  const scrolls: ScrollToOptions[] = [];
  scroller.scrollBy = ((options?: ScrollToOptions | number) => { if (options && typeof options !== "number") scrolls.push(options); }) as typeof scroller.scrollBy;
  const targetComment = comment({ anchor_type: "text_highlight", selected_quote: "centred target", prefix: "Before ", suffix: " after", css_selector: null, relative_x: null, relative_y: null });
  const renderer = createCommentRenderer(document, pageUrl); renderer.setComments([targetComment]);
  const marker = document.querySelector<HTMLElement>("[data-moodle-review-stored-highlight]")!;
  marker.getBoundingClientRect = () => ({ x: 100, y: rangeTop + 24, left: 100, top: rangeTop + 24, right: 138, bottom: rangeTop + 62, width: 38, height: 38, toJSON() {} });

  const first = renderer.takeToContext(targetComment.id);
  rangeTop = 240;
  window.dispatchEvent(new window.Event("scroll"));
  await new Promise<void>((resolve) => window.requestAnimationFrame(() => resolve()));
  const second = renderer.takeToContext(targetComment.id);
  const thread = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!.querySelector<HTMLElement>("[data-thread-popover]")!;
  const threadTop = thread.style.top;
  renderer.destroy();
  assert.equal(first, false);
  assert.deepEqual(scrolls, [{ top: 150, behavior: "smooth" }]);
  assert.equal(second, true);
  assert.equal(threadTop, "192px", "the centred marker's popover keeps the established 8px bottom clamp");
});

test("SCORM text context settles at centre using the viewport fallback", () => {
  const { window, document } = setup();
  Object.defineProperty(window, "top", { configurable: true, value: {} });
  Object.defineProperty(window, "innerHeight", { configurable: true, value: 600 });
  const paragraph = document.createElement("p"); paragraph.textContent = "Before fallback target after"; document.body.append(paragraph);
  let rangeTop = 500;
  const originalCreateRange = document.createRange.bind(document);
  document.createRange = (() => {
    const range = originalCreateRange();
    range.getBoundingClientRect = () => ({ x: 100, y: rangeTop, left: 100, top: rangeTop, right: 240, bottom: rangeTop + 20, width: 140, height: 20, toJSON() {} });
    range.getClientRects = () => [range.getBoundingClientRect()] as unknown as DOMRectList;
    return range;
  }) as typeof document.createRange;
  const scrolls: ScrollToOptions[] = [];
  window.scrollBy = ((options: ScrollToOptions) => { scrolls.push(options); }) as typeof window.scrollBy;
  const targetComment = comment({ anchor_type: "text_highlight", selected_quote: "fallback target", prefix: "Before ", suffix: " after", css_selector: null, relative_x: null, relative_y: null });
  const renderer = createCommentRenderer(document, pageUrl); renderer.setComments([targetComment]);
  const marker = document.querySelector<HTMLElement>("[data-moodle-review-stored-highlight]")!;
  marker.getBoundingClientRect = () => ({ x: 100, y: rangeTop + 24, left: 100, top: rangeTop + 24, right: 138, bottom: rangeTop + 62, width: 38, height: 38, toJSON() {} });

  const first = renderer.takeToContext(targetComment.id);
  rangeTop = 290;
  const second = renderer.takeToContext(targetComment.id);
  renderer.destroy();
  assert.equal(first, false);
  assert.deepEqual(scrolls, [{ top: 210, behavior: "smooth" }]);
  assert.equal(second, true);
});

test("SCORM correction is immediate but a later fresh navigation starts smoothly", () => {
  const { window, document } = setup();
  Object.defineProperty(window, "top", { configurable: true, value: {} });
  Object.defineProperty(window, "innerHeight", { configurable: true, value: 600 });
  const paragraph = document.createElement("p"); paragraph.textContent = "Before correction target after"; document.body.append(paragraph);
  let rangeTop = 500;
  const originalCreateRange = document.createRange.bind(document);
  document.createRange = (() => {
    const range = originalCreateRange();
    range.getBoundingClientRect = () => ({ x: 100, y: rangeTop, left: 100, top: rangeTop, right: 240, bottom: rangeTop + 20, width: 140, height: 20, toJSON() {} });
    range.getClientRects = () => [range.getBoundingClientRect()] as unknown as DOMRectList;
    return range;
  }) as typeof document.createRange;
  const scrolls: ScrollToOptions[] = [];
  window.scrollBy = ((options: ScrollToOptions) => { scrolls.push(options); }) as typeof window.scrollBy;
  const targetComment = comment({ anchor_type: "text_highlight", selected_quote: "correction target", prefix: "Before ", suffix: " after", css_selector: null, relative_x: null, relative_y: null });
  const renderer = createCommentRenderer(document, pageUrl); renderer.setComments([targetComment]);
  const marker = document.querySelector<HTMLElement>("[data-moodle-review-stored-highlight]")!;
  marker.getBoundingClientRect = () => ({ x: 100, y: rangeTop + 24, left: 100, top: rangeTop + 24, right: 138, bottom: rangeTop + 62, width: 38, height: 38, toJSON() {} });

  assert.equal(renderer.takeToContext(targetComment.id), false);
  assert.equal(renderer.takeToContext(targetComment.id), false);
  rangeTop = 290;
  assert.equal(renderer.takeToContext(targetComment.id), true);
  rangeTop = 500;
  assert.equal(renderer.takeToContext(targetComment.id), false);

  renderer.destroy();
  assert.deepEqual(scrolls.map((entry) => entry.behavior), ["smooth", "auto", "smooth"]);
});

test("SCORM pin context settles at centre in a nested scrollport", async () => {
  const { window, document } = setup();
  Object.defineProperty(window, "top", { configurable: true, value: {} });
  const scroller = document.createElement("div"); scroller.style.overflowY = "auto";
  Object.defineProperties(scroller, { clientHeight: { value: 400 }, scrollHeight: { value: 2000 } });
  scroller.getBoundingClientRect = () => ({ x: 0, y: 100, left: 0, top: 100, right: 800, bottom: 500, width: 800, height: 400, toJSON() {} });
  const target = document.querySelector<HTMLElement>("#target")!; scroller.append(target); document.body.append(scroller);
  let targetTop = 400;
  target.getBoundingClientRect = () => ({ x: 100, y: targetTop, left: 100, top: targetTop, right: 300, bottom: targetTop + 120, width: 200, height: 120, toJSON() {} });
  const scrolls: ScrollToOptions[] = [];
  scroller.scrollBy = ((options?: ScrollToOptions | number) => { if (options && typeof options !== "number") scrolls.push(options); }) as typeof scroller.scrollBy;
  const renderer = createCommentRenderer(document, pageUrl); renderer.setComments([comment()]);
  const marker = document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!;
  marker.getBoundingClientRect = () => ({ x: 100, y: targetTop + 41, left: 100, top: targetTop + 41, right: 138, bottom: targetTop + 79, width: 38, height: 38, toJSON() {} });

  const first = renderer.takeToContext(comment().id);
  targetTop = 240;
  window.dispatchEvent(new window.Event("scroll"));
  await new Promise<void>((resolve) => window.requestAnimationFrame(() => resolve()));
  const second = renderer.takeToContext(comment().id);
  const threadTop = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!.querySelector<HTMLElement>("[data-thread-popover]")!.style.top;
  renderer.destroy();
  assert.equal(first, false);
  assert.deepEqual(scrolls, [{ top: 160, behavior: "smooth" }]);
  assert.equal(second, true);
  assert.equal(threadTop, "281px", "an unclamped popover aligns its top with the centred marker");
});

test("SCORM pin context settles at centre using the viewport fallback", () => {
  const { window, document } = setup();
  Object.defineProperty(window, "top", { configurable: true, value: {} });
  Object.defineProperty(window, "innerHeight", { configurable: true, value: 800 });
  const target = document.querySelector<HTMLElement>("#target")!;
  let targetTop = 540;
  target.getBoundingClientRect = () => ({ x: 100, y: targetTop, left: 100, top: targetTop, right: 300, bottom: targetTop + 120, width: 200, height: 120, toJSON() {} });
  const scrolls: ScrollToOptions[] = [];
  window.scrollBy = ((options: ScrollToOptions) => { scrolls.push(options); }) as typeof window.scrollBy;
  const renderer = createCommentRenderer(document, pageUrl); renderer.setComments([comment()]);
  const marker = document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!;
  marker.getBoundingClientRect = () => ({ x: 100, y: targetTop + 41, left: 100, top: targetTop + 41, right: 138, bottom: targetTop + 79, width: 38, height: 38, toJSON() {} });

  const first = renderer.takeToContext(comment().id);
  targetTop = 340;
  const second = renderer.takeToContext(comment().id);
  renderer.destroy();
  assert.equal(first, false);
  assert.deepEqual(scrolls, [{ top: 200, behavior: "smooth" }]);
  assert.equal(second, true);
});

test("next scrolls a visual pin through its nested SCORM scroll container", async () => {
  const { window, document } = setup();
  Object.defineProperty(window, "top", { configurable: true, value: {} });
  const scroller = document.createElement("div");
  scroller.style.overflowY = "auto";
  Object.defineProperties(scroller, { clientHeight: { value: 600 }, scrollHeight: { value: 2000 } });
  scroller.getBoundingClientRect = () => ({ x: 0, y: 0, left: 0, top: 0, right: 800, bottom: 600, width: 800, height: 600, toJSON() {} });
  const later = document.createElement("div"); later.id = "later-in-scorm";
  let laterTop = 720;
  later.getBoundingClientRect = () => ({ x: 10, y: laterTop, left: 10, top: laterTop, right: 210, bottom: laterTop + 100, width: 200, height: 100, toJSON() {} });
  scroller.append(later); document.body.append(scroller);
  const scrolls: ScrollToOptions[] = [];
  scroller.scrollBy = ((options?: ScrollToOptions | number) => { if (options && typeof options !== "number") scrolls.push(options); }) as typeof scroller.scrollBy;
  const first = comment({ id: "00000000-0000-4000-8000-000000000036", body: "First", css_selector: "#target" });
  const second = comment({ id: "00000000-0000-4000-8000-000000000037", body: "Later", css_selector: "#later-in-scorm" });
  const renderer = createCommentRenderer(document, pageUrl);
  renderer.setComments([first, second]);
  document.querySelector<HTMLElement>(`[data-moodle-review-stored-pin="${first.id}"]`)!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;

  root.querySelector<HTMLButtonElement>('[data-thread-navigation] [data-direction="next"]')!.click();
  await settle();
  laterTop = 1000;
  renderer.takeToContext(second.id);

  assert.deepEqual(scrolls, [{ top: 470, behavior: "smooth" }, { top: 750, behavior: "smooth" }], "a fresh jump after Previous/Next must start smoothly");
  assert.equal(root.querySelector<HTMLElement>("[data-thread-position]")?.textContent, "Comment 2 of 2");
});

test("next restores the previous marker to its unfocused Sphere colour", async () => {
  const { document } = setup();
  const secondTarget = document.createElement("div"); secondTarget.id = "second-target";
  secondTarget.getBoundingClientRect = () => ({ x: 10, y: 220, left: 10, top: 220, right: 210, bottom: 320, width: 200, height: 100, toJSON() {} });
  document.body.append(secondTarget);
  const first = comment({ id: "00000000-0000-4000-8000-000000000034", body: "First", css_selector: "#target" });
  const second = comment({ id: "00000000-0000-4000-8000-000000000035", body: "Second", css_selector: "#second-target" });
  const renderer = createCommentRenderer(document, pageUrl);
  renderer.setComments([first, second]);
  const firstMarker = document.querySelector<HTMLElement>(`[data-moodle-review-stored-pin="${first.id}"]`)!;
  firstMarker.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;

  root.querySelector<HTMLButtonElement>('[data-thread-navigation] [data-direction="next"]')!.click();
  await settle();

  assert.equal(firstMarker.getAttribute("aria-expanded"), "false");
  assert.equal(firstMarker.style.background, "var(--sphere-primary)");
  assert.equal(firstMarker.style.borderColor, "var(--sphere-ink)");
});

test("next requests same-page navigation when the target belongs to another hidden Rise interaction", async () => {
  const { document } = setup();
  const navigations: Array<[string, string]> = [];
  const first = comment({ id: "00000000-0000-4000-8000-000000000036", body: "First tab" });
  const second = comment({ id: "00000000-0000-4000-8000-000000000037", body: "Second tab" });
  const renderer = createCommentRenderer(document, pageUrl, {
    navigateToComment: async (id, url) => { navigations.push([id, url]); },
  });
  renderer.setVisibleCommentIds?.(new Set([first.id]));
  renderer.setComments([first, second]);
  document.querySelector<HTMLElement>(`[data-moodle-review-stored-pin="${first.id}"]`)!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;

  root.querySelector<HTMLButtonElement>('[data-thread-navigation] [data-direction="next"]')!.click();
  await settle();

  assert.deepEqual(navigations, [[second.id, second.page_url]]);
});

test("next from the final anchor-ordered comment navigates to the following course page", async () => {
  const { document } = setup();
  const positions = [["first-on-page", 20], ["last-on-page", 220]] as const;
  for (const [id, top] of positions) {
    const target = document.createElement("div"); target.id = id;
    target.getBoundingClientRect = () => ({ x: 10, y: top, left: 10, top, right: 110, bottom: top + 40, width: 100, height: 40, toJSON() {} });
    document.body.append(target);
  }
  const navigations: Array<[string, string]> = [];
  const first = comment({ id: "00000000-0000-4000-8000-000000000041", body: "First here", page_title: "2 Current page", css_selector: "#first-on-page" });
  const last = comment({ id: "00000000-0000-4000-8000-000000000042", body: "Last here", page_title: "2 Current page", css_selector: "#last-on-page" });
  const following = comment({ id: "00000000-0000-4000-8000-000000000043", body: "First there", page_url: otherPageUrl, page_title: "3 Following page" });
  const renderer = createCommentRenderer(document, pageUrl, { navigateToComment: async (id, url) => { navigations.push([id, url]); } });
  renderer.setComments([last, following, first]);
  document.querySelector<HTMLElement>(`[data-moodle-review-stored-pin="${last.id}"]`)!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;

  root.querySelector<HTMLButtonElement>('[data-thread-navigation] [data-direction="next"]')!.click();
  await settle();

  assert.deepEqual(navigations, [[following.id, following.page_url]]);
});

test("failed cross-page navigation keeps the thread open and reports the error", async () => {
  const { document } = setup();
  const current = comment({ id: "00000000-0000-4000-8000-000000000044", body: "Current" });
  const following = comment({ id: "00000000-0000-4000-8000-000000000045", body: "Following", page_url: otherPageUrl, page_title: "3 Following page" });
  const renderer = createCommentRenderer(document, pageUrl, { navigateToComment: async () => { throw new Error("Could not reach the next course page"); } });
  renderer.setComments([current, following]);
  document.querySelector<HTMLElement>(`[data-moodle-review-stored-pin="${current.id}"]`)!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;

  root.querySelector<HTMLButtonElement>('[data-thread-navigation] [data-direction="next"]')!.click();
  await settle();

  assert.ok(root.querySelector("[data-thread-popover]"));
  assert.equal(root.querySelector<HTMLElement>("[data-navigation-error]")?.textContent, "Could not reach the next course page");
  assert.equal(root.querySelector<HTMLElement>("[data-navigation-error]")?.getAttribute("role"), "status");
});

test("editing uploads the selected attachment after saving the text", async () => {
  const { window, document } = setup();
  const calls: string[] = [];
  const renderer = createCommentRenderer(document, pageUrl, {
    editThread: async () => { calls.push("edit"); },
    uploadAttachment: async (_id, dataUrl) => { calls.push(`upload:${dataUrl}`); },
  });
  renderer.setComments([comment()]);
  document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;
  root.querySelector<HTMLElement>('[aria-label="Edit original comment"]')!.click();
  root.querySelector<HTMLTextAreaElement>("[data-edit-composer] textarea")!.value = "Updated";
  const attachment = root.querySelector<HTMLInputElement>("[data-edit-composer] [data-attachment]")!;
  Object.defineProperty(attachment, "files", { value: [new window.File(["notes"], "notes.pdf", { type: "application/pdf" })] });
  root.querySelector<HTMLElement>("[data-edit-composer] [data-save-edit]")!.click();
  await new Promise((resolve) => setTimeout(resolve, 20));

  assert.equal(calls[0], "edit");
  assert.match(calls[1] ?? "", /^upload:data:application\/pdf;base64,/);
});

test("edit composer presents an icon save beside the editor and red cancel at bottom right", () => {
  const { document } = setup();
  const renderer = createCommentRenderer(document, pageUrl, { editThread: async () => {} });
  renderer.setComments([comment()]);
  document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;
  root.querySelector<HTMLElement>('[aria-label="Edit original comment"]')!.click();

  const composer = root.querySelector<HTMLElement>("[data-edit-composer]")!;
  const fieldRow = composer.querySelector<HTMLElement>("[data-composer-field-row]")!;
  const actions = root.querySelector<HTMLElement>("[data-composer-actions]")!;
  assert.deepEqual(Array.from(fieldRow.children).map((node) => node.tagName), ["TEXTAREA", "BUTTON"]);
  const save = fieldRow.querySelector<HTMLElement>("[data-save-edit]")!;
  assert.equal(save.getAttribute("data-save-edit"), "true");
  assert.equal(save.getAttribute("aria-label"), "Save edited comment");
  assert.equal(save.title, "Save edited comment");
  assert.ok(save.querySelector('[data-review-icon="save"]'));
  assert.equal(fieldRow.nextElementSibling?.className, "attachment-field");
  assert.deepEqual(Array.from(actions.children).map((node) => node.textContent), ["Cancel"]);
  assert.equal(actions.previousElementSibling?.getAttribute("data-thread-navigation"), "true", "cancel sits below the navigation row");
  assert.match(root.querySelector("style")!.textContent!, /\.comment-composer-field-row\{display:grid;grid-template-columns:minmax\(0,1fr\) 34px;gap:8px/);
  assert.match(root.querySelector("style")!.textContent!, /\.comment-composer-field-row\{[^}]*margin-right:-6px/);
  assert.match(root.querySelector("style")!.textContent!, /\.comment-composer-save\{[^}]*width:34px;height:34px;min-height:34px[^}]*border:2px solid var\(--sphere-success-deep\)[^}]*background:var\(--sphere-success-deep\)/);
  assert.match(root.querySelector("style")!.textContent!, /\.comment-composer-cancel\{[^}]*border:2px solid var\(--sphere-danger\)[^}]*background:var\(--sphere-danger\)[^}]*color:#fff/);
  assert.match(root.querySelector("style")!.textContent!, /\.comment-composer-cancel\{[^}]*width:calc\(\(100% - 16px\)\/3\);[^}]*height:34px/);
  assert.match(root.querySelector("style")!.textContent!, /\.comment-composer-actions\{display:flex;justify-content:flex-end/);
});

test("reply composer mirrors edit controls and ordering", () => {
  const { document } = setup();
  const renderer = createCommentRenderer(document, pageUrl, { replyThread: async () => {}, uploadAttachment: async () => {} });
  renderer.setComments([comment()]);
  document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;
  root.querySelector<HTMLElement>("[data-reply-toggle]")!.click();

  const composer = root.querySelector<HTMLElement>("[data-reply-composer]")!;
  const row = composer.querySelector<HTMLElement>("[data-composer-field-row]")!;
  const actions = root.querySelector<HTMLElement>("[data-composer-actions]")!;
  assert.deepEqual(Array.from(row.children).map((node) => node.tagName), ["TEXTAREA", "BUTTON"]);
  const save = row.querySelector<HTMLElement>("[data-save-reply]")!;
  assert.equal(save.getAttribute("data-save-reply"), "true");
  assert.equal(save.getAttribute("aria-label"), "Save reply");
  assert.equal(save.title, "Save reply");
  assert.ok(save.querySelector('[data-review-icon="save"]'));
  assert.equal(row.nextElementSibling?.className, "attachment-field");
  assert.equal(actions.previousElementSibling?.getAttribute("data-thread-navigation"), "true");
  assert.deepEqual(Array.from(actions.children).map((node) => node.textContent), ["Cancel"]);
  assert.match(root.querySelector("style")!.textContent!, /\.comment-composer\[data-reply-composer\]\{margin-top:12px\}/);
});

test("replying uploads the selected attachment after saving the reply", async () => {
  const { window, document } = setup();
  const calls: string[] = [];
  const renderer = createCommentRenderer(document, pageUrl, {
    replyThread: async () => { calls.push("reply"); },
    uploadAttachment: async (_id, dataUrl) => { calls.push(`upload:${dataUrl}`); },
  });
  renderer.setComments([comment()]);
  document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;
  root.querySelector<HTMLElement>("[data-reply-toggle]")!.click();
  root.querySelector<HTMLTextAreaElement>("[data-reply-composer] textarea")!.value = "Reply";
  const attachment = root.querySelector<HTMLInputElement>("[data-reply-composer] [data-attachment]")!;
  Object.defineProperty(attachment, "files", { value: [new window.File(["image"], "image.png", { type: "image/png" })] });
  root.querySelector<HTMLElement>("[data-save-reply]")!.click();
  await new Promise((resolve) => setTimeout(resolve, 20));

  assert.equal(calls[0], "reply");
  assert.match(calls[1] ?? "", /^upload:data:image\/png;base64,/);
});

test("projection refreshes inside edit and reply callbacks keep the active thread visible", async () => {
  const { document } = setup();
  let renderer: ReturnType<typeof createCommentRenderer>;
  const updated = comment({ body: "Updated" });
  const replied = comment({ body: "Updated", replies: [{ id: "00000000-0000-4000-8000-000000000011", body: "Reply", author: { display_name: "LD", role: "ld_dcd" } }] });
  renderer = createCommentRenderer(document, pageUrl, {
    editThread: async () => { renderer.setComments([updated]); },
    replyThread: async () => { renderer.setComments([replied]); },
  });
  renderer.setComments([comment()]);
  document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;

  root.querySelector<HTMLElement>('[aria-label="Edit original comment"]')!.click();
  root.querySelector<HTMLTextAreaElement>("[data-edit-composer] textarea")!.value = "Updated";
  root.querySelector<HTMLElement>("[data-edit-composer] button")!.click();
  await settle();
  assert.ok(root.querySelector("[data-thread-popover]"), "edit refresh must not detach the active thread");
  assert.match(root.querySelector<HTMLElement>("[data-thread-popover]")!.textContent!, /Updated/);

  root.querySelector<HTMLElement>("[data-reply-toggle]")!.click();
  root.querySelector<HTMLTextAreaElement>("[data-reply-composer] textarea")!.value = "Reply";
  root.querySelector<HTMLElement>("[data-save-reply]")!.click();
  await settle();
  assert.ok(root.querySelector("[data-thread-popover]"), "reply refresh must not detach the active thread");
  assert.match(root.querySelector<HTMLElement>("[data-thread-popover]")!.textContent!, /Reply/);
});

test("switching threads flushes a queued mutation projection before opening the requested thread", async () => {
  const { document } = setup();
  const first = comment({ body: "First" });
  const second = comment({ id: "00000000-0000-4000-8000-000000000012", body: "Old second" });
  const freshSecond = { ...second, body: "Fresh second" };
  let renderer: ReturnType<typeof createCommentRenderer>;
  renderer = createCommentRenderer(document, pageUrl, {
    editThread: async () => { renderer.setComments([{ ...first, body: "First updated" }, freshSecond]); },
  });
  renderer.setComments([first, second]);
  document.querySelector<HTMLElement>(`[data-moodle-review-stored-pin="${first.id}"]`)!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;
  root.querySelector<HTMLElement>('[aria-label="Edit original comment"]')!.click();
  root.querySelector<HTMLTextAreaElement>("[data-edit-composer] textarea")!.value = "First updated";
  root.querySelector<HTMLElement>("[data-edit-composer] button")!.click();
  await settle();

  const staleSecondMarker = document.querySelector<HTMLElement>(`[data-moodle-review-stored-pin="${second.id}"]`)!;
  staleSecondMarker.click();

  assert.equal(staleSecondMarker.isConnected, false, "switching threads must replace stale markers from the queued projection");
  assert.match(root.querySelector<HTMLElement>("[data-thread-popover]")!.textContent!, /Fresh second/);
  const freshMarker = document.querySelector<HTMLElement>(`[data-moodle-review-stored-pin="${second.id}"]`)!;
  assert.match(freshMarker.getAttribute("aria-label")!, /Fresh second/);
  assert.equal(freshMarker.getAttribute("aria-expanded"), "true");
});

test("switching threads survives an intermediate empty mutation projection", async () => {
  const { document } = setup();
  const first = comment({ body: "First" });
  const second = comment({ id: "00000000-0000-4000-8000-000000000012", body: "Old second" });
  const freshSecond = { ...second, body: "Fresh second" };
  let releaseFetch!: () => void;
  const fetchFinished = new Promise<void>((resolve) => { releaseFetch = resolve; });
  let renderer: ReturnType<typeof createCommentRenderer>;
  renderer = createCommentRenderer(document, pageUrl, {
    editThread: async () => {
      renderer.setComments([]);
      await fetchFinished;
      renderer.setComments([{ ...first, body: "First updated" }, freshSecond]);
    },
  });
  renderer.setComments([first, second]);
  document.querySelector<HTMLElement>(`[data-moodle-review-stored-pin="${first.id}"]`)!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;
  root.querySelector<HTMLElement>('[aria-label="Edit original comment"]')!.click();
  root.querySelector<HTMLTextAreaElement>("[data-edit-composer] textarea")!.value = "First updated";
  root.querySelector<HTMLElement>("[data-edit-composer] button")!.click();
  await settle();

  document.querySelector<HTMLElement>(`[data-moodle-review-stored-pin="${second.id}"]`)!.click();
  assert.equal(root.querySelector("[data-thread-popover]"), null, "the stale thread must not open while the empty projection is current");

  releaseFetch();
  await settle();

  assert.equal(root.querySelectorAll("[data-thread-popover]").length, 1);
  assert.match(root.querySelector<HTMLElement>("[data-thread-popover]")!.textContent!, /Fresh second/);
  const freshMarker = document.querySelector<HTMLElement>(`[data-moodle-review-stored-pin="${second.id}"]`)!;
  assert.match(freshMarker.getAttribute("aria-label")!, /Fresh second/);
  assert.equal(freshMarker.getAttribute("aria-expanded"), "true");
});

test("a deferred thread request is cleared when the mutation confirms that thread disappeared", async () => {
  const { document } = setup();
  const first = comment({ body: "First" });
  const second = comment({ id: "00000000-0000-4000-8000-000000000012", body: "Second" });
  let releaseFetch!: () => void;
  const fetchFinished = new Promise<void>((resolve) => { releaseFetch = resolve; });
  let renderer: ReturnType<typeof createCommentRenderer>;
  renderer = createCommentRenderer(document, pageUrl, {
    editThread: async () => {
      renderer.setComments([]);
      await fetchFinished;
      renderer.setComments([{ ...first, body: "First updated" }]);
    },
  });
  renderer.setComments([first, second]);
  document.querySelector<HTMLElement>(`[data-moodle-review-stored-pin="${first.id}"]`)!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;
  root.querySelector<HTMLElement>('[aria-label="Edit original comment"]')!.click();
  root.querySelector<HTMLTextAreaElement>("[data-edit-composer] textarea")!.value = "First updated";
  root.querySelector<HTMLElement>("[data-edit-composer] button")!.click();
  await settle();
  document.querySelector<HTMLElement>(`[data-moodle-review-stored-pin="${second.id}"]`)!.click();

  releaseFetch();
  await settle();
  assert.equal(root.querySelector("[data-thread-popover]"), null);

  renderer.setComments([{ ...first, body: "First updated" }, { ...second, body: "Unrelated later refresh" }]);
  assert.equal(root.querySelector("[data-thread-popover]"), null, "a later projection must not revive a request for a removed thread");
  assert.equal(document.querySelector<HTMLElement>(`[data-moodle-review-stored-pin="${second.id}"]`)!.getAttribute("aria-expanded"), "false");
});

test("resolved confirmation survives a callback projection refresh until its three-second timeout", async () => {
  const { window, document } = setup();
  let delayed: (() => void) | undefined;
  let refreshes = 0;
  window.setTimeout = ((callback: TimerHandler, delay?: number) => { assert.equal(delay, 3000); delayed = callback as () => void; return 1; }) as unknown as typeof window.setTimeout;
  let renderer: ReturnType<typeof createCommentRenderer>;
  renderer = createCommentRenderer(document, pageUrl, {
    changeStatus: async () => { renderer.setComments([comment({ status: "resolved" })]); },
    refreshComments: async () => { refreshes += 1; },
  });
  renderer.setComments([comment()]);
  document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;

  root.querySelector<HTMLElement>('[aria-label="Resolve this comment"]')!.click();
  await settle();
  assert.ok(root.querySelector<HTMLElement>('[aria-label="Resolve this comment"] svg path'), "resolved confirmation uses the green pen tick");
  assert.equal(root.querySelector<HTMLElement>("[data-thread-status]")?.textContent, "Comment resolved. Moving to Resolved.", "popover confirmation matches the comments-list status message");
  assert.ok(root.querySelector("[data-thread-popover]"));
  assert.equal(refreshes, 0, "the Open list remains visible for the confirmation period");

  delayed?.();
  await settle();
  assert.equal(refreshes, 1, "the comment list refreshes as soon as the confirmation period ends");
  assert.equal(root.querySelector("[data-thread-popover]"), null);
  assert.equal(document.querySelector("[data-moodle-review-stored-pin]"), null, "resolved projection must leave the default Open view after confirmation closes");
});

test("delete refresh closes the thread and removes stale renderer artifacts", async () => {
  const { document } = setup();
  let renderer: ReturnType<typeof createCommentRenderer>;
  renderer = createCommentRenderer(document, pageUrl, { deleteThread: async () => { renderer.setComments([]); } });
  renderer.setComments([comment()]);
  document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;

  root.querySelector<HTMLElement>('[aria-label="Delete thread"]')!.click();
  await settle();
  assert.equal(root.querySelector("[data-thread-popover]"), null);
  assert.equal(document.querySelector("[data-moodle-review-stored-pin]"), null);
});

test("cancelling delete confirmation never sends a delete mutation", async () => {
  const { document } = setup();
  let deleteCalls = 0;
  const renderer = createCommentRenderer(document, pageUrl, {
    confirmAction: async () => false,
    deleteThread: async () => { deleteCalls += 1; },
  });
  renderer.setComments([comment()]);
  document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!.click();
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;

  root.querySelector<HTMLElement>('[aria-label="Delete thread"]')!.click();
  await settle();

  assert.equal(deleteCalls, 0);
  assert.ok(root.querySelector("[data-thread-popover]"));
});

test("takeToContext opens the matching anchored thread and destroy removes renderer artifacts", () => {
  const { document } = setup();
  const renderer = createCommentRenderer(document, pageUrl);
  renderer.setComments([comment()]);

  assert.equal(renderer.takeToContext(comment().id), true);
  assert.ok(document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot?.querySelector("[data-thread-popover]"));
  assert.equal(renderer.takeToContext("00000000-0000-4000-8000-000000000099"), false);

  renderer.destroy();
  assert.equal(document.querySelector("[data-moodle-review-stored-pin]"), null);
  assert.equal(document.querySelector("[data-moodle-review-renderer-root]"), null);
});

test("takeToContext scrolls the exact recovered text range within Rise's nested page scroller", () => {
  const { window, document } = setup();
  Object.defineProperty(window, "top", { configurable: true, value: {} });
  const scroller = document.createElement("div");
  scroller.className = "page-wrap";
  scroller.style.overflowY = "auto";
  Object.defineProperties(scroller, { clientHeight: { value: 600 }, scrollHeight: { value: 3000 } });
  scroller.getBoundingClientRect = () => ({ x: 0, y: 50, left: 0, top: 50, right: 800, bottom: 650, width: 800, height: 600, toJSON() {} });
  const paragraph = document.createElement("p");
  paragraph.textContent = "Before exact target after";
  let ancestorScrolls = 0;
  paragraph.scrollIntoView = () => { ancestorScrolls += 1; };
  scroller.append(paragraph);
  document.body.append(scroller);
  const originalCreateRange = document.createRange.bind(document);
  document.createRange = (() => {
    const range = originalCreateRange();
    const rect = { x: 100, y: 950, left: 100, top: 950, right: 220, bottom: 974, width: 120, height: 24, toJSON() {} };
    range.getBoundingClientRect = () => rect;
    range.getClientRects = () => [rect] as unknown as DOMRectList;
    return range;
  }) as typeof document.createRange;
  let scrollRequest: ScrollToOptions | undefined;
  scroller.scrollBy = ((options?: ScrollToOptions | number) => { if (options && typeof options !== "number") scrollRequest = options; }) as typeof scroller.scrollBy;
  const targetComment = comment({ anchor_type: "text_highlight", selected_quote: "exact target", prefix: "Before ", suffix: " after", css_selector: null, relative_x: null, relative_y: null });
  const renderer = createCommentRenderer(document, pageUrl);
  renderer.setComments([targetComment]);

  const completed = renderer.takeToContext(targetComment.id);
  renderer.destroy();
  assert.equal(completed, false);
  assert.deepEqual(scrollRequest, { top: 612, behavior: "smooth" });
  assert.equal(ancestorScrolls, 0);
});

test("takeToContext retries keep the requested thread open instead of toggling it closed", () => {
  const { document } = setup();
  const renderer = createCommentRenderer(document, pageUrl);
  renderer.setComments([comment()]);
  const marker = document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!;
  marker.getBoundingClientRect = () => ({ x: 10, y: 20, left: 10, top: 20, right: 48, bottom: 58, width: 38, height: 38, toJSON() {} });

  const firstCompleted = renderer.takeToContext(comment().id);
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;
  const thread = root.querySelector("[data-thread-popover]");
  const secondCompleted = renderer.takeToContext(comment().id);
  const threadAfterRetry = root.querySelector("[data-thread-popover]");
  const expandedAfterRetry = marker.getAttribute("aria-expanded");
  renderer.destroy();
  assert.equal(firstCompleted, true);
  assert.ok(thread);
  assert.equal(secondCompleted, true);
  assert.equal(threadAfterRetry, thread);
  assert.equal(expandedAfterRetry, "true");
});

test("takeToContext reports completion only after the requested marker and thread are visible", async () => {
  const { window, document } = setup();
  Object.defineProperty(window, "top", { configurable: true, value: {} });
  Object.defineProperty(window, "innerHeight", { configurable: true, value: 140 });
  const renderer = createCommentRenderer(document, pageUrl);
  renderer.setComments([comment()]);
  const marker = document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!;
  let top = 900;
  marker.getBoundingClientRect = () => ({ x: 10, y: top, left: 10, top, right: 48, bottom: top + 38, width: 38, height: 38, toJSON() {} });

  const completedWhileHidden = renderer.takeToContext(comment().id);
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;
  const hiddenBeforeScroll = root.querySelector<HTMLElement>("[data-thread-popover]")?.hidden;
  top = 20;
  window.dispatchEvent(new window.Event("scroll"));
  await new Promise<void>((resolve) => window.requestAnimationFrame(() => resolve()));
  const completedWhenVisible = renderer.takeToContext(comment().id);
  const hiddenAfterScroll = root.querySelector<HTMLElement>("[data-thread-popover]")?.hidden;
  renderer.destroy();
  assert.equal(completedWhileHidden, false);
  assert.equal(hiddenBeforeScroll, true);
  assert.equal(completedWhenVisible, true);
  assert.equal(hiddenAfterScroll, false);
});

test("takeToContext remains retryable while the open thread is outside the viewport", () => {
  const { window, document } = setup();
  Object.defineProperty(window, "top", { configurable: true, value: {} });
  Object.defineProperty(window, "innerHeight", { configurable: true, value: 140 });
  const renderer = createCommentRenderer(document, pageUrl);
  renderer.setComments([comment()]);
  const marker = document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!;
  marker.getBoundingClientRect = () => ({ x: 10, y: 20, left: 10, top: 20, right: 48, bottom: 58, width: 38, height: 38, toJSON() {} });
  assert.equal(renderer.takeToContext(comment().id), true);
  const root = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!;
  const thread = root.querySelector<HTMLElement>("[data-thread-popover]")!;
  thread.getBoundingClientRect = () => ({ x: 10, y: 900, left: 10, top: 900, right: 370, bottom: 1200, width: 360, height: 300, toJSON() {} });

  const completed = renderer.takeToContext(comment().id);
  const expanded = marker.getAttribute("aria-expanded");
  renderer.destroy();
  assert.equal(completed, false);
  assert.equal(expanded, "true");
});

test("a long thread remains viewport-bounded and completable on a short SCORM viewport", () => {
  const { window, document } = setup();
  Object.defineProperty(window, "top", { configurable: true, value: {} });
  Object.defineProperty(window, "innerHeight", { configurable: true, value: 500 });
  document.querySelector<HTMLElement>("#target")!.getBoundingClientRect = () => ({ x: 10, y: 200, left: 10, top: 200, right: 210, bottom: 300, width: 200, height: 100, toJSON() {} });
  const longComment = comment({
    body: "Long review comment ".repeat(20),
    replies: Array.from({ length: 10 }, (_, index) => ({ id: `00000000-0000-4000-8000-${String(index + 10).padStart(12, "0")}`, body: "Long reply ".repeat(20), author: { display_name: `Reviewer ${index}`, role: "beta_tester" } })),
  });
  const renderer = createCommentRenderer(document, pageUrl);
  renderer.setComments([longComment]);
  const marker = document.querySelector<HTMLElement>("[data-moodle-review-stored-pin]")!;
  marker.getBoundingClientRect = () => ({ x: 10, y: 20, left: 10, top: 20, right: 48, bottom: 58, width: 38, height: 38, toJSON() {} });
  renderer.takeToContext(longComment.id);
  const thread = document.querySelector<HTMLElement>("[data-moodle-review-renderer-root]")!.shadowRoot!.querySelector<HTMLElement>("[data-thread-popover]")!;
  thread.getBoundingClientRect = () => ({ x: 56, y: 8, left: 56, top: 8, right: 416, bottom: 492, width: 360, height: 484, toJSON() {} });

  const completed = renderer.takeToContext(longComment.id);
  const sizing = thread.style.boxSizing;
  renderer.destroy();
  assert.equal(sizing, "border-box");
  assert.equal(completed, true);
});

test("takeToContext scrolls a text range clipped by Rise's scrollport even when it is inside the browser viewport", () => {
  const { window, document } = setup();
  Object.defineProperty(window, "top", { configurable: true, value: {} });
  const scroller = document.createElement("div");
  scroller.style.overflowY = "auto";
  Object.defineProperties(scroller, { clientHeight: { value: 400 }, clientTop: { value: 5 }, scrollHeight: { value: 2000 } });
  scroller.getBoundingClientRect = () => ({ x: 0, y: 100, left: 0, top: 100, right: 800, bottom: 510, width: 800, height: 410, toJSON() {} });
  const paragraph = document.createElement("p");
  paragraph.textContent = "Before clipped target after";
  scroller.append(paragraph);
  document.body.append(scroller);
  const originalCreateRange = document.createRange.bind(document);
  document.createRange = (() => {
    const range = originalCreateRange();
    const rect = { x: 100, y: 650, left: 100, top: 650, right: 240, bottom: 670, width: 140, height: 20, toJSON() {} };
    range.getBoundingClientRect = () => rect;
    range.getClientRects = () => [rect] as unknown as DOMRectList;
    return range;
  }) as typeof document.createRange;
  let scrollRequest: ScrollToOptions | undefined;
  scroller.scrollBy = ((options?: ScrollToOptions | number) => { if (options && typeof options !== "number") scrollRequest = options; }) as typeof scroller.scrollBy;
  const targetComment = comment({ anchor_type: "text_highlight", selected_quote: "clipped target", prefix: "Before ", suffix: " after", css_selector: null, relative_x: null, relative_y: null });
  const renderer = createCommentRenderer(document, pageUrl);
  renderer.setComments([targetComment]);

  const completed = renderer.takeToContext(targetComment.id);
  renderer.destroy();
  assert.equal(completed, false);
  assert.deepEqual(scrollRequest, { top: 355, behavior: "smooth" });
});

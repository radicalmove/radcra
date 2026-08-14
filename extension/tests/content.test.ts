import assert from "node:assert/strict";
import test from "node:test";
import { Window } from "happy-dom";

import { bootstrapContentScript, countInaccessibleFrames, createInteractionTargetController, createLifecycleController, inaccessibleFrameOrigins, isConfiguredFrame, navigateToPreparedComment, prepareCommentNavigationWithRetry, refreshCourseBindingBeforeComment, restoreCommentListArrivalAfterRender, sendRuntimeMessage, startCourseReview, startEmbeddedReview } from "../src/content.ts";
import { peekCommentListArrival, writeCommentListArrival } from "../src/comment-list-arrival.ts";

class ArrivalStorage {
  readonly values = new Map<string, string>();
  reads = 0;
  getItem(key: string) { this.reads += 1; return this.values.get(key) ?? null; }
  setItem(key: string, value: string) { this.values.set(key, value); }
  removeItem(key: string) { this.values.delete(key); }
}

test("invalidated extension contexts fail quietly instead of throwing from a stale page timer", () => {
  let response: unknown;
  const sent = sendRuntimeMessage({ sendMessage: () => { throw new Error("Extension context invalidated."); } }, { type: "HEARTBEAT" }, (value) => { response = value; });
  assert.equal(sent, false);
  assert.deepEqual(response, { ok: false, status: "offline", error: "Extension context invalidated" });
});

test("comment submission refreshes the trusted course binding after a worker restart", async () => {
  const messages: unknown[] = [];
  await refreshCourseBindingBeforeComment(async (message) => {
    messages.push(message);
    return { id: "course-1" };
  }, { course_url: "https://moodle.example.invalid/course/view.php?id=7", title: "Law", moodle_course_id: 7 }, "course-1");
  assert.deepEqual(messages, [{ type: "RESOLVE_COURSE", payload: { course_url: "https://moodle.example.invalid/course/view.php?id=7", title: "Law", moodle_course_id: 7 } }]);
  await assert.rejects(() => refreshCourseBindingBeforeComment(async () => ({ id: "course-2" }), { course_url: "https://moodle.example.invalid/course/view.php?id=7", title: "Law" }, "course-1"), /connection changed/);
});

test("comment save waits for the authoritative list refresh before closing", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/course/view.php?id=1" });
  window.document.body.innerHTML = "<h1>Law</h1><p id='copy'>Select this text for review</p>";
  const messages: any[] = []; const pendingLists: Array<(response: any) => void> = [];
  const saved = { id: "00000000-0000-4000-8000-000000000099", body: "Saved feedback", category: "general", status: "open", author: { display_name: "SME", role: "sme" }, page_url: window.location.href, page_title: "Law", parent_activity_url: null, embedded_locator: null, anchor_type: "text_highlight" as const, selected_quote: "Select this text", prefix: "", suffix: " for review", css_selector: null, dom_selector: null, relative_x: null, relative_y: null, replies: [], status_history: [], capabilities: { can_reply: true, can_change_status: false, can_share_with_sme: false, can_delete: true } };
  let listCount = 0;
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    messages.push(message);
    if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } });
    else if (message.type === "GET_CURRENT_VIEWER") callback({ ok: true, data: { course_id: "123e4567-e89b-12d3-a456-426614174000", user: { id: "00000000-0000-4000-8000-000000000010", display_name: "SME", email: "sme@example.test", role: "sme" } } });
    else if (message.type === "LIST_COURSE_COMMENTS") { listCount += 1; if (listCount === 1) callback({ ok: true, data: [] }); else pendingLists.push(callback); }
    else if (message.type === "CREATE_COMMENT") callback({ ok: true, data: { id: saved.id } });
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as unknown as globalThis.Window & typeof globalThis, window.document as unknown as Document, runtime);
  await new Promise((resolve) => setTimeout(resolve, 0));
  const text = window.document.querySelector("#copy")!.firstChild!; const range = window.document.createRange(); range.setStart(text, 0); range.setEnd(text, 16); window.getSelection()!.removeAllRanges(); window.getSelection()!.addRange(range as any); window.document.dispatchEvent(new window.Event("selectionchange") as any);
  const shadow = window.document.querySelector("#moodle-course-review-overlay")!.shadowRoot!;
  (shadow.querySelector('[data-action="add-comment"]') as unknown as HTMLElement).click();
  const dialog = shadow.querySelector(".dialog") as unknown as HTMLElement; (dialog.querySelector("textarea") as unknown as HTMLTextAreaElement).value = "Saved feedback"; (dialog.querySelector("[data-save]") as unknown as HTMLButtonElement).click();
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.ok(shadow.querySelector(".dialog"), "save must wait for the list refresh");
  assert.equal(messages.filter((message) => message.type === "CREATE_COMMENT").length, 1);
  assert.equal(pendingLists.length, 1);

  pendingLists.shift()!({ ok: true, data: [saved] });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(shadow.querySelector(".dialog"), null);
  assert.equal(shadow.querySelector("[data-comment-count]")?.textContent, "1");
  assert.match(shadow.querySelector("[data-comment-item]")?.textContent ?? "", /Saved feedback/);
  cleanup();
});

test("comment navigation refreshes its course binding and retries one closed response channel", async () => {
  const messages: unknown[] = [];
  let prepares = 0;
  const result = await prepareCommentNavigationWithRetry(async (message) => {
    messages.push(message);
    if ((message as { type?: string }).type === "RESOLVE_COURSE") return { id: "course-1" };
    prepares += 1;
    if (prepares === 1) throw new Error("Review service unavailable");
    return { destination_url: "https://moodle.example.invalid/mod/scorm/player.php?cm=10&scoid=20" };
  }, { course_url: "https://moodle.example.invalid/course/view.php?id=7", title: "Law", moodle_course_id: 7 }, "course-1", "comment-1", "https://rise.example.invalid/lesson");

  assert.equal(result.destination_url, "https://moodle.example.invalid/mod/scorm/player.php?cm=10&scoid=20");
  assert.deepEqual(messages.map((message) => (message as { type: string }).type), ["PREPARE_COMMENT_NAVIGATION", "RESOLVE_COURSE", "PREPARE_COMMENT_NAVIGATION"]);
});

test("comment navigation does not retry a substantive destination failure", async () => {
  let calls = 0;
  await assert.rejects(() => prepareCommentNavigationWithRetry(async () => {
    calls += 1;
    throw new Error("This SCORM comment cannot be opened because its Moodle activity location is missing.");
  }, { course_url: "https://moodle.example.invalid/course/view.php?id=7", title: "Law" }, "course-1", "comment-1", "https://rise.example.invalid/lesson"), /Moodle activity location is missing/);
  assert.equal(calls, 1);
});

test("prepared cross-page navigation records the exact logical comment before assigning the destination", async () => {
  const storage = new ArrivalStorage();
  const assigned: string[] = [];
  const logicalPageUrl = "https://rise.example.invalid/activity#moodle-review-page=Lesson%202";
  await navigateToPreparedComment({
    send: async () => ({ destination_url: "https://moodle.example.invalid/mod/scorm/player.php?cm=10&scoid=20" }),
    context: { course_url: "https://moodle.example.invalid/course/view.php?id=7", title: "Law", moodle_course_id: 7 },
    courseId: "course-1",
    comment: { id: "comment-1", page_url: logicalPageUrl, status: "resolved" },
    storage,
    assign: (url) => { assert.ok(peekCommentListArrival(storage)); assigned.push(url); },
  });
  assert.deepEqual(assigned, ["https://moodle.example.invalid/mod/scorm/player.php?cm=10&scoid=20"]);
  const arrival = peekCommentListArrival(storage)!;
  assert.equal(arrival.version, 1);
  assert.equal(arrival.course_url, "https://moodle.example.invalid/course/view.php?id=7");
  assert.equal(arrival.page_url, logicalPageUrl);
  assert.equal(arrival.comment_id, "comment-1");
  assert.equal(arrival.status, "resolved");
  assert.ok(Number.isFinite(arrival.created_at));
  assert.ok(arrival.token);
});

test("prepared navigation continues when storage is blocked and clears its own record if assignment fails", async () => {
  const blocked = { getItem: () => { throw new Error("blocked"); }, setItem: () => { throw new Error("blocked"); }, removeItem: () => { throw new Error("blocked"); } };
  let assigned = false;
  const input = {
    send: async () => ({ destination_url: "https://moodle.example.invalid/mod/page/view.php?id=8" }),
    context: { course_url: "https://moodle.example.invalid/course/view.php?id=7", title: "Law" },
    courseId: "course-1",
    comment: { id: "comment-1", page_url: "https://moodle.example.invalid/mod/page/view.php?id=8", status: "open" },
  };
  await navigateToPreparedComment({ ...input, storage: blocked, assign: () => { assigned = true; } });
  assert.equal(assigned, true);

  const storage = new ArrivalStorage();
  await assert.rejects(
    () => navigateToPreparedComment({ ...input, storage, assign: () => { throw new Error("navigation blocked"); } }),
    /navigation blocked/,
  );
  assert.equal(peekCommentListArrival(storage), undefined);
});

test("arrival restoration clears only an exact rendered tuple and retains a not-yet-rendered destination", () => {
  const storage = new ArrivalStorage();
  const input = { course_url: "https://moodle.example.invalid/course/view.php?id=7", page_url: "https://rise.example.invalid/activity#moodle-review-page=Lesson%202", comment_id: "comment-1", status: "resolved" as const };
  const saved = writeCommentListArrival(storage, input, { now: () => 1_000, token: () => "arrival-token" })!;
  const restored: Array<[string, string]> = [];
  const overlay = { restoreCommentListGroup: (pageUrl: string, status: "open" | "resolved") => { restored.push([pageUrl, status]); return true; } };

  restoreCommentListArrivalAfterRender(storage, input.course_url, [], overlay, () => 1_001);
  assert.deepEqual(peekCommentListArrival(storage, () => 1_002), saved);
  restoreCommentListArrivalAfterRender(storage, input.course_url, [{ id: input.comment_id, page_url: input.page_url, status: input.status }], overlay, () => 1_003);
  assert.deepEqual(restored, [[input.page_url, input.status]]);
  assert.equal(peekCommentListArrival(storage, () => 1_004), undefined);
});

test("arrival restoration token-clears a different course and retains an exact tuple until its group renders", () => {
  const input = { course_url: "https://moodle.example.invalid/course/view.php?id=7", page_url: "https://rise.example.invalid/lesson", comment_id: "comment-1", status: "open" as const };
  const storage = new ArrivalStorage();
  writeCommentListArrival(storage, input, { now: () => 1_000, token: () => "first-token" });
  restoreCommentListArrivalAfterRender(storage, "https://moodle.example.invalid/course/view.php?id=8", [], { restoreCommentListGroup: () => true }, () => 1_001);
  assert.equal(peekCommentListArrival(storage, () => 1_002), undefined);

  writeCommentListArrival(storage, input, { now: () => 2_000, token: () => "second-token" });
  restoreCommentListArrivalAfterRender(storage, input.course_url, [{ id: input.comment_id, page_url: input.page_url, status: input.status }], { restoreCommentListGroup: () => false }, () => 2_001);
  assert.ok(peekCommentListArrival(storage, () => 2_002));
});

test("course review does not read arrival storage until the authoritative comment list renders", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/course/view.php?id=7" });
  window.document.body.innerHTML = "<h1>Law</h1>";
  const storage = new ArrivalStorage();
  Object.defineProperty(window, "sessionStorage", { configurable: true, value: storage });
  let respondToList: ((response: any) => void) | undefined;
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: "course-1" } });
    else if (message.type === "LIST_COURSE_COMMENTS") respondToList = callback;
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as any, window.document as any, runtime);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.ok(respondToList);
  assert.equal(storage.reads, 0);
  respondToList!({ ok: true, data: [] });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.ok(storage.reads > 0);
  cleanup();
});

test("non-SCORM navigation stays pending until the late anchor scroll succeeds", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/mod/page/view.php?id=2" });
  window.document.body.innerHTML = "<h1>Page two</h1>";
  const timers: Array<() => void> = []; const nativeTimeout = window.setTimeout.bind(window);
  window.setTimeout = ((handler: TimerHandler, delay?: number, ...args: any[]) => {
    if (delay === 250) { timers.push(handler as () => void); return 91 + timers.length; }
    return nativeTimeout(handler as Function, delay, ...args);
  }) as typeof window.setTimeout;
  const comment = { id: "00000000-0000-4000-8000-000000000081", body: "Late target", category: "general", status: "open", author: { display_name: "Reviewer", role: "beta_tester" }, page_url: window.location.href, page_title: "Page two", parent_activity_url: null, embedded_locator: null, anchor_type: "visual_pin", selected_quote: null, prefix: null, suffix: null, css_selector: "#late-target", dom_selector: null, relative_x: .5, relative_y: .5, replies: [], status_history: [], capabilities: { can_reply: true, can_change_status: false, can_share_with_sme: false, can_delete: false } };
  const messages: any[] = []; let completed = false;
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    messages.push(message);
    if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } });
    else if (message.type === "LIST_COURSE_COMMENTS") callback({ ok: true, data: [comment] });
    else if (message.type === "CONSUME_COMMENT_NAVIGATION") callback({ ok: true, data: completed ? {} : { comment_id: comment.id } });
    else if (message.type === "COMPLETE_COMMENT_NAVIGATION") { completed = true; callback({ ok: true, data: {} }); }
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as unknown as globalThis.Window & typeof globalThis, window.document as unknown as Document, runtime);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(completed, false);
  assert.ok(timers.length > 0, "an unresolved navigation must schedule another attempt");
  const target = window.document.createElement("section"); target.id = "late-target"; window.document.body.append(target);
  let scrolls = 0; target.scrollIntoView = (() => { scrolls += 1; }) as typeof target.scrollIntoView;
  const retries = timers.splice(0); for (const retry of retries) retry();
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(completed, true);
  assert.equal(scrolls, 1);
  assert.equal(messages.some((message) => message.type === "COMPLETE_COMMENT_NAVIGATION" && message.comment_id === comment.id), true);
  cleanup();
});

test("content activates on configured Moodle patterns", () => {
  assert.equal(isConfiguredFrame("https://moodle.example.invalid/course/view.php?id=1", ["https://moodle.example.invalid/*"], []), true);
  assert.equal(isConfiguredFrame("https://unrelated.example/course/view.php?id=1", ["https://moodle.example.invalid/*"], []), false);
});

test("authorised Moodle descendants activate when Rise uses an about:blank child frame", () => {
  assert.equal(isConfiguredFrame("about:blank", ["https://moodle.example.invalid/*"], [], () => false, "https://moodle.example.invalid/pluginfile.php/1/index.html"), true);
  assert.equal(isConfiguredFrame("about:blank", ["https://moodle.example.invalid/*"], [], () => false, "https://unrelated.example/activity"), false);
  assert.equal(isConfiguredFrame("blob:https://moodle.example.invalid/lesson-id", ["https://moodle.example.invalid/*"], []), true);
});

test("lifecycle teardown restores history and permits a clean restart without duplicate listeners", () => {
  const window = new Window({ url: "https://moodle.example.invalid/course/view.php?id=1" });
  const originalPush = window.history.pushState;
  let refreshes = 0;
  const first = createLifecycleController(window as unknown as globalThis.Window & typeof globalThis, window.document as unknown as Document, () => { refreshes += 1; }, 0);
  assert.notEqual(window.history.pushState, originalPush);
  first.teardown();
  assert.equal(window.history.pushState, originalPush);
  const second = createLifecycleController(window as unknown as globalThis.Window & typeof globalThis, window.document as unknown as Document, () => { refreshes += 1; }, 0);
  window.dispatchEvent(new window.Event("popstate"));
  second.flush();
  assert.equal(refreshes, 1);
  second.teardown();
});

test("Chrome wildcard host patterns match the root host and subdomains", () => {
  const patterns = ["https://*.example.com/*"];
  assert.equal(isConfiguredFrame("https://example.com/course", patterns, []), true);
  assert.equal(isConfiguredFrame("https://learn.example.com/course", patterns, []), true);
  assert.equal(isConfiguredFrame("https://notexample.com/course", patterns, []), false);
});

test("content activates in an optional frame only when host permission is granted", () => {
  const optional = ["https://rise.example.invalid/*"];
  assert.equal(isConfiguredFrame("https://rise.example.invalid/scorm/index.html", [], optional, () => true), true);
  assert.equal(isConfiguredFrame("https://rise.example.invalid/scorm/index.html", [], optional, () => false), false);
});

test("real bootstrap replaces its owned instance and recovers from a stale marker", async () => {
  const markers = new Set<string>();
  const root = {
    hasAttribute: (name: string) => markers.has(name),
    setAttribute: (name: string) => { markers.add(name); },
    removeAttribute: (name: string) => { markers.delete(name); },
  };
  const documentLike = {
    documentElement: root,
  };
  let injections = 0;
  let cleanups = 0;
  const workerEpochs: number[] = [];
  const options = {
    url: "https://moodle.example.invalid/course/view.php?id=1",
    document: documentLike,
    moodlePatterns: ["https://moodle.example.invalid/*"],
    optionalFramePatterns: [],
    inject: (workerInstanceEpoch: number) => { workerEpochs.push(workerInstanceEpoch); injections += 1; return () => { cleanups += 1; }; },
  };

  assert.equal(await bootstrapContentScript(options), true);
  assert.equal(await bootstrapContentScript(options), true);
  assert.equal(injections, 2);
  assert.equal(cleanups, 1);
  assert.deepEqual(workerEpochs, [1, 2]);
  assert.equal(markers.has("data-moodle-review-extension"), true);

  for (const symbol of Object.getOwnPropertySymbols(root)) delete (root as Record<symbol, unknown>)[symbol];
  assert.equal(await bootstrapContentScript(options), true);
  assert.equal(injections, 3);
  assert.deepEqual(workerEpochs, [1, 2, 1]);
  assert.equal(markers.has("data-moodle-review-extension"), true);
});

test("bootstrap wired to the real start entry tears down the old overlay instance", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/course/view.php?id=1" });
  window.document.body.innerHTML = "<h1>Law</h1>";
  let messages = 0;
  const runtime = { sendMessage: (_message: unknown, callback: (response: { ok: boolean }) => void) => { messages += 1; callback({ ok: true }); } };
  const options = {
    url: window.location.href,
    document: window.document as unknown as Document,
    moodlePatterns: ["https://moodle.example.invalid/*"],
    optionalFramePatterns: [] as string[],
    inject: () => startCourseReview(window as unknown as globalThis.Window & typeof globalThis, window.document as unknown as Document, runtime),
  };

  await bootstrapContentScript(options);
  const firstHistoryPatch = window.history.pushState;
  await bootstrapContentScript(options);

  assert.equal(window.document.querySelectorAll("#moodle-course-review-overlay").length, 1);
  assert.notEqual(window.history.pushState, firstHistoryPatch);
  assert.equal(messages, 2);
});

test("real content-script startup does not require chrome.permissions", async () => {
  const originalWindow = globalThis.window;
  const originalDocument = globalThis.document;
  const originalChrome = (globalThis as typeof globalThis & { chrome?: unknown }).chrome;
  const originalMoodle = (globalThis as typeof globalThis & { __MOODLE_PATTERNS__?: string[] }).__MOODLE_PATTERNS__;
  const originalOptional = (globalThis as typeof globalThis & { __OPTIONAL_FRAME_PATTERNS__?: string[] }).__OPTIONAL_FRAME_PATTERNS__;
  const markers = new Set<string>();
  let bootstraps = 0;
  try {
    Object.assign(globalThis, {
      window: { location: { href: "https://moodle.example.invalid/course/view.php?id=1" } },
      document: {
        documentElement: {
          hasAttribute: (name: string) => markers.has(name),
          setAttribute: (name: string) => { markers.add(name); },
          dispatchEvent: () => { bootstraps += 1; },
        },
      },
      chrome: { runtime: { sendMessage: (_message: unknown, callback: (response: unknown) => void) => callback({ ok: false, error: "Review context unavailable" }) } },
      __MOODLE_PATTERNS__: ["https://moodle.example.invalid/*"],
      __OPTIONAL_FRAME_PATTERNS__: ["https://rise.example.invalid/*"],
    });
    await import(`../src/content.ts?startup=${Date.now()}`);
    await new Promise((resolve) => setTimeout(resolve, 0));
    assert.equal(bootstraps, 1);
  } finally {
    Object.assign(globalThis, {
      window: originalWindow,
      document: originalDocument,
      chrome: originalChrome,
      __MOODLE_PATTERNS__: originalMoodle,
      __OPTIONAL_FRAME_PATTERNS__: originalOptional,
    });
  }
});

test("embedded review stays dormant until the coordinator activates its toolbar-free worker", async () => {
  const window = new Window({ url: "https://rise.example/activity#/lesson/1" });
  const parent = { postMessage: () => undefined };
  Object.defineProperty(window, "top", { value: parent }); Object.defineProperty(window, "parent", { value: parent });
  window.document.title = "Lesson 1"; window.document.body.innerHTML = "<main><h1>Lesson 1</h1><p>Meaningful Rise lesson content for review.</p></main>";
  let listener: ((message: any, sender: unknown, respond: (response: unknown) => void) => void) | undefined;
  let workerInstanceId = "";
  const runtime = {
    onMessage: { addListener: (candidate: typeof listener) => { listener = candidate; }, removeListener: (candidate: typeof listener) => { if (listener === candidate) listener = undefined; } },
    sendMessage: (message: any, callback: (response: any) => void) => {
      if (message.type === "GET_REVIEW_CONTEXT") callback({ ok: true, data: { course_id: "123e4567-e89b-12d3-a456-426614174000", course_title: "Law", parent_activity_url: "https://learn.example/mod/scorm/player.php?cmid=22" } });
      else { if (message.type === "REGISTER_REVIEW_FRAME") workerInstanceId = message.worker_instance_id; callback({ ok: true, data: {} }); }
    },
  };
  const cleanup = startEmbeddedReview(window as any, window.document as any, runtime as any);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(window.document.documentElement.getAttribute("data-moodle-review-registration"), "registered");
  assert.match(window.document.documentElement.getAttribute("data-moodle-review-capabilities") ?? "", /"contentBearing":true/);
  assert.equal(window.document.querySelector("#moodle-course-review-overlay"), null);
  listener!({ type: "ACTIVATE_REVIEW_FRAME", worker_instance_id: "223e4567-e89b-42d3-a456-426614174000", generation: 1 }, {}, () => undefined);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(window.document.querySelector("#moodle-course-review-overlay"), null);
  let activationResponse: unknown;
  listener!({ type: "ACTIVATE_REVIEW_FRAME", worker_instance_id: workerInstanceId, generation: 1 }, {}, (response) => { activationResponse = response; });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.deepEqual(activationResponse, { ok: true, worker_instance_id: workerInstanceId, generation: 1 });
  assert.equal(window.document.documentElement.getAttribute("data-moodle-review-activation"), "ready:1");
  assert.equal(window.document.querySelector("#moodle-course-review-overlay"), null, "an elected Rise frame must never own a toolbar");
  let reconstructionResponse: unknown;
  listener!({ type: "ACTIVATE_REVIEW_FRAME", worker_instance_id: workerInstanceId, generation: 0 }, {}, (response) => { reconstructionResponse = response; });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.deepEqual(reconstructionResponse, { ok: true, worker_instance_id: workerInstanceId, generation: 0 });
  cleanup();
});

test("embedded review re-registers after a background worker restart interval", async () => {
  const window = new Window({ url: "https://rise.example/activity#/lesson/1" });
  window.document.body.innerHTML = "<main><h1>Lesson</h1><p>Meaningful Rise lesson content for review.</p></main>";
  let contextRequests = 0; const registrations: any[] = [];
  const runtime = {
    onMessage: { addListener: () => undefined, removeListener: () => undefined },
    sendMessage: (message: any, callback: (response: any) => void) => {
      if (message.type === "GET_REVIEW_CONTEXT") { contextRequests += 1; callback({ ok: true, data: { course_id: "123e4567-e89b-12d3-a456-426614174000", course_title: "Law", parent_activity_url: "https://learn.example/mod/scorm/player.php?cmid=22" } }); }
      else { if (message.type === "REGISTER_REVIEW_FRAME") registrations.push(message); callback({ ok: true, data: {} }); }
    },
  };
  const cleanup = startEmbeddedReview(window as any, window.document as any, runtime as any, 0, 5);
  await new Promise((resolve) => setTimeout(resolve, 18));
  assert.ok(contextRequests >= 2);
  assert.ok(registrations.length >= 2);
  assert.match(registrations[0].worker_instance_id, /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
  assert.equal(new Set(registrations.map((message) => message.worker_instance_id)).size, 1);
  assert.equal(new Set(registrations.map((message) => message.worker_instance_epoch)).size, 1);
  assert.equal(registrations[0].worker_instance_epoch, 1);
  cleanup();
  const stoppedAt = contextRequests;
  await new Promise((resolve) => setTimeout(resolve, 10));
  assert.equal(contextRequests, stoppedAt);
});

test("embedded review obtains trusted course context and updates its hash identity without mounting a toolbar", async () => {
  const window = new Window({ url: "https://rise.example/activity#/lesson/1" });
  window.document.title = "Lesson 1"; window.document.body.innerHTML = "<p>Review phrase</p>";
  const messages: unknown[] = [];
  const runtime = { sendMessage: (message: unknown, callback: (response: any) => void) => {
    messages.push(message);
    if ((message as any).type === "GET_REVIEW_CONTEXT") callback({ ok: true, data: { course_id: "123e4567-e89b-12d3-a456-426614174000", course_title: "Law", parent_activity_url: "https://learn.example/mod/scorm/player.php?cmid=22" } });
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startEmbeddedReview(window as unknown as globalThis.Window & typeof globalThis, window.document as unknown as Document, runtime);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(window.document.querySelector("#moodle-course-review-overlay"), null);
  window.location.hash = "/lesson/2"; window.document.title = "Lesson 2"; window.dispatchEvent(new window.Event("hashchange"));
  await new Promise((resolve) => setTimeout(resolve, 140));
  assert.ok(messages.some((message: any) => message.type === "REVIEW_FRAME_READY"));
  cleanup();
});

test("elected SCORM worker publishes initial identity and selection before ready", async () => {
  const window = new Window({ url: "https://rise.example/activity#/lesson/1" });
  window.document.title = "Lesson 1"; window.document.body.innerHTML = "<main><h1>Lesson 1</h1><p>Review phrase</p></main>";
  const messages: any[] = [];
  let listener: ((message: any, sender: any, response: (value: unknown) => void) => void) | undefined;
  const runtime = { onMessage: { addListener: (next: typeof listener) => { listener = next; }, removeListener: () => undefined }, sendMessage: (message: any, callback: (response: any) => void) => {
    messages.push(message);
    if (message.type === "GET_REVIEW_CONTEXT") callback({ ok: true, data: { course_id: "123e4567-e89b-12d3-a456-426614174000", course_title: "Law", parent_activity_url: "https://learn.example/mod/scorm/player.php?cmid=22" } });
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startEmbeddedReview(window as any, window.document as any, runtime as any, 0);
  await new Promise((resolve) => setTimeout(resolve, 0));
  const workerInstanceId = messages.find((message) => message.type === "REGISTER_REVIEW_FRAME")?.worker_instance_id;
  listener!({ type: "ACTIVATE_REVIEW_FRAME", worker_instance_id: workerInstanceId, generation: 1 }, {}, () => undefined);
  await new Promise((resolve) => setTimeout(resolve, 0));
  const types = messages.map((message) => message.type);
  assert.notEqual(types.indexOf("SCORM_PAGE_IDENTITY_CHANGED"), -1);
  assert.notEqual(types.indexOf("SCORM_SELECTION_CHANGED"), -1);
  assert.ok(types.indexOf("SCORM_PAGE_IDENTITY_CHANGED") < types.indexOf("REVIEW_FRAME_READY"));
  assert.ok(types.indexOf("SCORM_SELECTION_CHANGED") < types.indexOf("REVIEW_FRAME_READY"));
  cleanup();
});

test("interaction target queues one intent while loading and replays it to an embedded worker", () => {
  let deadline!: () => void;
  const states: string[] = [];
  const intents: string[] = [];
  const desiredStates: Array<string | undefined> = [];
  let cancellations = 0;
  const controller = createInteractionTargetController({ scorm: true, requestablePermission: false, loadingTimeoutMs: 100,
    setTimeout: (handler) => { deadline = handler; return 1; }, clearTimeout: () => undefined,
    onState: (state) => states.push(state), onReplay: (intent) => intents.push(intent), onCancel: () => { cancellations += 1; }, onIntentChange: (intent) => desiredStates.push(intent) });
  controller.request("marker"); controller.request("selection");
  assert.equal(controller.queuedIntent(), "selection");
  controller.workerReady();
  assert.deepEqual(states, ["loading", "embedded"]);
  assert.deepEqual(intents, ["selection"]);
  deadline();
  assert.equal(states.at(-1), "embedded");
  controller.request("marker"); controller.request("marker");
  assert.equal(cancellations, 1);
  assert.equal(controller.queuedIntent(), undefined);
  assert.deepEqual(desiredStates.slice(-2), ["marker", undefined]);
  controller.request("marker");
  controller.workerLost(); controller.workerReady();
  assert.equal(controller.queuedIntent(), undefined, "a lost worker clears active marker mode");
  assert.equal(desiredStates.at(-1), undefined);
  assert.equal(intents.at(-1), "marker", "the original worker received the marker request once");
});

test("requestable permission never falls through to parent fallback", () => {
  let deadline!: () => void;
  const states: string[] = [];
  const controller = createInteractionTargetController({ scorm: true, requestablePermission: true, loadingTimeoutMs: 100,
    setTimeout: (handler) => { deadline = handler; return 1; }, clearTimeout: () => undefined,
    onState: (state) => states.push(state), onReplay: () => undefined });
  assert.equal(deadline, undefined, "permission-required must not start a fallback deadline");
  controller.permissionDenied(); controller.permissionRevoked();
  assert.deepEqual(states, ["permission-required"]);
  assert.equal(controller.state(), "permission-required");
});

test("unsupported SCORM becomes unavailable after its bounded loading deadline", () => {
  let deadline!: () => void;
  const states: string[] = [];
  createInteractionTargetController({ scorm: true, requestablePermission: false, loadingTimeoutMs: 100,
    setTimeout: (handler) => { deadline = handler; return 1; }, clearTimeout: () => undefined,
    onState: (state) => states.push(state), onReplay: () => undefined });
  deadline();
  assert.deepEqual(states, ["loading", "unavailable"]);
});

test("permission grant that cannot inject requires a precise reload state", () => {
  const states: string[] = [];
  const controller = createInteractionTargetController({ scorm: true, requestablePermission: true, loadingTimeoutMs: 100,
    setTimeout: () => 1, clearTimeout: () => undefined, onState: (state) => states.push(state), onReplay: () => undefined });
  controller.permissionGranted(true);
  assert.equal(controller.state(), "reload-required");
  assert.deepEqual(states, ["permission-required", "reload-required"]);
});

test("embedded review no longer loads a duplicate course comment list", async () => {
  const window = new Window({ url: "https://rise.example/activity#/lesson/1" });
  window.document.title = "Lesson 1"; window.document.body.innerHTML = "<p>Rise content</p>";
  const comment = { id: "00000000-0000-4000-8000-000000000001", body: "Course feedback", category: "general", status: "open", author: { display_name: "Reviewer", role: "beta_tester" }, page_url: "https://rise.example/activity#moodle-review-page=Lesson%201", page_title: "Embedded activity · Lesson 1", anchor_type: "visual_pin", selected_quote: null, prefix: null, suffix: null, css_selector: "p", dom_selector: null, relative_x: 0.5, relative_y: 0.5, replies: [], status_history: [], capabilities: { can_reply: true, can_change_status: false, can_share_with_sme: false, can_delete: false } };
  const messages: unknown[] = [];
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    messages.push(message);
    if (message.type === "GET_REVIEW_CONTEXT") callback({ ok: true, data: { course_id: "123e4567-e89b-12d3-a456-426614174000", course_title: "Law", parent_activity_url: "https://learn.example/mod/scorm/player.php?cmid=22" } });
    else if (message.type === "LIST_COURSE_COMMENTS") callback({ ok: true, data: [comment] });
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startEmbeddedReview(window as any, window.document as any, runtime);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(window.document.querySelector("#moodle-course-review-overlay"), null);
  assert.equal(messages.some((message: any) => message.type === "LIST_COURSE_COMMENTS"), false);
  cleanup();
});

test("validated Connected Package identity aliases persist across same-course pages and clear across courses", async () => {
  const courseA = "123e4567-e89b-12d3-a456-426614174010";
  const courseB = "123e4567-e89b-12d3-a456-426614174011";
  const pageUrl = "https://packages.articulateusercontent.com/content/example/boot.html#moodle-review-page=We%20couldn't%20load%20this%20course";
  const window = new Window({ url: "https://moodle.example.invalid/mod/scorm/player.php" });
  window.document.body.dataset.courseid = "10";
  window.document.body.innerHTML = "<h1>Connected Package</h1>";
  const legacyComment = {
    id: "00000000-0000-4000-8000-000000000010", body: "Legacy package feedback", category: "general", status: "open",
    author: { display_name: "Reviewer", role: "beta_tester" }, page_url: pageUrl, page_title: "Embedded activity · We couldn't load this course",
    parent_activity_url: "https://moodle.example.invalid/mod/scorm/view.php?id=20", embedded_locator: "#/lesson/1", interaction_context: null,
    anchor_type: "visual_pin", selected_quote: null, prefix: null, suffix: null, css_selector: "#marker", dom_selector: "main > #marker",
    relative_x: 0.25, relative_y: 0.75, replies: [], status_history: [],
    capabilities: { can_reply: true, can_change_status: false, can_share_with_sme: false, can_delete: false },
  };
  const latestComments = [legacyComment];
  const sent: any[] = [];
  let runtimeListener: ((message: any, sender?: any, sendResponse?: any) => boolean | void) | undefined;
  const runtime = {
    onMessage: {
      addListener: (listener: typeof runtimeListener) => { runtimeListener = listener; },
      removeListener: (listener: typeof runtimeListener) => { if (runtimeListener === listener) runtimeListener = undefined; },
    },
    sendMessage(message: any, callback: (response: any) => void) {
      sent.push(message);
      if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: message.payload.course_url.includes("id=11") ? courseB : courseA } });
      else if (message.type === "LIST_COURSE_COMMENTS") callback({ ok: true, data: latestComments });
      else callback({ ok: true, data: {} });
    },
  };
  const cleanup = startCourseReview(window as any, window.document as any, runtime, undefined, 5);
  await new Promise((resolve) => setTimeout(resolve, 0));
  const shadow = window.document.querySelector("#moodle-course-review-overlay")!.shadowRoot!;
  assert.match(shadow.textContent!, /We couldn't load this course/);

  runtimeListener!({ type: "SCORM_WORKER_EVENT", event: {
    protocol: 1, type: "SCORM_PAGE_IDENTITY_CHANGED", request_id: "00000000-0000-4000-8000-000000000001",
    worker_instance_id: "00000000-0000-4000-8000-000000000002", generation: 1, course_id: courseA, page_url: pageUrl,
    payload: { page_title: "Embedded activity · 1.1.1 Course foundations", embedded_locator: "#/lesson/1" },
  } });
  assert.match(shadow.textContent!, /1\.1\.1 Course foundations/);
  assert.doesNotMatch(shadow.textContent!, /We couldn't load this course/);
  const workerProjection = sent.filter((message) => message.type === "SCORM_TOP_COMMAND" && message.command_type === "SCORM_SET_COMMENTS").at(-1);
  assert.equal(workerProjection.payload.comments, latestComments, "the worker must receive authoritative comments, not the alias projection");
  assert.equal(workerProjection.payload.comments[0], legacyComment);
  assert.equal(workerProjection.payload.comments[0].page_url, pageUrl);
  assert.equal(workerProjection.payload.comments[0].css_selector, "#marker");
  assert.equal(workerProjection.payload.comments[0].dom_selector, "main > #marker");
  assert.equal(workerProjection.payload.comments[0].relative_x, 0.25);
  assert.equal(workerProjection.payload.comments[0].relative_y, 0.75);

  window.history.pushState({}, "", "?page=2");
  await new Promise((resolve) => setTimeout(resolve, 140));
  assert.match(shadow.textContent!, /1\.1\.1 Course foundations/, "same-course page navigation must retain aliases");
  assert.doesNotMatch(shadow.textContent!, /We couldn't load this course/);

  window.document.body.dataset.courseid = "11";
  window.dispatchEvent(new window.Event("moodle-review:navigate"));
  await new Promise((resolve) => setTimeout(resolve, 140));
  assert.match(shadow.textContent!, /We couldn't load this course/, "a course change must clear aliases before rendering its comments");
  runtimeListener!({ type: "SCORM_WORKER_EVENT", event: {
    type: "SCORM_PAGE_IDENTITY_CHANGED", course_id: courseA, page_url: pageUrl,
    payload: { page_title: "Embedded activity · Stale course A title", embedded_locator: "#/lesson/1" },
  } });
  assert.doesNotMatch(shadow.textContent!, /Stale course A title/);

  cleanup();
  assert.equal(runtimeListener, undefined, "teardown must detach alias-producing worker events");
});

test("embedded review retries while the top frame is still resolving", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/embedded" });
  let attempts = 0;
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    if (message.type === "GET_REVIEW_CONTEXT") { attempts += 1; callback(attempts === 1 ? { ok: false, error: "Review context unavailable" } : { ok: true, data: { course_id: "123e4567-e89b-12d3-a456-426614174000", course_title: "Law", parent_activity_url: "https://moodle.example/mod/scorm/player.php?cmid=22" } }); return; }
    callback({ ok: true, data: {} });
  } };
  const cleanup = startEmbeddedReview(window as unknown as globalThis.Window & typeof globalThis, window.document as unknown as Document, runtime, 0);
  await new Promise((resolve) => setTimeout(resolve, 10));
  assert.equal(attempts, 3);
  assert.equal(window.document.querySelector("#moodle-course-review-overlay"), null);
  cleanup();
});

test("embedded review retries while the course is not yet bound to the tab", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/embedded" });
  let attempts = 0;
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    if (message.type === "GET_REVIEW_CONTEXT") { attempts += 1; callback(attempts === 1 ? { ok: false, error: "Course is not bound to tab" } : { ok: true, data: { course_id: "123e4567-e89b-12d3-a456-426614174000", course_title: "Law", parent_activity_url: "https://moodle.example/mod/scorm/player.php?cmid=22" } }); return; }
    callback({ ok: true, data: {} });
  } };
  const cleanup = startEmbeddedReview(window as unknown as globalThis.Window & typeof globalThis, window.document as unknown as Document, runtime, 0);
  await new Promise((resolve) => setTimeout(resolve, 10));
  assert.equal(attempts, 3);
  assert.equal(window.document.querySelector("#moodle-course-review-overlay"), null);
  cleanup();
});

test("top navigation immediately removes stored markers before delayed responses return", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/mod/page/view.php?id=1" });
  window.document.body.innerHTML = "<h1>Page one</h1><p>An important phrase here</p>";
  const lists: Array<(response: any) => void> = [];
  const comment = { id: "00000000-0000-4000-8000-000000000001", body: "Stored feedback", category: "general", status: "open", author: { display_name: "beta@example.test", role: "beta_tester" }, page_url: window.location.href, page_title: "Page one", anchor_type: "text_highlight", selected_quote: "important phrase", prefix: "An ", suffix: " here", css_selector: null, dom_selector: null, relative_x: null, relative_y: null, replies: [], status_history: [] };
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } });
    else if (message.type === "LIST_COURSE_COMMENTS") lists.push(callback);
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as unknown as globalThis.Window & typeof globalThis, window.document as unknown as Document, runtime);
  await new Promise((resolve) => setTimeout(resolve, 0)); lists[0]!({ ok: true, data: [comment] }); await new Promise((resolve) => setTimeout(resolve, 0));
  assert.ok(window.document.querySelector("[data-moodle-review-stored-highlight]"));
  window.history.pushState({}, "", "/mod/page/view.php?id=2");
  assert.equal(window.document.querySelector("[data-moodle-review-stored-highlight]"), null);
  lists[0]!({ ok: true, data: [comment] }); await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(window.document.querySelector("[data-moodle-review-stored-highlight]"), null);
  cleanup();
});

for (const mutation of [
  { action: "status", message: "UPDATE_COMMENT_STATUS" },
  { action: "delete", message: "DELETE_COMMENT_THREAD" },
] as const) test(`a saved ${mutation.action} change preserves comments and reports a later refresh failure`, async () => {
  const window = new Window({ url: "https://moodle.example.invalid/mod/page/view.php?id=1" });
  window.document.body.innerHTML = "<h1>Page one</h1><p>An important phrase here</p>"; let delayedRefresh: (() => void) | undefined; const nativeTimeout = window.setTimeout.bind(window); window.setTimeout = ((handler: TimerHandler, delay?: number, ...args: any[]) => { if (delay === 3000) { delayedRefresh = handler as () => void; return 99; } return nativeTimeout(handler as Function, delay, ...args); }) as typeof window.setTimeout;
  let listCount = 0; const messages: any[] = [];
  const comment = { id: "00000000-0000-4000-8000-000000000011", body: "Stored feedback", category: "general", status: "open", author: { display_name: "Reviewer", role: "beta_tester" }, page_url: window.location.href, page_title: "Page one", parent_activity_url: null, embedded_locator: null, anchor_type: "text_highlight", selected_quote: "important phrase", prefix: "An ", suffix: " here", css_selector: null, dom_selector: null, relative_x: null, relative_y: null, replies: [], status_history: [], capabilities: { can_reply: true, can_change_status: true, can_share_with_sme: false, can_delete: true } };
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    messages.push(message);
    if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } });
    else if (message.type === "LIST_COURSE_COMMENTS") { listCount += 1; callback(listCount === 1 ? { ok: true, data: [comment] } : { ok: false, error: "List unavailable" }); }
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as unknown as globalThis.Window & typeof globalThis, window.document as unknown as Document, runtime);
  await new Promise((resolve) => setTimeout(resolve, 0)); const shadow = window.document.querySelector("#moodle-course-review-overlay")!.shadowRoot! as unknown as ShadowRoot;
  assert.ok(window.document.querySelector("[data-moodle-review-stored-highlight]"));
  shadow.querySelector<HTMLElement>('[data-action="panel"]')!.click(); shadow.querySelector<HTMLButtonElement>(`[data-comment-action="${mutation.action}"]`)!.click(); shadow.querySelector<HTMLButtonElement>("[data-confirm-action]")!.click(); await new Promise((resolve) => setTimeout(resolve, 0)); if (mutation.action === "status") { delayedRefresh?.(); await new Promise((resolve) => setTimeout(resolve, 0)); }
  assert.equal(messages.some((message) => message.type === mutation.message), true);
  assert.ok(window.document.querySelector("[data-moodle-review-stored-highlight]"));
  const row = shadow.querySelector<HTMLElement>("[role='listitem']")!; assert.equal(row.querySelector<HTMLElement>('[role="status"]')?.textContent, "Change saved, but comments could not be refreshed. Reload the page.");
  assert.equal(row.querySelector<HTMLButtonElement>(`[data-comment-action="${mutation.action}"]`)!.disabled, false);
  cleanup();
});

test("a stale failed mutation refresh yields to a newer successful comment projection", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/mod/page/view.php?id=1" }); window.document.body.innerHTML = "<h1>Page one</h1><p>An important phrase here</p>"; let delayedRefresh: (() => void) | undefined; const nativeTimeout = window.setTimeout.bind(window); window.setTimeout = ((handler: TimerHandler, delay?: number, ...args: any[]) => { if (delay === 3000) { delayedRefresh = handler as () => void; return 99; } return nativeTimeout(handler as Function, delay, ...args); }) as typeof window.setTimeout;
  let runtimeListener: ((message: any, sender?: any, sendResponse?: any) => boolean | void) | undefined; let mutationSaved = false; let rejectListA: ((response: any) => void) | undefined;
  const base = { id: "00000000-0000-4000-8000-000000000021", body: "Original", category: "general", status: "open", author: { display_name: "Reviewer", role: "beta_tester" }, page_url: window.location.href, page_title: "Page one", parent_activity_url: null, embedded_locator: null, anchor_type: "text_highlight", selected_quote: "important phrase", prefix: "An ", suffix: " here", css_selector: null, dom_selector: null, relative_x: null, relative_y: null, replies: [], status_history: [], capabilities: { can_reply: true, can_change_status: true, can_share_with_sme: false, can_delete: false } };
  const newer = { ...base, body: "Newer projection" };
  const runtime = { onMessage: { addListener: (listener: (message: any, sender?: any, sendResponse?: any) => boolean | void) => { runtimeListener = listener; }, removeListener: () => undefined }, sendMessage: (message: any, callback: (response: any) => void) => {
    if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } });
    else if (message.type === "UPDATE_COMMENT_STATUS") { mutationSaved = true; callback({ ok: true, data: {} }); }
    else if (message.type === "LIST_COURSE_COMMENTS") { if (mutationSaved && !rejectListA) rejectListA = callback; else callback({ ok: true, data: mutationSaved ? [newer] : [base] }); }
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as unknown as globalThis.Window & typeof globalThis, window.document as unknown as Document, runtime); await new Promise((resolve) => setTimeout(resolve, 0));
  const shadow = window.document.querySelector("#moodle-course-review-overlay")!.shadowRoot! as unknown as ShadowRoot; shadow.querySelector<HTMLElement>('[data-action="panel"]')!.click(); shadow.querySelector<HTMLButtonElement>('[data-comment-action="status"]')!.click(); shadow.querySelector<HTMLButtonElement>("[data-confirm-action]")!.click(); await new Promise((resolve) => setTimeout(resolve, 0)); delayedRefresh?.(); await new Promise((resolve) => setTimeout(resolve, 0)); assert.ok(rejectListA);
  runtimeListener!({ type: "SCORM_WORKER_EVENT", event: { type: "SCORM_COMMENTS_CHANGED" } }); await new Promise((resolve) => setTimeout(resolve, 0));
  assert.match(shadow.querySelector<HTMLButtonElement>("[data-comment-item]")!.textContent!, /Newer projection/);
  rejectListA!({ ok: false, error: "Obsolete list failure" }); await new Promise((resolve) => setTimeout(resolve, 0));
  assert.match(shadow.querySelector<HTMLButtonElement>("[data-comment-item]")!.textContent!, /Newer projection/); assert.equal(shadow.querySelector('[role="status"]'), null); assert.equal(shadow.querySelector<HTMLButtonElement>('[data-comment-action="status"]')!.disabled, false);
  cleanup();
});

test.skip("an ordinary comment refresh preserves the selected course page until authoritative comments arrive", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/mod/page/view.php?id=1" });
  window.document.body.innerHTML = "<h1>Page one</h1>";
  let runtimeListener: ((message: any, sender?: any, sendResponse?: any) => boolean | void) | undefined;
  const pendingLists: Array<(response: any) => void> = [];
  const firstPage = { id: "00000000-0000-4000-8000-000000000031", body: "First page", category: "general", status: "open", author: { display_name: "Reviewer", role: "beta_tester" }, page_url: window.location.href, page_title: "Page one", parent_activity_url: null, embedded_locator: null, anchor_type: "page_pin", selected_quote: null, prefix: null, suffix: null, css_selector: "body", dom_selector: null, relative_x: 0.5, relative_y: 0.5, replies: [], status_history: [] };
  const secondPage = { ...firstPage, id: "00000000-0000-4000-8000-000000000032", body: "Second page", page_url: "https://moodle.example.invalid/mod/page/view.php?id=2", page_title: "Page two" };
  const runtime = { onMessage: { addListener: (listener: typeof runtimeListener) => { runtimeListener = listener; }, removeListener: () => undefined }, sendMessage: (message: any, callback: (response: any) => void) => {
    if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } });
    else if (message.type === "LIST_COURSE_COMMENTS") pendingLists.push(callback);
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as unknown as globalThis.Window & typeof globalThis, window.document as unknown as Document, runtime);
  await new Promise((resolve) => setTimeout(resolve, 0));
  pendingLists.shift()!({ ok: true, data: [firstPage, secondPage] });
  await new Promise((resolve) => setTimeout(resolve, 0));
  const shadow = window.document.querySelector("#moodle-course-review-overlay")!.shadowRoot! as unknown as ShadowRoot;
  shadow.querySelector<HTMLElement>('[data-action="panel"]')!.click();
  shadow.querySelector<HTMLButtonElement>(`[data-comment-page-option="${secondPage.page_url}"]`)!.click();
  runtimeListener!({ type: "SCORM_WORKER_EVENT", event: { type: "SCORM_COMMENTS_CHANGED" } });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(shadow.querySelector<HTMLElement>(`[data-comment-page-option="${secondPage.page_url}"]`)?.getAttribute("aria-selected"), "true");
  assert.match(shadow.querySelector<HTMLElement>(".comment-results")!.textContent!, /Second page/);
  pendingLists.shift()!({ ok: true, data: [firstPage, secondPage] });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(shadow.querySelector<HTMLElement>(`[data-comment-page-option="${secondPage.page_url}"]`)!.getAttribute("aria-selected"), "true");
  cleanup();
});

test("sign in sends one authenticate per activation and refreshes course and comments without reload", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/course/view.php?id=1" });
  window.document.body.innerHTML = "<h1>Law</h1>";
  const messages: any[] = [];
  let signedIn = false;
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    messages.push(message);
    if (message.type === "RESOLVE_COURSE") callback(signedIn ? { ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } } : { ok: false, status: "signed-out", error: "Signed out" });
    else if (message.type === "AUTHENTICATE") { signedIn = true; callback({ ok: true, data: {} }); }
    else if (message.type === "LIST_COURSE_COMMENTS") callback({ ok: true, data: [] });
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as unknown as globalThis.Window & typeof globalThis, window.document as unknown as Document, runtime);
  await new Promise((resolve) => setTimeout(resolve, 0));
  const shadow = window.document.querySelector("#moodle-course-review-overlay")!.shadowRoot!;
  const signIn = shadow.querySelector('[data-action="authenticate"]') as unknown as HTMLElement;
  signIn.click();
  signIn.click();
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(messages.filter((message) => message.type === "AUTHENTICATE").length, 1);
  assert.equal(messages.filter((message) => message.type === "RESOLVE_COURSE").length, 2);
  assert.equal(messages.filter((message) => message.type === "LIST_COURSE_COMMENTS").length, 1);
  assert.match(shadow.textContent!, /Connected/);
  cleanup();
});

test("course access checking disables sign-in and does not invoke authentication", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/course/view.php?id=1" });
  window.document.body.innerHTML = "<h1>Law</h1>";
  let authenticateCalls = 0;
  let publicLookup: ((response: any) => void) | undefined;
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    if (message.type === "RESOLVE_COURSE") callback({ ok: false, status: "signed-out", error: "Signed out" });
    else if (message.type === "LOOKUP_REVIEW_COURSE") publicLookup = callback;
    else if (message.type === "AUTHENTICATE") authenticateCalls += 1;
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as any, window.document as any, runtime);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.ok(publicLookup);
  const shadow = window.document.querySelector("#moodle-course-review-overlay")!.shadowRoot!;
  const button = shadow.querySelector('[data-action="authenticate"]') as unknown as HTMLButtonElement;
  assert.equal(button.disabled, true);
  assert.equal(button.getAttribute("aria-busy"), "true");
  button.click();
  assert.equal(authenticateCalls, 0);
  publicLookup!({ ok: false, status: "offline", error: "Review service unavailable" });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.match(shadow.textContent!, /Service unavailable/);
  cleanup();
});

test("authenticated unregistered resolve responses show the server capability without a client role guess", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/course/view.php?id=2" });
  window.document.body.innerHTML = "<h1>New course</h1>";
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { registered: false, can_register: false } });
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as any, window.document as any, runtime);
  await new Promise((resolve) => setTimeout(resolve, 0));
  const shadow = window.document.querySelector("#moodle-course-review-overlay")!.shadowRoot!;
  assert.match(shadow.textContent!, /Course not registered/);
  assert.equal(shadow.querySelector('[data-action="register-course"]'), null);
  cleanup();
});

test("successful registration forces a fresh read-only resolve for the current course", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/course/view.php?id=3" });
  window.document.body.innerHTML = "<h1>New course</h1>";
  const messages: any[] = []; let resolves = 0;
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    messages.push(message);
    if (message.type === "RESOLVE_COURSE") { resolves += 1; callback(resolves === 1 ? { ok: true, data: { registered: false, can_register: true } } : { ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174003", title: "New course" } }); }
    else if (message.type === "REGISTER_COURSE") callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174003" } });
    else if (message.type === "GET_CURRENT_VIEWER") callback({ ok: true, data: {} });
    else callback({ ok: true, data: [] });
  } };
  const cleanup = startCourseReview(window as any, window.document as any, runtime);
  await new Promise((resolve) => setTimeout(resolve, 0));
  const shadow = window.document.querySelector("#moodle-course-review-overlay")!.shadowRoot!;
  (shadow.querySelector('[data-action="register-course"]') as unknown as HTMLButtonElement)!.click();
  (shadow.querySelector('[data-register-confirm]') as unknown as HTMLButtonElement)!.click();
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(messages.filter((message) => message.type === "REGISTER_COURSE").length, 1);
  assert.equal(messages.filter((message) => message.type === "RESOLVE_COURSE").length, 2);
  assert.equal(messages.filter((message) => message.type === "GET_CURRENT_VIEWER").length, 1);
  cleanup();
});

test("delayed registration cannot clear or refresh a course reached during navigation", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/course/activity.php?id=30" });
  window.document.body.dataset.courseid = "30";
  window.document.body.innerHTML = "<h1>Registration course</h1>";
  const messages: any[] = [];
  const resolveCallbacks: Array<(response: any) => void> = [];
  let registrationCallback: ((response: any) => void) | undefined;
  let resolves = 0;
  const runtime = { sendMessage(message: any, callback: (response: any) => void) {
    messages.push(message);
    if (message.type === "RESOLVE_COURSE") {
      resolves += 1;
      if (resolves === 1) callback({ ok: true, data: { registered: false, can_register: true } });
      else resolveCallbacks.push(callback);
    } else if (message.type === "REGISTER_COURSE") registrationCallback = callback;
    else callback({ ok: true, data: [] });
  } };
  const cleanup = startCourseReview(window as any, window.document as any, runtime);
  await new Promise((resolve) => setTimeout(resolve, 0));
  const shadow = window.document.querySelector("#moodle-course-review-overlay")!.shadowRoot!;
  (shadow.querySelector('[data-action="register-course"]') as unknown as HTMLButtonElement)!.click();
  (shadow.querySelector('[data-register-confirm]') as unknown as HTMLButtonElement)!.click();
  assert.ok(registrationCallback);

  window.document.body.dataset.courseid = "31";
  window.document.querySelector("h1")!.textContent = "Navigated course";
  window.dispatchEvent(new window.Event("moodle-review:navigate"));
  assert.equal(shadow.querySelector('[role="dialog"]'), null);
  registrationCallback!({ ok: true, data: { id: "registered-too-late" } });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(resolves, 1, "stale registration must not force a resolve for the new course");
  assert.match(shadow.querySelector(".course")?.textContent ?? "", /Navigated course/);
  assert.equal(shadow.querySelector("[data-auth-status]")?.classList.contains("connecting"), true);
  cleanup();
});

test("a stale course lookup cannot overwrite the current URL or course state", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/course/view.php?id=4" });
  window.document.body.innerHTML = "<h1>First</h1>";
  const callbacks: Array<(response: any) => void> = [];
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    if (message.type === "RESOLVE_COURSE") callbacks.push(callback);
    else if (message.type === "LIST_COURSE_COMMENTS") callback({ ok: true, data: [] });
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as any, window.document as any, runtime);
  window.document.querySelector("h1")!.textContent = "Second";
  window.history.pushState({}, "", "https://moodle.example.invalid/course/view.php?id=5");
  window.dispatchEvent(new window.Event("moodle-review:navigate"));
  await new Promise((resolve) => setTimeout(resolve, 150));
  assert.equal(callbacks.length, 2);
  callbacks[1]!({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174005", title: "Second" } });
  await new Promise((resolve) => setTimeout(resolve, 0));
  callbacks[0]!({ ok: true, data: { registered: false, can_register: true } });
  await new Promise((resolve) => setTimeout(resolve, 0));
  const shadow = window.document.querySelector("#moodle-course-review-overlay")!.shadowRoot!;
  assert.match(shadow.querySelector(".course")?.textContent ?? "", /Second/);
  cleanup();
});

test("same-page course navigation immediately invalidates bindings and ignores stale comments", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/course/activity.php?id=10" });
  window.document.body.dataset.courseid = "10";
  window.document.body.innerHTML = "<h1>First course</h1>";
  const listCallbacks: Array<(response: any) => void> = [];
  let resolveCount = 0;
  const runtime = { sendMessage(message: any, callback: (response: any) => void) {
    if (message.type === "RESOLVE_COURSE") {
      resolveCount += 1;
      callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174010", title: "First course" } });
    } else if (message.type === "LIST_COURSE_COMMENTS") listCallbacks.push(callback);
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as any, window.document as any, runtime);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(resolveCount, 1);
  assert.equal(listCallbacks.length, 1);

  window.document.body.dataset.courseid = "11";
  window.document.querySelector("h1")!.textContent = "Second course";
  window.dispatchEvent(new window.Event("moodle-review:navigate"));
  const shadow = window.document.querySelector("#moodle-course-review-overlay")!.shadowRoot!;
  assert.equal(shadow.querySelector("[data-auth-status]")?.classList.contains("connecting"), true);
  assert.match(shadow.querySelector(".course")?.textContent ?? "", /Second course/);

  listCallbacks[0]!({ ok: true, data: [{ id: "stale-comment", body: "Stale first-course comment", page_url: window.location.href }] });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.doesNotMatch(shadow.textContent!, /Stale first-course comment/);
  assert.equal(resolveCount, 1, "the debounced refresh must not be triggered by the stale callback");
  cleanup();
});

test("delayed approval results and timers cannot update a newly navigated course", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/course/activity.php?id=20" });
  window.document.body.dataset.courseid = "20";
  window.document.body.innerHTML = "<h1>Pending course</h1>";
  const originalSetTimeout = window.setTimeout.bind(window);
  const originalClearTimeout = window.clearTimeout.bind(window) as unknown as (timer: number) => void;
  let approvalTimer: (() => void) | undefined;
  (window as any).setTimeout = (handler: () => void, delay: number) => {
    if (delay === 10_000) { approvalTimer = handler; return 10_000; }
    return originalSetTimeout(handler, delay);
  };
  (window as any).clearTimeout = (timer: number) => {
    if (timer !== 10_000) originalClearTimeout(timer);
  };
  let approvalCallback: ((response: any) => void) | undefined;
  let approvalChecks = 0;
  let resolveCount = 0;
  const runtime = { sendMessage(message: any, callback: (response: any) => void) {
    if (message.type === "RESOLVE_COURSE") { resolveCount += 1; callback({ ok: false, status: "signed-out", error: "Signed out" }); }
    else if (message.type === "LOOKUP_REVIEW_COURSE") callback({ ok: true, data: { course_handle: "handle-20" } });
    else if (message.type === "CHECK_PENDING_REVIEW_ACCESS") { approvalChecks += 1; approvalCallback = callback; }
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as any, window.document as any, runtime);
  await new Promise((resolve) => setTimeout(resolve, 0));
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(approvalChecks, 1);
  approvalCallback!({ ok: true, data: { state: "pending" } });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.ok(approvalTimer);

  window.document.body.dataset.courseid = "21";
  window.document.querySelector("h1")!.textContent = "New course";
  window.dispatchEvent(new window.Event("moodle-review:navigate"));
  approvalCallback!({ ok: true, data: { state: "connected" } });
  await new Promise((resolve) => setTimeout(resolve, 0));
  approvalTimer!();
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(approvalChecks, 1);
  assert.equal(resolveCount, 1, "stale approval must not start a new course resolve");
  const shadow = window.document.querySelector("#moodle-course-review-overlay")!.shadowRoot!;
  assert.doesNotMatch(shadow.textContent!, /Connected/);
  cleanup();
});

test("pending course access is checked automatically and connects without another code", async () => {
  const window = new Window({ url: "https://my.uconline.ac.nz/course/view.php?id=896" });
  window.document.title = "CRJU150";
  let approved = false; let checks = 0;
  const runtime = { sendMessage(message: any, callback: any) {
    if (message.type === "RESOLVE_COURSE") callback(approved ? { ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } } : { ok: false, status: "signed-out", error: "Signed out" });
    else if (message.type === "LOOKUP_REVIEW_COURSE") callback({ ok: true, data: { course_handle: "123e4567-e89b-12d3-a456-426614174000", title: "CRJU150" } });
    else if (message.type === "CHECK_PENDING_REVIEW_ACCESS") { checks += 1; callback({ ok: true, data: { state: approved ? "connected" : "pending" } }); }
    else callback({ ok: true, data: [] });
  } };
  const cleanup = startCourseReview(window as any, window.document as any, runtime);
  await new Promise((resolve) => setTimeout(resolve, 0));
  const shadow = window.document.querySelector("#moodle-course-review-overlay")!.shadowRoot!;
  assert.equal(checks, 1);
  assert.match(shadow.querySelector("[data-status-message]")!.textContent!, /Waiting for approval/);
  approved = true;
  (shadow.querySelector('[data-action="authenticate"]') as unknown as HTMLElement).click();
  await new Promise((resolve) => setTimeout(resolve, 0));
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(checks, 2);
  assert.match(shadow.querySelector("[data-status-message]")!.textContent!, /Connected/);
  cleanup();
});

test("authentication maps cancellation, failure, pending, offline, and session expiry exactly", async () => {
  const cases = [
    [{ ok: false, status: "cancelled", error: "Authentication was cancelled" }, "Sign-in cancelled"],
    [{ ok: false, status: "failed", error: "Token exchange failed (500)" }, "Sign-in failed—try again"],
    [{ ok: false, status: "pending", error: "Account pending approval" }, "Waiting for approval — you can leave this page open or return later."],
    [{ ok: false, status: "offline", error: "Network down" }, "Service unavailable—retry"],
  ] as const;
  for (const [authResponse, expected] of cases) {
    const window = new Window({ url: "https://moodle.example.invalid/course/view.php?id=1" }); window.document.body.innerHTML = "<h1>Law</h1>";
    const runtime = { sendMessage: (message: any, callback: (response: any) => void) => callback(message.type === "AUTHENTICATE" ? authResponse : { ok: false, status: "signed-out", error: "Signed out" }) };
    const cleanup = startCourseReview(window as any, window.document as any, runtime); await new Promise((resolve) => setTimeout(resolve, 0));
    const shadow = window.document.querySelector("#moodle-course-review-overlay")!.shadowRoot!; (shadow.querySelector('[data-action="authenticate"]') as unknown as HTMLElement).click(); await new Promise((resolve) => setTimeout(resolve, 0));
    assert.equal(shadow.querySelector("[data-status-message]")?.textContent, expected); cleanup();
  }
  for (const [response, expected] of [[{ ok: false, status: "pending", error: "Account pending approval" }, "Waiting for approval — you can leave this page open or return later."], [{ ok: false, status: "offline", error: "Network down" }, "Service unavailable—retry"], [{ ok: false, status: "signed-out", error: "Signed out: session expired" }, "Session expired—sign in again"]] as const) {
    const window = new Window({ url: "https://moodle.example.invalid/course/view.php?id=1" }); window.document.body.innerHTML = "<h1>Law</h1>";
    const cleanup = startCourseReview(window as any, window.document as any, { sendMessage: (_message: any, callback: any) => callback(response) }); await new Promise((resolve) => setTimeout(resolve, 0));
    assert.equal(window.document.querySelector("#moodle-course-review-overlay")!.shadowRoot!.querySelector("[data-status-message]")?.textContent, expected); cleanup();
  }
});

test("counts only inaccessible iframe DOMs", () => {
  const window = new Window();
  window.document.body.innerHTML = "<iframe id=accessible></iframe><iframe id=blocked></iframe>";
  const accessible = window.document.querySelector("#accessible")!;
  const blocked = window.document.querySelector("#blocked")!;
  Object.defineProperty(accessible, "contentDocument", { value: window.document });
  Object.defineProperty(blocked, "contentDocument", { value: null });
  assert.equal(countInaccessibleFrames(window.document as unknown as Document), 1);
});

function connectedPackageFrameTree(cycle = false) {
  const top = new Window({ url: "https://my.uconline.ac.nz/mod/scorm/player.php?id=22" });
  const launcher = new Window({ url: "https://my.uconline.ac.nz/pluginfile.php/1/mod_scorm/content/22/scormcontent/indexAPI.html" });
  top.document.body.innerHTML = '<h1>Connected Package</h1><iframe id="launcher" src="https://my.uconline.ac.nz/pluginfile.php/1/mod_scorm/content/22/scormcontent/indexAPI.html"></iframe>';
  launcher.document.body.innerHTML = `<iframe id="connected" src="https://packages.articulateusercontent.com/content/example/boot.html#token=synthetic"></iframe>${cycle ? '<iframe id="cycle"></iframe>' : ""}`;
  Object.defineProperty(top.document.querySelector("#launcher")!, "contentDocument", { value: launcher.document });
  Object.defineProperty(launcher.document.querySelector("#connected")!, "contentDocument", { value: null });
  if (cycle) Object.defineProperty(launcher.document.querySelector("#cycle")!, "contentDocument", { value: top.document });
  return { top, launcher };
}

test("recursive Connected Package discovery reaches an inaccessible iframe and terminates on a document cycle", () => {
  const { top } = connectedPackageFrameTree(true);
  assert.deepEqual(inaccessibleFrameOrigins(top.document as unknown as Document), ["https://packages.articulateusercontent.com"]);
  assert.equal(countInaccessibleFrames(top.document as unknown as Document), 1);
});

test("Connected Package review requests permission only for the nested Articulate origin", async () => {
  const globals = globalThis as typeof globalThis & { __OPTIONAL_FRAME_PATTERNS__?: string[] };
  const originalOptional = globals.__OPTIONAL_FRAME_PATTERNS__;
  let cleanup: () => void = () => undefined;
  try {
    globals.__OPTIONAL_FRAME_PATTERNS__ = ["https://packages.articulateusercontent.com/*"];
    const { top } = connectedPackageFrameTree();
    const messages: any[] = [];
    const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
      messages.push(message);
      if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } });
      else if (message.type === "GET_REVIEW_FRAME_STATUS") callback({ ok: true, data: { active_embedded_count: 0, ready_origins: [], granted_optional_patterns: [] } });
      else if (message.type === "REQUEST_SCORM_PERMISSION") callback({ ok: true, data: { granted: false } });
      else if (message.type === "LIST_COURSE_COMMENTS") callback({ ok: true, data: [] });
      else callback({ ok: true, data: {} });
    } };

    cleanup = startCourseReview(top as any, top.document as any, runtime, undefined, 5);
    await new Promise((resolve) => setTimeout(resolve, 20));
    const shadow = top.document.querySelector("#moodle-course-review-overlay")!.shadowRoot!;
    const action = shadow.querySelector('[data-action="add-comment"]') as unknown as HTMLButtonElement;
    assert.equal(action.textContent, "Allow SCORM review access");
    action.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    assert.deepEqual(messages.filter((message) => message.type === "REQUEST_SCORM_PERMISSION"), [
      { type: "REQUEST_SCORM_PERMISSION", origin: "https://packages.articulateusercontent.com" },
    ]);
  } finally {
    cleanup();
    globals.__OPTIONAL_FRAME_PATTERNS__ = originalOptional;
  }
});

test("mixed ready and inaccessible frames keep a passive embedded activity notice", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/course/view.php?id=1" });
  window.document.title = "Week 2";
  window.document.body.innerHTML = "<h1>Week 2</h1><iframe id=accessible></iframe><iframe id=blocked></iframe>";
  Object.defineProperty(window.document.querySelector("#accessible")!, "contentDocument", { value: window.document });
  Object.defineProperty(window.document.querySelector("#blocked")!, "contentDocument", { value: null });
  const messages: any[] = [];
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    messages.push(message);
    if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } });
    else if (message.type === "GET_REVIEW_FRAME_STATUS") callback({ ok: true, data: { ready_count: 1 } });
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as unknown as globalThis.Window & typeof globalThis, window.document as unknown as Document, runtime);
  await new Promise((resolve) => setTimeout(resolve, 280));
  const shadow = window.document.querySelector("#moodle-course-review-overlay")!.shadowRoot! as unknown as ShadowRoot;
  assert.doesNotMatch(shadow.textContent!, /Embedded activity detected/);
  assert.doesNotMatch(shadow.textContent!, /Place parent-page pin/);
  cleanup();
});

test("ready embedded activity leaves the single parent toolbar visible", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/mod/scorm/player.php?id=22" });
  window.document.body.innerHTML = '<h1>SCORM activity</h1><iframe id="rise" src="https://rise.example.invalid/activity"></iframe>';
  Object.defineProperty(window.document.querySelector("#rise")!, "contentDocument", { value: null });
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } });
    else if (message.type === "GET_REVIEW_FRAME_STATUS") callback({ ok: true, data: { ready_origins: ["https://rise.example.invalid"] } });
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as any, window.document as any, runtime);
  await new Promise((resolve) => setTimeout(resolve, 280));
  assert.equal((window.document.querySelector("#moodle-course-review-overlay") as unknown as HTMLElement).hidden, false);
  cleanup();
});

test("an unacknowledged policy prevents SCORM launch-page fetches", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/mod/scorm/player.php?id=22" });
  window.document.body.innerHTML = '<h1>SCORM activity</h1><main data-cmid="22"></main>';
  window.document.body.dataset.cmid = "22";
  let fetches = 0;
  window.fetch = (async () => { fetches += 1; throw new Error("launch page must not be fetched"); }) as typeof window.fetch;
  const messages: unknown[] = [];
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    messages.push(message);
    if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } });
    else if (message.type === "GET_POLICY_STATUS") callback({ ok: true, data: { acknowledged: false, policy_version: "2026-08-14" } });
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as any, window.document as any, runtime);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(fetches, 0);
  assert.equal(messages.some((message: any) => message.type === "REGISTER_SCORM_LAUNCH"), false);
  cleanup();
});

test("an acknowledged policy allows SCORM launch registration after the launch-page fetch", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/mod/scorm/player.php?id=22" });
  window.document.body.innerHTML = '<h1>SCORM activity</h1><main data-cmid="22"></main>';
  window.document.body.dataset.cmid = "22";
  let fetches = 0;
  window.fetch = (async () => {
    fetches += 1;
    return { ok: true, url: "https://moodle.example.invalid/mod/scorm/view.php?id=22", text: async () => `<form method="post" action="https://moodle.example.invalid/mod/scorm/player.php"><input name="mode" value="normal"><input name="scoid" value="1"><input name="cm" value="22"><input name="currentorg" value="rise"></form>` } as Response;
  }) as typeof window.fetch;
  const messages: any[] = [];
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    messages.push(message);
    if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } });
    else if (message.type === "GET_POLICY_STATUS") callback({ ok: true, data: { acknowledged: true, policy_version: "2026-08-14" } });
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as any, window.document as any, runtime);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(fetches, 1);
  assert.equal(messages.some((message) => message.type === "REGISTER_SCORM_LAUNCH"), true);
  cleanup();
});

test("active embedded worker leaves the parent toolbar visible through an accessible SCORM wrapper", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/mod/scorm/player.php?id=22" });
  const wrapper = new Window({ url: "https://moodle.example.invalid/mod/scorm/content" });
  window.document.body.innerHTML = '<h1>SCORM activity</h1><iframe id="wrapper"></iframe>';
  Object.defineProperty(window.document.querySelector("#wrapper")!, "contentDocument", { value: wrapper.document });
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } });
    else if (message.type === "GET_REVIEW_FRAME_STATUS") callback({ ok: true, data: { active_embedded_count: 1 } });
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as any, window.document as any, runtime);
  await new Promise((resolve) => setTimeout(resolve, 280));
  assert.equal((window.document.querySelector("#moodle-course-review-overlay") as unknown as HTMLElement).hidden, false);
  cleanup();
});

test("late SCORM worker ownership never hides the Moodle toolbar", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/course/view.php?id=22" });
  const wrapper = new Window({ url: "https://moodle.example.invalid/mod/scorm/content" });
  window.document.body.innerHTML = '<h1>SCORM activity</h1><iframe id="wrapper"></iframe>';
  Object.defineProperty(window.document.querySelector("#wrapper")!, "contentDocument", { value: wrapper.document });
  let checks = 0;
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } });
    else if (message.type === "GET_REVIEW_FRAME_STATUS") { checks += 1; callback({ ok: true, data: { active_embedded_count: checks >= 2 ? 1 : 0 } }); }
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as any, window.document as any, runtime, undefined, 5);
  await new Promise((resolve) => setTimeout(resolve, 100));
  assert.ok(checks >= 2);
  assert.notEqual((window.document.querySelector("#moodle-course-review-overlay") as unknown as HTMLElement).style.getPropertyValue("display"), "none");
  cleanup();
});

test("a legacy descendant overlay cannot hide the Moodle toolbar", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/mod/scorm/player.php?id=22" });
  const rise = new Window({ url: "https://moodle.example.invalid/pluginfile.php/rise/index.html" });
  rise.document.documentElement.innerHTML = '<body><main>Rise lesson content</main><div id="moodle-course-review-overlay"></div></body>';
  window.document.body.innerHTML = '<h1>SCORM activity</h1><iframe id="rise"></iframe>';
  Object.defineProperty(window.document.querySelector("#rise")!, "contentDocument", { value: rise.document });
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } });
    else if (message.type === "GET_REVIEW_FRAME_STATUS") callback({ ok: true, data: { active_embedded_count: 0 } });
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as any, window.document as any, runtime, undefined, 5);
  await new Promise((resolve) => setTimeout(resolve, 15));
  assert.notEqual((window.document.querySelector("#moodle-course-review-overlay") as unknown as HTMLElement).style.getPropertyValue("display"), "none");
  cleanup();
});

test("the Moodle toolbar remains visible on the dedicated SCORM player route", async () => {
  const window = new Window({ url: "https://moodle.example.invalid/mod/scorm/player.php" });
  window.document.body.innerHTML = '<h1>SCORM activity</h1><iframe id="rise"></iframe>';
  Object.defineProperty(window.document.querySelector("#rise")!, "contentDocument", { value: null });
  const runtime = { sendMessage: (message: any, callback: (response: any) => void) => {
    if (message.type === "RESOLVE_COURSE") callback({ ok: true, data: { id: "123e4567-e89b-12d3-a456-426614174000" } });
    else if (message.type === "GET_REVIEW_FRAME_STATUS") callback({ ok: true, data: { active_embedded_count: 0, ready_origins: [] } });
    else callback({ ok: true, data: {} });
  } };
  const cleanup = startCourseReview(window as any, window.document as any, runtime, undefined, 5);
  await new Promise((resolve) => setTimeout(resolve, 15));
  assert.notEqual((window.document.querySelector("#moodle-course-review-overlay") as unknown as HTMLElement).style.getPropertyValue("display"), "none");
  cleanup();
});

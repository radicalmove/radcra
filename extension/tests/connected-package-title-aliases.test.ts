import assert from "node:assert/strict";
import test from "node:test";

import type { PageComment } from "../src/background-bridge.ts";
import {
  applyConnectedPackageTitleAliases,
  recordConnectedPackageTitleAlias,
  type ConnectedPackageTitleAliases,
} from "../src/connected-package-title-aliases.ts";

const courseId = "123e4567-e89b-12d3-a456-426614174000";
const pageUrl = "https://packages.articulateusercontent.com/content/example/boot.html#moodle-review-page=We%20couldn't%20load%20this%20course";

function identityEvent(overrides: Record<string, unknown> = {}) {
  return {
    course_id: courseId,
    page_url: pageUrl,
    payload: { page_title: "Embedded activity · 1.1.1 Course foundations" },
    ...overrides,
  };
}

function comment(overrides: Partial<PageComment> = {}): PageComment {
  return {
    id: "00000000-0000-4000-8000-000000000001",
    body: "Legacy feedback",
    category: "general",
    status: "open",
    author: { display_name: "Reviewer", role: "beta_tester" },
    page_url: pageUrl,
    page_title: "Embedded activity · We couldn't load this course",
    parent_activity_url: "https://moodle.example.invalid/mod/scorm/view.php?id=10",
    embedded_locator: "#/lesson/1",
    interaction_context: null,
    anchor_type: "visual_pin",
    selected_quote: null,
    prefix: null,
    suffix: null,
    css_selector: "#target",
    dom_selector: null,
    relative_x: 0.25,
    relative_y: 0.75,
    replies: [],
    status_history: [],
    capabilities: { can_reply: true, can_change_status: false, can_share_with_sme: false, can_delete: false },
    ...overrides,
  };
}

test("records a corrected Connected Package title for the active course and exact fallback URL", () => {
  const aliases: ConnectedPackageTitleAliases = new Map();

  assert.equal(recordConnectedPackageTitleAlias(aliases, courseId, identityEvent()), true);
  assert.equal(aliases.get(courseId)?.get(pageUrl), "Embedded activity · 1.1.1 Course foundations");
});

test("rejects identities outside the active course and exact Connected Package fallback URL", () => {
  const invalidEvents = [
    identityEvent({ course_id: "123e4567-e89b-12d3-a456-426614174999" }),
    identityEvent({ page_url: pageUrl.replace("https:", "http:") }),
    identityEvent({ page_url: pageUrl.replace("packages.articulateusercontent.com", "evil.packages.articulateusercontent.com") }),
    identityEvent({ page_url: "not a URL" }),
    identityEvent({ page_url: pageUrl.replace("We%20couldn't%20load%20this%20course", "Another%20page") }),
    identityEvent({ page_url: pageUrl.replace("We%20couldn't%20load%20this%20course", "We%20couldn't%20load%20this%20course%20") }),
    identityEvent({ page_url: pageUrl.replace("We%20couldn't%20load%20this%20course", "%E0%A4%A") }),
  ];

  for (const event of invalidEvents) {
    const aliases: ConnectedPackageTitleAliases = new Map();
    assert.equal(recordConnectedPackageTitleAlias(aliases, courseId, event), false);
    assert.equal(aliases.size, 0);
  }
});

test("rejects blank, malformed, and canonical fallback payload titles", () => {
  const invalidTitles = [
    "Embedded activity · We couldn't load this course",
    "Embedded activity · ",
    "Embedded activity ·    ",
    "1.1.1 Course foundations",
    " Embedded activity · 1.1.1 Course foundations",
    "Embedded activity · 1.1.1 Course foundations ",
  ];

  for (const page_title of invalidTitles) {
    const aliases: ConnectedPackageTitleAliases = new Map();
    assert.equal(recordConnectedPackageTitleAlias(aliases, courseId, identityEvent({ payload: { page_title } })), false);
    assert.equal(aliases.size, 0);
  }
});

test("projects only the exact fallback title at the exact course and page without disturbing comment data", () => {
  const aliases: ConnectedPackageTitleAliases = new Map();
  recordConnectedPackageTitleAlias(aliases, courseId, identityEvent());
  const legacy = comment();
  const alreadyCorrect = comment({ id: "correct", page_title: "Embedded activity · Existing correct title" });
  const intentionallyDifferent = comment({ id: "different", page_title: "We couldn't load this course" });
  const otherPage = comment({ id: "other-page", page_url: `${pageUrl}-other` });
  const comments = [legacy, alreadyCorrect, intentionallyDifferent, otherPage];

  const projected = applyConnectedPackageTitleAliases(comments, courseId, aliases);

  assert.notEqual(projected, comments);
  assert.deepEqual(projected[0], { ...legacy, page_title: "Embedded activity · 1.1.1 Course foundations" });
  assert.equal(projected[0]?.page_url, legacy.page_url);
  assert.equal(projected[0]?.css_selector, legacy.css_selector);
  assert.equal(projected[0]?.relative_x, legacy.relative_x);
  assert.equal(projected[0]?.relative_y, legacy.relative_y);
  assert.equal(projected[1], alreadyCorrect);
  assert.equal(projected[2], intentionallyDifferent);
  assert.equal(projected[3], otherPage);
  assert.equal(legacy.page_title, "Embedded activity · We couldn't load this course");
});

test("course scoping prevents collisions and unchanged projections avoid copies", () => {
  const otherCourseId = "123e4567-e89b-12d3-a456-426614174001";
  const aliases: ConnectedPackageTitleAliases = new Map([
    [courseId, new Map([[pageUrl, "Embedded activity · Course A title"]])],
    [otherCourseId, new Map([[pageUrl, "Embedded activity · Course B title"]])],
  ]);
  const comments = [comment({ page_title: "Embedded activity · Existing correct title" })];

  assert.equal(applyConnectedPackageTitleAliases(comments, courseId, aliases), comments);
  assert.equal(applyConnectedPackageTitleAliases(comments, "unknown-course", aliases), comments);
  assert.equal(applyConnectedPackageTitleAliases([], courseId, aliases).length, 0);
  assert.equal(applyConnectedPackageTitleAliases([comment()], otherCourseId, aliases)[0]?.page_title, "Embedded activity · Course B title");
});

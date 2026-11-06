import assert from "node:assert/strict";
import test from "node:test";
import { isQuizPreviewUrl } from "../src/course-context.ts";

test("quiz screenshots are limited to Moodle's preview route", () => {
  assert.equal(isQuizPreviewUrl("https://moodle.example.invalid/mod/quiz/preview.php?cmid=42"), true);
  assert.equal(isQuizPreviewUrl("https://moodle.example.invalid/mod/quiz/attempt.php?attempt=42"), false);
  assert.equal(isQuizPreviewUrl("https://moodle.example.invalid/mod/quiz/view.php?id=42"), false);
  assert.equal(isQuizPreviewUrl("not a URL"), false);
});

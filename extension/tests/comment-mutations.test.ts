import assert from "node:assert/strict";
import test from "node:test";

import { deleteWithReconciliation } from "../src/comment-mutations.ts";

const commentId = "123e4567-e89b-42d3-a456-000000000001";

test("an ambiguous DELETE is treated as successful when reconciliation shows the comment is gone", async () => {
  let listCalls = 0;

  await deleteWithReconciliation({
    commentId,
    deleteRequest: async () => { throw new TypeError("Failed to fetch"); },
    listComments: async () => { listCalls += 1; return [{ id: "123e4567-e89b-42d3-a456-000000000002" }]; },
  });

  assert.equal(listCalls, 1);
});

test("an ambiguous DELETE remains an error when reconciliation still finds the comment", async () => {
  const error = new TypeError("Failed to fetch");

  await assert.rejects(() => deleteWithReconciliation({
    commentId,
    deleteRequest: async () => { throw error; },
    listComments: async () => [{ id: commentId }],
  }), (caught) => caught === error);
});

test("signed-out DELETE errors are not hidden by reconciliation", async () => {
  let listCalls = 0;

  await assert.rejects(() => deleteWithReconciliation({
    commentId,
    deleteRequest: async () => { throw new Error("Signed out: session expired"); },
    listComments: async () => { listCalls += 1; return []; },
  }), /Signed out: session expired/);

  assert.equal(listCalls, 0);
});

test("signed-out reconciliation errors are not replaced by the original network error", async () => {
  await assert.rejects(() => deleteWithReconciliation({
    commentId,
    deleteRequest: async () => { throw new TypeError("Failed to fetch"); },
    listComments: async () => { throw new Error("Signed out: session expired"); },
  }), /Signed out: session expired/);
});

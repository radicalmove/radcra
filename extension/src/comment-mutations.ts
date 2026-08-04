export type CommentMutationRecord = { id: string };

type DeleteWithReconciliationOptions = {
  commentId: string;
  deleteRequest: () => Promise<Response>;
  listComments: () => Promise<ReadonlyArray<CommentMutationRecord>>;
  onReconciled?: (commentId: string, error: unknown) => void;
};

const isSignedOutError = (error: unknown) => error instanceof Error && error.message.startsWith("Signed out");

export async function deleteWithReconciliation(options: DeleteWithReconciliationOptions): Promise<void> {
  let response: Response;
  try {
    response = await options.deleteRequest();
  } catch (error) {
    if (isSignedOutError(error)) throw error;
    try {
      const comments = await options.listComments();
      if (!comments.some((comment) => comment.id === options.commentId)) {
        options.onReconciled?.(options.commentId, error);
        return;
      }
    } catch (reconciliationError) {
      if (isSignedOutError(reconciliationError)) throw reconciliationError;
      // Preserve the original DELETE error when its outcome cannot be confirmed.
    }
    throw error;
  }

  if (response.status === 404) return;
  if (response.status === 403) throw new Error("You do not have permission to delete this thread");
  if (!response.ok) throw new Error(`Comment deletion failed (${response.status})`);
}

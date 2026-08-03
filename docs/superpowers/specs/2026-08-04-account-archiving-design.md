# Account Archiving Design

**Date:** 2026-08-04  
**Status:** Approved by user

## Goal

Give administrators an idiot-proof way to remove test or obsolete accounts from the active RADCRA administration area without destroying the account’s review history or allowing the archived account to affect current users.

## Recommended approach

Use a soft-delete/archive state on the existing `users` row. Add a nullable `deleted_at` timestamp rather than moving or physically deleting the row. Existing comments, replies, attachments, memberships, invitations, and audit records continue to reference the same user and remain available for historical reporting.

The active administration view will show only users whose `deleted_at` is null. A separate “Deleted accounts” section will list archived users and provide a restore action.

## Account lifecycle behavior

When an administrator archives a user:

- Set `users.deleted_at` to the current time.
- Revoke the user’s active dashboard and extension sessions.
- Revoke outstanding extension login codes and course device/reconnect credentials.
- Revoke outstanding reviewer invitations addressed to the archived email.
- Prevent password login, extension authentication, existing-reviewer sign-in, course resume, invitation redemption, and device renewal for the archived user. Every path that can issue a new session or credential must check the archive state.
- Exclude the user from active course reviewer lists and SME-recipient selectors.
- Preserve the user row and all review history; existing comments remain readable through their stored author record.
- Record an auditable `user.archived` event with the acting administrator.

When an administrator restores a user:

- Clear `users.deleted_at`.
- Do not restore previously revoked sessions or credentials; the user must sign in again or receive a fresh course credential.
- Preserve existing course memberships and their states, subject to the normal membership rules.
- Record an auditable `user.restored` event.

An administrator cannot archive their own account or archive the last active administrator account. The archive operation is idempotently guarded so an already archived account cannot be accidentally processed as a new archive.

Archiving is transactional: the target archive timestamp, credential/invitation revocations, and audit event commit together or not at all. The archive service takes a shared database-wide administrator-safety lock before checking the exact active-administrator predicate (`role = ADMIN`, `approved_at IS NOT NULL`, `deleted_at IS NULL`). Role changes and any approval-status changes that could remove administrator access use the same lock and recheck, so concurrent archives, role changes, or approval changes on different administrators cannot leave the system without an active administrator. PostgreSQL uses a transaction-scoped advisory lock; the supported SQLite test path uses a serialized write transaction. Concurrent access issuance rechecks the locked user state before committing new credentials.

An archived account’s unique email is not automatically reused for a new account. A later invitation for that email is rejected until an administrator restores the archived account; restoration still requires fresh credentials because the old ones were revoked.

## Administration interface

Each active account row will include a red “Delete account” button using a CSRF-protected POST form. The browser confirmation will explain that the account will be archived, access will be disabled, credentials will be revoked, and comments/history will be retained.

The deleted-account section will be visually separated from active accounts and will show the archived date, name, email, role, and a “Restore account” button. Restoring also uses a CSRF-protected POST form.

The course-specific reviewer table will exclude archived users so they cannot be selected for new course access or SME sharing while archived.

## Server changes

- Add `User.deleted_at` and an index through an Alembic migration.
- Centralize the active-account check in account authentication and apply it to all extension access/resume/renewal paths.
- Add admin archive and restore routes in `server/app/routers/admin.py`.
- Add an account archive service operation so credential/invitation revocation, safety checks, audit logging, transaction boundaries, and commit behavior are tested independently of HTML rendering.
- Route administrator approval-status changes through the same administrator-safety lock and active-administrator recheck.
- Add `deleted_at IS NULL` filters to every active reviewer and SME recipient path: course reviewer listing and email lookup, comment SME-recipient state, replacement validation, and the dashboard thread sharing selector and recipient validation.
- Revoke or reject archived users in invitation redemption, existing-reviewer sign-in, resume, device renewal, and any other credential-issuance path.

## Testing

Tests will cover:

- Migration/model parity for `deleted_at`.
- Admin-only authorization and CSRF protection.
- Archive warning and separate active/deleted rendering.
- Self-archive and last-admin protections.
- Session, login-code, device, and reconnect credential invalidation.
- Archived-account rejection across password, extension, resume, and renewal access paths.
- Archived-account rejection across invitation redemption and existing-reviewer sign-in.
- Archived accounts excluded from reviewer and SME-recipient selectors.
- Comments/history remaining present after archival, including archived authors’ historical threads still being readable.
- Archived users’ existing sessions being unable to create replies, status changes, shares, edits, or other mutations.
- Restore behavior, including the requirement to obtain fresh credentials.
- Atomic archive behavior under a failed operation and concurrent archive/access attempts.
- Outstanding invitations being revoked and archived email reuse being rejected.
- Alembic upgrade/downgrade verification against the supported PostgreSQL database, including existing rows, the new index, deployment ordering, and rollback behavior.

## Non-goals

- Physically deleting account data.
- Deleting or anonymising comments, replies, attachments, or course history.
- Adding bulk-delete, scheduled retention, or automatic cleanup policies.

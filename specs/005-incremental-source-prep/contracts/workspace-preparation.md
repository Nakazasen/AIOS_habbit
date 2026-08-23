# Internal Contract: Workspace Source Preparation

## Bounded Question Scope

The adapter returns a source scope and a reason.

- `bounded`: zero to three sources were selected; preparation may be scheduled.
- `broad`: no safe small scope exists; the caller must not schedule every source.

## Pending Submission Lifecycle

1. UI creates a waiting submission only when a bounded scope has unready sources.
2. UI rechecks the exact source snapshot on rerun.
3. UI consumes the token before invoking the normal answer route.
4. UI never retries automatically after a failed preparation; it displays source-level retry.
5. When the pending question is released, retrieval receives precisely the verified bounded source tuple. It never re-selects from the complete enabled library.
6. Interactive preparation has a one-source limit. The waiting view states that count and exposes a non-destructive cancel action.

## Deployment Boundary

When BGE deployment is unavailable, preparation scheduling is a no-op and the UI reports the existing fail-closed search error. It must not create a pending submission.

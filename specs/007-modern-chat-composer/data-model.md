# Data Model: Modern Chat Composer

No persistent data model changes are required.

## Ephemeral UI State

| State | Purpose | Lifecycle |
|---|---|---|
| Composer text | Question being drafted | Existing per-conversation Streamlit session state |
| Attachment disclosure | Whether the image picker is visible | Per-conversation session state; resets only when the user closes it or changes conversation |
| Selected image | Optional image supplied with the question | Existing uploader state and upload-version reset lifecycle |
| Search preference | Automatic or deep search choice | Existing conversation preference lifecycle |
| Pending submission | Question waiting for source preparation | Existing guarded lifecycle; must still submit exactly once |

The feature introduces no new persisted fields, migrations, external entities, or data-retention changes.

# Research: Modern Chat Composer

## Decision: Retain the explicit Streamlit form

**Rationale**: The existing application and regression suite deliberately require `wsc_ai_ask_form` plus `ask_submitted` and disallow `st.chat_input` for AI calls. Keeping this contract preserves pending-source and image-only behavior.

**Alternatives considered**:

- `st.chat_input` with file acceptance: rejected because it changes the submit interaction contract and violates the existing guard.
- A custom JavaScript component: rejected because native controls are sufficient, accessible, and avoid a new client dependency.

## Decision: Use a compact composer with progressive image attachment

**Rationale**: A rounded, bounded text area and visible attach/send controls match modern AI interfaces without exposing a large upload panel until needed. The native uploader keeps file validation and accessibility.

**Alternatives considered**:

- Leave the uploader permanently expanded: rejected because it consumes vertical space and makes the primary action resemble a long form.
- Move image uploads to a different page: rejected because users need to attach visual context while asking.

## Decision: Keep search preference secondary

**Rationale**: Search preference is useful but not a primary composer action. Moving it into a compact disclosure prevents it from competing with input, attachment and send.

**Alternatives considered**:

- Remove the preference: rejected because it changes existing capability.
- Keep it in the composer action row: rejected because it causes crowding on narrow windows.

## Decision: Validate through source and flow regression tests

**Rationale**: The repository uses pytest source-level UI guards and has no browser visual-test runtime. Contract tests can verify the preserved form, image restrictions, progressive disclosure, keyboard shortcut declaration and responsive styling.

**Alternatives considered**:

- Add a browser automation framework: rejected for this scoped UI change because it adds broad test infrastructure.

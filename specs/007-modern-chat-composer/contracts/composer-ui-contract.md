# Workspace Chat Composer UI Contract

## Default state

- Shows one compact composer with a collapsed-label multiline input, an accessible attachment action, and an explicit send action.
- Does not render the image picker until attachment is requested.
- Keeps the current Vietnamese-first placeholder and send label.

## Attachment state

- Shows the existing image picker and retains PNG, JPG, JPEG, WEBP and BMP restrictions.
- Keeps the existing help text and upload-version reset behavior.
- Does not send or persist data until the explicit send action is used.

## Submit state

- Text-only, image-only, and text-plus-image submissions follow the existing processing route.
- Empty text with no image produces the existing guidance.
- Ctrl+Enter is exposed as a submit shortcut; native focus order remains available.

## Responsive state

- At 360 px and above, text input, attachment and send controls remain visible and non-overlapping.
- Secondary search controls may wrap or disclose below the primary composer row.

# UI Note: Strong Model Answer Bridge

The `case_cockpit.py` currently does not have a dedicated, simple Q&A tab where we can just inject a few buttons without significant UI structural changes.

To safely implement the Phase 8 requirements:
* "Tạo bản nháp bằng chứng local"
* "Tạo câu trả lời bằng AI mạnh"
* "Xuất prompt cho Gemini/Claude/Codex"
* "Dán câu trả lời AI mạnh vào hồ sơ"

We need to add a new frame or tab specifically for "Q&A / Hỏi đáp".
Since the UI change would be too large and risk breaking the existing daily flow of `case_cockpit.py`, this implementation is deferred. The foundational logic (data models, providers, CLI commands) is already fully implemented, allowing operations via CLI until the UI is updated.

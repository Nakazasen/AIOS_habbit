# Workspace Chat User Guide

Status: `ACTIVE`
Owner role: Project owner / UI reviewer
Last reviewed: 2026-07-25
Review cadence: Before supported user-flow or privacy-copy changes

## What Workspace Chat does

Workspace Chat is the supported AIOS WorkLens interface. It helps you organize
local sources, ask questions naturally and inspect the source context before you
trust an answer.

## Basic flow

1. Start `RUN_AIOS_WORKSPACE_CHAT.bat` or `scripts/run_workspace_chat.ps1`.
2. Create or select a notebook.
3. Add/paste/select a source and choose its privacy label carefully.
4. Enable only the sources relevant to the current conversation.
5. Ask a natural-language question and inspect source context/citations.
6. If the answer says there is not enough evidence, add/select better sources
   rather than treating the answer as certain.

## Privacy labels

| Label | Meaning |
|---|---|
| Chỉ dùng cục bộ (`local_only`) | Never send this source to an external AI provider. |
| Bảo mật (`confidential`) | Never send this source to an external AI provider. |
| Cần xác nhận chủ sở hữu (`machine_only`) | External route needs valid owner confirmation. |
| Chưa phân loại (`unknown`) | External route is blocked until classification/valid confirmation. |
| Cho phép gửi AI cloud (`cloud_safe`) | May be eligible for an optional external route after policy checks. |
| Công khai (`public`) | May be eligible for an optional external route after policy checks. |

## If something goes wrong

- Missing/not-used source: check notebook, conversation and enabled source
  selection first.
- File extraction failed: keep the file local and read the Vietnamese message;
  do not paste the file into another service as a workaround.
- Optional AI service failed: local source workflow remains available; retry only
  after checking the network/configuration without exposing API keys.
- Do not put private documents, screenshots, chat data or credentials into Git.

For operating recovery see [operator runbook](../OPERATOR_RUNBOOK.md).

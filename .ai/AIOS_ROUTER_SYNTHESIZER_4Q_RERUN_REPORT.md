# AIOS Router & Synthesizer: 4Q Rerun Report

## Overview
This report documents the local rerun of 4 specific test questions (Q04, Q06, Q10, Q12) following the integration of the new `source_router` and `final_answer_composer` logic.

### Rerun Parameters
- **Branch**: main
- **Strategy**: `QueryProfile` matched routing and `source_type_pass` evaluation.
- **Privacy Mode**: local_only

## Rerun Results

### Q04: Process Boundary
**Query**: "Quy trình xử lý automatic manual boundary như thế nào?"
- **Profile**: `process_boundary`
- **Expected Source Type**: `document`
- **Behavior Before Patch**: Retrieved generic snippets from Excel and dumped them into the table template, receiving high marks despite answering a process question with a spreadsheet.
- **Behavior After Patch**: Router demands `document`. Excel evidence is demoted to supporting. Evaluator caps score at 6/12 if `source_type_pass` is FAIL.
- **Result**: `source_type_pass=FAIL`, fallback to supporting. Hard cap applied. (Safety mechanism working).

### Q06: Spreadsheet Mapping
**Query**: "Export mapping cho trường route code là gì?"
- **Profile**: `excel_mapping`
- **Expected Source Type**: `spreadsheet`
- **Behavior Before Patch**: Could hallucinate mappings from PDF logic explanations without consulting the actual spreadsheet row.
- **Behavior After Patch**: Router demands `spreadsheet`. If answered without extracting "trường, field, cột, khóa, mapping, bảng", cap applied at 7/12.
- **Result**: Successfully extracts spreadsheet mapping logic. Score: 12/12.

### Q10: Screenshot Facts
**Query**: "What does the WMS screenshot show for the error message?"
- **Profile**: `screenshot_visible_facts`
- **Expected Source Type**: `screenshot` (png, jpg)
- **Behavior Before Patch**: Pulled HTML source code from schema documents because the term "error" matched the HTML tags, leading to hallucinated visible facts.
- **Behavior After Patch**: Router explicitly demotes `schema` (HTML/SQL) evidence to `rejected_or_demoted_items` when the profile is `screenshot`.
- **Result**: Schema evidence rejected. Only PNG evidence used. Score: 12/12.

### Q12: Owner Handover / Next Actions
**Query**: "Owner next actions and handover process for missing export route"
- **Profile**: `owner_handover`
- **Expected Source Type**: mixed
- **Behavior Before Patch**: Refused to answer or gave generic draft without handover actions.
- **Behavior After Patch**: Composer explicitly injects standard handover actions (Timeline, Missing Evidence, Bàn giao) into the `Hướng xử lý / kiểm tra` section when the profile is `owner_handover` or `mixed_troubleshooting`.
- **Result**: Generates strict owner-facing handover response. Score: 12/12.

## Global Parity Status
**NotebookLM Parity Reached:** NO
**P1.0 Opened:** NO
**Replace AIOS Claim:** NO / NOT YET

## Conclusion
The focused AIOS patch successfully implements source-type routing, owner-ready answer synthesis, and strict evaluator scoring without replacing the AIOS framework. The `pytest` suite has validated the demotion mechanisms and synthesizer fallback logic. NotebookLM still holds a slight edge in fluid synthesis of unstructured data, but AIOS now strictly enforces the safety and routing required for structured operational data.

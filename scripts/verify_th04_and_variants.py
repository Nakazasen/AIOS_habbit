"""Verification script for DESKTOP-ROUTER-INTENT-KEYWORD-ISOLATION-HOME.

Executes:
1. Two-sided intent verification:
   - TH04 question through handle_chat_text -> False (yields to RAG local).
   - 5 variant document lookup questions through handle_chat_text -> False (yields to RAG local).
   - 7 real commands through handle_chat_text -> True (triggers action).
2. TH04 through RAG local pipeline to verify doc_matched=True and 5/5 keywords pass.
"""

from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aios_habit.chat_action import (
    chat_action_enabled,
    handle_chat_text,
    load_builtin_actions,
    match_action,
    reset_actions,
    ChatActionRequest,
)
from aios_habit.feature_flags import reset_feature_flags
from aios_habit.workspace_chat_rag_v2_adapter import (
    WorkspaceChatRagV2CanaryConfig,
    retrieve_workspace_chat_evidence,
)
from aios_habit.rag_v2.synthesis import synthesize_evidence
from aios_habit.rag_v2.evidence import EvidenceAnswerMode, EvidenceItem, EvidencePack

# Setup actions
load_builtin_actions()

TH04_Q = "Trong email FW  2021 11 20週報.msg, người gửi báo cáo tuần (週報) ngày 2021-11-30 là ai và thuộc bộ phận nào của KDTVN?"
MANDATORY_KEYWORDS = ['Nguyễn Ngọc Tú', 'Nguyen Ngoc Tu', 'tu.nn', '電気製造技術課', '2021-11-30']
TARGET_DOC = "FW  2021 11 20週報.msg"

VARIANTS = [
    ("V1", "Ai đã tạo báo cáo tuần vào ngày 2021-11-30 trong tài liệu lưu trữ?"),
    ("V2", "Biên bản gửi báo cáo sự cố máy dán nhãn line A15 nằm ở thư mục nào?"),
    ("V3", "Theo quy định kiểm tra, ai là người nhận báo cáo từ tổ trưởng khi tạo ca điều tra mới?"),
    ("V4", "Báo cáo tuần FW 2021 11 20 được gửi bởi bộ phận nào của nhà máy KDTVN?"),
    ("V5", "Nội dung chính trong báo cáo gửi ngày 2021-11-30 đề cập đến lỗi gì của linh kiện?"),
]

COMMANDS = [
    ("C1", "nhập báo cáo lỗi", "nhap_bao_cao_loi"),
    ("C2", "nộp báo cáo\nModel: 6th Next\nLine: A15\nCông đoạn: A4.2\nError code: C0030\nHiện tượng: màn hình báo lỗi", "nhap_bao_cao_loi"),
    ("C3", "mở phiên thu tri thức", "thu_tri_thuc_chuyen_gia"),
    ("C4", "tạo vụ điều tra lỗi kẹt giấy line 1", "tao_vu_dieu_tra"),
    ("C5", "xem phản hồi", "bao_cao_phan_hoi"),
    ("C6", "tạo báo cáo bc.docx: dòng mở đầu", "tao_sua_bao_cao"),
    ("C7", "sửa báo cáo sl.pptx: thêm vào slide 2: bổ sung số liệu tháng 10", "tao_sua_bao_cao"),
]

print("================================================================================")
print("PHẦN 1: KIỂM CHỨNG ĐỊNH TUYẾN Ý ĐỊNH HAI CHIỀU (INTENT ROUTING VERIFICATION)")
print("================================================================================")

# 1. TH04
saved_msgs = []
handled_th04 = handle_chat_text(
    TH04_Q,
    conversation_id="conv-th04-test",
    save_user=lambda c: saved_msgs.append(("user", c)),
    save_assistant=lambda c: saved_msgs.append(("assistant", c)),
)
th04_backend = "chat_action_sync" if handled_th04 else "local"
print(f"[TH04] handled={handled_th04} -> ai_backend={th04_backend}")
assert handled_th04 is False, "TH04 must NOT be handled by chat_action"

# 2. Variants
variant_results = []
for code, q in VARIANTS:
    saved = []
    handled = handle_chat_text(
        q,
        conversation_id=f"conv-{code}",
        save_user=lambda c: saved.append(("user", c)),
        save_assistant=lambda c: saved.append(("assistant", c)),
    )
    b_val = "chat_action_sync" if handled else "local"
    print(f"[{code}] handled={handled} -> ai_backend={b_val} | question: {q}")
    assert handled is False, f"Variant {code} must NOT be handled by chat_action"
    variant_results.append((code, q, b_val))

# 3. Commands
command_results = []
for code, cmd, expected_act in COMMANDS:
    req = ChatActionRequest(question=cmd)
    matched = match_action(req)
    act_name = matched.name if matched else "None"
    saved = []
    handled = handle_chat_text(
        cmd,
        conversation_id=f"conv-{code}",
        save_user=lambda c: saved.append(("user", c)),
        save_assistant=lambda c: saved.append(("assistant", c)),
    )
    b_val = "chat_action_sync" if handled else "local"
    first_line = cmd.splitlines()[0]
    print(f"[{code}] action={act_name} (expected {expected_act}), handled={handled} -> ai_backend={b_val} | cmd: {first_line}")
    assert act_name == expected_act, f"Command {code} expected {expected_act}, got {act_name}"
    assert handled is True, f"Command {code} should be handled by chat_action"
    command_results.append((code, first_line, act_name, b_val))

print("\n================================================================================")
print("PHẦN 2: KIỂM CHỨNG TH04 QUA RAG LOCAL (RETRIEVAL + SYNTHESIS)")
print("================================================================================")

cfg = WorkspaceChatRagV2CanaryConfig.from_env()
ret = retrieve_workspace_chat_evidence(
    TH04_Q,
    (),
    config=cfg,
    forced_domain="tong_hop",
)

items = ret.get("evidence_items", [])
print(f"Số lượng evidence items tìm được: {len(items)}")

doc_matched = False
matched_titles = []
for it in items:
    title = it.get("title", "")
    matched_titles.append(title)
    if TARGET_DOC.lower() in title.lower() or "2021 11 20" in title:
        doc_matched = True

print(f"Doc matched ({TARGET_DOC}): {doc_matched}")
print(f"Titles: {matched_titles[:3]}")

# Local synthesis from adapter
syn = ret.get("local_synthesis") or {}
ans_text = syn.get("answer", "")
print("\n--- CÂU TRẢ LỜI TỪ RAG LOCAL ---")
print(ans_text[:400] + "...")

# Keyword verification
kw_status = {}
for kw in MANDATORY_KEYWORDS:
    present = kw.lower() in ans_text.lower()
    kw_status[kw] = present

pass_count = sum(1 for v in kw_status.values() if v)
print(f"\nTừ khóa bắt buộc: {pass_count}/{len(MANDATORY_KEYWORDS)} passed")
for kw, ok in kw_status.items():
    print(f"  - '{kw}': {'PASS' if ok else 'FAIL'}")

assert doc_matched is True, f"Target doc {TARGET_DOC} not matched!"
assert pass_count == len(MANDATORY_KEYWORDS), f"Keywords passed {pass_count}/{len(MANDATORY_KEYWORDS)}: {kw_status}"
print(f"\n=> KẾT LUẬN TH04: doc_matched={doc_matched}, kw_count={pass_count}/5 (ĐẠT ĐIỀU KIỆN VÀ)")

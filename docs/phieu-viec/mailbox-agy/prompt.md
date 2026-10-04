# Vé: TOOL-1-FIX — Sửa mục 4 báo cáo kiểm kê cho khớp bảng

> Thợ agy (máy nhà, chế độ 4 watcher song song). Model: gemini-3.8-flash-high.
> Mailbox này: `docs/phieu-viec/mailbox-agy/`. Sửa báo cáo `docs/phieu-viec/ket-qua/tool1-kiem-ke.md`
> (KHÔNG tạo file mới), commit + push lên `phieu-viec/rag-fix1`.

## Bối cảnh
- Vé TOOL-1 đã xong, verdict: **ĐẠT phần bảng kiểm kê** (267 module, nhất quán, spot-check đúng).
- Mục 4 "Phân tích các module chưa nối & Kiến nghị lộ trình" **không khớp bảng**:
  - Liệt kê 7 module mà bảng ghi ĐÃ nối: `mom_benchmark`, `rag_benchmark`, `rag_rerank`,
    `index_domain`, `visual_knowledge_map`, `chat_action_visual_maps`, `evidence_graph_viewer`.
  - Dùng tên sai (thêm hậu tố `.py` không có trong bảng): `cli.py`, `audit.py`, `case_audit.py`,
    `phase_gate.py`, `gemini_web_engine.py` → sửa thành tên đúng trong bảng.
  - Bỏ sót nhiều module bảng ghi CHƯA nối (vd: `digest_qa`, `knowledge_digest`,
    `golden_question_export`, `golden_question_quality`, `production_prediction.reporting`,
    `production_prediction.rt_consumer`, `production_prediction.rt_replay`, `visual_map_models`,
    `extraction`, `memory`, `study_store`, `audit`, `case_audit`, `case_prompt`, `claim_guard`,
    `cli`, `discovery`, `evidence`, `export_pack`, `gemini_web_engine`, `handover`, `ide_bridge`,
    `models`, `notebook_bridge`, `notebook_case_actions`, `notebook_qa`, `owner_workflow_state`,
    `paths`, `phase_gate`, `profiles`, `provider_safety`, `route_log_ui`,
    `router_synth_redaction`, `storage`, `workflow`).

## Việc cần làm
1. Viết script nhỏ đối chiếu: với mỗi module trong mục 4, kiểm tra cột "đã nối" trong bảng —
   chỉ giữ module bảng ghi CHƯA nối.
2. Bổ sung đầy đủ các module bảng ghi CHƯA nối còn thiếu vào đúng nhóm (Benchmark / RAG v2
   chuyên sâu / Visual / Khác).
3. Sửa tên sai (bỏ `.py`), đếm lại tổng số module chưa nối (bảng: 60), cập nhật câu mở đầu mục 4.
4. Chạy lại script đối chiếu sau khi sửa: mục 4 phải khớp 100% với bảng.

## Cấm
- Chỉ sửa file báo cáo. Không sửa code.
- Không đụng ổ D.

## Tiêu chí ĐẠT
- Mọi module trong mục 4 đều có trong bảng và bảng ghi CHƯA nối.
- Mọi module bảng ghi CHƯA nối đều có mặt trong mục 4 (đúng nhóm).
- Số lượng mục 4 = 60 = số module chưa nối trong bảng.

## Báo cáo
Cập nhật cùng file `docs/phieu-viec/ket-qua/tool1-kiem-ke.md` (ghi thêm dòng "Sửa mục 4 ngày ...:
đồng bộ với bảng, kiểm tra bằng script"). Commit lên `phieu-viec/rag-fix1`,
`docs/phieu-viec/mailbox-agy/trang-thai.md` → `xong-cho-duyet`.

## Quy ước watcher (bắt buộc)
- Nhận vé: đặt `trang-thai.md` thành `dang-lam` NGAY LẬP TỨC (commit + push), kèm `ghi_chu` có timestamp giờ máy.
- Trước mỗi push: `git pull --rebase origin phieu-viec/rag-fix1` trước. Không force-push.

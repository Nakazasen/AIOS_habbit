# Ticket XẾP HÀNG: TOOL-5 — Nối visual maps vào chat

## Bối cảnh
Theo khung TOOL-2. Nối `visual_knowledge_map`, `knowledge_map_html`,
`evidence_graph_viewer`, `worklens_semantic_map` vào chat.

## Việc cần làm
1. Đăng ký visual maps làm chat action.
2. User hỏi "vẽ bản đồ tri thức về X" → render map ngay trong câu trả lời.
3. Test đầy đủ.

## Cấm
- Không ghi index production. Chỉ code + test.
- Không merge `main`. Không đụng ổ D.

## Báo cáo
`docs/phieu-viec/ket-qua/tool5-visual-chat.md`. Commit lên `phieu-viec/rag-fix1`,
`trang-thai.md` → `xong-cho-duyet`.

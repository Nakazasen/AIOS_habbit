# Ticket XẾP HÀNG: TOOL-4 — Nối interview + prediction vào chat

## Bối cảnh
Theo khung TOOL-2. Nối `expert_interview*`, `production_prediction`,
`prediction_shadow_ui` vào chat.

## Việc cần làm
1. Đăng ký interview và prediction làm chat action.
2. User hỏi "phỏng vấn chuyên gia về X" → chạy interview flow trong chat.
3. User hỏi "dự đoán X" → chạy prediction → hiện kết quả trong câu trả lời.
4. Test đầy đủ.

## Cấm
- Không ghi index production. Chỉ code + test.
- Không merge `main`. Không đụng ổ D.

## Báo cáo
`docs/phieu-viec/ket-qua/tool4-interview-prediction-chat.md`. Commit lên
`phieu-viec/rag-fix1`, `trang-thai.md` → `xong-cho-duyet`.

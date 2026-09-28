# Vé P1.4 — B1–B5 smoke test kho production (tuyến nội bộ)

Ngày viết: 2026-09-28 (Muse VM). Quyết định tuyến do user (chủ dữ liệu) ủy quyền cho Muse chốt lúc 20:55 +07.
Nhánh: `phieu-viec/rag-fix1`. Máy: `h410asrock` (Win 10 Pro). Không đụng `main`. Không force-push.

## Bối cảnh (review P1.3)
- P1.3 sao lưu + chép kho: **ĐẠT**. Backup production cũ D→C (32.452.608 byte, SHA `eedf4bf2…`, quick_check ok). Canary → production D (2.552.659.968 byte, SHA `062ec090…` khớp nguồn, quick_check ok, không lỗi I/O). App mở được, manifest phân giải đúng production.
- P1.3 **CHƯA ĐẠT** nghiệm thu vì B1–B5 chưa chạy. OMP dừng đúng (báo cáo `docs/phieu-viec/ket-qua/VE_P1_3_dong-dau-kho-that.md` mục 4+6).
- Vé này giải quyết 2 blocker còn lại. **ĐẠT vé này = P1.3 đóng.**

## Quyết định tuyến: NỘI BỘ (user chốt 1 trong 2, Muse chọn)
- **Cấm gọi AI ngoài.** Lý do: `00_governance/DATA_POLICY.md` dòng 39 — nhãn `local_only` "tuyệt đối không được gửi tới provider". Kho `tri_thuc` là tài liệu công ty (MOM/LSU/Điều-tra-lỗi), nhãn local_only. Không có ngoại lệ cho smoke test.
- User (chủ dữ liệu) **cho phép rõ ràng tuyến nội bộ** cho B1–B5 — giải quyết blocker "cần user chọn rõ nhà cung cấp".

## 1. Tuyến synthesis (chỉ nội bộ)
- Được dùng: `openai_compatible_local` (qua `AIOS_LOCAL_AI_ENDPOINT`/`AIOS_LOCAL_AI_MODEL`), Ollama local, hoặc deterministic fallback (chỉ dựng câu trả lời từ bằng chứng, không gọi AI).
- Cấm tuyệt đối: cầu nối Gemini Web, Nakazasen Router, Groq, mọi provider cloud.
- Trước khi chạy B1–B5: liệt kê provider thực tế sẽ dùng, xác nhận không có cloud. Ghi vào báo cáo.

## 2. Không ghi lên D
- Production `runtime_root` đang trên D (ổ đã cảnh báo hỏng vật lý). Vé này **cấm mọi ghi lên D**.
- Chạy B1–B5 với file index mở ở chế độ chỉ đọc (`mode=ro`), hoặc copy production sang C rồi chạy trên bản copy.
- Ledger/scheduler (`workspace_chat.sqlite`): không được khởi tạo/cập nhật trên D. Nếu scheduler đòi ghi, chuyển ledger sang C hoặc vô hiệu scheduler cho lượt test. Ghi rõ cách đã làm vào báo cáo.

## 3. Chạy B1–B5
- Câu hỏi: `docs/phieu-viec/ket-qua/FIX3_dieu-tra-B-sai.md`.
- B4 **loại khỏi chấm điểm** (ground truth không có trong corpus — không bịa đáp án).
- Ghi nguyên văn kết quả từng câu + thời gian chạy + provider/backend thực tế.

## 4. Tiêu chí ĐẠT
- B1/B2/B3/B5 chạy xong, không lỗi, không timeout.
- Câu trả lời có căn cứ từ bằng chứng truy xuất (không bịa).
- Không có byte nào ghi lên D trong suốt lượt chạy (kiểm chứng được).
- Không có dữ liệu nào rời khỏi máy.

## 5. Báo cáo
- Viết `docs/phieu-viec/ket-qua/VE_P1_4_smoke-test-noi-bo.md`: provider đã dùng, cách chống ghi D, kết quả B1–B5 nguyên văn + latency.
- Cập nhật mailbox `trang-thai.md`: `xong-cho-duyet`, ghi SHA commit báo cáo.

## Cấm kỵ
- Không gọi AI ngoài dưới mọi hình thức (kể cả "thử một câu").
- Không ghi lên D (kể cả log, cache, ledger).
- Không sửa code để "cho qua". Không `--apply`, không vacuum, không embed.
- Không đụng `main`. Không force-push.

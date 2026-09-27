# Vé A — Chốt điểm dừng G1: verify integrity index + ghi điểm resume (CHỈ ĐỌC, không embed tiếp)

Ngày viết: 2026-09-27 (Muse). Branch: `phieu-viec/rag-fix1`. Không đụng `main`.

## Bối cảnh

- User đã DỪNG mẻ embed CPU của G1 (thợ nghỉ, tiến trình về 0). File index còn nguyên ~1,7GB.
- G1 trước đó: nạp văn bản xong 433/433 nguồn (422 mới, 3 trùng toàn bộ, 8 trống nội dung); dry-run ONNX ghi nhận 106.267 vector mới pending; embedding đã chạy một phần rồi dừng giữa chừng.
- Chế độ tự lái toàn phần (user 2026-09-26, siết 2026-09-27): tự quyết mọi quyết định kỹ thuật, KHÔNG hỏi; sai thì revert commit và viết ticket sửa. Gate cứng: không code thật thì không vé mới.

## Việc cần làm (vé này CHỈ ĐỌC index, KHÔNG embed/resume)

1. Chạy `integrity_check` lên file index hiện tại → ghi kết quả `ok`/`fail` + chi tiết nếu fail.
2. Chốt điểm resume chính xác: đếm chunk đã có vector ONNX (fingerprint `016c5255…`), chunk còn pending, chunk còn vector PyTorch cũ (`ce7fb53f…`); ghi rõ resume bắt đầu từ document/chunk/batch nào (mã cụ thể, không ước lượng).
3. Ghi: kích thước file index trước/sau (vé này chỉ đọc nên phải bằng nhau), số doc/chunk/retrievable/pending theo từng fingerprint, hostname, SHA code lúc chạy.

## Điều cấm

- KHÔNG merge vào `main`. KHÔNG embed/resume trong vé này (resume để sau vé B).
- KHÔNG sửa code E-chain/backend trong vé này (nếu thiếu tool kiểm tra chỉ-đọc thì được viết script mới, nhưng script đó cũng chỉ đọc).

## Nghiệm thu

- Số liệu từ lần chạy thật, không ước lượng: integrity ok/fail, đã embed bao nhiêu / pending bao nhiêu theo fingerprint, điểm resume chính xác đến batch.
- Mọi con số trong báo cáo phải kèm cách đếm (lệnh/script đã chạy).

## Bàn giao

- Báo cáo: `docs/phieu-viec/ket-qua/G1_checkpoint_diem-dung.md`
- Commit **riêng** + push `phieu-viec/rag-fix1`, không đụng `main`.
- Định dạng số liệu chuẩn (áp dụng mọi vé từ nay): mã commit, hệ điều hành + Python, số đỗ/trượt hoặc số đếm độc lập.

---

# Vé B — Đường GPU: khảo sát onnxruntime-gpu + CUDA cho GTX 1060 3GB (làm SAU khi vé A xong)

Ngày viết: 2026-09-27 (Muse). Branch: `phieu-viec/rag-fix1`. Không đụng `main`.

## Bối cảnh

- Máy nhà: GTX 1060 3GB. Embed CPU quá chậm; máy hiện rảnh (mẻ CPU đã dừng theo lệnh user).
- Mục tiêu: nếu GPU chạy được và fingerprint khớp CPU thì resume phần pending bằng GPU cho nhanh; không được thì báo để chạy CPU tiếp.

## Việc cần làm

1. **Khảo sát môi trường**: driver NVIDIA + CUDA toolkit hiện có (ghi phiên bản), cài `onnxruntime-gpu` đúng bản tương thích (ghi phiên bản), kiểm tra `CUDAExecutionProvider` khả dụng trong onnxruntime.
2. **Mẻ thử 20 chunk** (chỉ chạy lúc máy rảnh, không tranh CPU với việc khác): embed 20 chunk bằng GPU, đo và so với CPU:
   - thời gian/chunk GPU vs CPU (CPU: lấy từ log G1 hoặc đo lại đúng 20 chunk đó bằng CPU),
   - fingerprint vector GPU — PHẢI bằng `016c5255…` (cùng model fp32; lệch là CHƯA ĐẠT),
   - cosine similarity vector GPU vs vector CPU của cùng chunk (kỳ vọng ~1.0),
   - VRAM dùng đỉnh (model ~2,2GB trên 3GB VRAM là chật; thử batch nhỏ dần, ghi batch size tối đa chạy ổn định; OOM thì báo rõ).
3. **Quyết định theo bằng chứng**:
   - ĐẠT (fingerprint khớp + nhanh hơn CPU rõ rệt + không OOM ở batch size thực tế): backup MỚI (file sibling, `integrity_check=ok`, fail-closed nếu backup lỗi) → resume phần pending bằng GPU theo batch có resume, bắt đầu đúng điểm vé A đã chốt.
   - CHƯA ĐẠT (OOM không khắc phục được / fingerprint lệch / không nhanh hơn): DỪNG, báo rõ lý do để chạy CPU tiếp — không cố đấm ăn xôi.

## Điều cấm

- KHÔNG merge vào `main`. KHÔNG resume khi chưa có backup mới integrity ok.
- KHÔNG đổi default backend, KHÔNG đụng code E-chain/extractor (vé này chỉ dùng model ONNX fp32 đã có).
- Mọi apply đều dry-run trước + backup mới + batch/resume; thiếu một trong ba thì DỪNG.

## Nghiệm thu

- Bảng số từ lần chạy thật: phiên bản driver/CUDA/onnxruntime-gpu, 20 chunk (giây/chunk GPU vs CPU), fingerprint GPU, cosine GPU-CPU, VRAM đỉnh, batch size tối đa.
- Nếu đã resume bằng GPU: số liệu trước/sau (pending về bao nhiêu), integrity trước/sau, thời gian thực tế.
- Verdict rõ ràng một dòng: ĐẠT → đã resume bằng GPU, hay CHƯA ĐẠT → lý do + đề xuất chạy CPU.

## Bàn giao

- Báo cáo: `docs/phieu-viec/ket-qua/G1_duong-GPU.md`
- Commit **riêng** + push `phieu-viec/rag-fix1`, không đụng `main`.
- Khi cả vé A và vé B xong: cập nhật `trang-thai.md` → `xong-cho-duyet` (ghi cả 2 commit SHA + 2 đường dẫn báo cáo).
- Định dạng số liệu chuẩn: mã commit, hệ điều hành + Python, số đỗ/trượt hoặc số đếm độc lập.

# FIX 2 Bước C — worker ONNX hết timeout + B1–B5/H3 so với PyTorch

Ngày: 2026-09-26. Hostname: `h410asrock`. Branch: `phieu-viec/rag-fix1`.
Ticket: `docs/phieu-viec/mailbox/prompt.md` (Bước C only). Không đụng `main`.
Bước C không ghi index — chỉ đọc + query (config read-only).

## Kết luận trước

- **Timeout đã hết**: worker `BGE_BACKEND=onnx` init **3,94 s** (<< 300 s),
  nhanh hơn ~25× so với init PyTorch 97,18 s ở baseline `484ac76`.
  Fingerprint backend `016c5255…` (`onnxruntime-int8` 1.28.0), pending 0.
- B1–B5 + H3 trên worker ONNX: cùng mode/path với PyTorch
  (`local_extractive_provider_fallback` / `hybrid`), không abstain, nhanh hơn
  PyTorch ở cả 6 câu (B1 nhanh hơn ~39×: 2,63 s so với 101,61 s).
- Đáp án B1–B5 vẫn **sai toàn bộ** so với đáp án tham chiếu — đúng như dự kiến
  từ điều tra `b90a94a` (chunk đáp án không có trong index đã migrate, nên đổi
  backend không thể sinh ra đáp án). So ONNX-vs-PyTorch: B2/B4/B5 **giống hệt**,
  B1/B3/H3 khác ở chọn chunk (cùng mode, cùng limitations).
- Không xóa/sửa vector PyTorch cũ; index sau chạy vẫn dense 340/340 hai
  fingerprint, `integrity_check ok`.

## C1. Init worker ONNX

- Index:
  `local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite`
  (12.652.544 byte lúc chạy — đã migrate Bước B).
- Dry-run trước chạy: pending **0**, already_onnx 340 (không re-embed).
- Config như nghiệm thu `484ac76` (read-only, `ensure_embeddings_on_open=False`,
  profile `bge_m3_hybrid`, model BGE-M3 pinned, 25 specs `cloud_safe` đã index),
  khác duy nhất `BGE_BACKEND=onnx` + `bge_backend="onnx_int8"` trong config
  (tên nội bộ legacy của backend fp32).
- Init: **3,94 s**, `bge_backend: onnx_int8`, model fingerprint `016c5255…`,
  không timeout, không retry. So sánh: PyTorch baseline `484ac76` init
  97,18 s; lần timeout trước Bước B là `bge_worker_init_timeout` sau 300 s.
- Tuyệt đối không xóa/sửa vector PyTorch cũ: sau chạy, dense ONNX × 340 +
  dense PyTorch × 340, `integrity_check ok`.

## C2. B1–B5 (+H3), ONNX vs PyTorch `484ac76`

Cả hai flag summary-first + provenance bật như baseline. Timeout query 180 s;
không câu nào timeout/error.

| Câu | ONNX s | PyTorch s (`484ac76`) | Mode/path | Abstain | Đáp án ONNX vs PyTorch | Đáp án tham chiếu |
| --- | ---: | ---: | --- | --- | --- | --- |
| B1 | 2,63 | 101,61 | extractive_fallback / hybrid | không | **khác** (đổi chunk [2]–[5], cùng limitations) | sai cả hai (không có 11922/12860/12626) |
| B2 | 0,77 | 2,25 | extractive_fallback / hybrid | không | **giống hệt** | sai cả hai (không có YY2-Z151/Z152.exe) |
| B3 | 0,84 | 3,64 | extractive_fallback / hybrid | không | **khác 1 chunk** (đổi 1 slide `①進度管理…` sang slide `MOM (Opceter)…`; cả hai đều lẫn XML `xmlns`) | sai cả hai (không có nvarchar(4000)) |
| B4 | 0,86 | 2,19 | extractive_fallback / hybrid | không | **giống hệt** | sai cả hai (không có Y302YL93020100) |
| B5 | 0,61 | 1,81 | extractive_fallback / hybrid | không | **giống hệt** | sai cả hai (không có HOUSE_METHOD '0'/'1') |
| H3 | 0,36 | 1,18 | extractive_fallback / hybrid | không | **khác** (đổi chunk [2]–[4], thêm [12]; cùng limitations) | held-out, có trả lời cả hai |

- B2/B4/B5 giống hệt từng byte (cùng độ dài). B1/B3/H3 khác ở ranking chọn
  chunk trong cùng corpus — phù hợp cosine ONNX–PyTorch ≈ 1.0 nhưng thứ tự
  top-k có thể xê dịch ở biên (recall proxy vòng 3 là top-10 agreement trên
  corpus khác, không bảo đảm cùng chunk từng câu).
- Không so on/off flag theo ticket — chỉ so backend onnx vs pytorch.

## Files và bàn giao

- Raw JSONL: `C:/Users/Admin/AppData/Local/Temp/fix2_stepC_onnx.jsonl`
  (máy `h410asrock`, không commit). Runner `scratch/fix2_onnx_verify_C.py`
  (git-ignore, đã dùng xong).
- File báo cáo này: `docs/phieu-viec/ket-qua/FIX2_onnx-worker-verify.md`.
  Commit riêng + push `phieu-viec/rag-fix1`, không merge `main`.
  Cập nhật `trang-thai.md` → `xong-cho-duyet`. DỪNG chờ ticket tiếp theo
  (quyết định default backend ngoài phạm vi Bước C).

# Vé: SPEED-COLDSTART-HOME-R1 — chạy lại câu E3 qua lane 1 (bù tiêu chí 6/6)

Lane: [NHÀ] OMP đo trên máy nhà. Không merge `main`; code tương thích Python 3.11; không force-push; không ghi index.

## Bối cảnh

- Vé `SPEED-COLDSTART-HOME` verdict **CHƯA ĐẠT toàn vé** (2/3 tiêu chí, báo cáo `docs/phieu-viec/ket-qua/speed-coldstart-home.md`, SHA `b88938e274`):
  - ✅ 3/3 lần restart gắn lại worker cũ (PID 11896), không nạp lại model; config lệch bị chặn đúng thiết kế P3+P4.
  - ✅ Init lạnh 112,1 s; bảng thời gian 6 câu đầy đủ; parity 5 câu nhận được; SHA index production không đổi.
  - ❌ Chỉ **5/6** câu qua lane 1: câu **E3** gọi Gemini 3 lần nhưng đáp án thiếu nhãn trích dẫn `[n]` → cổng kiểm từ chối (`provider_answer_missing_citations` / `provider_answer_uncited_material_claim`) → rơi về tổng hợp cục bộ, không tính lane 1. Không nới cổng.
- Cổng trích dẫn làm đúng việc (từ chối đáp án không nhãn). Vé `LLM-ENABLE-DO-NHA-R1` trước đó đã chứng minh E3 qua được lane 1 với trace valid → nhiều khả năng probe lần này thiếu nhắc định dạng trích dẫn, không phải hệ thống hỏng.

## Việc OMP làm [NHÀ]

1. Worker BGE persist (PID 11896) vẫn sống — gắn lại qua named pipe, không nạp lại model.
2. Chạy lại **câu E3** bằng đúng đường đo cũ (`search_with_summary`, `allowed_document_ids=None`, `limit=15`, `per_document_limit=3`; `synthesize_with_provider` + cầu nối `gemini-web`; `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1` trong tiến trình đo), ghi 3 mốc retrieval/synthesis/tổng.
3. Trong probe nhắc **rõ định dạng trích dẫn `[n]`** cho mọi khẳng định vật liệu (điểm khác duy nhất so với lượt trước; không sửa mã sản phẩm, không nới cổng kiểm).
4. Tối đa 3 lần gọi như lượt trước. Nếu vẫn không qua cổng → dừng, báo rõ, đặt `cho-muse` (không tự nới cổng, không tự bịa đáp án).

## Tiêu chí ĐẠT

- E3 nhận `provider_validated` qua lane 1, trace valid → đủ **6/6** câu lạnh qua lane 1/3.
- SHA index production trước/sau không đổi.

## Báo cáo

- Bổ sung vào `docs/phieu-viec/ket-qua/speed-coldstart-home.md` (hoặc file `speed-coldstart-home-r1.md` mới) + `xong-cho-duyet`.

# Vé OPT-LEXICAL-BENCH-NHA — bench Phase B trên index thật máy nhà (chỉ đọc)

LANE: [NHÀ] OMP bench trên index thật máy nhà → Muse review. KHÔNG phải vé nghiệm thu — số chốt vẫn ở PC0575.

## Bối cảnh
- Phase B code+test đã xong trên VM (commit `1f30092`): instrumentation tách 3 phần lexical + 6 candidate tối ưu sau kill-switch `AIOS_RAGV2_LEXICAL_V2` (default 0), mỗi tối ưu có toggle riêng `AIOS_RAGV2_LEX_V2_<TÊN>` để A/B.
- Bench trên VM dùng index synthetic 20k chunk cho thấy FTS −41%, CJK −15% — cần số đo trên index thật (149.800 chunk) trước khi verify PC0575. Máy nhà đang chờ lane [NGƯỜI DÙNG] của J3 nên chạy vé này song song, không đụng J3/JIG.

## Việc cần làm
1. `git pull` tip `phieu-viec/rag-fix1` (≥ `1f30092`).
2. Chạy 6 câu L1–L3/E1–E3 (nguyên văn như vé `hodap-home`) qua đúng stack truy xuất của app, **chỉ đọc index**, 2 cấu hình:
   - A: `AIOS_RAGV2_LEXICAL_V2=0` — đường cũ; lấy split 3 phần lexical từ instrumentation (eligibility/temp build, FTS MATCH+bm25+JOIN, vòng Python scoring) + thời gian lexical từng câu.
   - B: `AIOS_RAGV2_LEXICAL_V2=1` — bật các tối ưu theo default của code.
3. So top-15 từng câu giữa A và B: % khớp id + thứ tự; ghi rõ mọi lệch, đặc biệt câu chữ Nhật/Hàn (E1).
4. Nếu còn thời gian: A/B riêng từng toggle đáng ngờ (`SKIP_FULL_ELIGIBLE`, `NARROW_ELIGIBILITY`, `SCORE_CACHE`...). Riêng `CJK_TRIGRAM`: chỉ chạy khi bảng `chunks_fts_trigram` đã có sẵn — KHÔNG tự build bảng trên index thật (ghi index bị cấm ở vé này); thiếu bảng thì bỏ qua và ghi rõ.

## Ràng buộc cứng
- Chỉ đọc index: ghi SHA + dung lượng kho trước và sau, không được đổi một byte.
- Kill-switch mặc định vẫn 0 — không đổi hành vi app đang chạy; không restart app.
- Không đụng `main`, không ghi ổ D, không đụng gói dùng thử J3 / tool JIG.
- Xong bench, mailbox về `xong-cho-duyet` — Muse review xong sẽ phát hành lại vé J3 (đang giữ nguyên chờ lane [NGƯỜI DÙNG]).

## Báo cáo
- `docs/phieu-viec/ket-qua/opt-lexical-bench-nha.md`: bảng thời gian lexical/câu (A vs B) + split 3 phần + parity top-15 từng câu + SHA kho trước/sau + kết luận toggle nào nên bật khi verify PC0575.

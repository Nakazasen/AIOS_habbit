# Báo cáo vé LLM-ENABLE-DO-NHA-R1 — đường AI ngoài trên máy nhà

Máy: `h410asrock`. Nhánh: `phieu-viec/rag-fix1`. Tip lúc chốt số đo: `41f791a`. Thời điểm: 2026-10-02 23:13–23:32 +07. Không đụng `main`, không force-push, **không ghi index**.

## 1. Kết luận

**Đường gọi provider ngoài: ĐẠT trên cả 6 câu** (lượt đo chấp nhận). Mỗi câu đều có `provider_used=true`, model `gemini-web`, provider hiển thị `AI trong máy tương thích OpenAI` (`openai_compatible_local`), trace `valid`, không có nhãn trích dẫn lạ.

**Router Nakazasen: KHÔNG dùng được.** Khóa cloud trong env lỗi ngay (`gemini`/`openrouter`: `unknown_error`; `groq`: `auth_error`). Vé cho phép rơi về Cầu nối Gemini Web. Cầu nối `127.0.0.1:8585` = `direct_ready`. Không in khóa.

**Chất lượng so với lane cục bộ `hodap-home`: không đồng đều, không ghi PASS chất lượng.** Đáp án Gemini ngắn, sạch, hết XML thô; nhưng thường bỏ số liệu và đôi khi nói “chưa đủ bằng chứng” trong khi lane cục bộ vẫn rút được mảnh. Chi tiết mục 6.

Lô đo đầu (nhắc định dạng yếu) chỉ E2 qua được cổng kiểm; 5 câu kia Gemini có trả lời nhưng thiếu nhãn `[n]` nên lane rơi về cục bộ. Lượt chạy lại với nhắc định dạng chặt hơn thì L1–L3, E1, E3 qua cổng. Không giấu lô đầu: bản JSON nằm ở `C:\tmp\llm-enable-do-nha\batch1\`.

## 2. Cổng gate

- Watcher tự mở lại OMP **`RELAUNCH 1/4`** lúc `2026-10-02 23:19:25` (`launchStallCount=1`, log `D:\Sandbox\Vong_lap_giao_viec\watcher.log`). Vé gốc đã escalate `cho-muse` lúc 23:04 (4/4); vé R1 là vé mới, bộ đếm về 1.
- **Điều kiện mở đã tới:** vé lane [NHÀ], cầu nối `direct_ready`, index chỉ đọc còn nguyên. Không đặt `cho-muse`, không quay no-op.
- PID 10792 trong ghi chú Muse là tiến trình VOICEVOX, không phải OMP. Không có OMP thứ hai cùng làm.

## 3. Cách chạy

- Công tắc `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1` đặt **trong tiến trình probe** trước khi dựng `RouterSynthesisProvider` và `RagV2DevPipeline` (không chỉ gõ ở shell rồi quên).
- Endpoint: `AIOS_LOCAL_AI_ENDPOINT=http://127.0.0.1:8585/v1/chat/completions`, model `gemini-web`.
- Probe ngoài Git: `C:\tmp\llm-enable-do-nha\probe.py`. Gọi đúng `synthesize_with_provider` + `RouterSynthesisProvider` (vá `1b6200b`, `f9a0dbb`). Chỉ đưa cấu hình cầu nối vào router, vì khóa cloud fail-fast làm lượt sửa lỗi bỏ qua cầu nối (`max_attempts=3`).
- Gemini Web bỏ hợp đồng tiếng Anh, viết mẫu riêng không nhãn. Probe thêm một đoạn nhắc định dạng tiếng Việt (2–3 dòng, mỗi dòng kết thúc `[n]`). Hợp đồng sản xuất vẫn gắn phía sau. Đây là ràng buộc của probe, không phải sửa code sản phẩm.
- Truy xuất giống `hodap-home`: index chỉ đọc, `limit=15`, `per_document_limit=3`, `expected_source_fingerprints={}`.
- App UI `localhost:8501` **không chạy** (connection refused). Không bật UI: hội thoại theo sổ sẽ chuẩn bị nguồn và có thể ghi index — cùng lý do vé `hodap-home` đo bằng probe.

## 4. Index chỉ đọc

| Mục | Trước (22:47, `identity.json`) | Sau 6 câu (23:31) |
| --- | --- | --- |
| Đường dẫn | `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | cùng đường |
| Dung lượng | 2.942.201.856 B | 2.942.201.856 B |
| mtime | 2026-10-01 08:27:27 | 2026-10-01 08:27:27 |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | **khớp** |

`quick_check=ok` lúc 22:47. Sau các lượt hỏi, size/mtime/SHA không đổi.

## 5. Sáu câu (lượt chấp nhận)

Thời gian đơn vị giây, trừ cột LLM (mili giây, lần gọi thành công được ghi). Init của câu đầu lượt này: **2,89 s** (worker đã nóng từ lượt trước; init lạnh trong phiên khoảng 5 s, không phải 30 s).

| Câu | Init | Tìm | Viết (LLM) | Tổng | Mode | Trace |
| --- | ---: | ---: | --- | ---: | --- | --- |
| L1 | 2,89 | 4,03 | 3308 ms | 10,26 | `provider_validated` | `trc_9bf8e732d7cf` valid, cited 1 |
| L2 | 2,47 | 4,43 | 3020 ms | 9,96 | `provider_validated` | `trc_e7dcdea6cb2b` valid, cited 2 |
| L3 | 2,41 | 4,45 | 2919 ms | 9,83 | `provider_validated` | `trc_26ff62a985d0` valid, cited 1 |
| E1 | 2,39 | 17,15 | 3280 ms | 22,84 | `provider_validated` | `trc_9413fb097c3c` valid, cited 1 |
| E2 | 5,01 | 10,04 | 3219 ms + sửa 23983 ms | 42,29 | `provider_validated_after_repair` | `trc_5b0f0770bfea` valid, cited 2 |
| E3 | 2,96 | 4,87 | 3348 ms | 11,22 | `provider_validated` | `trc_bb884560283b` valid, cited 1 |

Provider/model mọi câu: `openai_compatible_local` / `gemini-web`. `unknown_cited_ids` rỗng. Cổng kiểm sản xuất chấp nhận nhãn và literal then chốt trên dòng đã trích — không đối chiếu tay từng tên file ngoài cổng đó.

### Toàn văn đáp án lượt chấp nhận

L1 — LSU là gì và gồm những bộ phận quang học chính nào?

- Chưa đủ bằng chứng để xác định LSU là gì và các bộ phận quang học chính [1]

L2 — Hiện tượng đai đen trong hình ảnh liên quan thế nào tới đường kính BEAM?

- Với đường kính BEAM lớn, khoảng cách quá hẹp khiến ảnh bị chèn ép và xuất hiện đai đen [1]
- Trạng thái đường kính BEAM nghiêng hoặc trục quang bị nghiêng có thể gây ra lỗi hình ảnh như đai đen [2]

L3 — Đường kính BEAM bao nhiêu là đạt, và khi nào gây lỗi hình ảnh?

- Với đường kính BEAM lý tưởng là 60 µm thì khoảng cách giữa các BEAM là 60 µm và chất lượng ảnh chuẩn [2]
- `LIMITATIONS: incomplete_query_term_coverage`

E1 — Lỗi Beam径 NG trên Iris LSU là gì, nguyên nhân và hướng xử lý?

- Không có nguồn đủ mạnh để xác định lỗi Beam径 NG trên Iris LSU là gì, nguyên nhân và hướng xử lý [1]
- Chưa đủ bằng chứng để cung cấp thông tin chi tiết về lỗi Beam径 NG trên Iris LSU theo các nguồn cung cấp [1]
- `LIMITATIONS: incomplete_query_term_coverage`

E2 — Dán SIM vào LD BLOCK ASSY có tác dụng gì khi xử lý lỗi beam?

- Kẹp LD mirror bằng SIM giúp xác nhận xu hướng đường kính Beam có thay đổi hay không [4], [5].

E3 — Khi beam diameter NG thì cần kiểm tra những hạng mục nào (LD mirror, trục quang, độ sâu chỉnh)?

- Khi trục quang bị lệch thì xảy ra hiện tượng không thể điều chỉnh đường kính beam và timing [4]
- Cần điều chỉnh hướng X và hướng Y để đồng nhất với trục quang [4]
- `LIMITATIONS: incomplete_query_term_coverage`

Bản JSON đầy đủ (kể cả lô rơi local) nằm ngoài Git: `C:\tmp\llm-enable-do-nha\qa-1.json` … `qa-6.json`, lô đầu ở `batch1\`. Không dán mảnh tài liệu thô vào Git.

## 6. Đối chứng với `hodap-home` (lane cục bộ)

Lane cục bộ nối mảnh, có số và tên bộ phận, kèm nhiễu/XML. Lane Gemini sạch hơn, ngắn hơn, hay bỏ số.

| Câu | So với lane cục bộ | Chi tiết ngoài bằng chứng |
| --- | --- | --- |
| L1 | **Kém hơn về độ đủ** | Cục bộ nêu Lens CYLINDRICAL, POLYGON, Lens F, LD mirror. Gemini chỉ nói chưa đủ bằng chứng. Không bịa tên bộ phận, nhưng bỏ nội dung mảnh khác [1]. |
| L2 | **Sạch hơn, thiếu số** | Đúng quan hệ đai đen / đường kính BEAM / trục nghiêng. Không nêu 100 µm và 20 µm mà cục bộ có. Không dính XML. |
| L3 | **Sạch hơn, thiếu ngưỡng lỗi** | Có chuẩn 60 µm. Không nêu ngưỡng 100 µm làm khoảng cách còn 20 µm rồi đai đen. Có marker giới hạn vì cổng phủ từ khóa. |
| E1 | **Cùng mỏng, Gemini còn trống hơn** | Cả hai bị `incomplete_query_term_coverage`. Cục bộ còn mảnh motor polygon / PWB APC. Gemini từ chối. Không bịa nguyên nhân. |
| E2 | **Đúng câu hỏi hơn, ít quy trình hơn** | Đúng tác dụng kẹp SIM để xem xu hướng đường kính Beam. Không kể unit test 2 MOUNT trên 5 JIG mà cục bộ có. Hết mảnh lệch chủ đề. |
| E3 | **Sạch hơn, thiếu hạng mục** | Có lệch trục quang và chỉnh hướng X/Y. Không kể MOUNT LD BLOCK, FRAME, PWB APC, vết sửa MIRROR LD, số lệch µm mà cục bộ có. |

Nhắc định dạng “đúng 2 hoặc 3 dòng” của probe góp phần làm đáp án ngắn. Không kết luận Gemini kém năng lực độc lập với ràng buộc đó.

## 7. Điều kiện không đạt

1. **Router Nakazasen không gọi được** — bằng chứng lượt Phase 0 trước khi siết cầu nối: `gemini` `unknown_error` 396 ms, `openrouter` `unknown_error` 841 ms, `groq` `auth_error` 242 ms. Không dán thông báo lỗi thô có thể chứa bí mật.
2. **Lô đầu 5/6 rơi local** dù Gemini đã trả lời — lỗi gốc `provider_answer_missing_citations` + `provider_answer_uncited_material_claim`; L2/L3 thêm `provider_answer_unsupported_critical_literal` nên không được sửa lần hai. Lượt chấp nhận xử lý bằng nhắc định dạng, không tắt cổng kiểm.
3. **Chất lượng không hơn lane cục bộ trên mọi câu** — mục 6. Không ghi PASS chất lượng.
4. **App UI không được bật kèm công tắc** — đo bằng probe, cùng stack truy xuất, chỉ đọc.

## 8. Trạng thái

`trang-thai.md` → `xong-cho-duyet`. Chờ Muse đối chứng. Không merge `main`.

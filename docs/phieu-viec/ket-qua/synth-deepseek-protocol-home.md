# Báo cáo vé SYNTH-DEEPSEEK-PROTOCOL-HOME — sửa lỗi giao thức khiến đáp án DeepSeek bị chặn oan

- **Mã vé:** `SYNTH-DEEPSEEK-PROTOCOL-HOME`
- **Máy thực hiện:** Nhà `h410asrock` (thợ OMP, truy xuất CPU-only).
- **Thời điểm:** 2026-10-09 02:42 – 04:50 +07.
- **Căn cứ:** vé `SYNTH-CLAIMBUDGET-DIAG-HOME` phát hiện 34/38 câu DeepSeek "0 lượt gọi" thực ra đã gọi thành công nhưng toàn bộ nội dung dồn vào `reasoning_content`, `content` rỗng; hệ thống ghi nhầm thành lỗi mạng.
- **Kết quả một câu:** **ĐÃ sửa** — gọi lại đúng một lần với yêu cầu mạnh hơn (ngân sách ×2, trần 8192) và chỉ thị trả lời trực tiếp; nếu vẫn rỗng thì phân loại là **lỗi định dạng riêng** (`bad_response` / `provider_empty_answer`, không còn ghi "lỗi mạng") và chuyển tầng dự phòng ngay. Nguyên tắc an toàn giữ nguyên: tuyệt đối không lấy `reasoning_content` làm đáp án. Đo lại tập con 34 câu: **phục vụ 0/34 → 27/34; qua kiểm định 0/34 → 14/34; tổng điểm 45,18 → 49,18**; chi phí thật 0,195443 đô (trần vé 0,5).

---

## 1. Chẩn đoán điểm nghẽn giao thức

### 1.1. Đường gọi DeepSeek trong mã nguồn

1. Runner gọi `synthesize_with_provider(...)` — `src/aios_habit/rag_v2/synthesis.py:930`.
2. → `RouterSynthesisProvider.__call__` — `src/aios_habit/rag_v2_synthesis_provider.py:138`.
3. → `route_answer(...)` — `src/aios_habit/ai_router.py:262`.
4. → `call_openai_compatible_provider(...)` — `src/aios_habit/ai_router.py:166`.
5. → `answer_with_provider(...)` — `src/aios_habit/ai_provider_bridge.py:334`.
6. → `_post_chat(...)` — `src/aios_habit/ai_provider_bridge.py:318`.

### 1.2. Tham số yêu cầu đang được gửi (TRƯỚC khi sửa)

Payload gửi đi (hàm `_post_chat`, `ai_provider_bridge.py`, bản cũ dòng 272–280) chỉ có `model`, `messages`, `temperature: 0.1`, `max_tokens: 2048` — **không** gửi bất kỳ tham số suy luận nào. DeepSeek V4.1 Flash mặc định BẬT chế độ suy luận; ngân sách 2048 bị suy luận ăn hết trước khi sinh đáp án → `content` rỗng, `finish_reason="length"`, `reasoning_tokens=~2048`.

Bằng chứng dữ kiện thô (`rows-synth-deepseek.jsonl`): 34/38 câu "0 lượt gọi" đều có `completion_tokens=2048` (đúng trần) và tốn 0,0017–0,0029 đô mỗi câu — **token + tiền thật đã tiêu rồi đáp án bị vứt**.

### 1.3. Điểm quyết định "đáp án rỗng" rồi ghi thành lỗi mạng

1. `_post_chat` (bản cũ dòng 303–308): thấy `content` rỗng thì ném `RuntimeError("Endpoint không trả về nội dung trả lời (content rỗng).")` — **đúng chủ ý an toàn**: không bao giờ lấy `reasoning_content` làm đáp án (dòng 301–302).
2. `answer_with_provider` (bản cũ dòng 412–431) bắt mọi `RuntimeError` rồi **viết lại thông báo** thành `"Nguồn AI không phản hồi: RuntimeError."` — mất dấu hiệu "content rỗng".
3. `route_answer` (dòng 374–375) phân loại bằng `classify_provider_error` (dòng 116–125); thông báo đã viết lại không khớp mẫu nào → trả về **`unknown_error`** (nhật ký lượt đo cũ: `openai_compatible_local:failed(unknown_error)`).
4. `RouterSynthesisProvider.__call__` (dòng 177–190) thấy `used_fallback` → ném `RuntimeError("All synthesis providers failed ...")`.
5. `synthesize_with_provider` (bản cũ dòng 991–1002) bắt mọi ngoại lệ → gắn limitation **`provider_network_error`** — ghi nhầm lỗi định dạng thành lỗi mạng, đúng như vé nêu.
6. Vì ngoại lệ bắn ra TRƯỚC khi lớp ghi nhớ trả kết quả, runner đếm `so_lan_goi_provider=0` — trông như "chưa gọi model" dù đã gọi và trả tiền.

### 1.4. Các tham số "tắt/giới hạn suy luận" đều VÔ HIỆU qua cổng hiện tại

Gọi thật (cùng một prompt lớn) ba biến thể: `"thinking": {"type": "disabled"}` (DeepSeek native), `"reasoning_effort": "low"`, `"reasoning": {"effort": "none"}` (kiểu OpenRouter) — **cả ba đều vô hiệu**: vẫn suy luận 2048 token, `content` rỗng, `finish=length`. Kết luận: phải đi hướng "yêu cầu trả lời trực tiếp mạnh hơn + đủ ngân sách", đúng như vé chỉ ra.

### 1.5. Bằng chứng ngân sách là nút thắt (đo thật, cùng prompt Q0699)

| Thử nghiệm | content | finish | reasoning_tokens | chi phí |
|---|---|---|---|---|
| `max_tokens=2048` (hiện trạng) | **rỗng** | length | 1955 | ~0,0017 đô (vứt đi) |
| `max_tokens=4096` | **2039 ký tự** | stop | 2002 | ~0,0022 đô |
| `max_tokens=8192` | 1493 ký tự | stop | 7545 | ~0,0054 đô |

→ Suy luận của DeepSeek dài biến thiên mạnh (1.400–7.500 token); ngân sách 2048 là nguyên nhân trực tiếp.

---

## 2. Hướng sửa đã chọn và lý do

Ưu tiên 1 của vé (tắt/giới hạn suy luận bằng tham số chính thức) **không khả thi qua cổng hiện tại** (Mục 1.4). Chọn ưu tiên 2 của vé, giữ nguyên tắc an toàn:

1. **Gọi lại đúng một lần** khi lần đầu rỗng-vì-suy-luận (`reasoning_content` có nội dung hoặc `finish_reason=length`):
   - ngân sách ×2 (trần `EMPTY_ANSWER_RETRY_TOKEN_CEILING = 8192`);
   - thêm chỉ thị hệ thống: "Trả lời TRỰC TIẾP trong nội dung chính; giữ phần suy luận nội bộ thật ngắn; tuyệt đối không để nội dung trả lời rỗng."
2. **Vẫn rỗng** → ném lỗi định dạng riêng `ProviderEmptyAnswerError`:
   - `answer_with_provider` trả `safety_status="fallback_provider_empty_answer"`, thông báo mang mốc máy đọc `(empty answer)`;
   - `classify_provider_error` nhận diện → **`bad_response`** (khóa tạm riêng model, tự động chuyển nguồn khác trong cùng lượt);
   - `synthesize_with_provider` ghi limitation **`provider_empty_answer`** thay vì `provider_network_error`.
3. **Cấm tuyệt đối lấy suy luận làm đáp án giữ nguyên** — không đụng lớp lọc an toàn; `reasoning_content` chỉ là *dấu hiệu* để quyết định thử lại, không bao giờ được trả ra (test khẳng định chuỗi suy luận không lọt vào đáp án).

### 2.1. Vì sao không đặt sau cờ tính năng

Đây là sửa hành vi lỗi (đổi phân loại sai + một lần thử lại có trần) theo tiền lệ đang có trong mã nguồn: vòng "sửa đáp án" của lớp tổng hợp (`synthesis.py:1029–1042`) và vòng "tự thay model" của lớp điều phối (`ai_router.py:393–394`) đều là các lần thử lại không đặt sau cờ. Vé không yêu cầu cờ cho hạng mục này. Nếu điều phối muốn bọc cờ, đây là điểm dễ tách thành vé phụ.

### 2.2. Điểm sửa cụ thể

| Tệp | Thay đổi |
|---|---|
| `src/aios_habit/ai_provider_bridge.py` | Tách `_post_chat_once`/`_first_choice`; thêm lần thử lại có trần + chỉ thị trực tiếp; thêm `ProviderEmptyAnswerError`; `answer_with_provider` trả đúng mã định dạng |
| `src/aios_habit/rag_v2_synthesis_provider.py` | Thông báo lỗi cuối mang theo mã lỗi nhà cung cấp (`error_types=…`) |
| `src/aios_habit/rag_v2/synthesis.py` | Phân biệt `provider_empty_answer` (định dạng) với `provider_network_error` (mạng) |
| `tests/test_ai_provider_bridge.py` | 2 test mới: thử lại 1 lần với yêu cầu mạnh hơn; vẫn rỗng → mã định dạng riêng, không trả suy luận |
| `tests/test_ai_router.py` | 1 test mới: thông báo từ bridge phân loại `bad_response` + chuyển nguồn ngay |
| `tests/test_rag_v2_synthesis.py` | 1 test mới: limitation `provider_empty_answer`, không phải mạng |
| `tests/test_rag_v2_synthesis_provider.py` | 1 test mới: mã lỗi nhà cung cấp ra tới lớp tổng hợp |

Commit code + test: **`d098073`** (chỉ 7 tệp trên, không đụng tệp khác).

---

## 3. Kiểm chứng cổng

- 4 tệp test liên quan (`test_ai_provider_bridge.py`, `test_ai_router.py`, `test_rag_v2_synthesis.py`, `test_rag_v2_synthesis_provider.py`): **123/123 PASS** (gồm 5 test mới).
- 6 tệp vùng lân cận (`test_antigravity_bridge`, `test_strong_answer_ui`, `test_workspace_chat_router_adapter`, `test_provider_model_discovery`, `test_route_log_ui`, `test_provider_health`): **122/122 PASS**.
- `uv run --no-sync --group dev python -m compileall src tests`: sạch.
- `uv run --no-sync --group dev python -m aios_habit.cli audit`: `"status": "PASS"`.
- `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"`: OK.
- Full suite `pytest -q tests/`: **10 failed / 4205 passed / 46 skipped / 19 errors** (27 phút 8 giây). Phân loại đầy đủ ở Mục 6.

## 4. Smoke thật tại đúng câu từng lỗi (Q0699)

Chạy đúng đường tổng hợp thật (pipeline RAG v2 chỉ đọc + `RouterSynthesisProvider` cố định DeepSeek), câu Q0699:

| Lượt gọi | ngân sách | content | finish | reasoning_tokens |
|---|---|---|---|---|
| 1 (lần đầu) | 2048 | **0 ký tự** | length | 2048 |
| 2 (**thử lại có chỉ thị mạnh**) | 4096 | **844 ký tự** | stop | 3211 |

- Provider **đã phục vụ đáp án thật** (844 ký tự) — trước đây câu này chưa từng có đáp án nhà cung cấp.
- Đáp án vẫn **trượt kiểm định trích dẫn** → rớt về trích cục bộ; đây là **nút thắt thứ hai đã biết** (kỷ luật trích dẫn), ngoài phạm vi vé.
- Hai lượt gọi sau trong bản ghi là lượt "sửa đáp án" của lớp tổng hợp (cùng bị rỗng, được phân loại đúng `bad_response`).
- Chi phí lượt smoke: 0,009635 đô; băm chỉ mục trước/sau khớp.

## 5. Đo kiểm chứng trên tập con 34 câu

**Cách chọn tập con:** đúng các câu từng dính lỗi đáp án rỗng của lượt đo DeepSeek cũ — `rows-synth-deepseek.jsonl`, điều kiện `so_lan_goi_provider=0` và `che_do=local_extractive_provider_fallback` → **đúng 34 câu** (4 câu `not_called` do cổng độ phủ bằng chứng, không phải lỗi giao thức, bị loại đúng theo định nghĩa).

**Runner:** `C:/tmp/lsu-quality-rag-home/do_rag_subset_deepseek_protocol.py` — bản sao cùng cấu trúc của runner hiện hành `do_rag_50_synth_deepseek.py` (cùng pipeline, cùng cách gọi `synthesize_with_provider`, cùng rubric chấm), chỉ lọc đúng 34 câu; DeepSeek cố định `deepseek/deepseek-v4.1-flash`; CPU-only; index chỉ đọc; reset bộ nhớ trạng thái từng câu; trần chi phí cứng 0,5 đô; checkpoint từng câu.

### 5.1. Bảng trước/sau

| Chỉ số | TRƯỚC (lượt đo cũ) | SAU (lượt đo này) |
|---|---|---|
| Câu có đáp án nhà cung cấp được phục vụ | **0/34 (0%)** | **27/34 (79,4%)** |
| Câu qua kiểm định (validated) | **0/34 (0%)** | **14/34 (41,2%)** (8 trực tiếp + 6 sau sửa) |
| Câu rớt về trích cục bộ (fallback) | 34/34 | 20/34 |
| Tổng điểm (thang 34×3,0 = 102) | 45,18 | **49,18** |
| GPA | 1,33 | **1,45** |
| Câu đạt 3,0 điểm | 4 | 5 (Q0689, Q0695, Q1798, Q0674, Q0680) |
| Câu đạt ≥ 2,0 điểm | 4 | 7 |
| Lỗi kỹ thuật | 0 | 0 |
| Limitation `provider_network_error` | 34 (ghi nhầm) | **0** |
| Limitation `provider_empty_answer` (định dạng) | 0 (chưa có mã riêng) | 7 (đúng 7 câu vẫn rỗng cả 2 lượt) |
| Chi phí | 0,060488 đô (vứt đi 0 lượt phục vụ) | **0,195443 đô** (min 0,001285 / max 0,009554 / TB 0,005748) |

**Điểm từng câu:** 3 câu tăng điểm (Q1798: 1,0→3,0; Q0706: 1,0→2,0; Q0787: 1,0→2,0), 31 câu giữ nguyên, **0 câu giảm**.

### 5.2. Phân loại 7 câu còn rỗng

Q0703, Q0850, Q0685, Q0677, Q0633, Q0684, Q0924 — rỗng ở CẢ HAI lượt (kể cả lượt thử lại) → hệ thống phân loại `bad_response` + limitation `provider_empty_answer` (định dạng) và **chuyển tầng dự phòng ngay**, không còn ghi "lỗi mạng". Đây là biến thiên độ dài suy luận của model (có câu suy luận vượt cả 8192 token), không phải lỗi hệ thống; 0 lỗi kỹ thuật trên toàn lượt đo.

### 5.3. Tệp bằng chứng (kích thước lấy bằng lệnh liệt kê tệp thật)

| Tệp | Kích thước |
|---|---|
| `docs/phieu-viec/ket-qua/rows-synth-deepseek-protocol.jsonl` | 101.439 byte (34 dòng) |
| `docs/phieu-viec/ket-qua/ket-qua-synth-deepseek-protocol.json` | 837 byte |

Độ trễ lượt đo (lưu ý: chạy song song với lượt đo của thợ `agy` trên cùng máy nên số giây bị đội): tổng hợp trung bình 48,75s / trung vị 47,86s / cao nhất 91,5s mỗi câu; toàn câu trung bình 54,72s.

## 6. Rào cứng đã giữ

- **Không đổi model chính và thứ tự chuỗi dự phòng:** không sửa `.env`, không sửa cấu hình máy; runner dựng cấu hình tuyến cố định DeepSeek **trong bộ nhớ** đúng như runner cũ (không có cấu hình tạm nào cần khôi phục).
- **Không ghi chỉ mục:** `library.sqlite` mở chỉ đọc; SHA-256 trước/sau trùng khớp tuyệt đối `45eb0e07…b7c0`, 2.942.201.856 byte (`index_chi_doc_khop: true` trong tệp tổng).
- **Không merge `main`:** toàn bộ commit nằm trên nhánh `phieu-viec/rag-fix1`.
- **Không in ký tự nào của khóa truy cập:** script chỉ in endpoint; không có log nào in khóa.
- **Không đụng lớp lọc an toàn:** cấm lấy `reasoning_content` giữ nguyên; chỉ thêm *dấu hiệu* để quyết định thử lại và mã lỗi riêng.
- **Full suite (27 phút 8 giây):** 10 failed / 4205 passed / 46 skipped / 19 errors — chạy riêng tái hiện đủ cả 29 ca đỏ, **toàn bộ ngoài phạm vi vé**:
  - **19 error môi trường (100% thiếu tệp nguồn của máy khác, đường `\home\hatch\workspace\...`):** 10 × `test_error_cases_f4` (thiếu `02XC_自己診断表示一覧表-Iris2020 VN.xls`), 9 × `test_chat_action_error_lookup` (thiếu `Loi KDTPS.xlsx`).
  - **10 failed, nguyên nhân từng ca:** (a) 3 ca `test_workspace_chat_source_selection_owner_flow` (×2) + `test_large_library_nonblocking_chat` là **bảo vệ chuỗi mã nguồn đã cũ** — đòi chuỗi `query_relevant_sources = ready_sources or ready_in_scope` không còn tồn tại trong `workspace_chat_app.py` (dòng đó bị thay bởi commit `afd7fc6` của vé UI-ANSWER-QUALITY2-HOME, kiểm bằng `git log -S`, không phải vé này); (b) 2 ca `test_rag_v2_opt_pyloops` (preload/prefilter) lệch hành vi truy xuất sau các commit `8a3beb5`/`ce6212c`/`abce118` của vé khác — không đụng gì trong vé này; (c) 5 ca môi trường: antigravity privacy guard (lỗi DNS `getaddrinfo`), notebook QA (không có LLM cục bộ — `WinError 10061`), production index filtering (kho máy 496/889 — ca quen thuộc ngoài vé), `test_bge_subprocess_worker` (`bge_worker_query_timeout` khi máy đang chạy song song), test fixture `yield_rate_check` (logic fixture tự chứa).
  - Không ca nào chạm các tệp vé sửa (`ai_provider_bridge.py`, `rag_v2_synthesis_provider.py`, `rag_v2/synthesis.py` và 4 tệp test của vé) — 245/245 test vùng vé + lân cận chạy riêng đều xanh.
  - Số passed tăng so nền cũ (4195 → 4205) gồm 5 test mới của vé này và các test mới của vé khác trên cùng nhánh.

## 7. Rủi ro tồn dư / ghi nhận

1. **Thời gian chờ nhà cung cấp khi lên go-live:** app lấy thời gian chờ từ `AIOS_LOCAL_AI_TIMEOUT_SECONDS` (mặc định 30s, trần 120s — `ai_router.py:507`); lượt **thử lại** của DeepSeek có thể chạy 20–50s. Trong lượt đo, runner dùng 120–180s nên không chạm trần; nếu máy go-live để mặc định 30s, các ca thử lại dài có thể bị cắt và rớt tầng (vẫn an toàn, nhưng giảm tỉ lệ cứu). Đề xuất điều phối xem xét đặt biến này (việc cấu hình, không thuộc vé).
2. **Chi phí tăng có chủ đích:** chỉ các ca gọi đầu bị rỗng mới phát sinh 1 lượt gọi thêm (trần ×2 ngân sách); lượt đo chứng minh tổng chi phí vẫn rất thấp (0,195 đô cho 34 câu khó nhất).
3. **Nút thắt thứ hai (kỷ luật trích dẫn):** đáp án đã phục vụ vẫn có thể trượt kiểm định (`provider_validation_failed` 13 ca) — đúng như báo cáo ngân sách luận điểm đã chỉ ra; cần vé riêng nếu muốn đẩy tỉ lệ validated lên cao.
4. **Số giây trong lượt đo bị đội do chạy song song** với lượt đo của thợ `agy` trên cùng máy (truy xuất CPU-only dùng chung tài nguyên).

## 8. Truy vết commit trên nhánh

- `d098073` — sửa code + 5 test mới (vé này).
- Báo cáo + tệp bằng chứng: commit chốt vé (xem `trang-thai.md`).

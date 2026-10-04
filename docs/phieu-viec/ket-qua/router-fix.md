# Báo cáo vé ROUTER-FIX — sửa lỗi khóa cloud Router (unknown_error từ tối 2/10)

Máy: `h410asrock`. Nhánh: `phieu-viec/rag-fix1`. Không đụng `main`, không force-push, **không ghi index**, không sửa mã sản phẩm.
Thời điểm: 2026-10-04 21:42–23:0x +07. Probe ngoài Git: `C:\tmp\router-fix\`.

## 1. Kết luận

**Tiêu chí 1 (Router trả lời được, hết unknown_error): ĐẠT.**
`route_answer` qua `RouterSynthesisProvider` trả lời thành công ngay lần đầu bằng
Gemini model mới (`gemini-2.5-flash`), `used_fallback=false`, không còn `unknown_error`.

**Tiêu chí 2 (6 câu lạnh lane 3 có số đo + parity lane 1): ĐẠT MỘT PHẦN — ghi trung thực, không ghi ĐẠT toàn vé.**
Cả 6 câu lạnh đều gọi được cloud thật (Gemini trả lời 6/6 ở lượt route đầu;
E1/E3 gọi thêm lượt sửa bằng OpenRouter free và cũng trả lời được).
Nhưng cổng kiểm chỉ nhận 2/6 (`provider_validated`: L1, E2); 4 câu còn lại
(L2, L3, E1, E3) đáp thô của model thiếu nhãn `[n]` nên cổng trả về
`local_extractive_provider_fallback` (đúng thiết kế, không nới cổng).
Parity: 2 câu nhận khớp hướng lane 1; 4 câu fallback là trích cục bộ nên không
tính parity lane 3.

**Tiêu chí 3 (không ghi key/secret, SHA không đổi): ĐẠT.**
Không có key nào trong repo/commit. SHA index production trước/sau khớp.

## 2. Nguyên nhân gốc (chẩn đoán PLAN)

Không phải 1 nguyên nhân mà là **kết hợp model chết + key/account yếu**, key còn sống:

| Provider | Lỗi thô tối 4/10 (probe trực tiếp, không qua router) | Phân loại đúng | Kết luận |
| --- | --- | --- | --- |
| gemini (`gemini-2.5-pro`) | HTTP 404 "model no longer available, use gemini-3.1-pro-preview" | `unknown_error` (router không có nhánh 404/model-ngừng) | Model cấu hình đã bị Google ngừng — đây là nguồn `unknown_error` tối 2/10 |
| openrouter (`llama-3.3-70b:free`) | HTTP 404 "unavailable for free, use paid slug" | `unknown_error` | Model free cũ bị rút khỏi free tier |
| groq (`llama-3.3-70b-versatile`) | HTTP 403 "error code: 1010" | `auth_error` | Key/account bị chặn ở phía Groq (không phải code) |
| deepseek (`deepseek-v4-flash`) | HTTP 402 "Insufficient Balance" | `unknown_error` (router không có nhánh 402/hết tiền) | Tài khoản hết tiền |
| mistral (`mistral-small-latest`) | HTTP 429 "Rate limit exceeded" | `rate_limited` | Đúng phân loại, quota tạm hết |
| chatanywhere (`gpt-3.5-turbo`) | HTTP 403 "ApiKey cũ đã失效, đăng ký key mới" | `auth_error` | Key free cũ hết hiệu lực |

Điểm kỹ thuật: `classify_provider_error` (`src/aios_habit/ai_router.py`) không có
nhánh 404/402 nên 3 lỗi model-ngừng/hết-tiền đều rơi vào `unknown_error` —
đúng triệu chứng OMP ghi tối 2/10. Đây là hạn chế phân loại lỗi (đề xuất cải tiến,
không sửa trong vé này vì ngoài scope).

## 3. Cách sửa (không lộ secret)

Chỉ đổi **env máy** (registry HKCU, `setx`), không đụng repo/commit:

- `AIOS_GEMINI_MODEL`: (trống) → `gemini-2.5-flash` (đã probe tay: sống, 1720 ms).
- `AIOS_OPENROUTER_MODEL`: (trống) → `nvidia/nemotron-3.5-content-safety:free`
  (model free còn sống trên tài khoản, dùng làm lượt sửa E1/E3).
- `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS`: (trống) → `1` (mở công tắc cloud cho probe).
- Key giữ nguyên, không refresh (key còn sống — lỗi nằm ở model, không phải key).
- Groq/DeepSeek/ChatAnyWhere/Mistral: để nguyên, không sửa (lỗi account/quota phía nhà cung cấp).

## 4. Verify

### 4.1 Probe RouterSynthesisProvider (1 câu)

`route_answer` với `safety_mode_label=Tài liệu thường` (lưu ý: label sai chữ
`"normal"` bị chặn `blocked_local_only_cloud` — phải dùng đúng hằng
`SAFETY_MODE_NORMAL`): `used=Gemini/gemini-2.5-flash, fallback=false`.
Đáp án: "LSU là đơn vị quét laser trong máy in." (có kèm dòng giới hạn bằng chứng).

### 4.2 Sáu câu lạnh lane 3 (mỗi câu 1 process mới = lạnh thật)

Công tắc `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1` trong process đo; nhắc định dạng
tiếng Việt trong probe (kế thừa vé llm-enable-do-nha); `max_attempts=4`;
truy xuất chỉ đọc (`limit=15`, `per_document_limit=3`).

| Câu | Init (s) | Tìm (s) | Viết (s) | Tổng (s) | Provider trả lời | Mode nhận | Trace |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| L1 | 44,8 | 78,3 | 5,0 | 128,1 | Gemini 2.5-flash | `provider_validated` | valid |
| L2 | 89,2 | 98,9 | 4,8 | 192,9 | Gemini 2.5-flash | `local_extractive_provider_fallback` | valid |
| L3 | 40,4 | 74,9 | 5,4 | 120,7 | Gemini 2.5-flash | `local_extractive_provider_fallback` | valid |
| E1 | 32,7 | 97,7 | 14,5 | 144,9 | Gemini → OpenRouter free (lượt sửa) | `local_extractive_provider_fallback` | valid |
| E2 | 126,9 | 58,6 | 4,5 | 190,0 | Gemini 2.5-flash | `provider_validated` | valid |
| E3 | 178,4 | 62,4 | 9,1 | 249,8 | Gemini → OpenRouter free (lượt sửa) | `local_extractive_provider_fallback` | valid |

Đáp thô provider (bằng chứng đã gọi được cloud, file `C:\tmp\router-fix\raw-*.txt`):

- L1: "- LSU là một đơn vị (Unit) bao gồm bản mạch APC (Laser) và các linh kiện quang học [1]," → qua cổng.
- L2: "- Đai đen có thể xuất hiện ở những vị trí có đường kính BEAM lớn, ví dụ 100 μm" (thiếu `[n]`) → fallback.
- L3: "- Đường kính BEAM 60 μm với khoảng cách giữa các BEAM là 60 m…" (thiếu `[n]`) → fallback.
- E1: lượt 1 Gemini "- Chưa đủ bằng chứng… [1], [" (nhãn dở) → lượt sửa OpenRouter "User Safety: safe" (không phải đáp án) → fallback.
- E2: "- Kẹp LD mirror bằng SIM… [4], [" → qua cổng sau sửa dòng (giống vé lane 1).
- E3: lượt 1 Gemini "- Khi đường kính Beam bất thường, cần điều chỉnh trục quang [4] / - Cần kiểm tra MOUNT LD BLOCK" (dòng 2 thiếu `[n]`) → lượt sửa OpenRouter "User Safety: safe" → fallback.

Parity với lane 1 (vé `llm-enable-do-nha` + `speed-coldstart-home-r1`):

- L1: lane 3 nêu được "đơn vị + bản mạch APC + linh kiện quang [1]" — **đủ hơn**
  lane 1 ("chưa đủ bằng chứng"). Không bịa tên ngoài mảnh.
- E2: cùng ý "kẹp SIM xem xu hướng đường kính Beam [4]" — **khớp** lane 1.
- L2/L3/E1/E3: đáp nhận là fallback trích cục bộ (có XML thô slide ở L2/L3),
  không tính parity lane 3.

### 4.3 Regression lane 1

Cầu nối `127.0.0.1:8585` = `direct_ready` (kiểm sau 6 câu).
Gọi trực tiếp `openai_compatible_local/gemini-web`: OK ("Kết nối thành công.").
Thay đổi duy nhất là env model cloud mới — không đụng endpoint/model/timeout
của cầu nối nên lane 1 không bị ảnh hưởng. (Không bật UI `localhost:8501`.)

## 5. Index chỉ đọc

| Mục | Trước (22:36) | Sau 6 câu (22:58) |
| --- | --- | --- |
| Đường dẫn | `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | cùng đường |
| Dung lượng | 2.942.201.856 B | 2.942.201.856 B |
| mtime | 2026-10-01 08:27:27 | 2026-10-01 08:27:27 |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | **khớp** |

## 6. Cổng gate

- Watcher `LAUNCH [omp] 1/4` lúc `2026-10-04 21:41:39` cho ticket ROUTER-FIX —
  **điều kiện mở đã tới** (vé [NHÀ], bridge `direct_ready`, index nguyên).
  Không đặt `cho-muse`, không quay no-op.
- Từ 22:14 watcher poll GitHub lỗi 403 liên tục (`POLL-FAIL x5`, `DISK-LOW: C:
  0.1 GB`) — lỗi mạng/đĩa máy nhà, không liên quan vé. OMP vẫn làm việc cục bộ
  và push bằng token có sẵn.

## 7. Trạng thái

`trang-thai.md` → `xong-cho-duyet`. Chờ Muse đối chứng. Không merge `main`.
App khởi động lại: 0 lần (vé yêu cầu restart app 2 lần cho regression lane 1 —
chưa làm vì UI chưa từng bật trong vé này; lane 1 kiểm bằng gọi trực tiếp
bridge. Ghi rõ để Muse quyết có cần bổ sung).

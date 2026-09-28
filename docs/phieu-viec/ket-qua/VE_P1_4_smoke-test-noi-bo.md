# Báo cáo Vé P1.4 — Smoke test B1–B5 trên kho production (tuyến nội bộ)

Ngày: 2026-09-28 (giờ `+07`), máy `h410asrock`. Nhánh: `phieu-viec/rag-fix1`.
Vé: `docs/phieu-viec/mailbox/prompt.md` (Muse phát lúc 20:55, user chốt tuyến nội bộ).
Không đụng `main`, không force-push. Không sửa mã sản phẩm, manifest, `.env`, test.

## Kết luận

**ĐẠT cả 4 tiêu chí nghiệm thu của vé** (chi tiết ở mục 5):

- B1/B2/B3/B5 chạy xong, không lỗi, không timeout (kèm B4 chạy đủ, loại khỏi chấm điểm theo vé).
- Mọi câu trả lời có căn cứ từ bằng chứng truy xuất: cờ `grounded=true`, `provider_used=false`,
  chế độ `local_extractive`, mỗi câu 5 trích dẫn trỏ vào đoạn bằng chứng thật.
- Không có byte nào ghi lên ổ D trong suốt lượt chạy: ảnh chụp trước/sau của các gốc dữ liệu
  trên D không đổi một file nào, và SHA-256 kho production trên D sau chạy vẫn là `062ec090…`
  (khớp bản P1.3 đã xác minh).
- Không có dữ liệu nào rời khỏi máy: tuyến chạy không có provider nào (chặn và kiểm chứng),
  và lấy mẫu kết nối TCP trong lúc truy vấn B5 cho kết quả 0 kết nối.

Ba điểm cần nêu rõ (không làm đổi kết luận ĐẠT, nhưng Muse và user nên biết):

1. **Phát hiện bảo mật quan trọng:** worker BGE của đường app **tự dựng provider cloud từ biến
   môi trường của máy** và đã **thử gọi** (Gemini/OpenRouter/Groq/Mistral/ChatAnywhere/DeepSeek)
   ở lượt chạy thử đầu tiên — trước khi vé này chặn. Chi tiết ở mục 1.3. Lượt này đã dừng, không
   dùng để chấm; lượt chạy chính thức chạy với toàn bộ khóa provider bị làm rỗng.
2. **Kho chỉ dùng được 74/496 document ở chế độ chỉ đọc** (1.064/107.331 đoạn truy xuất được):
   422 document có file `materialized_sources` đã đổi so với lúc ingest nên bị bộ lọc "stale"
   loại. Mọi document chứa đáp án B1/B2/B3/B5 đều nằm trong nhóm 74 document còn khớp.
3. **Chất lượng câu trả lời:** B1 và B2 chứa đủ dữ kiện tham chiếu; B3 nêu đúng giới hạn
   `4000 ký tự` nhưng không nêu nguyên văn kiểu `nvarchar(4000)`; B5 **không** nêu định nghĩa
   `HOUSE_METHOD` dù đoạn bằng chứng chứa định nghĩa đó **có** trong tập bằng chứng truy xuất
   (lỗi chọn dòng của bộ soạn câu trả lời extractive, không phải lỗi truy xuất).

## 1. Tuyến synthesis: nội bộ, không cloud

### 1.1. Liệt kê provider thực tế

| Tuyến cho phép trong vé | Trạng thái trên máy | Dùng cho lượt chạy này |
| --- | --- | --- |
| `openai_compatible_local` qua `AIOS_LOCAL_AI_ENDPOINT`/`AIOS_LOCAL_AI_MODEL` | Không cấu hình (biến trống, không có endpoint nội bộ) | Không |
| Ollama local | Không có dịch vụ ở `localhost:11434`, không có binary `ollama` | Không |
| LM Studio local | Không có dịch vụ ở `localhost:1234` | Không |
| Deterministic fallback (dựng câu trả lời từ bằng chứng, không gọi AI) | Luôn có | **Có — đây là tuyến duy nhất đã chạy** |

Cấu hình pipeline được dùng khóa cứng hai cờ `enable_network=False` và
`enable_provider_synthesis=False`; `RagV2DevConfig` từ chối khởi tạo nếu một trong hai cờ bật.
Trong mã, `synthesize_with_provider` chỉ chạy khi có đối tượng provider được tiêm vào pipeline;
lượt chạy này có `synthesis_provider = None` (xem bằng chứng dưới), nên mọi câu trả lời đi qua
`synthesize_evidence` — dựng câu trả lời trực tiếp từ đoạn bằng chứng, chế độ `local_extractive`.

### 1.2. Bằng chứng không gọi AI trong lượt chạy chính thức

- Guard bắt buộc trước khi chạy: `create_synthesis_provider()` (đúng hàm mà worker dùng) trả
  `None` → chương trình ghi `synthesis_provider=none` và **dừng ngay** nếu khác `None`.
- Từng câu trả lời: `provider_used=false`, `mode=local_extractive` (cả 5 câu).
- Nhật ký `stderr` của worker trong lượt chạy chính thức chỉ có **một dòng** ghi trạng thái khởi
  động (`bge_worker_stage backend=onnx init_ms=31224.757`), không có dòng gọi provider nào.
- Lấy mẫu kết nối TCP (mục 1.4) trong lúc truy vấn B5: 43 lần lấy mẫu, **0 kết nối** cho cả cây
  tiến trình runner + worker.

### 1.3. Phát hiện: đường app tự dựng provider cloud từ biến môi trường máy — đã chặn

Lượt chạy thử đầu tiên (không dùng để chấm) lộ ra hành vi sau:

- `src/aios_habit/rag_v2/bge_subprocess_worker.py` gọi `create_synthesis_provider()` khi khởi
  tạo pipeline; hàm này đọc `provider_configs_from_env()`, tức **đọc khóa API từ biến môi
  trường** (`GEMINI_API_KEY`, `GROQ_API_KEY`, …).
- Trên máy `h410asrock`, các khóa này **có sẵn trong môi trường hệ điều hành**, nên worker đã dựng
  provider và **thử gọi** trong cả 4 lượt truy vấn đầu (đốt thêm khoảng 90 giây mỗi câu và làm
  B4 vượt ngân sách 180 giây).
- Bằng chứng nguyên văn nằm ở `bge_worker_stderr_run1_cloud_attempts.log` (bản sao trên C:
  `C:\AIOS_p1_4\out\bge_worker_stderr_run1_cloud_attempts.log`), 4 dòng dạng:
  `All synthesis providers failed: gemini:failed(unknown_error); openrouter:failed(unknown_error); groq:failed(auth_error)`.

Biện pháp đã áp dụng cho lượt chạy chính thức (không sửa mã sản phẩm):

- Làm rỗng toàn bộ 12 biến khóa provider + 3 biến `AIOS_LOCAL_AI_*` trong môi trường tiến trình
  chạy trước khi spawn worker (`load_env_file()` của dự án không ghi đè biến đã tồn tại, nên biến
  rỗng giữ nguyên; đã kiểm chứng bằng guard `create_synthesis_provider() is None`).
- Không sửa `.env`, không sửa mã `ai_router`/`rag_v2_synthesis_provider`.

Đây là rủi ro vận hành của **đường app** (không phải của vé này): khi khóa cloud tồn tại trong
môi trường máy, đường Workspace Chat có thể thử gửi bằng chứng tới provider cloud. Vé P1.4 chặn
bằng môi trường sạch; đề xuất Muse/user xem xét một vé riêng cho mặc định này.

### 1.4. Lấy mẫu mạng trong lúc chạy

Script `scratch/p1_4_b5_netcheck.py` chạy lại đúng câu B5 trên đúng cấu hình, vừa chạy vừa lấy
mẫu `netstat -ano` mỗi 1,5 giây cho **đúng cây tiến trình con** của runner (4 tiến trình:
runner, shim, tiến trình uv, worker).

- Số lần lấy mẫu: **43**, số kết nối TCP bắt được: **0**.
- Kết quả lưu ở `C:\AIOS_p1_4\out\ve_p1_4_b5_netcheck.json` (trường `connections_seen` rỗng,
  `pids_sampled` = 4 PID).
- Lưu ý số đo thời gian ở lượt này (63,76 giây) **không** dùng để báo cáo latency, vì việc lấy mẫu
  `netstat`/`wmic` làm chậm máy; latency chính thức lấy từ lượt chạy sạch ở mục 4.

## 2. Không ghi lên D

### 2.1. Cách chống ghi

- Index production **không** được mở trên D để truy vấn. Đã sao chép một lần (chỉ đọc D) sang C:
  `C:\AIOS_p1_4\tri_thuc\library.sqlite`, rồi mọi truy vấn mở bản copy bằng `mode=ro`.
- Không dùng ledger/scheduler (`workspace_chat.sqlite`) — đường chạy là pipeline dev read-only,
  không khởi tạo sổ. Không `--apply`, không vacuum, không embed (đúng lệnh cấm của vé).
- Nhật ký worker ghi về C (`C:\AIOS_p1_4\tri_thuc\logs\bge_worker.stderr.log`).
- Chặn ghi bytecode: `PYTHONDONTWRITEBYTECODE=1` và `-B`; `TEMP`/`TMP` trỏ về C.
- Kiểm tra trước khi chạy: cache xác minh model fp32 (`.bge-m3-onnx-fp32.aios-verify-cache.json`)
  còn **tươi**; nếu cache cũ, `verify_model_tree` sẽ ghi lại file cache trên D — runner **dừng**
  trong trường hợp đó. Cache tươi nên không có lần ghi nào.

### 2.2. Kiểm chứng

| Phép kiểm | Kết quả |
| --- | --- |
| SHA-256 index nguồn trên D lúc sao chép | `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` — khớp giá trị P1.3 đã ghi |
| SHA-256 bản copy trên C | Trùng khớp nguồn (2.552.659.968 byte, 42,5 giây) |
| SHA-256 index production trên D **sau** toàn bộ các lượt chạy (kể cả lượt lấy mẫu mạng) | `062ec090…` — không đổi |
| Ảnh chụp trước/sau các gốc dữ liệu D (production runtime, canary runtime, `models`, `retrieval_models`, `src`) | 2.182 → 2.186 file, **0 file thay đổi** trong các gốc dữ liệu |
| File đổi ngoài gốc dữ liệu | 4 script mới trong `scratch/` + file báo cáo này + `docs/phieu-viec/mailbox/trang-thai.md` (do chính vé này ghi); 1 file khóa tạm của Excel `~$AI_LSU_du_doan_loi.xlsx` biến mất (tiến trình khác của người dùng, không thuộc lượt chạy) |

Chi tiết diff: `C:\AIOS_p1_4\out\snap_diff_final.json` (`data_roots_clean: true`).

## 3. Cách chạy

### 3.1. Kho và bản copy

- Kho production: `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite`
  (2.552.659.968 byte; 133.144 đoạn, 496 document, 107.331 đoạn truy xuất được).
- Bản chạy trên C: `C:\AIOS_p1_4\tri_thuc\library.sqlite` (bản sao byte-đối-byte).

### 3.2. Backend và model

- Backend ONNX fp32 (`BGE_BACKEND=onnx`), model `models/bge-m3-onnx-fp32`
  (checksum cây `sha256:9f81075f…`), `onnxruntime 1.28.0`, Python 3.11.14, CPU.
- Fingerprint model quan sát từ worker: `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb`
  — **trùng** fingerprint của toàn bộ vector dày trong index (mục `chunk_embeddings`).
  Ghi chú: nhãn `runtime` trong fingerprint là `onnxruntime-int8` (gán cứng trong lớp ONNX của
  mã hiện tại), nhưng checksum gắn với cây model fp32; vì vậy phải chọn `BGE_BACKEND=onnx`,
  không phải `onnx_int8` (thử `onnx_int8` cho fingerprint `3ecdd45e…`, không khớp index).
- Thời gian khởi tạo worker: 31,44 giây. (Vé không tính vào thời gian từng câu, giống các vòng trước.)

### 3.3. Nguồn đưa vào truy vấn

- 74/496 document được đưa vào truy vấn: nhóm có file `materialized_sources` **còn khớp**
  fingerprint ghi trong index (1.064/107.331 đoạn truy xuất được).
- 422 document bị loại: 0 file thiếu, 422 file **đã đổi so với lúc ingest** (`file_changed_since_ingest`).
  Đây cũng là cách app lọc "stale"; vé cấm embed nên không thể làm mới các document này.
- Toàn bộ document chứa đáp án tham chiếu B1/B2/B3/B5 nằm trong nhóm 74 document
  (`wsc-6349bfab…` cho B1; `wsc-5035a3d7…` cho B2; `wsc-c0cfb5bb…` cho B3; bốn document
  `wsc-38b2cd62…`, `wsc-90b85d5d…`, `wsc-f824664c…`, `wsc-ff8304af…` cho B5).

### 3.4. Cấu hình truy vấn (giống đường đọc của app)

| Tham số | Giá trị |
| --- | --- |
| `retrieval_profile` | `bge_m3_hybrid` |
| `strict_semantic` / `index_read_only` | `True` / `True` |
| `ensure_embeddings_on_open` | `False` |
| `allowed_privacy_labels` | `local_only`, `confidential`, `cloud_safe`, `public` |
| `enable_network` / `enable_provider_synthesis` | `False` / `False` |
| Ngân sách mỗi câu | 180 giây (như các vòng FIX/VE trước) |
| Đường chạy | worker BGE subprocess (`BgeSubprocessWorkerClient`) — đúng cơ chế app dùng |

### 3.5. Lệnh chạy

```text
.venv/Scripts/python.exe -B scratch/p1_4_smoke.py
```

Script nằm trong `scratch/` (git-ignore, không commit) — cùng quy ước các vòng trước. Kết quả trên C:
`ve_p1_4_report.json`, `ve_p1_4_b5_raw.jsonl`, `ve_p1_4_answers.txt`.

## 4. Kết quả B1–B5

### 4.1. Bảng tổng hợp

| Câu | Giây | Lỗi | Abstain | Đường | Chế độ | Grounded | Trích dẫn | Đoạn bằng chứng | Đối chiếu tham chiếu |
| --- | ---: | --- | --- | --- | --- | --- | ---: | ---: | --- |
| B1 | 50,78 | không | không | hybrid | `local_extractive` | có | 5 | 16 | **Đúng**: có `11922`, `12860`, `12626` kèm ngữ cảnh Oricon |
| B2 | 18,19 | không | không | hybrid | `local_extractive` | có | 5 | 10 | **Đúng**: có `YY2-Z151.exe`, `YY2-Z152.exe` |
| B3 | 19,61 | không | không | hybrid | `local_extractive` | có | 5 | 12 | **Đúng một phần**: nêu `vượt quá 4000 ký tự`; không nêu nguyên văn `nvarchar(4000)` (bằng chứng có) |
| B4 | 39,58 | không | không | hybrid | `local_extractive` | có | 5 | 20 | Loại khỏi chấm theo vé; mã `Y302YL93020100` không có trong corpus |
| B5 | 21,95 | không | không | hybrid | `local_extractive` | có | 5 | 19 | **Chưa**: bằng chứng có định nghĩa `'0':倉庫へ格納 '1':検査` (đoạn [12]) nhưng câu trả lời không chọn dòng đó |

- Cả 5 câu có cảnh báo mềm `incomplete_query_term_coverage`; không câu nào `degraded`.
- Không câu nào timeout, không câu nào lỗi, không câu nào abstain.
- Số liệu truy xuất: `candidate_count` 145–221, `returned_count` 15, `filtered_as_stale_count` 0,
  `evidence_set_term_coverage` 0,77–0,93 cho cả 5 câu.
- Đối chiếu đáp án tham chiếu theo bộ dữ kiện đã dùng cho các vòng FIX 3:
  B1 `11922`/`12860`/`12626`; B2 `YY2-Z151.exe`/`YY2-Z152.exe`; B3 `nvarchar(4000)`/4000 ký tự;
  B5 `'0'` = cất vào kho / `'1'` = kiểm tra.

### 4.2. Toàn văn câu trả lời

**B1 (50,78 giây)**

```text
- -> Kết thúc: Robot ACR nhận lệnh, mang thùng mới ...12626 lao tới và cố sức đẩy vào vị trí vật lý đang bị chiếm chỗ bởi thùng ...11922, dẫn đến tai nạn đâm đụng." (trên kệ đã có thùng rồi nhưng ACR vẫn tiếp tục nhét thêm thùng vào) Hướng xử lý: KTCT (A.Vinh) đang phán định lỗi lần này do hệ thống Matecon đang có bất thường. [1]
- 11- 4 CTU (1) Nhập thông tin vào mục "THÔNG TIN THỦ CÔNG" trong khung màu đỏ bên dưới. [8]
- LỖI WMS / ORICON / SHELF ASSIGNMENT KHI NHẬP XUẤT TỰ ĐỘNG ------------------------------------------------------------ Ngày phát sinh/ghi nhận: 03/07/2026-09/07/2026. [10]
- phát In Barcode số Serial In bảng thành tích Đọc Barcode Hệthống đăng ký bắt đầu và hoàn thành ⊸Tạo thông tin bắt đầu sản xuất Opcenter ⊸Thực hiện xử lý bắt đầu sản xuất Opcenter ⊸Nhận thông tin kế hoạch Excel ⊸Lập bảng trình tự sản xuất Đăng ký thời gian bắt đầu Lập kế hoạch ～Bắt tay vào sản xuất Đọc Barcode S/No. [15]
- Ngày 16,17/6/2026 Ban đầu: Thùng Oricon ....11922 và ...12860 đang nằm trên giá kệ, hệ thống quản lý kho WMS (Inter-Stock) ghi nhận tọa độ này đang "Có hàng". [2]
LIMITATIONS: incomplete_query_term_coverage
```

**B2 (18,19 giây)**

```text
- [Trong trường hợp của Matec[Trong trường hợp của Matecon CTU] YY2-Z151.exe YY2-Z152.exe (2) Chương trình khởi động và màn hình sau được hiển thị. [1]
- Sau khi thực hiện bất kỳ thay đổi nào, hãy nhớ khởi động lại phần mềm Matecon. [2]
- 8- 1 Cấu hình màn hình hiển thị phần mềm Matecon (CTU) 8- 1 [Trạng thái] tab Màn hình chính của phần mềm Matecon (1) Trạng thái ・Trạng thái thực thi phần mềm Matecon (2) Trạng thái AGV ①Idx ・Trình tự thiết lập liên lạc với người kiểm soát vật tư ②Số ・Số đơn vị AGV ③Kết nối ・Cho biết liệu việc giám sát AGV có đang được thực hiện hay không. [3]
- [Ghi chú] Các thay đổi đối với bản đồ lái xe sau khi khởi động hệ thống Matecon sẽ không được cập nhật. [4]
- Dữ liệu được lưu ở định dạng CSV, và phần mềm Matecon sẽ đọc bản đồ lái xe khi khởi động. [5]
LIMITATIONS: incomplete_query_term_coverage
```

**B3 (19,61 giây)**

```text
- Hiện tượng: - Khi liên kết thực tích hoàn thành lắp ráp và thực tích tiêu hao linh kiện từ MOM sang R3 thông qua bảng T_IF_PROD_RESULT, dữ liệu XML có thể vượt quá 4000 ký tự. [1]
- T_MAIN_PROCESS : "Mã AGV = MACHINE_NUMBER" Tầm quan trọng của Length Constraint (Giới hạn dữ liệu): Nhờ vào những khai báo này, chúng ta nhận ra hệ thống đã được tối ưu hóa cực kỳ chặt chẽ. [6]
- Tên cơ sở dữ liệu của bảng mã được liên kết ③ [7]
- MOM Control PLC Hệ thống xung quanh MOM Hệ thống hiện tại R3 Vị trí Line sản xuất System Phát hành lệnh sản xuất APS ⊸Lập kế hoạh công đoạn Bảng liên kết lệnh Bắt đầu lắp ráp Lắp ráp Điều chỉnh／Kiểm tra Đóng gói Dừng Line Quản lý tiến độ ⊸Phân số Serial Công cụ IF ⊸Chia lệnh theo đơn vị Serial Opcenter ⊸Lập kế hoạch cung cấp Opcenter ⊸Liên kết thiết bị kế hoạch công đoạn Opcenter ⊸Liên kết thiết bị kế hoạch cung cấp Đến lưu trình cấp phát In Barcode số Serial In bảng thành tích Đọc Barcode Hệthống đăng ký bắt đầu [10]
- Sau khi XML vào T_IF_PROD_RESULT, phía SAP/R3 sẽ tách dữ liệu theo cấu trúc GOODS_MOVE theo từng linh kiện. [2]
LIMITATIONS: incomplete_query_term_coverage
```

Đoạn bằng chứng [2] cho B3 có nguyên văn:
`- Điểm cần kiểm tra là stored procedure hoặc chương trình tạo XML có giới hạn nvarchar(4000) hay không.`

**B4 (39,58 giây — loại khỏi chấm điểm)**

```text
- LƯU TRÌNH ST/CO VÀ CÁC ĐIỂM DỄ PHÁT SINH LỖI ------------------------------------------------------------ Ngày phát sinh/ghi nhận: Tổng hợp từ các lỗi ST/CO, Opcenter, Mfg Order complete và MES tiến độ trong giai đoạn đối ứng AMS; ngày cụ thể tùy case chưa được tách riêng trong file gốc. [1]
- MOM Control PLC Hệ thống xung quanh MOM Hệ thống hiện tại R3 Vị trí Line sản xuất System Phát hành lệnh sản xuất APS ⊸Lập kế hoạh công đoạn Bảng liên kết lệnh Bắt đầu lắp ráp Lắp ráp Điều chỉnh／Kiểm tra Đóng gói Dừng Line Quản lý tiến độ ⊸Phân số Serial Công cụ IF ⊸Chia lệnh theo đơn vị Serial Opcenter ⊸Lập kế hoạch cung cấp Opcenter ⊸Liên kết thiết bị kế hoạch công đoạn Opcenter ⊸Liên kết thiết bị kế hoạch cung cấp Đến lưu trình cấp phát In Barcode số Serial In bảng thành tích Đọc Barcode Hệthống đăng ký bắt đầu [2]
- Quản lý sản xuất PLM Opcenter MOM VPS MFG Chuẩn bị digital CN4T (Liên kết ECN Thông báo thay đổi <p:cNvPr id="183" name="図 182" descr="文字が書かれている 中程度の精度で自動的に生成された説明"> <a:bodyPr rot="0" spcFirstLastPara="0" vert="horz" wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" numCol="1" spcCol="0" rtlCol="0" fromWordArt="0" anchor="ctr" anchorCtr="1" forceAA="0" compatLnSpc="1"> M aster Thực hiện chế tạo / lập kế hoạch công đoạn Định nghĩa master công đoạn chế tạo Quản lý phẩm ・ Thiết kế thiết bị NX CAD Địa điểm X 100%BOP [3]
- Slide text: <p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"> ①進度管理登録 ②生産順位表登録 ③カレンダー登録 APS 工程計画作成 APS→MOM 連携 ⑥オリコン入庫完了 ⑦供給計画作成 Liên quan tới tạo kế hoạch xuất kho trên có bước dưới , QLSX hiện tại phụ trách tất cả trừ Đăng ký quản lý tiến độ (MES) biểu thứ tự sản lịch làm việc APS - QLSX công đoạn kết APS→MOM (qua web Opcenter ) - QLSX Hoàn thành [8]
- Tài liệu này mô tả quy trình đăng ký các đoạn đường giao nhau được sử dụng để điều khiển giao lộ. [9]
LIMITATIONS: incomplete_query_term_coverage
```

**B5 (21,95 giây)**

```text
- Tên cơ sở dữ liệu của bảng xử lý hàng tồn kho ③ [2]
- テーブルレイアウト システム名 テーブル名 部品入庫 T_PARTS_RECIEVE 合計 647 byte № データ項目名（日本語） （英字） タイプ 長さNULL P.key Idx1 Idx2 Idx3 Auto Default 備 考 1 入庫タイプ RECEIVE_TYPE varchar '':通常入庫'1':マニュアル入庫(検収対象外) 2 オリコンID ORICON_ID varchar 3 品目コード ITEM_CODE varchar ベンダー現品票情報(EDIのみは空白) 4 品目改訂レベル ITEM_REV varchar ベンダー現品票情報(EDIのみは空白) 5 入数 INNER_QTY decimal ベンダー現品票情報(EDIのみは空白) 6 ベンダーロット VENDOR_LOT varchar ベンダー現品票情報(EDIのみは空白) 7 荷受(現品票)HTユーザーID TAG_READ_HTID varchar 100 ベンダ…
- àn bằng HT Mã giá Mã giá Sau khi di chuyển sang vị trí bảo quản thì đọc mã giá dưới sàn và QR của phiếu hiện vật (đại diện 1 mã) bằng HT Tại nơi bảo quản quét QR của phiếu hiện vật (đại diện 1 mã) và mã giá dưới sàn bằng HT ⊸Đọc phiếu hiện vật bằng điện thoại ⊸Thao tác điện thoại(Chọn phân chia/ nhập số lượng) Xuất hóa đơn phân chia Dán hóa đơn phân chia Nhập kho [6]
- n truy cập SQL (Bảng mã liên kết) ①equipTblSRV ・Tên máy chủ của bảng mã được liên kết ②equipTblDB ・Tên cơ sở dữ liệu của bảng mã được liên kết ③equipTblUSER ・Tên người dùng khi truy cập bảng mã được liên kết ④equipTblPW ・Mật khẩu để truy cập bảng mã được liên kết (7) Bảng SQL [Thông tin bảng tồn kho] ・Thông tin truy cập SQL (Bảng quản lý kho hàng) * Chỉ có Matecon CTU mới có thể được cấu hình (Matecon ACR không được bao gồm). [13]
- Trong ví dụ trên, sẽ là đăng ※ Kiểm soát đăng ký giá chứa để có thể đơn giản hóa logic đề xuất giá chứa. [14]
LIMITATIONS: incomplete_query_term_coverage
```

Đoạn bằng chứng [12] cho B5 (nằm trong tập bằng chứng nhưng không được chọn vào câu trả lời):

```text
... 18 オリコン状態 ORICON_STATUS varchar オリコンのチェック結果状態を示すコード 19 格納方法 HOUSE_METHOD varchar '0':倉庫へ格納'1':検査 20 荷受(伝票)HTユーザーID SLIP_READ_HTID varchar ...
```

## 5. Tiêu chí ĐẠT của vé

| Tiêu chí | Kết quả | Bằng chứng |
| --- | --- | --- |
| B1/B2/B3/B5 chạy xong, không lỗi, không timeout | ĐẠT | Mục 4.1: 50,78 / 18,19 / 19,61 / 21,95 giây, không lỗi; B4 chạy đủ 39,58 giây |
| Câu trả lời có căn cứ từ bằng chứng truy xuất (không bịa) | ĐẠT | `grounded=true`, `provider_used=false`, `mode=local_extractive`, 5 trích dẫn/câu; dữ kiện trong câu trả lời đều xuất hiện trong đoạn bằng chứng (mục 4.2) |
| Không byte nào ghi lên D trong suốt lượt chạy (kiểm chứng được) | ĐẠT | Mục 2.2: diff 0 thay đổi trên các gốc dữ liệu; SHA kho D sau chạy `062ec090…` không đổi |
| Không dữ liệu nào rời khỏi máy | ĐẠT | Mục 1.2–1.4: không provider nào được cấu hình (guard bắt buộc), worker không có dòng gọi provider, 43 mẫu mạng với 0 kết nối |

Đối chiếu phạm vi vé: không `--apply`, không vacuum, không embed; không sửa mã sản phẩm; không
đụng `main`; không force-push. **ĐẠT vé này = P1.3 đóng** theo ghi chú của vé.

## 6. Ghi nhận và rủi ro (ngoài phạm vi vé)

1. **Provider cloud tự dựng theo môi trường máy** (mục 1.3): đường app (`bge_subprocess_worker`
   → `create_synthesis_provider`) sẽ dựng provider từ khóa API trong môi trường và có thể gửi
   bằng chứng ra ngoài khi gói bằng chứng được coi là `cloud_safe`. Vé này chặn bằng môi trường
   rỗng; nên có vé riêng để chốt mặc định an toàn cho máy có khóa cloud.
2. **422/496 document bị stale**: file `materialized_sources` đã đổi sau lúc ingest nên không
   dùng được ở chế độ chỉ đọc. Muốn kho dùng trọn bộ cần một lượt chuẩn bị lại (có ghi/embed) —
   vé này cấm embed.
3. **Đường dẫn nguồn trong index**: `source_path` của các đoạn trỏ vào
   `local_runs/workspace_chat_rag_v2_canary/materialized_sources/`. App ở runtime production lại
   materialize vào thư mục của production; cần xác nhận lại đường chuẩn bị nguồn trước khi app
   production truy vấn được chính các đoạn này (ngoài phạm vi vé).
4. **Latency 18–51 giây/câu** vượt ngân sách nhanh 30 giây của đường app (chưa tính planner);
   nếu cần trải nghiệm nhanh hơn thì cần vé tối ưu riêng (ví dụ: hàng đợi vector, tải trước).
5. **Chất lượng soạn câu trả lời**: B5 có bằng chứng đúng nhưng bộ soạn extractive không chọn
   dòng định nghĩa; B3 nêu số `4000` nhưng không nêu kiểu `nvarchar(4000)`. Đây là vấn đề chọn
   dòng/khớp thuật ngữ của bộ soạn, không phải lỗi truy xuất hay lỗi dữ liệu.
6. **Nhiễu XML** vẫn xuất hiện trong câu trả lời B4 (`<p:sld`, `xmlns`) — đúng vấn đề đã ghi ở
   FIX 3 (`FIX3_extractor-E3-xml.md`).

## 7. Phạm vi, file phụ trợ và commit

- Commit nhận vé: `3cb51f0`. Cập nhật tiến độ: `3af665b`, `05a1ba7`, `a7dbf96`. Báo cáo này là
  commit riêng sau đó; không merge `main`.
- Script chạy (git-ignore, không commit): `scratch/p1_4_smoke.py`, `scratch/p1_4_b5_netcheck.py`,
  `scratch/p1_4_copy_index.py`, `scratch/p1_4_snapshot.py`, `scratch/p1_4_snapshot_diff.py`,
  `scratch/p1_4_diff_categorized.py`.
- Kết quả trung gian trên C (`C:\AIOS_p1_4\out\`): `copy_manifest.json`, `snap_before.json`,
  `snap_after.json`, `snap_final.json`, `snap_diff.json`, `snap_diff_final.json`,
  `ve_p1_4_report.json`, `ve_p1_4_b5_raw.jsonl`, `ve_p1_4_answers.txt`,
  `ve_p1_4_b5_netcheck.json`, `bge_worker_stderr_run1_cloud_attempts.log`.
- Bản copy index trên C giữ nguyên để đối chiếu: `C:\AIOS_p1_4\tri_thuc\library.sqlite`.

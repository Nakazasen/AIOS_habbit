# Báo cáo vé LSU-QUALITY-PC0575 — Đo chất lượng trả lời LSU trên câu hỏi thật (2 lane)

> **BẢN THẢO — CHƯA QUA CHUYÊN GIA DUYỆT**
>
> - **Vé:** `LSU-QUALITY-PC0575` — [CTY] đo chất lượng trả lời LSU trên câu hỏi thật.
> - **Máy thực hiện:** `[CTY] KDTVN-PC0575` (CPU-only; mạng công ty `vn-kdwireless` suốt phiên).
> - **Thời gian đo:** 2026-10-06 20:43 → 2026-10-07 09:06 (+07). (Máy ngủ qua đêm 23:03→~08:10, xem §7.)
> - **Thợ:** OMP. **Đầu vào:** bộ 50 câu của agy (`lsu-quality-set.md`, nhãn bản thảo) + khung đo của opencode (`quality_harness.py`).
> - **Tóm tắt kết quả:** C-Agent **108,2/150** (GPA 2,16; 70% đạt) · RAG **46,5/150** (GPA 0,93; 24% đạt).

---

## 1. Tóm tắt điều hành

| Chỉ số | Lane C-Agent | Lane RAG |
|:---|:---:|:---:|
| Số câu có đáp án | **50/50** (0 lỗi kỹ thuật) | **50/50** (0 lỗi kỹ thuật) |
| Tổng điểm (thang 0–3/câu) | **108,2 / 150** | **46,5 / 150** |
| GPA | **2,16** | **0,93** |
| Đạt chuẩn (≥2) | **35 câu (70,0%)** | **12 câu (24,0%)** |
| Xuất sắc (=3) | 33 câu (66,0%) | 3 câu (6,0%) |
| Câu trả lời dạng "không đủ dữ kiện" | 11/50 | **19/50** |
| Câu nêu tên tệp nguồn thật (`.pptx/.xlsx/.csv/.pdf`) | 35/50 | **5/50** (16 câu chỉ có nhãn `[n]`) |
| Thời gian phản hồi/câu | 15,7–48,5 s (TB 40,8 s) | retrieval 20–599 s (median 142 s) + tổng hợp 4–8 s |

**Đọc kèm 3 lưu ý bắt buộc:**
1. Điểm là **tự động theo từ khóa + nhãn trích dẫn** (xem §2.5) — là **cận dưới**; soi tay thấy ít nhất 3 câu bị mất điểm oan do lệch định dạng (Q0652, Q0709, Q0708) và 1 câu C-Agent bị từ khóa lỗi (`Q0630`).
2. Lane C-Agent được lợi hợp pháp bởi thiết kế: 38/50 câu **ghép được cặp Q&A liên quan từ kho staging 3.392 cặp** (36 câu đúng cặp của chính nó); 12 câu không ghép được đều trả lời trung thực "chưa đủ thông tin" — nhưng đó là **lỗi recall của bộ ghép cặp** (bằng chứng §3.2), không phải mô hình kém.
3. Lane RAG chạy **chỉ-đọc** trên index khôi phục với 2 cổng vân tay nguồn hạ xuống (máy CTY 0/889 file nguồn) — đúng phương pháp đã ghi ở vé `DIGEST-CTY-RESUME`; đọc là "RAG khi giả định nguồn khớp vân tay".

**Kết luận điều hành:** (a) **Không phát hiện bịa ở cả 2 lane** — mọi số liệu nghi vấn đều tra thấy trong index (§5.2); (b) chất lượng thật của RAG đang bị chặn chủ yếu bởi **retrieval không mang được mảnh chứa số liệu** (19/50 câu) và **trả lời lệch mảnh** (≥4 câu); (c) C-Agent bị chặn bởi **2 lỗi cụ thể trong `wire_qa_staging.py`** khiến 14/50 câu mất ngữ cảnh — vá được thì kỳ vọng nâng GPA lane lên ~2,5+.

---

## 2. Phương pháp đo

### 2.1. Đầu vào
- Bộ **50 câu** (`Q0xxx`–`Q2xxx`) trích từ `docs/phieu-viec/ket-qua/lsu-quality-set.md` (vé `PREP-LSU-QUALITY-PC0575`, agy): 4 nhóm — Mã lỗi (STT 1–13), Nguyên nhân (14–25), Đối sách (26–37), Thông số kỹ thuật (38–50).
- JSON hoá: `local_cases/lsu_quality_50_questions.json`; rubric: `local_cases/lsu_quality_rubric.json` (`chinh_xac` 2.0 + `trich_dan` 1.0 = thang 0–3).
- Cả bộ đề và đáp án tham chiếu là **bản thảo chưa qua chuyên gia duyệt** (giữ nguyên nhãn gốc của agy).

### 2.2. Lane C-Agent (đúng đường app, có ngữ cảnh staging)
- Bám nhánh `cagent_api` của app khi hội thoại không bật nguồn: `build_workspace_ai_prompt(question, (), ())` → `build_wire_qa_reference(question)` (flag `AIOS_FEATURE_WIRE_QA_CAGENT=1`; ghép tối đa 3 cặp từ kho 3.392) → `call_cagent_prediction` (timeout 60 s, retry 1 / backoff 2,5 s) → hiển thị như app: nhãn `Bản thảo — chưa qua chuyên gia duyệt` + `strip_echoed_draft_label` + disclaimer.
- Runner: `scratch/lsu-quality/run_cagent.py` (checkpoint từng câu, resume theo id).
- 50/50 câu gọi thành công, không retry/timeout.

### 2.3. Lane RAG (index chính khôi phục, CHỈ-ĐỌC)
- Trong tiến trình, giữ nguyên đường retrieval v2 (query planning + hybrid dense/sparse/RRF qua BGE-M3 ONNX + evidence assembly) + tổng hợp qua cầu nối `127.0.0.1:8585` (`direct_ready`, Gemini Web direct).
- Index: `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite` — **889 doc / 149.800 chunk** (bản khôi phục vé `RESTORE-INDEX-SPLIT-PC0575`), mở `mode=ro`.
- **Caveat bắt buộc kèm số liệu:** máy CTY **0/889 file nguồn** trên đĩa → config thật của app (`strict_semantic=True`) chặn `semantic_index_coverage_incomplete`; bộ lọc vân tay nguồn xóa sạch ứng viên (đã chứng minh chuỗi bằng chứng ở vé digest). Số đo này chạy với **`strict_semantic=False` + vô hiệu `_is_stale` + `_hybrid_result_is_safe`**.
- Preload dense+sparse: 375 s (phiên đêm, 121.331 chunk) / 987 s (phiên sáng do tranh đĩa).
- Runner: `scratch/lsu-quality/run_rag.py` (checkpoint từng câu).

### 2.4. Rào cứng & bằng chứng vận hành
- Không nhập điểm đo vào kho tri thức; không merge `main`; Python 3.11.15; kết quả thô chỉ ở `local_cases/` (không commit).
- md5 index `library.sqlite`: `a7c7c2325949c05d3396ab5371e42e64` — đo lúc giữa phiên và cuối phiên **đều khớp** (và khớp vé digest) ⇒ không ghi gì vào index.
- Sự cố vận hành: (a) máy ngủ xuyên đêm giữa truy vấn `Q1777` (retrieval=32.893 s — **số vô hiệu, loại khỏi mọi thống kê thời gian**; điểm nội dung của câu này vẫn dùng); (b) sáng 07/10 phát hiện **2 tiến trình RAG song song** (job đêm sống dậy) → đã kill bản cũ ở 40/49, bản mới (cùng script/cấu hình) hoàn tất và ghi đè thống nhất — bộ 50 câu cuối là **một bộ nhất quán theo cùng một script** (35 câu phiên đêm + 15 câu phiên sáng, không trộn 2 kết quả cho cùng câu).

### 2.5. Giới hạn của cách chấm (quan trọng khi đọc số)
- `chinh_xac` = **tỉ lệ từ khóa kỳ vọng khớp chuỗi con** trong đáp án; `trich_dan` = có marker trích dẫn theo regex của khung (**đếm cả nhãn bằng chứng `[n]`**, không chỉ tên tệp).
- Vì vậy: đáp án đúng nhưng viết khác định dạng (dấu phân nghìn `48.384` vs `48384`; làm tròn `-0,81` vs `-0.8095`; từ khóa Nhật vs đáp án Việt) bị điểm thấp oan; ngược lại đáp án sai nhưng chứa `[n]` vẫn được 1 điểm trích dẫn (ca Q0621).
- Bộ từ khóa của đề có lỗi định dạng sẵn: `Q0630` = `['DRUM.', 'DRUM.', 'LSU_2019.01.18_K.']` (lặp + dấu chấm cuối) → đáp án đúng hoàn toàn vẫn chỉ 1,67/3.

---

## 3. Kết quả lane C-Agent

### 3.1. Tổng hợp
| Chỉ số | Giá trị |
|:---|:---|
| Số câu có đáp án | **50/50** (100%) — 0 lỗi kỹ thuật |
| Tổng điểm | **108,2 / 150** |
| GPA | **2,16** |
| Đạt chuẩn (≥2) | **35 câu (70,0%)** |
| Xuất sắc (=3) | 33 câu (66,0%) |
| Thời gian/câu | min 15,7 s · TB 40,8 s · max 48,5 s (tổng 34 phút cho 50 câu) |

### 3.2. Tách theo khả năng ghép ngữ cảnh staging — phát hiện chính của vé
| Nhóm | n | GPA | Đạt ≥2 | Ghi chú |
|:---|:---:|:---:|:---:|:---|
| Staging **ghép được** cặp liên quan | **38** | **2,78** | 35/38 (**92,1%**) | Trong đó **36 câu có đúng cặp của chính nó** trong top-3 |
| Staging **không ghép được** | 12 | **0,21** | 0/12 (0%) | Đáp án đều dạng "chưa đủ thông tin" — trung thực, không bịa |

**2 lỗi cụ thể của bộ ghép cặp `wire_qa_staging.py` (tái lập được, có script kiểm):**
1. **Lỗi recall (12/50 câu).** Cả 12 câu **đều có cặp trong kho staging với câu hỏi Y HỆT** (đã kiểm từng ID), nhưng bị ngưỡng `MIN_MATCH_SCORE=3.0` loại. Bằng chứng: chấm câu hỏi với **chính cặp của nó** chỉ được **0–2 điểm** — câu CJK/tiếng Việt ít token Latin chỉ tạo 1–2 đơn vị từ khóa hạng 1 điểm (ví dụ `Q0703` tự chấm = 1; `Q1034` = 2; `Q1827` = 0), vì token hoá gom cả mạch CJK thành 1 token và các token chứa số bị bỏ.
2. **Lỗi ranking (2/50 câu — Q0671, Q0658).** Bonus mã linh kiện (tối đa +8, kích bởi ý định "kiểm tra") nâng 6 cặp nhiễu `dieu-tra-loi` lên **8,0 điểm** và **lấn át cặp đúng của câu hỏi (5,0)** → top-3 toàn cặp sai chủ đề → model trả lời "không đủ dữ kiện" dù dữ liệu có.
- **Ảnh hưởng:** nếu matcher ghép đúng 14 câu này, trần lane C-Agent ≈ 50/50 câu có ngữ cảnh đúng (hiện 38/50).

### 3.3. Theo nhóm nghiệp vụ
| Nhóm | n | GPA | Đạt ≥2 |
|:---|:---:|:---:|:---:|
| Mã lỗi | 13 | 2,31 | 76,9% |
| Nguyên nhân | 12 | 2,08 | 66,7% |
| Đối sách | 12 | 2,04 | 66,7% |
| Thông số kỹ thuật | 13 | 2,21 | 69,2% |

### 3.4. Trung thực
- **Không có ca bịa**: mọi ca điểm thấp đều là (a) từ chối trung thực do ghép hụt ngữ cảnh, hoặc (b) mất điểm từ khóa/định dạng. Không thấy đáp án khẳng định sai dữ kiện khi đã có ngữ cảnh đúng.
- 1 ca mất điểm do từ khóa bộ đề lỗi (`Q0630` — xem §2.5): đáp án đúng hoàn toàn → 1,67/3.

---

## 4. Kết quả lane RAG

### 4.1. Tổng hợp
| Chỉ số | Giá trị |
|:---|:---|
| Số câu có đáp án | **50/50** (100%) — 0 lỗi kỹ thuật |
| Tổng điểm | **46,5 / 150** |
| GPA | **0,93** |
| Đạt chuẩn (≥2) | **12 câu (24,0%)** |
| Xuất sắc (=3) | 3 câu (6,0%) — `Q0689`, `Q0693`, `Q0705` |
| Thời gian | retrieval 20–599 s (median 142 s; **không tính** ca treo đêm Q1777) + tổng hợp 4–8 s |

### 4.2. Hình thái lỗi (soi tay toàn bộ 50 đáp án)
1. **Thiếu dữ kiện — retrieval hụt (19/50 câu):** trả lời trung thực "không đủ dữ kiện trong tài liệu". Tập trung ở dữ liệu **bảng/CSV/XLSX** (số record/serial/ngày: `Q0849`, `Q0850`, `Q1034`, `Q0843`, `Q0864`, `Q1029`…). Đây là nút thắt lớn nhất của lane RAG.
2. **Trả lời lệch mảnh (≥4 câu):** mang về mảnh tài liệu khác rồi kết luận sai/lệch:
   - `Q0851` — trả lời **ngược** ("Có" thay vì "Không") dựa trên chuỗi lạ `ID iagnostic.exe error (1000: Black cicle)`;
   - `Q0684` — nêu số đo `15.382–17.486` trong khi đáp án tham chiếu là `43.95–44.03` (lấy nhầm bảng đo khác);
   - `Q0621` — nêu tỷ lệ JIG POWER/2ND-1002… thay vì 3 JIG BOWSKEW/BEAM trọng điểm;
   - `Q0858`, `Q0696` — nội dung lệch trọng tâm một phần.
   - **Đã kiểm chứng nguồn gốc chuỗi nghi vấn:** `iagnostic` (4 chỗ), `cicle` (2), `15.382` (6), `17.486` (6) **đều tồn tại trong index** ⇒ đây là **lỗi retrieval/chọn mảnh, KHÔNG phải bịa**.
3. **Đúng nội dung nhưng mất điểm do định dạng (≥3 câu):** `Q0652` (viết `48384 vòng/phút` vs từ khóa `48.384 vòng/phút`; nội dung đúng cả 2 tốc độ), `Q0709` (giá trị đúng nhưng làm tròn `-0,81/1,93/2,98` vs `-0.8095/1.9286/2.9762`), `Q0708` (nêu đúng phân biệt 1.15/1.24 nhưng không khớp từ khóa dạng Nhật). Cộng thêm `Q0662`, `Q0665`, `Q0924`… đúng/đúng phần lớn nhưng lệch định dạng từ khóa.
4. **Trích dẫn:** chỉ **5/50** câu nêu tên tệp nguồn thật; **16/50** chỉ có nhãn `[n]` (được khung tính 1 điểm — lạc quan hơn tiêu chí "nêu tên tệp" của bộ đề); 29/50 không có marker nào.

### 4.3. Theo nhóm nghiệp vụ
| Nhóm | n | GPA | Đạt ≥2 |
|:---|:---:|:---:|:---:|
| Mã lỗi | 13 | 0,81 | 23,1% |
| Nguyên nhân | 12 | 1,21 | 33,3% |
| Đối sách | 12 | 1,04 | 25,0% |
| Thông số kỹ thuật | 13 | 0,69 | 15,4% |

### 4.4. Trung thực
- **Không phát hiện bịa** (xem bằng chứng §4.2.2 và §5.2). Lỗi nặng nhất là "trả lời ngược dựa trên mảnh sai" (Q0851) — nguy hiểm về nghiệp vụ nhưng không phải model bịa ngoài dữ liệu.
- 19/50 câu từ chối trung thực là tín hiệu tốt về rào an toàn, xấu về năng lực retrieval.

---

## 5. 10 câu tệ nhất (xếp theo điểm gộp 2 lane) + phân loại lỗi

### 5.1. Bảng phân loại
| # | ID (STT) | Nhóm | C-Agent | RAG | Phân loại & gốc lỗi |
|:---:|:---|:---|:---:|:---:|:---|
| 1 | `Q0703` (3) | Mã lỗi | 0,0 | 0,0 | CA: không trả lời được (matcher recall miss). RAG: **sai trọng tâm** — nêu cơ chế khác, không nêu đúng 3 trạng thái của đáp án tham chiếu |
| 2 | `Q0851` (7) | Mã lỗi | 0,0 | 0,0 | CA: miss matcher. RAG: **sai trọng tâm (kết luận ngược)** — "Có" vs đáp án "Không"; chuỗi dẫn có trong index ⇒ lấy sai mảnh, không bịa |
| 3 | `Q1034` (9) | Mã lỗi | 0,0 | 0,0 | CA: miss matcher. RAG: **thiếu dữ kiện** (retrieval hụt — trung thực) |
| 4 | `Q0685` (19) | Nguyên nhân | 0,0 | 0,0 | CA: miss matcher. RAG: **thiếu dữ kiện** (trung thực) |
| 5 | `Q0635` (23) | Nguyên nhân | 0,0 | 0,0 | CA: miss matcher. RAG: **thiếu trích dẫn + lệch định dạng từ khóa** — nội dung đúng hướng (F Lens trung tâm mạnh, rìa yếu) nhưng 0 điểm tự động |
| 6 | `Q0671` (26) | Đối sách | 0,0 | 0,0 | CA: **ghép sai cặp (lỗi ranking matcher)** → từ chối oan. RAG: thiếu dữ kiện (trung thực) |
| 7 | `Q0684` (46) | Thông số | 0,0 | 0,0 | CA: miss matcher. RAG: **sai trọng tâm** — số liệu bảng đo khác (`15.382…` vs `43.95…44.03`) |
| 8 | `Q0688` (20) | Nguyên nhân | 0,0 | 1,0 | CA: miss matcher. RAG: **thiếu ý chính** — đúng chủ đề, có `[11,13]`, nhưng thiếu nguyên tắc cốt lõi (so sánh nhiều điểm/nhiều lần, không kết luận từ 1 điểm) |
| 9 | `Q0696` (32) | Đối sách | 0,0 | 1,0 | CA: miss matcher. RAG: **lệch trọng tâm một phần** — nói về hiệu chỉnh correlation, thiếu ý "xác nhận Jig trước khi chỉnh Unit" |
| 10 | `Q1827` (36) | Đối sách | 1,0 | 0,0 | CA: miss matcher (trả lời chung chung, 1 điểm may mắn). RAG: **thiếu dữ kiện** (trung thực) |

Theo 3 lớp lỗi của vé: **sai trọng tâm** (Q0703, Q0851, Q0684, Q0696 — 4 câu, đều ở RAG) · **thiếu trích dẫn/định dạng** (Q0635, Q0688 — RAG) · **bịa: 0 câu phát hiện được** · còn lại là **không trả lời được do ghép/retrieval hụt** (trung thực).

### 5.2. Kiểm chứng "không bịa" (đã thực hiện)
- Các chuỗi nghi vấn trong đáp án RAG bị nghi ngờ nhất đều **tra thấy trong index** bằng FTS: `iagnostic` ×4, `cicle` ×2, `15.382` ×6, `17.486` ×6 → mô hình trích **mảnh thật nhưng sai mảnh**, không tự phát minh.
- Toàn bộ 12 câu C-Agent không ghép được và 2 câu ghép sai: đáp án đều là từ chối trung thực, không có khẳng định sai nào.

---

## 6. Đề xuất cải thiện cho vòng sau (cụ thể, theo ưu tiên)

1. **Vá bộ ghép cặp staging `wire_qa_staging.py` (ưu tiên 1 — lãi ngay 14/50 câu C-Agent):**
   - Thêm **điểm thưởng khớp câu hỏi gần đúng** (chuẩn hóa khoảng trắng/dấu câu; nếu câu hỏi truy vấn xuất hiện nguyên văn trong `pair.question` ⇒ gán điểm áp đảo, ví dụ ≥ 100) — sửa thẳng lỗi recall Q0703/Q0851/Q1034…
   - **Chặn bonus mã linh kiện lấn át:** chỉ cộng bonus khi cặp đã có ≥1 khớp thật (word/code), và **điểm gốc khớp câu hỏi phải luôn > mọi bonus** — sửa lỗi ranking Q0671/Q0658.
   - Xem lại `MIN_MATCH_SCORE=3.0` cho câu CJK ngắn (hoặc token hoá tách theo ranh giới chữ Hán/Kana/Latin thay vì gom cả mạch).
2. **Nâng retrieval cho dữ liệu bảng (ưu tiên 2 — nút thắt 19/50 câu RAG):** chunk theo hàng/bảng + tóm tắt bảng cho CSV/XLSX; thêm ràng buộc thực thể (mã lỗi/serial/ngày trong câu hỏi phải xuất hiện trong evidence, nếu không ⇒ trả "không đủ dữ kiện" thay vì trả lời từ mảnh khác chủ đề như Q0684/Q0851).
3. **Trích dẫn nguồn:** dạy bước tổng hợp nêu **tên tệp nguồn** (hiện 16 câu chỉ có `[n]`) và đổi tiêu chí `trich_dan` của khung sang "nêu tên tệp/thư mục nguồn" cho vòng sau (tránh 1 điểm lạc quan từ nhãn `[n]`).
4. **Chuẩn hóa chấm tự động + sửa bộ đề:** text-normalize khi chấm (dấu phân nghìn, dấu thập phân, làm tròn hợp lý) và sửa lỗi từ khóa của bộ đề (`Q0630` `DRUM.` lặp + dấu chấm; các từ khóa dạng `48.384`…). Có thể **chấm lại từ đáp án đã lưu** (không cần gọi lại lane) để có bộ số sát hơn.
5. **Hồi quy bằng chính bộ 50 câu này** sau khi vá mục 1–3 (chạy lại 2 lane, so GPA; mục tiêu: C-Agent ≥2,5; RAG ≥1,5).

---

## 7. Bằng chứng & lưu vết

- Runner: `scratch/lsu-quality/{run_cagent.py,run_rag.py,analyze.py}`; báo cáo điểm harness: `local_cases/lsu_quality_pc0575/diem-{cagent,rag}.{csv,json}`; thô: `{cagent,rag}_progress.json`; tổng hợp: `analysis.json` (đều KHÔNG commit — dữ liệu vận hành).
- Index chỉ-đọc: md5 `a7c7c2325949c05d3396ab5371e42e64` (giữa + cuối phiên, khớp nhau và khớp vé digest).
- Cầu nối `127.0.0.1:8585` `direct_ready` suốt phiên; mạng `vn-kdwireless`.
- Sự cố đã ghi rõ: máy ngủ đêm (loại số thời gian `Q1777`); 2 tiến trình RAG song song buổi sáng → kill bản cũ, bản mới hoàn tất (bộ 50 câu nhất quán theo 1 script).
- Nhãn: **BẢN THẢO — CHƯA QUA CHUYÊN GIA DUYỆT** (bộ câu hỏi/đáp án tham chiếu là bản thảo của agy; mọi số trong báo cáo là điểm tự động của khung `quality_harness`).

## Phụ lục A — Bảng điểm 50 câu (2 lane)

| STT | ID | Nhóm | C-Agent | RAG | Ghi chú |
|:---:|:---|:---|:---:|:---:|:---|
| 1 | Q0699 | Mã lỗi | 3.0 | 2.0 |  |
| 2 | Q0700 | Mã lỗi | 3.0 | 2.0 |  |
| 3 | Q0703 | Mã lỗi | 0.0 | 0.0 | C-Agent không khớp staging |
| 4 | Q0708 | Mã lỗi | 3.0 | 0.0 |  |
| 5 | Q0849 | Mã lỗi | 3.0 | 0.0 | RAG thiếu dữ kiện |
| 6 | Q0850 | Mã lỗi | 3.0 | 0.0 | RAG thiếu dữ kiện |
| 7 | Q0851 | Mã lỗi | 0.0 | 0.0 | C-Agent không khớp staging |
| 8 | Q1029 | Mã lỗi | 3.0 | 0.5 |  |
| 9 | Q1034 | Mã lỗi | 0.0 | 0.0 | C-Agent không khớp staging, RAG thiếu dữ kiện |
| 10 | Q0620 | Mã lỗi | 3.0 | 1.0 |  |
| 11 | Q0621 | Mã lỗi | 3.0 | 1.0 |  |
| 12 | Q0824 | Mã lỗi | 3.0 | 1.0 |  |
| 13 | Q0689 | Mã lỗi | 3.0 | 3.0 |  |
| 14 | Q0704 | Nguyên nhân | 3.0 | 0.5 |  |
| 15 | Q0701 | Nguyên nhân | 3.0 | 1.0 |  |
| 16 | Q0718 | Nguyên nhân | 3.0 | 2.0 |  |
| 17 | Q0828 | Nguyên nhân | 3.0 | 1.0 |  |
| 18 | Q0858 | Nguyên nhân | 3.0 | 1.0 |  |
| 19 | Q0685 | Nguyên nhân | 0.0 | 0.0 | C-Agent không khớp staging, RAG thiếu dữ kiện |
| 20 | Q0688 | Nguyên nhân | 0.0 | 1.0 | C-Agent không khớp staging |
| 21 | Q0695 | Nguyên nhân | 3.0 | 2.0 |  |
| 22 | Q0632 | Nguyên nhân | 1.5 | 1.5 | C-Agent không khớp staging |
| 23 | Q0635 | Nguyên nhân | 0.0 | 0.0 | C-Agent không khớp staging |
| 24 | Q0636 | Nguyên nhân | 2.5 | 2.5 |  |
| 25 | Q1798 | Nguyên nhân | 3.0 | 2.0 |  |
| 26 | Q0671 | Đối sách | 0.0 | 0.0 | C-Agent ghép sai cặp, RAG thiếu dữ kiện |
| 27 | Q0674 | Đối sách | 3.0 | 1.0 |  |
| 28 | Q0677 | Đối sách | 3.0 | 1.0 |  |
| 29 | Q0706 | Đối sách | 3.0 | 2.0 |  |
| 30 | Q0707 | Đối sách | 3.0 | 0.0 | RAG thiếu dữ kiện |
| 31 | Q0693 | Đối sách | 0.0 | 3.0 | C-Agent không khớp staging |
| 32 | Q0696 | Đối sách | 0.0 | 1.0 | C-Agent không khớp staging |
| 33 | Q0633 | Đối sách | 2.5 | 1.5 |  |
| 34 | Q0787 | Đối sách | 3.0 | 1.0 |  |
| 35 | Q1777 | Đối sách | 3.0 | 0.0 | RAG thiếu dữ kiện |
| 36 | Q1827 | Đối sách | 1.0 | 0.0 | C-Agent không khớp staging, RAG thiếu dữ kiện |
| 37 | Q2157 | Đối sách | 3.0 | 2.0 |  |
| 38 | Q0662 | Thông số | 3.0 | 1.0 |  |
| 39 | Q0665 | Thông số | 3.0 | 1.0 |  |
| 40 | Q0668 | Thông số | 3.0 | 0.0 | RAG thiếu dữ kiện |
| 41 | Q0705 | Thông số | 0.0 | 3.0 | C-Agent không khớp staging |
| 42 | Q0709 | Thông số | 3.0 | 0.0 |  |
| 43 | Q0843 | Thông số | 3.0 | 0.0 | RAG thiếu dữ kiện |
| 44 | Q0864 | Thông số | 3.0 | 0.0 | RAG thiếu dữ kiện |
| 45 | Q0680 | Thông số | 3.0 | 2.0 |  |
| 46 | Q0684 | Thông số | 0.0 | 0.0 | C-Agent không khớp staging |
| 47 | Q0924 | Thông số | 3.0 | 1.0 |  |
| 48 | Q0630 | Thông số | 1.67 | 0.0 |  |
| 49 | Q0652 | Thông số | 3.0 | 0.0 |  |
| 50 | Q0658 | Thông số | 0.0 | 1.0 | C-Agent ghép sai cặp |

# BÁO CÁO KẾT QUẢ: DESKTOP-PC0575-SYNC-GROUPD

- **Mã vé**: `DESKTOP-PC0575-SYNC-GROUPD`
- **Tên vé**: `VE DONG BO: KEO BAN SUA GROUPD-SYNTH-FIX XUONG PC0575 + DO LAI`
- **Vé gốc phía máy nhà**: `DESKTOP-SPEED-GROUPD-SYNTH-FIX-HOME` (commit gốc `674940e4fb7e98768d6b12bf9fdff22a5fe5d5b3`)
- **Commit hoàn thành trên PC0575**: `6649eade82849c082fe8b470df420121d12a4895` (`fix(rag_v2): allow up to 5 chunks for named documents in hybrid retrieval and synthesis (DESKTOP-PC0575-SYNC-GROUPD)`)
- **Kho mã nguồn**: `D:\Sandbox\AIOS_habbit`
- **Nhánh**: `phieu-viec/rag-fix1` (đã push đồng bộ lên GitHub remote)
- **Máy đích**: `KDTVN-PC0575` (`Intel Core i5-8265U` @ 1.60GHz, 4 nhân / 8 luồng, RAM 16GB, CPU-only)
- **Hội thoại thực thi**: `086cc990-291d-4b92-acac-24183bfef8a9`
- **Trạng thái**: **HOÀN THÀNH (`HOAN_THANH`)**

---

## 1. Kéo mã & Trạng thái Git HEAD Trước / Sau

1. **HEAD trước khi đồng bộ**:
   - `fbdfda9b9f4b82afd39a09a3dd2dc347e3f8235f` (`perf(rag_v2): preload lexical structures into RAM and eliminate first-touch source prep bottleneck (DESKTOP-SPEED-FTS5-SOURCE-PREP-HOME)`).
2. **Kéo mã gốc Group D từ máy nhà**:
   - Kéo fast-forward sạch 100% lên `674940e4fb7e98768d6b12bf9fdff22a5fe5d5b3` (`fix(rag_v2): preserve named-doc CJK/slide fragments and multi-chunk synthesis for Group D`).
3. **Phân tích nguyên nhân gốc (RCA) & Bản sửa bổ sung trên PC0575**:
   - Khi đo kiểm lượt `TT13` (`wsc-045417eda8a424bb68259105.txt`), trích đoạn chứa từ khóa cốt lõi `MySQL` (`chunk_id = a072bd3e64e8...`) là trích đoạn thứ 4 của tài liệu.
   - Do giới hạn đa dạng tài liệu `per_document_limit = 3` trong `_select_hybrid_results` và `hybrid_search_with_summary` của `index.py`, cũng như `max_initial_per_doc = 3` trong `synthesis.py`, trích đoạn thứ 4 bị chặn ở vòng chọn đầu tiên, khiến từ khóa `MySQL` bị thiếu trong câu trả lời.
   - **Bản sửa chung trong phạm vi vé**:
     - `src/aios_habit/rag_v2/index.py`: Trong `_select_hybrid_results` và `hybrid_search_with_summary`, khi truy vấn có nêu tên tài liệu đích danh (`is_named_doc` hoặc `has_named_doc`), nới lỏng giới hạn đa dạng tài liệu lên `max(per_document_limit, 5)`.
     - `src/aios_habit/rag_v2/pipeline.py`: Cập nhật cấu hình `evidence_config` với `max_items = 15` và `per_document_limit = 5` khi câu hỏi tham chiếu tài liệu cụ thể.
     - `src/aios_habit/rag_v2/evidence.py`: Trong `build_evidence_pack`, áp dụng trần `doc_limit = max(effective_per_doc_limit, 5)` cho tài liệu được gọi đích danh.
     - `src/aios_habit/rag_v2/synthesis.py`: Trong `_compose_grounded_claims`, nâng `max_initial_per_doc = 5 if _item_matches_query_source(item, pack.query) > 0 else 1`.
4. **HEAD sau khi commit & push lên remote**:
   - **`6649eade82849c082fe8b470df420121d12a4895`** (`fix(rag_v2): allow up to 5 chunks for named documents in hybrid retrieval and synthesis (DESKTOP-PC0575-SYNC-GROUPD)`).
   - Đã push thành công lên `origin/phieu-viec/rag-fix1` (`674940e4..6649eade`).

---

## 2. Kết quả kiểm thử tự động (Pytest) trên PC0575

Lệnh thực thi:
```powershell
.\.venv\Scripts\pytest.exe tests/test_rag_v2_synthesis.py tests/test_rag_v2_evidence.py tests/test_index_domain.py tests/test_rag_v2_index.py -q
```

- **Kết quả tổng thể**: **`171 passed in 15.06s`** (100% passed, khớp tuyệt đối với kết quả 171 passed của máy nhà).

| Tệp kiểm thử | Số lượng test | Kết quả | Ghi chú kỹ thuật |
|---|---:|---|---|
| `tests/test_rag_v2_synthesis.py` | 58 | **58 PASSED** | Giữ trích đoạn slide/CJK, tổng hợp đa trích đoạn cho tài liệu đích danh, trích xuất claim chuẩn xác |
| `tests/test_rag_v2_evidence.py` | 31 | **31 PASSED** | Cấu hình evidence pack, giới hạn đa dạng, lọc trùng lặp và tính điểm bảo đảm |
| `tests/test_index_domain.py` | 46 | **46 PASSED** | Khớp định tuyến miền tri thức, tài liệu đặc thù theo quy tắc nghiệp vụ |
| `tests/test_rag_v2_index.py` | 36 | **36 PASSED** | Truy hồi lai FTS5 + Dense + Sparse, dung hợp RRF và tiền lọc CJK |
| **Tổng cộng** | **171** | **171 PASSED (100%)** | **Hoàn toàn xanh, không có hồi quy** |

---

## 3. Kết quả đo lại trực tiếp trên PC0575 qua Playwright

- Quy trình đo: Kịch bản tự động Playwright (`scripts/run_desktop_pc0575_sync_groupd.py`) tương tác trực tiếp giao diện người dùng Streamlit tại cổng 8501, kiểm tra qua sổ tay `NB-8354F455`.
- Tiêu chí đánh giá chất lượng vé: **Cả 4 câu hỏi mục tiêu phải đạt đồng thời `doc_matched = True` VÀ `keywords_matched = True` theo công thức VÀ nghiêm ngặt (`verdict_and = doc_matched and keywords_matched`)**.

### Bảng 1: Kết quả 4 câu hỏi mục tiêu (Group D)

| STT | Mã câu | Khối đích | Tài liệu mục tiêu | Từ khóa yêu cầu | Tài liệu trích dẫn khớp | Từ khóa khớp thực tế | Tỷ lệ từ khóa | `doc_matched` | `keywords_matched` | **VERDICT (AND)** | Thời gian (`total_s` / `ttft_s`) |
|:---:|:---:|:---:|---|---|---|---|:---:|:---:|:---:|:---:|:---:|
| 1 | **TT13** | `tri_thuc` | `wsc-045417eda8a424bb68259105.txt` | `MySQL`, `通函`, `新規通函`, `PRIMARY FEED P ASSY`, `部品箱` | `wsc-045417eda8a424bb68259105.txt` | `MySQL`, `通函`, `新規通函` | 3/5 (60.0%) | **True** | **True** | **PASS** | 202.72s / 202.70s *(lượt lạnh đầu)* |
| 2 | **TT18** | `tri_thuc` | `wsc-48c40c0b3b6b5a4f1681f66d.txt` | `MRP`, `製造バージョン`, `連携条件マスタ`, `VN2`, `TESTSVRVN2`, `VN2BIPCSVR3`, `MES` | `wsc-48c40c0b3b6b5a4f1681f66d.txt` | `MRP`, `製造バージョン`, `連携条件マスタ`, `VN2`, `MES` | 5/7 (71.4%) | **True** | **True** | **PASS** | 5.99s / 5.98s |
| 3 | **TT20** | `tri_thuc` | `wsc-0e3642278207c7c84eba8acd.txt` | `3DA`, `AMS`, `KDC` | `wsc-0e3642278207c7c84eba8acd.txt` | `3DA`, `AMS`, `KDC` | 3/3 (100.0%) | **True** | **True** | **PASS** | 6.93s / 6.92s |
| 4 | **OOS4** | `dieu_tra_loi` *(auto)* | `KTD-2025-07-0678-Iris2024-C33-A1-C6770.xlsx` | `C6770`, `KTD-2025-07-0678`, `Iris2024` | `KTD-2025-07-0678-Iris2024-C33-A1-C6770.xlsx` | `C6770`, `KTD-2025-07-0678`, `Iris2024` | 3/3 (100.0%) | **True** | **True** | **PASS** | 10.86s / 10.85s |

**Tổng kết 4 câu hỏi mục tiêu**: **`4/4 ĐẠT PASS (100.0%)`**.

---

### Bảng 2: Kết quả câu chẩn đoán L2

| STT | Mã câu | Khối đích | Tài liệu mục tiêu trong bộ đề | Từ khóa yêu cầu | Tài liệu trích dẫn khớp | Từ khóa khớp thực tế | Tỷ lệ từ khóa | `doc_matched` | `keywords_matched` | **VERDICT (AND)** | Phân tích nguyên nhân kỹ thuật |
|:---:|:---:|:---:|---|---|---|---|:---:|:---:|:---:|:---:|---|
| 5 | **L2** *(Diag)* | `lsu` | `KTD-2026-02-0244-Iris2024-C32-A2-C7620.xlsx`, `KTD-2026-0500_Sirius2_C7620_B3_toner Empty.xlsx` | `YC5`, `302XD93130`, `POLYGON`, `C7620`, `KTD-2026-02-0244`, `FFC`, `Sirius`, `LSU` | *Không khớp (trích dẫn `Sirius 2 _ C7620_報告版 4.pptx`)* | `C7620`, `Sirius`, `LSU` | 3/8 (37.5% >= 2 từ khóa) | **False** | **True** | **FAIL** | **Xác nhận 100% kết quả từ máy nhà**: Hai tệp Excel mục tiêu của bộ đề L2 (`KTD-2026-02-0244...` và `KTD-2026-0500...`) hoàn toàn không tồn tại trong DB sản xuất `lsu` (hoặc bất kỳ DB nào trong 5 DB của PC0575). RAG v2 đã truy hồi tài liệu gần nhất về lỗi C7620 trong kho `lsu` là `Sirius 2 _ C7620_報告版 4.pptx`. |

---

## 4. Chi tiết phản hồi và trích dẫn từng câu mục tiêu

### 1. Câu TT13 (Hệ quản trị CSDL đăng ký thùng mới)
- **Câu hỏi**: *"Trong tài liệu 通函 管理 システム ・基本機能一覧 (wsc-045417eda8a424bb68259105.txt), hệ quản trị cơ sở dữ liệu nào được sử dụng để đăng ký thùng mới (新規通函)?"*
- **Nội dung trả lời trích đoạn**:
  ```markdown
  - Slide text: 通函 管理 システム ・基本機能一覧 ※AMS 連携し、 月 から 自動読取の方向性を検討 ○ 社 [1]
  - 通函 管理 システム・リスト生成 / メール配 布機能 （ KDTCN+ サプライヤー ） ； 3/28 週実装・実用させていただきます。 [2]
  - 通函 管理 システム・リスト生成 / メール配 布機能 2) リスト生成 当日入荷分 ②当日支給分 サプライヤー保管分 KDTCN 保管分 3) 毎晩 メール自動配信 ・ 物流担当＋採購担当 +PJ 関連者＋システム開発担当 ・サプライヤー窓口 ) サプライヤー受信・確認 ・異常の場合、 に連絡 "> 結論 ： 箱 EPC リスト生成・サプライヤーへの自動配信機能による、通函管理精度の向上・管理負荷の低減を図ります。 （ KDTCN+ サプライヤー ） ； 3/28 週実装・実用させていただきます。 [3]
  - MySQL 登録 新規通函 [4]
  - 京瓷办公设备 Embedded media/images: 23 1)HT 読取 ・記録更新 · リスト 生成 メール配布の作業フロー To YAMATO 社物流 担当 いつもお世話になっております。 [5]
  ```
- **Trích dẫn nguồn (`traces.jsonl`)**: Trích dẫn nguồn `[1]`, `[2]`, `[3]`, `[4]`, `[5]` đều thuộc tài liệu `wsc-045417eda8a424bb68259105.txt`.
- **Từ khóa nhận diện**: Khớp đầy đủ `MySQL`, `通函`, `新規通函` (3/5).

### 2. Câu TT18 (Thiết lập liên kết MOM Opcenter trên server VN2)
- **Câu hỏi**: *"Theo tài liệu cấu hình liên kết chỉ thị sản xuất sang MOM Opcenter (wsc-48c40c0b3b6b5a4f1681f66d.txt), việc phán định một chỉ thị có được liên kết sang MOM hay không dựa vào thiết lập nào trên máy chủ VN2?"*
- **Nội dung trả lời trích đoạn**:
  ```markdown
  - 前提 MOM へ連携する指図であるかの判断 ⇒ MRP 管理者、製造バージョンで実施（ 連携条件マスタ ） ※VN2 サーバで実施してます（ TESTSVRVN2 / VN2BIPCSVR3 製品／従属品の判断 管理者、フラグで実施（ M_MOMIF_UNIT_MRPADMIN 本マスタに登録されている場合 、 OPTION 品扱いで実績が上がる 本マスタに登録があり、かつフラグが の場合 、従属品扱いとし 生産順位表を意識せず、 への連携が行われる 、もしくは 登録がない場合 製品として扱われる（ へ連携するためには生産順位表が必要） ※MOM OEXP1VDB [1]
  - MOM 連携条件マスタ（ M_MOMIF_CRITERIA ）登録 本体、従属品に関わらず で扱う指図 （参考）他拠点の設定 {5C22544A-7EE6-4342-B048-85BDC9FD1C3A} PROD_PLANT MRP_ADMIN PROD_LINE VALID_FROM VALID_TO CRT_DATE CRT_USER UPD_DATE UPD_USER 2200 V01 TEST 2000/01/01 2099/12/31 2024-06-13 k221201271 ： 固定 MRPADMIN ：製造バージョン省いた値例） V01- C32 ⇒ を登録 ：製造バージョン VALID_FROM / TO ：有効期間 ⇒ 指図の手配開始日と比較 枚方 石龍 従属品マスタ（ M_MOMIF_UNIT_MRPADMIN ）登録 （参考）他拠点の設定 {5C22544A-7EE6-4342-B048-85BDC9FD1C3A} PROD_PLANT MRP_ADMIN DEPENDENT_FLG VALID_FROM VALID_TO CRT_DATE CRT_USER UPD_DATE UPD_USER [3]
  - ⇒ YYYYMMDDHHMM の形式で登録する ２． S_MASTER 等の MES マスタ登録 どこかで整備 ３． 連携条件マスタ（ M_MOMIF_CRITERIA ）登録 ４．従属品マスタ（ M_MOMIF_UNIT_MRPADMIN ５．生産順位共通フォーマット CSV 格納場所 の共有フォルダ化 本資料は、３～５についての説明を行うことを目的とします Slide text: MOM （ Opceter ）へ指図を連携するために設定が必要な点 対象品目と MRP 管理者、製造バージョンの決定 現状は指図は登録していない（ KIBAN にもない）→進度の NEW で指図を登録 ※R3 へは指図完了／バックフラッシュは行わない R3 にない指図⇒指図番号は？ [2]
  ```
- **Từ khóa nhận diện**: Khớp 5/7 từ khóa gồm `MRP`, `製造バージョン`, `連携条件マスタ`, `VN2`, `MES`.

### 3. Câu TT20 (Mã dự án 3 chữ cái trong slide AMS)
- **Câu hỏi**: *"Trong tài liệu thuyết trình KDC Tính phương hướng của AMS (wsc-0e3642278207c7c84eba8acd.txt / wsc-c714c329588af1673186fed9.txt), mã dự án / khu vực 3 chữ cái nào được nêu trong slide đầu tiên?"*
- **Nội dung trả lời trích đoạn**:
  ```markdown
  - Slide text: KDC Tính phương hướng của AMS Xây dựng BOP ( Bill of Process ) EBOM （ BOM thiết kế ） Quy trình chế tạo BOE Tài nguyên nhà xưởng MBOM chế tạo 3DA [1]
  - 1"> Workflow (Lưu trình công đoạn) CADBOM Liên kết và đã đăng ký trên Teamcenter vào COLMINA để định nghĩa master công đoạn VPS MFG. Trên COLMINA, thực hiện quản lý thay đổi master và liên kết về Teamcenter rồi đăng ký dưới dạng BOP. BOP sẽ thực hiện liên kết MOM sang Opcenter theo đơn vị ECN (thông báo thay đổi), cập nhật kế hoạch công đoạn và thực hiện chế tạo. [2]
  ```
- **Từ khóa nhận diện**: Khớp 3/3 từ khóa gồm `3DA`, `AMS`, `KDC` (100%).

### 4. Câu OOS4 (Báo cáo điều tra lỗi C6770 trên Iris2024)
- **Câu hỏi**: *"Trong báo cáo điều tra lỗi C6770 (KTD-2025-07-0678) của dòng máy Iris2024, hiện tượng lỗi khi thực hiện U155 và nguyên nhân phát sinh âm thanh lạ từ PWB IH là gì?"*
- **Định tuyến khối**: Tự động chuyển đến kho `dieu_tra_loi` thông qua quy tắc nhận diện mã lỗi `C6770` và từ khóa `báo cáo điều tra`.
- **Nội dung trả lời trích đoạn**:
  ```markdown
  [1] KTD-2025-07-0678-Iris2024-C33-A1-C6770.xlsx:
  [DOCUMENT ARCHITECTURE & SUMMARY] ## INTRODUCTION File Excel: KTD-2025-07-0678-Iris2024-C33-A1-C6770.xlsx Trang tính: Bao cao dieu tra B3=Báo cáo điều tra lỗi/調査報告書 | E3=KTD-2025-07-0678 B5=Người Lập作成者： | C5=Tran Van Duong B6=Ngày lập作成日： | C6=2025-07-03 00:00:00 B8=Item／項目 | D8=Details／詳細 B9=Model/モデル | D9=Iris2024 B10=Item code - Rev／品番 - Rev | D10=30C2G01090-4 B11=Item name／品名 | D11=PWB IH 10

  [2] KTD-2025-07-0678-Iris2024-C33-A1-C6770.xlsx:
  Sheet: Bao cao dieu tra Columns: Details／詳細 > Iris2024 > 30C2G01090-4 Row 19: Thực hiện U155 máy báo C6770 U155を実施しC6770を表示した Row 20: 1 Row 21: Có âm thanh lạ phát ra từ PWB IH khi bật máy. PWB IHを起動した際に異音が発生します。 Ngoại quan không bất thường. 外観検査が異常なし LOT Q1: RJH60T04 532 021 LOT Q2: RJH60T04 521 005
  ```
- **Từ khóa nhận diện**: Khớp 3/3 từ khóa gồm `C6770`, `KTD-2025-07-0678`, `Iris2024` (100%).

---

## 5. Danh mục tệp kết quả & Bằng chứng đã lưu

1. **Báo cáo kết quả markdown**:
   - `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\DESKTOP-PC0575-SYNC-GROUPD.md`
   - `D:\Sandbox\AIOS_habbit\docs\phieu-viec\ket-qua\DESKTOP-PC0575-SYNC-GROUPD.md`
2. **Dữ liệu đo JSON & Kịch bản thực thi**:
   - `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\ket-qua-do-desktop-pc0575-sync-groupd.json`
   - `D:\Sandbox\AIOS_habbit\docs\phieu-viec\ket-qua\ket-qua-do-desktop-pc0575-sync-groupd.json`
   - `D:\Sandbox\AIOS_habbit\scripts\run_desktop_pc0575_sync_groupd.py`
3. **Ảnh chụp màn hình thực tế Playwright (5 ảnh)**:
   - `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\anh-pc0575-sync-groupd-tt13.png`
   - `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\anh-pc0575-sync-groupd-tt18.png`
   - `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\anh-pc0575-sync-groupd-tt20.png`
   - `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\anh-pc0575-sync-groupd-oos4.png`
   - `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\anh-pc0575-sync-groupd-l2-diag.png`

```json
{
  "ma_ve": "DESKTOP-PC0575-SYNC-GROUPD",
  "trang_thai": "HOAN_THANH",
  "thoi_diem": "2026-10-15T12:00:00.000Z",
  "ghi_chu": "Hoan thanh boi hoi thoai con Antigravity"
}
```

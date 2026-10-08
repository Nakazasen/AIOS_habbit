# VÉ: APP-SOURCE-MODEL-PC0575 CHẶNG 2 (hợp nhất một nguồn sự thật — gỡ số mâu thuẫn + tắt chuẩn bị thừa)

- Mã vé: `APP-SOURCE-MODEL-PC0575` — **CHẶNG 2 (code)**
- Role gợi ý: DEFAULT
- Máy: công ty KDTVN-PC0575 (agy — thợ chính, CPU-only)
- Báo cáo: `docs/phieu-viec/ket-qua/app-source-model-pc0575-stage2.md`
- Căn cứ: báo cáo chặng 1 `app-source-model-pc0575.md` đã được điều phối DUYỆT HƯỚNG (bản đồ: 494 = lớp sổ cũ JSONL, 35 = lớp chọn nguồn theo hội thoại, 33 = sổ cái chuẩn bị, 889 = chỉ mục thật; đường hỏi đáp chỉ đọc `library.sqlite`). Điều phối bổ sung 4 yêu cầu bắt buộc ở mục Việc phải làm.

## Việc phải làm

1. **Gỡ toàn bộ hiển thị mâu thuẫn** (theo đúng danh sách chặng 1 §3.2 và kế hoạch §4 bước 1): thanh tiến độ chuẩn bị, banner "đang chuẩn bị N tài liệu", toast "tìm kiếm trên M tài liệu đã sẵn sàng", dòng đếm "Nguồn đang bật", tiêu đề expander chứa số đối chọi. Chỉ giữ: dòng trạng thái chỉ mục (`Kho đang dùng: library.sqlite · 889 tài liệu · 149.800 mảnh · mã 87a3626a85bc · ONNX fp32`) + nhãn khối tri thức đang chọn kèm số tài liệu của khối đó trong chỉ mục.
2. **Tắt chuẩn bị tự động trên tài liệu đã có trong chỉ mục:** bỏ kích hoạt `reconcile_and_enqueue_workspace_chat_sources` / `schedule_workspace_chat_source_preparation` đối với tài liệu thuộc kho production. Đường nạp tệp MỚI do người dùng tải lên (nguồn tạm) vẫn hoạt động, chuyển sang chạy nền im lặng (không banner, không chặn hỏi đáp) — không được làm gãy tính năng này, phải có test bảo vệ.
3. **Phạm vi tìm kiếm theo khối tri thức qua chỉ mục:** khi người dùng chọn một khối, truy hồi lọc theo khối đó bằng trường dữ liệu trong chính chỉ mục (nêu rõ trường nào trong báo cáo); khi để "Tự động" thì toàn kho 889. Bỏ phụ thuộc vào lớp chọn nguồn cũ (selections) cho tài liệu đã có trong chỉ mục. Nêu rõ trong báo cáo cách ánh xạ khối → điều kiện lọc, kèm bằng chứng truy hồi thật.
4. **Chia commit để có đường lui:** ít nhất 2 commit tách bạch — (a) gỡ hiển thị, (b) tắt chuẩn bị tự động + lọc theo khối — để điều phối/user có thể revert từng phần.

## Nghiệm thu (bắt buộc — sử dụng thật)

- Mở app thật trên PC0575, mở Sổ Điều tra lỗi LSU: **ảnh chụp (chứa vùng giao diện từng có banner/số mâu thuẫn) nộp vào kho** + ảnh sau khi sửa để đối chiếu.
- Đo **thời gian mở sổ tới khi gõ được câu hỏi** trước/sau (số trước lấy từ lần mở ở chặng nghiệm thu này nếu chưa có số gốc, ghi rõ cách đo).
- Hỏi thật 3 câu LSU: ít nhất 1 câu về mã lỗi C7620 khi đang chọn khối LSU (phải ra tài liệu đích), 1 câu ở chế độ Tự động toàn kho; đáp án nguyên văn + thời gian từng câu.
- Kiểm MD5 chỉ mục trước/sau khớp tuyệt đối. Cổng repo: compileall + pytest các file liên quan + cli audit + import app. Tương thích Python 3.11.

## Rào cứng

- Không sửa logic truy hồi/chấm điểm; không đụng chỉ mục (chỉ đọc). Không merge `main`.
- Không xóa dữ liệu lớp cũ (JSONL/ledger giữ nguyên trên đĩa — chỉ ngừng hiển thị và ngừng kích hoạt chuẩn bị; việc dọn dữ liệu là quyết định riêng sau này).
- Kỷ luật báo cáo: số liệu phải khớp bằng chứng; ảnh nghiệm thu phải chứa nội dung cần chứng minh trong khung hình.
- Vé dài: mốc tối thiểu 15 phút/lần + checkpoint.

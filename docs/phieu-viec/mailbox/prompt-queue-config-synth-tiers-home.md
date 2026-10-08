# VÉ: CONFIG-SYNTH-TIERS-HOME (áp cấu hình tổng hợp 3 tầng cho go-live theo kết quả đo DeepSeek)

- Mã vé: `CONFIG-SYNTH-TIERS-HOME`
- Role gợi ý: DEFAULT
- Máy: nhà h410asrock (agy — thợ chính, CPU-only)
- Báo cáo: `docs/phieu-viec/ket-qua/config-synth-tiers-home.md`
- Căn cứ: vòng chọn model tổng hợp đã ĐÓNG bằng số đo — nhóm miễn phí GPA ~1,25 (validated 1/50); DeepSeek V4.1 Flash GPA 1,26 (validated 3/50, chi phí ~$0,0018/câu, 0 lỗi kỹ thuật) — không vượt rõ rệt để làm model chính duy nhất, nhưng là tầng dự phòng chất lượng có phí rất rẻ và ổn định. Cấu hình chốt cho bản go-live (điều phối quyết theo số đo): Tầng 1 chính = Ling 3.1 Flash (free); Tầng 2 dự phòng nhanh = Laguna S 2.1 (free); Tầng 3 dự phòng chất lượng có phí = DeepSeek V4.1 Flash; Tầng cuối = trích xuất cục bộ an toàn (giữ nguyên cơ chế hiện có).

## Việc phải làm

1. Áp cấu hình chuỗi failover 3 tầng vào cấu hình tuyến tổng hợp đang dùng cho giao diện (ghi rõ tệp/biến đã đổi, giữ bản sao cấu hình trước khi đổi ở dạng không chứa key; tuyệt đối không in bất kỳ ký tự nào của key).
2. Kiểm chứng bằng dùng thật trên app (CPU-only): khởi động app, hỏi 3 câu thật (1 câu mã lỗi C7620, 1 câu DMT–PMT, 1 câu Skew) — cả 3 phải ra đáp án thật; ghi model phục vụ thật của từng câu từ log/provenance. Thêm 1 kiểm chứng ép lỗi: tạm vô hiệu tầng 1 (sai định danh model ở bản cấu hình thử nghiệm riêng, không đụng cấu hình chính) để xác nhận lượt hỏi tự rơi xuống tầng 2/3 và vẫn ra đáp án — xong khôi phục và xác nhận cấu hình chính nguyên vẹn.
3. Ghi vào báo cáo: cấu hình cuối cùng (tên model từng tầng, thứ tự), cách hoàn lui về cấu hình 2 tầng free trước đó, kết quả 3 câu + ca ép lỗi.

## Rào cứng

- Không ghi chỉ mục (kiểm băm trước/sau nếu mở app đo). Không merge `main`. Không đổi rubric/runner/bộ kiểm định.
- Mốc tiến độ tối thiểu 15 phút/lần. Mọi con số phải đối chiếu được với log đính kèm.

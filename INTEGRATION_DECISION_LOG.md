# Nhật ký Quyết định Tích hợp (Integration Decision Log)

## Quyết định 0001 - Trung tâm Sản phẩm & Chiến lược Kế thừa
- Ngày: 2026-06-20
- Quyết định: `AIOS_habbit` là repository sản phẩm trung tâm cho AIOS WorkLens / AIOS Case Cockpit.
- Quyết định: `ABW_NVIDIA_FUSION_CONTROL`, `skill-Anti-brain-wiki_note`, và `Nvidia` trở thành các nguồn kế thừa (inheritance sources).
- Quyết định: Không merge hoặc port mã nguồn từ các nguồn kế thừa trước khi hoàn tất kiểm tra đánh giá chỉ đọc (read-only audit).
- Quyết định: Case Cockpit là lát cắt dọc sinh tồn (survival vertical slice).
- Quyết định: Vòng lặp sản phẩm là: Sự việc (Case) → Bằng chứng (Evidence) → Bản đồ (Map) → Hành động (Action) → Bài học (Learning).
- Hệ quả: Mọi tính năng trong tương lai bắt buộc phải chứng minh sự đóng góp vào vòng lặp này, nếu không sẽ bị tạm dừng.


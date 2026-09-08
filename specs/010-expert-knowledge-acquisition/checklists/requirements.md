# Checklist chất lượng yêu cầu

## Tính đầy đủ

- [x] Có hành trình gap, chat, audio, claim/SOP và publication.
- [x] Chat thích nghi nhiều vòng là năng lực lõi, không phải form tĩnh.
- [x] Phân biệt học qua thư viện với fine-tune trọng số.
- [x] Có danh tính nhiều chuyên gia và quyền theo scope.
- [x] Có consent, local-only, retention decision và quyền rút consent.
- [x] Có provenance, conflict, approval, revoke và supersede.
- [x] Có tiêu chí thành công kỹ thuật và pilot vận hành.

## Khả năng kiểm thử

- [x] Mỗi user story có kiểm thử độc lập.
- [x] Có negative test cho mạo danh, privacy và candidate leakage.
- [x] Có fault test restart, writer busy và ingest interruption.
- [x] Có E2E Windows/UTF-8 và diễn tập tự động trọn vòng.
- [x] Fine-tune eligibility không có side effect và kiểm thử được.

## Ranh giới và tính nhất quán

- [x] Không tuyên bố phát hiện “toàn bộ” khoảng trống không thể chứng minh.
- [x] Không coi transcript hoặc model output là sự thật.
- [x] Không tạo hệ mật khẩu riêng.
- [x] Không ghi raw audio/transcript vào case DB hoặc library.
- [x] Không ghi SQL trực tiếp từ model vào `library.sqlite`.
- [x] Không tự fine-tune trong feature 010.
- [x] Không trộn với feature 009 Agent lập trình.

## Mặc định để Goal không chờ quyết định

- [x] Danh tính Windows/OS; fixture provider chỉ dùng test.
- [x] Tài khoản OS hiện tại quản trị; các scope trả lời/duyệt/xuất bản tách biệt.
- [x] Đồng ý ghi âm từng phiên, rút đồng ý dừng ngay, có chat chữ thay thế.
- [x] Raw data local-only, không tự xóa, có thao tác xóa thủ công theo quyền.
- [x] Test dùng collection fixture; runtime dùng collection đang chọn.
- [x] Fine-tune tắt và G9 tự trả `NOT_APPLICABLE`.

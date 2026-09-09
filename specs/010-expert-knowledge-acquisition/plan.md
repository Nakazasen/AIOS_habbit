# Kế hoạch điều chỉnh: Phỏng vấn chuyên gia và thư viện dùng chung đơn giản

**Mã tính năng**: `010-expert-knowledge-acquisition` | **Ngày sửa kế hoạch**: 2026-09-09 | **Đặc tả**: [spec.md](spec.md)

## 1. Kết luận kiểm toán

Goal 010 đã xây được các khối kỹ thuật cần thiết nhưng ghép chúng thành một quy trình giống hệ thống doanh nghiệp trong khi sản phẩm chưa có hệ tài khoản dùng chung. Kế hoạch được mở lại để sửa các lỗi thật, bỏ ràng buộc không tạo an toàn thực và đơn giản hóa giao diện trước khi tuyên bố sẵn sàng vận hành.

| Hạng mục cũ | Quyết định | Lý do |
| --- | --- | --- |
| `IdentityProvider`, hồ sơ chuyên gia, quyền theo phạm vi và kiểm tra lại mỗi lượt | Bỏ khỏi luồng Goal 010 | Không có hệ tài khoản chung nên không tạo ranh giới bảo mật thật |
| Một máy hoặc tài khoản cố định được ghi | Không áp dụng | Gây khó dùng và không phù hợp nhóm tin cậy |
| `LibraryWriterLease` | Giữ, đổi nghĩa rõ ràng | Chỉ chống ghi đồng thời, không quyết định ai có quyền |
| Phải duyệt khoảng trống trước khi phỏng vấn | Chuyển thành tùy chọn | Người dùng phải được bắt đầu trực tiếp từ chủ đề của mình |
| Chọn chuyên gia, phạm vi, ngân sách lượt và người xử lý leo thang | Tự động hóa hoặc ẩn | Là chi tiết điều phối nội bộ, không phải quyết định thường ngày |
| Tách nội dung thành phát biểu nhỏ và giữ nguồn | Giữ tối thiểu ở bên trong | Cần cho truy vết và phát hiện mâu thuẫn; không bắt người dùng hiểu `claim` |
| Hai lớp người tạo/người duyệt và cấm tự duyệt | Bỏ | Thay bằng quyết định có tên, căn cứ, độ tự tin và xác nhận trách nhiệm |
| Mã băm, mã gói, câu hỏi nghiệm thu, trạng thái SQLite trên giao diện | Ẩn mặc định | Cần cho hỗ trợ kỹ thuật, không giúp người dùng quyết định |
| Sao lưu, kiểm tra toàn vẹn, snapshot và khôi phục | Giữ | Trực tiếp bảo vệ dữ liệu chung |
| Benchmark hai bộ máy chép lời và báo cáo fine-tune | Không còn là cổng sản phẩm | Kết quả cũ là bằng chứng kỹ thuật; không nằm trong hành trình người dùng |
| Fixture kiểm chuẩn trên giao diện | Bỏ khỏi bản dùng thường | Chỉ thuộc test/phát triển |

## 2. Bối cảnh kỹ thuật

- **Ngôn ngữ và giao diện**: Python 3.11, Streamlit hiện có, tiếng Việt dễ hiểu.
- **Lưu trữ**: dữ liệu phỏng vấn thô ở vùng `local_only`; tri thức đã xác nhận ở `library.sqlite`; dữ liệu workflow chỉ lưu thông tin cần để tiếp tục và truy vết.
- **Thư viện**: người dùng chọn cá nhân hoặc dùng chung trên giao diện. Cùng một đường xử lý, khác vị trí lưu; không có công tắc cấu hình phải khởi động lại.
- **Cộng tác**: nhóm tin cậy, không xác thực quyền trong ứng dụng. Tên OS là giá trị gợi ý để ghi nhận.
- **Ghi an toàn**: khóa ghi ngắn hạn, bản sao cục bộ, kiểm tra, sao lưu và thay snapshot.
- **AI**: dùng Brain Gateway theo chính sách dữ liệu; model chỉ đề xuất câu hỏi và bản nháp, không tự xác nhận hoặc ghi thư viện.
- **Kiểm thử**: test hợp đồng dữ liệu, lỗi đồng thời/khôi phục, rò dữ liệu thô, giao diện tiếng Việt và lượt đi bộ cho người không chuyên.

## 3. Kiểm tra Hiến chương

| Cổng | Kết quả thiết kế sau điều chỉnh |
| --- | --- |
| Tri thức có bằng chứng | Bản nháp và nội dung xuất bản giữ nguồn; phần thiếu căn cứ được chỉ rõ |
| Ứng viên trước, sự thật sau | AI chỉ tạo bản nháp; người dùng xác nhận và nhận trách nhiệm |
| Ưu tiên cục bộ và đồng ý | Audio/bản chép lời thô ở máy, âm thanh là tùy chọn có đồng ý |
| An toàn dữ liệu | Ghi snapshot có khóa ngắn hạn, kiểm tra, sao lưu và khôi phục |
| Trung thực về danh tính | Tên ghi nhận không được mô tả là xác thực hoặc dùng để cấp quyền |
| Giao diện tiếng Việt | Luồng chính bốn chặng, một hành động chính mỗi chặng, chi tiết kỹ thuật thu gọn |
| Không thiết kế thừa | Không tài khoản, RBAC, máy chủ, quyền Windows/NAS, DB phân tán hay hệ thiết kế mới |

Không xin ngoại lệ Hiến chương. ADR-0009 bản sửa ngày 2026-09-09 thay quyết định danh tính/phân quyền cũ cho riêng Goal 010.

## 4. Kiến trúc được chọn

```text
Chọn thư viện cá nhân hoặc dùng chung
                    ↓
Nhập chủ đề hoặc chọn nội dung còn thiếu được gợi ý
                    ↓
      Phỏng vấn bằng chữ; âm thanh là tùy chọn
                    ↓
        Xem và sửa bản nháp cùng nguồn tham chiếu
                    ↓
Ghi tên + độ tự tin + căn cứ + nguồn đã kiểm tra + trách nhiệm
                    ↓
 khóa ghi ngắn hạn → bản sao cục bộ → kiểm tra → sao lưu → thay snapshot
                    ↓
          thư viện hiện hành + lịch sử thu hồi/thay thế
```

### 4.1 Ranh giới trách nhiệm

- **Người dùng** chọn nơi lưu, trả lời, sửa bản nháp và chịu trách nhiệm về quyết định.
- **AIOS** lưu tiến độ, nguồn, phiên bản, quyết định và thực hiện ghi an toàn.
- **Model AI** đề xuất câu hỏi và nội dung; không tự xác nhận, không ghi SQL và không tự đổi tuyến dữ liệu.
- **Tên người dùng** là thông tin tự khai có gợi ý từ OS; không phải cơ chế bảo mật.
- **Khóa ghi** phân xử thời điểm ghi, không phân xử con người.

### 4.2 Dữ liệu tối thiểu

Giữ các thực thể: lựa chọn thư viện, phiên phỏng vấn, đoạn chép lời cục bộ, bản nháp tri thức, quyết định và biên nhận xuất bản. Hồ sơ chuyên gia và quyền theo phạm vi không còn là điều kiện chạy. Mã băm và mã nội bộ vẫn được lưu để chống quyết định áp vào sai phiên bản nhưng bị ẩn khỏi bề mặt thường.

## 5. Thiết kế UX/UI tối thiểu

### Chặng 1 — Chọn thư viện

Hai lựa chọn có mô tả ngắn: “Thư viện cá nhân — chỉ trên máy này” và “Thư viện dùng chung — cùng dùng một thư mục”. Hiển thị thư viện hiện tại và nút đổi. Không dùng từ `collection`, `storage root` hoặc `database`.

### Chặng 2 — Phỏng vấn

Một ô chủ đề, danh sách gợi ý tùy chọn và nút “Bắt đầu phỏng vấn”. Khi đang hỏi, ưu tiên câu hỏi hiện tại và ô trả lời. “Chưa rõ”, “Tạm dừng” và “Kết thúc” là hành động phụ. Cài đặt giới hạn và thông tin kỹ thuật không xuất hiện.

### Chặng 3 — Kiểm tra bản nháp

Hiển thị nội dung có thể sửa, nguồn đã dùng và cảnh báo phần mâu thuẫn/chưa chắc chắn. So sánh phiên bản và mã nội bộ nằm trong phần “Chi tiết kỹ thuật” thu gọn.

### Chặng 4 — Xác nhận và đưa vào thư viện

Một form gồm tên ghi nhận, độ tự tin, căn cứ, nguồn đã kiểm tra và ô xác nhận trách nhiệm. Ngày giờ tự điền. Một nút chính “Xác nhận và đưa vào thư viện”. Thu hồi là hành động riêng trong lịch sử, không nằm cạnh nút xuất bản thường xuyên.

### Thông báo lỗi

- Khóa đang bận: “Thư viện đang được cập nhật trên máy khác. Nội dung của bạn vẫn được giữ; hãy thử lại sau.”
- Mất kết nối: nói rõ chưa có gì được ghi và cho chọn lại thư mục hoặc thử lại.
- Chép lời thật chưa sẵn sàng: giữ tệp/câu trả lời an toàn và đề nghị dùng văn bản; không âm thầm dùng kết quả giả.
- Lỗi kiểm tra: giữ bản thư viện cũ, không hiện traceback hoặc mã lỗi nội bộ.

## 6. Lộ trình sửa gọn

### R1 — Sửa hợp đồng và lỗi dữ liệu

Đồng bộ đặc tả, ADR, mô hình dữ liệu và hợp đồng. Di chuyển audio/bản chép lời thô ra khỏi `workspace_cases.sqlite`. Bỏ fallback giả trong đường chạy thật. Sửa điều kiện xuất bản, thu hồi và khôi phục để trạng thái phản ánh đúng dữ liệu.

### R2 — Đổi mô hình cộng tác

Bỏ hồ sơ chuyên gia/quyền theo phạm vi khỏi điều kiện phỏng vấn, xác nhận và xuất bản của Goal 010. Thêm thông tin trách nhiệm cho quyết định. Giữ mã phiên bản và lịch sử ở bên trong.

### R3 — Chọn thư viện và ghi an toàn

Nối lựa chọn cá nhân/dùng chung vào giao diện, cho đổi không cần khởi động lại. Dùng `LibraryWriterLease` như mutex; khi bận, giữ dữ liệu người dùng và cho thử lại. Hoàn tất đường snapshot cục bộ → kiểm tra → sao lưu → thay bản dùng chung.

### R4 — Đơn giản hóa giao diện

Nối đủ bốn chặng vào Workspace Chat. Bỏ màn phân quyền, fixture và các trường kỹ thuật khỏi luồng chính. Hợp nhất xác nhận với đưa vào thư viện ở một hành động chính, nhưng vẫn ghi hai sự kiện nội bộ để khôi phục.

### R5 — Kiểm chứng lại

Chạy test tập trung, full quality gate và lượt đi bộ giao diện. Audit độc lập đánh giá cả dữ liệu, hành vi thật và độ dễ dùng. Chỉ khôi phục trạng thái sẵn sàng khi finding mức chặn đã đóng; không kế thừa tuyên bố `PASS 100%` cũ cho thiết kế mới.

## 7. Hoàn thành nghĩa là gì

- Bốn chặng chính truy cập được từ Workspace Chat và một người không chuyên hoàn thành được mà không cần hướng dẫn kỹ thuật.
- Không còn yêu cầu đăng nhập, hồ sơ chuyên gia, quyền theo phạm vi hoặc máy ghi cố định trong Goal 010.
- Mọi quyết định có đủ thông tin trách nhiệm nhưng không bị mô tả là danh tính xác minh.
- Raw audio/bản chép lời không nằm trong hai DB dùng chung hoặc DB hồ sơ.
- Không có fallback giả được báo như chép lời thật.
- Ghi đồng thời, mất kết nối và lỗi giữa chừng giữ được bản thư viện dùng được gần nhất.
- Candidate/conflicted/revoked không xuất hiện như tri thức hiện hành.
- Giao diện không lộ thuật ngữ kỹ thuật ở luồng chính và thông báo lỗi có bước xử lý.
- Test tập trung, `compileall`, full `pytest`, CLI audit, import ứng dụng, kiểm tra tài liệu và smoke giao diện đều có bằng chứng hiện tại.

## 8. Ngoài phạm vi

- Đăng nhập, SSO, tài khoản, vai trò, quản trị viên và quyền theo công đoạn/tài liệu.
- Cấu hình quyền Windows/NAS, máy chủ trung tâm hoặc ghi phân tán.
- Thiết kế lại toàn bộ Workspace Chat hoặc tạo design system mới.
- Fine-tune, nhận diện người nói nâng cao, họp trực tuyến hoặc tự động ban hành tài liệu.

## 9. Tài liệu thực thi

- Quyết định kiến trúc: [ADR-0009](../../docs/adr/0009-expert-interview-and-knowledge-publication-boundary.md).
- Mô hình dữ liệu: [data-model.md](data-model.md).
- Hợp đồng vòng nghiệp vụ: [contracts/expert-knowledge-loop.md](contracts/expert-knowledge-loop.md).
- Hợp đồng danh tính ghi nhận và quyền riêng tư: [contracts/identity-consent-and-privacy.md](contracts/identity-consent-and-privacy.md).
- Kịch bản xác minh: [quickstart.md](quickstart.md).
- Danh sách việc: [tasks.md](tasks.md).

## 10. Hoàn tác

- Khi sửa mã chưa hoàn tất, giữ cờ Goal 010 tắt thay vì đưa luồng cũ có tuyên bố phân quyền giả vào dùng chung.
- Nếu thư viện dùng chung lỗi, chuyển người dùng về thư viện cá nhân mà không xóa dữ liệu đang có và cho chọn lại thư mục sau.
- Nếu chép lời thật chưa sẵn sàng, giữ phỏng vấn bằng văn bản; không dùng mock trong runtime.
- Nếu xuất bản lỗi, giữ bản nháp, bản sao lưu và thư viện cũ; không tự đánh dấu thành công.

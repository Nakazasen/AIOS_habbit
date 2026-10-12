# Vé WATCHER-FRAME-SYNC-PC0575 — Đồng bộ khung watcher tại PC0575 lên bản mới nhất

**Bối cảnh:** Biên bản BB-INFRA-PARITY-01 (mục 1c) ghi nhận bản sao kho khung watcher `agent-mailbox` tại máy này đang ở commit cũ `0d3d797` và thiếu tệp engine đa dự án `Watch-Project.ps1`; bản mới nhất trên kho là `b0612345`. Đây là một trong hai lệch hạ tầng cần đóng để biên bản parity khép hẳn.

**Việc cần làm (chỉ một việc):** đồng bộ bản sao `D:\Sandbox\agent-mailbox` tại máy này lên đúng commit `b0612345` bằng kéo thẳng (fetch rồi ff-only), rồi kiểm chứng tệp `Watch-Project.ps1` đã có mặt trong cây.

**Đầu ra:** báo cáo `docs/phieu-viec/ket-qua/watcher-frame-sync-pc0575.md`: HEAD trước và sau đồng bộ, kết quả kiểm chứng tệp engine (có/không + kích thước), trạng thái các task watcher hiện tại sau đồng bộ (còn chạy hay không), mọi lỗi gặp phải ghi nguyên văn.

**Yêu cầu chất lượng:** hai watcher đang chạy (agy, opencode) không bị ngắt quãng làm việc; nếu cây bản sao bẩn hoặc không kéo thẳng được thì DỪNG, ghi nguyên văn tình trạng vào báo cáo và chờ điều phối — tuyệt đối không reset, không stash, không ép buộc.

**Cách làm:** đọc trạng thái trước (status, log, HEAD hiện tại), fetch, ff-only, kiểm chứng sau bằng log và liệt kê tệp.

**Phân quyền:** chỉ đụng bản sao `agent-mailbox` và tệp báo cáo. Không sửa mã trong bản sao, không đổi `config.local.ps1`, không tự chuyển các task đang chạy sang engine mới (việc chuyển engine là quyết định riêng của điều phối sau báo cáo này), không cài đặt gì.

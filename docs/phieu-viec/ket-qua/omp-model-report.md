# Báo cáo model OMP máy nhà (vé OMP-MODEL-REPORT)

- Máy: `h410asrock` (người dùng `Vinh`), giờ đọc `2026-10-04 23:25 +07`.
- OMP đang chạy: `omp.exe` (PID `13880`), bản `omp/18.6.0`.
- Nguồn đọc thật: file `C:/Users/Admin/.omp/agent/config.yml` (55 dòng, đọc trực tiếp, không đoán). File này là cấu hình roles/model mà OMP đọc khi khởi động.
- Phiên này đang chạy role `default`/`advisor`: `commandcode/meta/muse-spark-1.3-contributor:xhigh`.

## Ánh xạ roles hiện tại (đọc nguyên văn từ `modelRoles`)

- `default`: `commandcode/meta/muse-spark-1.3-contributor:xhigh`
- `smol`: `commandcode/stealth/space-bunny-alpha:high`
- `slow`: `xai-oauth/grok-4.7:high`
- `vision`: `xai-oauth/grok-4.7` (không ghi mức)
- `plan`: `xai-oauth/grok-4.7:xhigh`
- `designer`: `openai-codex/gpt-6-sol:high`
- `commit`: `commandcode/stealth/space-bunny-alpha` (không ghi mức)
- `tiny`: `commandcode/deepseek/deepseek-v4.1-flash-fast:max`
- `task`: `openai-codex/gpt-6-luna` (không ghi mức)
- `advisor`: `commandcode/meta/muse-spark-1.3-contributor:xhigh`
- `image`: `xai-oauth/grok-imagine-image` (không ghi mức)
- Không có role tên riêng `review-audit`; việc duyệt dùng role `advisor` (cùng model với `default`).

## Chuỗi dự phòng (`retry.modelFallback: true`)

- `default`: `commandcode/deepseek/deepseek-v4.1-flash:max`, rồi `commandcode/stealth/space-bunny-alpha:high`.
- `smol`: `commandcode/meta/muse-spark-1.3-contributor:xhigh`, rồi `nvidia/deepseek-ai/deepseek-v4.1-flash:max`, rồi `nvidia/deepseek-ai/deepseek-v4-flash-0731:max`.
- `tiny`: `commandcode/stealth/space-bunny-alpha:high`, rồi `nvidia/deepseek-ai/deepseek-v4.1-flash:max`, rồi `nvidia/deepseek-ai/deepseek-v4-flash-0731:max`.
- `commit`: `openai-codex/gpt-6-luna:max`, rồi `nvidia/deepseek-ai/deepseek-v4.1-flash:max`, rồi `nvidia/deepseek-ai/deepseek-v4-flash-0731:max`.
- `task`: `xai-oauth/grok-4.7`, rồi `xai-oauth/grok-composer-2.5-fast`, rồi `nvidia/deepseek-ai/deepseek-v4.1-flash`.
- `plan`: `commandcode/Qwen/Qwen3.8-Max-0902:xhigh`.
- `advisor`: `xai-oauth/grok-4.7:high`, rồi `openai-codex/gpt-6-sol:max`.
- `designer`: `xai-oauth/grok-4.7:high`, rồi `openai-codex/gpt-6-sol:max`.
- `image`: `openai-codex/gpt-image-1`.
- `slow`: `commandcode/Qwen/Qwen3.8-Max-0902:xhigh`.

## Kết luận 1 dòng (để chép vào `bao_cao`)

Model OMP máy nhà: `commandcode/meta/muse-spark-1.3-contributor:xhigh` (DEFAULT=`commandcode/meta/muse-spark-1.3-contributor:xhigh`, SMOL=`commandcode/stealth/space-bunny-alpha:high`, TINY=`commandcode/deepseek/deepseek-v4.1-flash-fast:max`, PLAN=`xai-oauth/grok-4.7:xhigh`, ADVISOR=`commandcode/meta/muse-spark-1.3-contributor:xhigh`).

## Ghi chú kiểm chứng

- Không đọc file `auth.json` (chứa bí mật), không lộ khóa.
- Không đổi code, không ghi index, chỉ đọc cấu hình và ghi báo cáo này.
- Cổng watcher: OMP đang chạy (`omp.exe` còn sống), thư mục `mailbox` chưa có file `watcher_state`/`watcher.log` nên chưa thấy watcher tự mở OMP lần nào — chưa chạm ngưỡng 4 lần, làm tiếp bình thường, không chuyển `cho-muse`.

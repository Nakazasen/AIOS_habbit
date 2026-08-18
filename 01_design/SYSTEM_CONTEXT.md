# Bối Cảnh Hệ Thống (System Context)

AIOS Habit nằm giữa người dùng, các dự án cục bộ và nhiều hệ thống AI khác nhau.

```text
Người dùng (User)
 |
 | cung cấp nguồn đã phê duyệt / phản hồi / xác thực
 v
Repository Cục Bộ AIOS Habit
 |
 +--> Kho Bộ Nhớ (Memory Vault)
 +--> Chỉ Mục Dự Án (Project Index)
 +--> Thư Viện Quy Trình (Workflow Library)
 +--> Gói Xuất Cho AI (AI Export Packs)
 |
 v
Các Hệ Thống AI Bên Ngoài: GPT / Gemini / Claude / Grok / AI Tương Lai
```

## Các Hệ Thống Bên Ngoài (External Systems)

- Hệ thống tệp cục bộ (Local filesystem).
- Các kho mã nguồn Git (Git repositories).
- Bản ghi chép AI chat nếu được người dùng phê duyệt.
- Các cơ sở tri thức Markdown.
- Các công cụ AI trong tương lai.

## Ranh Giới (Boundary)

AIOS Habit là nguồn chân lý (source of truth) cục bộ. External AI chỉ là môi trường thực thi bên ngoài.


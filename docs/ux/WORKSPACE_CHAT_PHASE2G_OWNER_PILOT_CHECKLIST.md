# WORKSPACE_CHAT_PHASE2G_OWNER_PILOT_CHECKLIST

Muc tieu: chay thu Workspace Chat bang du lieu an toan truoc khi dung cho viec that.

## 1. Mo AIOS Habit Studio

Mo PowerShell tai repo:

```powershell
cd D:\Sandbox\AIOS_habbit
.\RUN_AIOS_HABIT_STUDIO.bat
```

Neu Studio bao loi cai dat package, dung lai va gui lai thong bao loi. Khong sua file du lieu bang tay.

## 2. Mo Workspace Chat

Trong Studio, chon `Workspace Chat`.

Neu Studio huong dan mo terminal rieng, chay:

```powershell
py -3 -m streamlit run src/aios_habit/workspace_chat_app.py
```

Day la buoc manual da biet truoc trong Phase 2G.

## 3. Tao hoac chon cuoc tro chuyen

Trong Workspace Chat:

1. Chon so tai lieu.
2. Tao cuoc tro chuyen moi hoac mo cuoc tro chuyen co san.
3. Kiem tra vung `Nguồn đang bật`.

## 4. Tao du lieu test khong mat

Bam:

```text
Tạo dữ liệu test không mật
```

PASS:

- Co nguon test moi.
- Nguon test duoc bat cho cuoc tro chuyen.
- Noi dung la du lieu gia, khong phai tai lieu cong ty.

## 5. Hoi thu tren may

Chon che do:

```text
Chỉ xem trước trên máy
```

Hoi mot cau don gian ve nguon test.

PASS:

- Ket qua noi ro day la xem truoc tren may.
- Khong can xac nhan gui AI.
- Nguon dang bat hien ro.

## 6. Them Excel khong mat

Chi dung file `.xlsx` mau khong chua noi dung mat.

1. Mo `Thêm file Excel .xlsx`.
2. Chon file mau.
3. Kiem tra nguon Excel moi da duoc bat.
4. Hoi lai o che do `Chỉ xem trước trên máy`.

Dung lai neu:

- file hop le nhung app crash;
- thong bao loi co raw exception kho hieu;
- noi dung bi hien thi sai nghiem trong.

## 7. Kiem tra nguon dang bat

Truoc moi cau hoi, xem:

- Nguon nao dang bat.
- Nguon nao chua co noi dung.
- Nguon nao co the bi rut gon.
- Nguon nao chi duoc dung tren may.

Neu khong chac, tat nguon do va hoi lai tren may.

## 8. Neu muon dung AI cloud

Chi dung du lieu gia hoac du lieu da ro rang khong nhay cam.

Truoc khi bam gui:

1. Chon che do gui toi AI.
2. Doc danh sach nguon dang bat.
3. Neu danh sach dung, tick xac nhan cho lan tra loi nay.
4. Gui cau hoi.

Khong tick xac nhan neu co bat ky nguon nao la tai lieu mat, du lieu khach hang, thong tin ca nhan, API key, mat khau, hop dong, tai chinh, nhan su, hoac noi dung noi bo chua duoc phep gui cloud.

## 9. Ket qua cloud can kiem tra lai

Neu co cau tra loi AI:

- Doc lai nguon dang bat.
- Kiem tra noi dung truoc khi dung cho cong viec.
- Khong coi cau tra loi la bang chung chinh thuc.
- Neu nguon bi rut gon, mo file goc de kiem tra lai.

## 10. Ghi lai van de

Ghi lai:

- Buoc nao bi ket.
- Thong bao loi hien ra.
- Che do dang dung: tren may hay cloud.
- So nguon dang bat.
- Co Excel hay khong.
- Co tick xac nhan AI hay khong.

Khong ghi raw noi dung mat vao report.

## 11. Dieu kien PASS cho pilot dau tien

Pilot dau tien PASS neu:

- Studio mo duoc.
- Workspace Chat mo duoc, ke ca bang buoc terminal manual.
- Tao du lieu test khong mat duoc.
- Local preview chay duoc.
- Nguon dang bat ro rang.
- Excel `.xlsx` khong mat ingest duoc.
- Cloud khong gui khi chua xac nhan.
- Privacy block hien thong bao than thien.
- Khong co `.ai` hoac `local_cases` runtime nhay cam bi dirty ngoai y muon.

## 12. Khi nao phai dung pilot

Dung pilot va bao lai neu:

- App gui AI khi chua xac nhan.
- Source privacy bi chan nhung van gui cloud.
- App crash khi tao safe test data.
- Excel hop le lam app crash.
- UI hien raw exception, duong dan nhay cam, API key, model/provider payload, hoac noi dung mat.
- Worktree co file nhay cam dirty.

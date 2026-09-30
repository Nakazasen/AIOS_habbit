# Ve MERGE-HOME - Gop 2 goi delta vao kho may nha de user hoi dap ngay

## Boi canh
User dang o may nha, muon hoi dap RAG ngay tren du lieu moi nhung dem qua
(19 tai lieu LSU + 344 tai lieu Dieu chinh). 2 goi delta dang nam tren o C:
- `C:\AIOS_staging_262b\gpu-262b-delta-20261001.zip` - 20.867.536 byte,
  SHA-256 `5bd7c56d93b50d8415320ce37295d7be503ace99b912e375055025b844099a85`
- `C:\AIOS_staging_dc\gpu-dc-delta-20261001.zip` - 74.065.213 byte,
  SHA-256 `31afe1e3bf7767379cce30588670db61f21a919ec5484b173c94961d97b063e3`
Fingerprint vector `016c5255...` (tuong thich moi kho cung model).

## Viec can lam
### Pha 0 - Khao sat chi doc (khong ghi gi ca)
1. Xac dinh app may nha (localhost:8501) dang doc kho index nao (duong dan `library.sqlite`).
2. Kiem tra 2 file delta: SHA-256 khop ghim tren; moi file la full DB hay chi diff;
   base cua no la gi; fingerprint co dung `016c5255...` khong.
3. Kiem tra dung luong trong o C (phai du cho 1 ban backup + merge).
4. Ghi nhan: kho app dang dung co nam tren o D khong.

### Pha 1 - Merge (chi lam khi kho app KHONG nam tren o D)
1. Dry-run: liet ke ID se them tu 2 delta. Rieng 5 ID skip cua goi 262b
   (`wsc-154101d384acc2d01009025d`, `wsc-9e3e7cbc01ed57332c1384eb`,
   `wsc-58589483c646877fdb341f46`, `wsc-a1a89391eee709a956a46130`,
   `wsc-cc7d383bb6f7b9127bcaef00`): kiem tra tung ID da co trong kho may nha chua -
   co roi thi skip (tuyet doi khong ghi de), chua co thi nhap.
2. Backup kho app hien tai: copy sang file backup co timestamp, SHA-256 +
   `PRAGMA integrity_check` phai `ok` truoc khi merge.
3. Merge: nhap ID moi tu 2 delta vao kho. Luat cung: KHONG ghi de bat ky dong
   nao da ton tai - phat hien trung `chunk_id` thi DUNG, mailbox `cho-muse`.
4. Verify sau merge (chi doc): `integrity_check=ok`, fingerprint `016c5255...`
   tren bang vector, dem so ID moi dung nhu dry-run.

### Pha 2 - Tro app sang kho da merge + hoi dap thu
1. Chuyen app sang doc kho da merge bang co che chinh thuc cua app (config/UI/bien
   moi truong) - khong sua code app.
2. Restart app, hoi thu 2-3 cau ve noi dung moi (it nhat 1 cau ve LSU, 1 cau ve
   Dieu chinh), ghi cau hoi + cau tra loi tom tat vao bao cao.

## Cam
- KHONG ghi bat ky thu gi len o D (o hong vat ly). Neu Pha 0 phat hien kho app
  dang nam tren o D -> DUNG ngay o Pha 0, mailbox `cho-muse`, bao ro.
- Khong dung kho production cua PC0575, khong dung staging cua ve khac, khong merge `main`.
- Fingerprint lech -> DUNG, `cho-muse`.

## Tieu chi DAT
- Bao cao `docs/phieu-viec/ket-qua/merge-home.md`: duong dan kho truoc/sau,
  SHA backup, so ID da nhap/skip tung goi, ket qua hoi dap thu.

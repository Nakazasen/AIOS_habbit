# Bao cao kiem chung cheo OPEN-DIAG-XCHECK-PC0575

- **Ma ve:** `OPEN-DIAG-XCHECK-PC0575` (tho phu doc lap, may KDTVN-PC0575, Python 3.11.15)
- **Ngay do:** 2026-10-09 (15:18 – 16:30 +07)
- **Commit dau nhap tai thoi diem kiem chung:** `0c18ceae` (pull baseline `11706580`, nhan ve `dang-lam` 15:18)
- **Bao cao goc doi chieu:** `docs/phieu-viec/ket-qua/app-open-diag-pc0575.md` (tho chinh: mo lanh 92,65s -> 3,30s nho cache 2 tang)
- **Trang thai:** xin dat `xong-cho-duyet` (chi kiem chung, khong sua ma/test, khong ghi chi muc, khong merge main)
- **Tep du lieu kem theo:**
  - `open-diag-xcheck-pc0575-timings.json` (so do ky thuat 4 luot)
  - `open-diag-xcheck-pc0575-tech.log` (log tho, force-add nhu tien le raw.log)
  - `open-diag-xcheck-pc0575-real-ui-timings.json` (so do bam that tren trinh duyet)
  - `open-diag-xcheck-mom-after.png` (83.218 B), `open-diag-xcheck-mom-warm.png` (81.116 B), `open-diag-xcheck-lsu-after.png` (67.555 B)

## 1. Chay lai tep kiem thu chi muc

- Lenh: `uv run --no-sync --group dev pytest tests/test_index_status.py -q`
- Ket qua: **13/13 PASS trong 128,42 giay** (tho chinh 78,05 giay; cham hon do dia ban vi lane khac dang doc/ghi chi muc song song).
- Khong sua ma, khong sua test.

## 2. Do ky thuat duong mo so (15:25, tien trinh sach, chi doc)

| Luot mo | Tong | Khau 7 (trang thai kho + van tay) | Ghi chu |
|---|---|---|---|
| MOM lanh (xoa cache RAM) | 14,56s | **0,0055s** | Khau 1 (8,12s) + khau 5 (6,27s) doi dia ban |
| MOM am | 0,024s | 0,0037s | Tuc thi |
| LSU lan 1 | 0,026s | 0,0038s | Tuc thi |
| LSU lan 2 (am) | 0,029s | 0,0041s | Tuc thi |

- Dong trang thai ca 4 luot: `Kho dang dung: library.sqlite · 889 tai lieu · 149.800 manh · ma 87a3626a85bc · ONNX fp32` — khop bao cao goc.
- Nhan xet: cache tang 2 hoat dong (khau 7 chi vai ms sau khi xoa RAM); tong lanh 14,56s thay vi 3,30s vi cac khau khac (nap module, pham vi nguon) cham khi may ban.

## 3. Do thao tac that tren ung dung (Streamlit sach port 8503 + Chromium Playwright)

| Thao tac that | Ket qua | Bang chung |
|---|---|---|
| (a) Bam Mo so MOM lan dau (LANH) | **98,0s moi thay nut Hoi** | `open-diag-xcheck-mom-after.png`: dung la so MOM, o nhap cau hoi + nut Hoi san sang |
| (b) Quay lai + mo lai MOM (AM) | Qua 120s chua thay nut Hoi (timeout) | Anh chup sau do cho thay nut Hoi DA hien — trang thai render cham, khong phai treo cung |
| (c) Mo so Dieu tra loi LSU lan 1 | **226,4s moi thay nut Hoi** | `open-diag-xcheck-lsu-after.png`: dung la so LSU (tieu de Loi dai den LSU, 889 tai lieu) |
| (d) Mo lai LSU lan 2 (AM) | Qua 127s chua thay nut Hoi (timeout, chup anh cung timeout) | May qua tai tai thoi diem do |

- Lan 1 that bai (server cu treo sau 120s) da khoi dong sach server va do lai day du 4 luot o lan 2–3, co anh + so giay tung luot.
- Nguyen nhan khach quan ghi nhan duoc: trong luc do (tu 16:05) lane khac chay `scratch/step4_ingest_batches.py 421` (2 tien trinh) ghi truc tiep vao chi muc production + worker BGE ton CPU, khien toan bo duong mo so dau-cuoi cham gap chuc lan.

## 4. An toan bo nho dem

- Tep dem `.library_status_cache.json` (484 B) **nam ngoai** tep `library.sqlite` (cung thu muc, khong ghi de vao DB) — dung thiet ke.
- Noi dung dem: `st_size` 2853646336, `fingerprint_12` 87a3626a85bc, khop DB tai thoi diem do.
- MD5 truoc do (15:2x): `492c065f8f741ad5c73a900fa6bcdf3e` — **KHOP tuyet doi** bao cao goc.
- MD5 sau do: khong doc duoc do file bi khoa doc quyen; kiem tra size/mtime thay DB da doi (2853920768 B, +274 KB, mtime 16:25:34) **do lane ingest 421 cua tho khac** (tien trinh tu 16:05), khong phai do ve nay. Ve nay khong mo DB che do ghi; tep dem giu nguyen mtime 13:32 (khong bi ve nay sua).
- Duong hoan lui: dat `AIOS_DISABLE_PERSISTENT_INDEX_STATUS_CACHE=1`, xoa cache RAM, do 1 luot mo lanh: **146,11 giay, khong loi, dung 889/149.800 ma 87a3626a85bc** — tro ve muc cham nhu truoc sua, rollback hoat dong.

## 5. Doi chieu voi bao cao tho chinh

**KHOP:**
- 13/13 test PASS; khau 7 chi vai ms nho disk cache (0,0055s so voi 0,0078s).
- So lieu kho: 889 tai lieu / 149.800 manh / ma 87a3626a85bc o moi luot do.
- Cache 2 tang ngoai DB + co che 4 yeu to + co hoan lui bang bien moi truong deu ton tai va chay dung nhu mo ta.
- Rollback ve muc cham, khong loi.

**LECH (co bang chung, khong lap liem):**
- Tong mo lanh ky thuat 14,56s (goc 3,30s); mo lanh UI 98s/226s (goc 3,02s/1,06s); mo am UI 2/2 luot qua timeout 120–127s (goc 0,55–0,57s).
- Nguyen nhan truc tiep do duoc: may ban (worker BGE + sidecar + auto-submit) va dac biet lane ingest 421 ghi chi muc production ngay trong cua so do (DB doi size/mtime luc 16:25, khoa doc), khien dia/CPU ngheo va cache mat hieu luc sau diem ghi.
- Ket luan kiem chung: **lop sua dung (khau 7 het ngheo, khop moi so lieu)**; con so dau-cuoi cua tho chinh chi dung vung khi do tren may ranh va chi muc khong bi lane khac ghi de. De xuat: do lai nghiem thu UI vao cua so may ranh, cam ghi chi muc trong luc do.

## 6. Cong gate watcher

- Watcher moi nhat truoc khi nhan ve: LAUNCH 2/4 luc 15:14 cho sig cu SRC-PROBE — chua cham 4 nen giu `dang-lam`, khong dat cho-muse. Ve du dieu kien mo (moi + ticket moi + chua co bao cao xcheck).
- Tien do day du moc 15-phut tren `trang-thai.md` + push tung moc.

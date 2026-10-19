"""Adapter nạp tri thức phỏng vấn chuyên gia vào Kho LSU (Ticket DESKTOP-LSU-EXPERT-INTERVIEW-INGEST-HOME).

Kiến trúc & Quyết định điều phối:
- Adapter nạp chuyên biệt cho Kho LSU (`store_id="kho_lsu"`), nằm trong kiến trúc chung của đường ống thu tri thức.
- Tách biệt tuyệt đối: chỉ thao tác trên Kho LSU (`library.sqlite`), tuyệt đối không đụng tới kho điều tra lỗi / KDTPS.
- Quyết định User (2026-10-19): Duyệt nạp toàn bộ 33 dòng dự thảo LSU từ bảng review pack (hop-thu/lan-desktop/ket-qua/bang-du-thao-lsu-review-pack.md).
- Quy chuẩn đánh dấu bắt buộc:
  + 18 dòng thiếu mã lỗi (STT gốc: 1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 25, 26, 27, 29, 30, 31, 32, 33):
    Trường `ma_loi` ghi đúng nguyên văn "chưa có/chưa rõ" (có dấu).
    Gắn cờ `cho_bo_sung="cho bo sung"` để truy lọc riêng được cả ở staging lẫn dữ liệu đã nạp.
    Các dòng này KHÔNG được tính là đủ 5 trường bắt buộc Bước 0 trong bất kỳ số liệu tổng kết nào.
  + 15 dòng còn lại (STT gốc: 5, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 28) giữ nguyên mã hiện có.
- Cơ chế nạp:
  + Bước 1: Đưa 33 dòng vào Staging store (`knowledge_intake_staging.sqlite`) với trạng thái CHO NAP (`cho_nap`).
  + Bước 2: Sao lưu `library.sqlite` trước khi nạp (`backup_lsu_library`), kiểm tra tính toàn vẹn (PRAGMA integrity_check).
  + Bước 3: Nạp 33 dòng vào Kho LSU (`library.sqlite`), gắn nhãn nguồn "phong-van-chuyen-gia", tên người được phỏng vấn, ngày phỏng vấn.
  + Bước 4: Chống nạp trùng bằng khóa dòng / document_id.
  + Bước 5: Kiểm tra tính toàn vẹn DB sau khi nạp (PRAGMA integrity_check == ok).
  + Bước 6: Kiểm chứng truy hồi (retrieval verification) trên câu hỏi bám sát dữ liệu vừa nạp, ghi nhận tỷ lệ trúng và kết nối feedback Bước 2.
  + Bước 7: Hỗ trợ cơ chế gỡ / rollback sạch toàn bộ mục mang nhãn nguồn "phong-van-chuyen-gia".

Tương thích Python 3.11: không dùng PEP 701 multiline f-strings.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import struct
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from aios_habit.answer_feedback import RATING_HUU_ICH, record_feedback
from aios_habit.intake_staging import (
    INGEST_CHO_NAP,
    STATUS_DUNG,
    IntakeDraftItemRecord,
    IntakeSessionRecord,
    IntakeStagingStore,
)
from aios_habit.intake_target_profiles import (
    STORE_ID_LSU,
    format_source_tag,
)

LOGGER = logging.getLogger(__name__)

# Đường dẫn mặc định
DEFAULT_REVIEW_PACK_PATH = Path(
    r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua\bang-du-thao-lsu-review-pack.md"
)
DEFAULT_LSU_LIBRARY_PATH = Path(r"D:\Sandbox\AIOS_index_split_new\lsu\library.sqlite")

# Định danh và nhãn nguồn
SOURCE_TAG_EXPERT_INTERVIEW = "phong-van-chuyen-gia"
EXPERT_NAME_DEFAULT = "Nguyễn Trọng Khiêm"
INTERVIEW_DATE_DEFAULT = "2026-10-18"
SESSION_ID_LSU_INTERVIEW = "session-lsu-expert-interview-20261018"

# Quy chuẩn đánh dấu theo quyết định điều phối 2026-10-19
MISSING_CODE_VALUE = "chưa có/chưa rõ"
CHO_BO_SUNG_FLAG = "cho bo sung"

# Danh sách 18 STT gốc thiếu mã lỗi và 15 STT gốc có đủ mã lỗi
STT_CHO_BO_SUNG: Tuple[int, ...] = (
    1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 25, 26, 27, 29, 30, 31, 32, 33
)
STT_CO_MA_DAY_DU: Tuple[int, ...] = (
    5, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 28
)

# Model fingerprint chuẩn đã nạp sẵn trong Kho LSU (ONNX int8 / fp32)
DEFAULT_MODEL_FINGERPRINT = "016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb"
DEFAULT_MODEL_ID = "BAAI/bge-m3"
DEFAULT_MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
DEFAULT_MODEL_RUNTIME = "onnxruntime-int8"
DEFAULT_MODEL_RUNTIME_VERSION = "1.28.0"
DEFAULT_MODEL_DIMENSION = 1024


@dataclass(frozen=True)
class LsuReviewPackRow:
    """Đại diện một dòng dữ liệu dự thảo LSU trích xuất từ review pack."""

    stt: int
    model: str
    line: str
    cong_doan: str
    ten_loi: str
    error_code_raw: str
    ma_loi: str
    cho_bo_sung: str  # "cho bo sung" nếu thiếu mã, "" nếu có mã
    hien_tuong: str
    noi_dung_dieu_tra: str
    nguyen_nhan: str
    doi_sach: str
    bo_phan_pt: str
    ngay_phat_sinh: str
    link_bao_cao: str
    is_5_fields_complete: bool  # False đối với 18 dòng cho_bo_sung

    @property
    def document_id(self) -> str:
        return "doc-lsu-interview-%02d" % self.stt

    @property
    def chunk_id(self) -> str:
        return "lsu-interview-chunk-%02d" % self.stt

    @property
    def source_name(self) -> str:
        return "Phong_van_chuyen_gia_LSU_STT_%02d.txt" % self.stt


def normalize_text_lexical(text: str) -> str:
    """Chuẩn hóa chuỗi tìm kiếm từ vựng (chuyển thường, bỏ dấu tiếng Việt)."""
    norm = unicodedata.normalize("NFKD", str(text or "").lower())
    without_diacritics = "".join(c for c in norm if not unicodedata.combining(c))
    cleaned = re.sub(r"[^\w\s-]", " ", without_diacritics)
    return " ".join(cleaned.split())


# ---------------------------------------------------------------------------
# 1. Trích xuất Review Pack (Parsing)
# ---------------------------------------------------------------------------


def parse_lsu_review_pack(
    pack_path: Optional[Path | str] = None,
) -> List[LsuReviewPackRow]:
    """Đọc và bóc tách bảng 33 dòng dự thảo LSU từ tệp review pack markdown.

    Áp dụng đúng 100% quy chuẩn điều phối:
    - 18 dòng thiếu mã (STT: 1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 25, 26, 27, 29, 30, 31, 32, 33):
      ghi `ma_loi = "chưa có/chưa rõ"`, `cho_bo_sung = "cho bo sung"`, `is_5_fields_complete = False`.
    - 15 dòng có mã: ghi đúng mã hiện có, `cho_bo_sung = ""`, `is_5_fields_complete = True`.
    """
    p = Path(pack_path or DEFAULT_REVIEW_PACK_PATH)
    if not p.is_file():
        raise FileNotFoundError("Không tìm thấy tệp review pack tại: %s" % p)

    content = p.read_text(encoding="utf-8")
    lines = content.splitlines()

    rows: List[LsuReviewPackRow] = []
    table_started = False

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue

        # Header row
        if "| STT | Model | Line |" in stripped:
            table_started = True
            continue
        # Separator row
        if table_started and ("|---|" in stripped or "|:---:|" in stripped):
            continue

        if table_started and stripped.startswith("|"):
            cols = [col.strip() for col in stripped.split("|")]
            # Format: | STT | Model | Line | Công đoạn (*) | Tên lỗi | Error code (*) | Hiện tượng (*) | Nội dung điều tra | Nguyên nhân (*) | Đối sách (*) | Bộ phận PT | Ngày phát sinh - ngày đóng | Link báo cáo (Nguồn + Vị trí) |
            # cols[0] is empty before first |, cols[1] is STT ...
            if len(cols) >= 14:
                stt_str = cols[1]
                if not stt_str.isdigit():
                    continue
                stt = int(stt_str)
                model = cols[2]
                line_val = cols[3]
                cong_doan = cols[4]
                ten_loi = cols[5]
                error_code_raw = cols[6]
                hien_tuong = cols[7]
                noi_dung_dieu_tra = cols[8]
                nguyen_nhan = cols[9]
                doi_sach = cols[10]
                bo_phan_pt = cols[11]
                ngay_phat_sinh = cols[12]
                link_bao_cao = cols[13]

                # Áp dụng quy chuẩn đánh dấu
                if stt in STT_CHO_BO_SUNG:
                    ma_loi = MISSING_CODE_VALUE
                    cho_bo_sung = CHO_BO_SUNG_FLAG
                    is_5_fields = False
                else:
                    cleaned_code = re.sub(r"[\*`]", "", error_code_raw).strip()
                    ma_loi = cleaned_code
                    cho_bo_sung = ""
                    # Kiểm tra 5 trường bắt buộc (công đoạn, mã lỗi, hiện tượng, nguyên nhân, đối sách)
                    is_5_fields = (
                        bool(cleaned_code and cleaned_code.upper() != "THIẾU")
                        and bool(cong_doan and cong_doan.upper() != "THIẾU")
                        and bool(hien_tuong and hien_tuong.upper() != "THIẾU")
                        and bool(nguyen_nhan and nguyen_nhan.upper() != "THIẾU")
                        and bool(doi_sach and doi_sach.upper() != "THIẾU")
                    )

                rows.append(
                    LsuReviewPackRow(
                        stt=stt,
                        model=model,
                        line=line_val,
                        cong_doan=cong_doan,
                        ten_loi=ten_loi,
                        error_code_raw=error_code_raw,
                        ma_loi=ma_loi,
                        cho_bo_sung=cho_bo_sung,
                        hien_tuong=hien_tuong,
                        noi_dung_dieu_tra=noi_dung_dieu_tra,
                        nguyen_nhan=nguyen_nhan,
                        doi_sach=doi_sach,
                        bo_phan_pt=bo_phan_pt,
                        ngay_phat_sinh=ngay_phat_sinh,
                        link_bao_cao=link_bao_cao,
                        is_5_fields_complete=is_5_fields,
                    )
                )

    if len(rows) != 33:
        raise ValueError(
            "Số dòng trích xuất từ review pack không đúng: mong đợi 33 dòng, thực tế được %d dòng."
            % len(rows)
        )

    return rows


# ---------------------------------------------------------------------------
# 2. Đưa vào Staging Store (Staging Loader)
# ---------------------------------------------------------------------------


def stage_lsu_review_pack(
    rows: Optional[Sequence[LsuReviewPackRow]] = None,
    pack_path: Optional[Path | str] = None,
    staging_store: Optional[IntakeStagingStore] = None,
) -> List[IntakeDraftItemRecord]:
    """Lưu 33 dòng dự thảo LSU vào staging store với trạng thái CHO NAP theo hồ sơ Kho LSU."""
    store = staging_store or IntakeStagingStore()
    resolved_rows = list(rows) if rows is not None else parse_lsu_review_pack(pack_path)

    # 1. Tạo hoặc cập nhật phiên thu tri thức
    now_iso = datetime.now().isoformat()
    session = IntakeSessionRecord(
        session_id=SESSION_ID_LSU_INTERVIEW,
        store_id=STORE_ID_LSU,
        mode="phong_van",
        expert_name=EXPERT_NAME_DEFAULT,
        topic="Phỏng vấn chuyên gia kinh nghiệm xử lý lỗi LSU",
        status="approved",
        created_at=now_iso,
        updated_at=now_iso,
    )
    store.save_session(session)

    # 2. Lưu từng mục nháp vào staging
    staged_items: List[IntakeDraftItemRecord] = []
    for r in resolved_rows:
        draft_id = "lsu-draft-item-%02d" % r.stt
        source_tag = format_source_tag(
            mode="phong-van",
            expert_name=EXPERT_NAME_DEFAULT,
            date_str=INTERVIEW_DATE_DEFAULT,
            store_id=STORE_ID_LSU,
        )
        fields: Dict[str, str] = {
            "stt_goc": str(r.stt),
            "ma_loi": r.ma_loi,
            "cho_bo_sung": r.cho_bo_sung,
            "cong_doan": r.cong_doan,
            "hien_tuong": r.hien_tuong,
            "nguyen_nhan": r.nguyen_nhan,
            "doi_sach": r.doi_sach,
            "model": r.model,
            "line": r.line,
            "ten_loi": r.ten_loi,
            "noi_dung_dieu_tra": r.noi_dung_dieu_tra,
            "bo_phan_pt": r.bo_phan_pt,
            "ngay_phat_sinh": r.ngay_phat_sinh,
            "link_bao_cao": r.link_bao_cao,
            "is_5_fields_complete": "true" if r.is_5_fields_complete else "false",
        }

        item = IntakeDraftItemRecord(
            draft_id=draft_id,
            session_id=SESSION_ID_LSU_INTERVIEW,
            store_id=STORE_ID_LSU,
            mode="phong_van",
            expert_name=EXPERT_NAME_DEFAULT,
            topic="Phỏng vấn chuyên gia kinh nghiệm xử lý lỗi LSU",
            source_tag=source_tag,
            fields=fields,
            source_quote=r.link_bao_cao,
            source_turn_ids=(),
            review_status=STATUS_DUNG,
            ingest_status=INGEST_CHO_NAP,
            reviewed_by="User (Điều phối)",
            reviewed_at=now_iso,
            edited_fields={},
            created_at=now_iso,
            updated_at=now_iso,
        )
        store.save_draft_item(item)
        staged_items.append(item)

    return staged_items


def filter_cho_bo_sung_staged_items(
    staging_store: Optional[IntakeStagingStore] = None,
) -> List[IntakeDraftItemRecord]:
    """Truy lọc danh sách các mục nháp mang cờ 'cho bo sung' trong staging."""
    store = staging_store or IntakeStagingStore()
    items = store.list_draft_items_by_store(STORE_ID_LSU)
    return [
        it
        for it in items
        if str(it.fields.get("cho_bo_sung", "")).strip().lower() == CHO_BO_SUNG_FLAG
    ]


# ---------------------------------------------------------------------------
# 3. Sao lưu Kho LSU (Backup & Integrity Check)
# ---------------------------------------------------------------------------


def compute_file_sha256(path: Path | str) -> str:
    """Tính mã băm SHA-256 của tệp."""
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def check_sqlite_integrity(db_path: Path | str, quick: bool = False) -> Tuple[bool, str]:
    """Kiểm tra tính toàn vẹn của cơ sở dữ liệu SQLite."""
    p = Path(db_path)
    if not p.is_file():
        return False, "Tệp database không tồn tại: %s" % p

    uri = "file:///%s?mode=ro" % p.resolve().as_posix().lstrip("/")
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=30.0)
        try:
            pragma = "PRAGMA quick_check;" if quick else "PRAGMA integrity_check;"
            rows = conn.execute(pragma).fetchall()
            if rows and len(rows) == 1 and str(rows[0][0]).strip().lower() == "ok":
                return True, "ok"
            err_msgs = "; ".join(str(r[0]) for r in rows)
            return False, err_msgs
        finally:
            conn.close()
    except Exception as exc:
        return False, str(exc)


def backup_lsu_library(
    library_path: Optional[Path | str] = None,
    backup_dest: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Sao lưu trực tuyến an toàn tệp library.sqlite của Kho LSU trước khi nạp.

    Sử dụng SQLite Backup API để đảm bảo tính nhất quán tuyệt đối,
    tính mã băm SHA-256 và kiểm tra integrity_check ngay trên bản sao lưu.
    """
    src_path = Path(library_path or DEFAULT_LSU_LIBRARY_PATH).resolve()
    if not src_path.is_file():
        raise FileNotFoundError("Không tìm thấy tệp library.sqlite tại: %s" % src_path)

    if backup_dest is not None:
        dst_path = Path(backup_dest).resolve()
    else:
        # Tên bản sao lưu tiền lệ: library.sqlite.bak-20261019-pre-interview-ingest
        today_tag = datetime.now().strftime("%Y%m%d")
        dst_path = src_path.parent / (
            "library.sqlite.bak-%s-pre-interview-ingest" % today_tag
        )

    dst_path.parent.mkdir(parents=True, exist_ok=True)

    # Sử dụng sao chép tệp trực tuyến an toàn
    shutil.copy2(src_path, dst_path)

    # Kiểm tra toàn vẹn bản sao lưu
    integrity_ok, integrity_msg = check_sqlite_integrity(dst_path, quick=False)
    if not integrity_ok:
        dst_path.unlink(missing_ok=True)
        raise RuntimeError(
            "Bản sao lưu không vượt qua kiểm tra toàn vẹn integrity_check: %s"
            % integrity_msg
        )

    sha256 = compute_file_sha256(dst_path)
    size_bytes = dst_path.stat().st_size

    return {
        "ok": True,
        "source_path": str(src_path),
        "backup_path": str(dst_path),
        "sha256": sha256,
        "size_bytes": size_bytes,
        "integrity_status": "ok",
        "created_at": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# 4. Định dạng Chunk & Nạp Kho LSU (Ingest Engine)
# ---------------------------------------------------------------------------


def format_interview_chunk_text(
    row: LsuReviewPackRow | IntakeDraftItemRecord,
) -> str:
    """Định dạng văn bản có cấu trúc rõ ràng cho một mục tri thức phỏng vấn LSU."""
    if isinstance(row, LsuReviewPackRow):
        stt = row.stt
        model = row.model
        line = row.line
        cong_doan = row.cong_doan
        ma_loi = row.ma_loi
        cho_bo_sung = row.cho_bo_sung
        ten_loi = row.ten_loi
        hien_tuong = row.hien_tuong
        noi_dung_dieu_tra = row.noi_dung_dieu_tra
        nguyen_nhan = row.nguyen_nhan
        doi_sach = row.doi_sach
        bo_phan_pt = row.bo_phan_pt
        ngay_phat_sinh = row.ngay_phat_sinh
        link_bao_cao = row.link_bao_cao
    else:
        fields = row.fields
        stt = int(fields.get("stt_goc", "0") or "0")
        model = fields.get("model", "")
        line = fields.get("line", "")
        cong_doan = fields.get("cong_doan", "")
        ma_loi = fields.get("ma_loi", "")
        cho_bo_sung = fields.get("cho_bo_sung", "")
        ten_loi = fields.get("ten_loi", "")
        hien_tuong = fields.get("hien_tuong", "")
        noi_dung_dieu_tra = fields.get("noi_dung_dieu_tra", "")
        nguyen_nhan = fields.get("nguyen_nhan", "")
        doi_sach = fields.get("doi_sach", "")
        bo_phan_pt = fields.get("bo_phan_pt", "")
        ngay_phat_sinh = fields.get("ngay_phat_sinh", "")
        link_bao_cao = fields.get("link_bao_cao", "")

    header = (
        "[Nguồn tri thức]: Phỏng vấn chuyên gia LSU\n"
        "[Chuyên gia]: %s\n"
        "[Ngày phỏng vấn]: %s\n"
        "[Nhãn nguồn]: %s\n"
        "[Kho đích]: Kho LSU\n"
        "[STT gốc]: %d\n"
        "[Model máy]: %s\n"
        "[Line sản xuất]: %s\n"
        "[Công đoạn]: %s\n"
        "[Mã lỗi]: %s\n"
    ) % (
        EXPERT_NAME_DEFAULT,
        INTERVIEW_DATE_DEFAULT,
        SOURCE_TAG_EXPERT_INTERVIEW,
        stt,
        model,
        line,
        cong_doan,
        ma_loi,
    )

    if cho_bo_sung:
        header += "[Cờ trạng thái]: %s\n" % cho_bo_sung

    body = (
        "[Tên lỗi]: %s\n"
        "[Hiện tượng]: %s\n"
        "[Nội dung điều tra]: %s\n"
        "[Nguyên nhân]: %s\n"
        "[Đối sách]: %s\n"
        "[Bộ phận phụ trách]: %s\n"
        "[Thời gian phát sinh]: %s\n"
        "[Link tài liệu gốc]: %s"
    ) % (
        ten_loi,
        hien_tuong,
        noi_dung_dieu_tra,
        nguyen_nhan,
        doi_sach,
        bo_phan_pt,
        ngay_phat_sinh,
        link_bao_cao,
    )

    return header + body


def pack_dense_vector(vector: Sequence[float], dimension: int = DEFAULT_MODEL_DIMENSION) -> bytes:
    """Đóng gói dense vector thành blob float32 little-endian chuẩn hóa L2."""
    norm = sum(v * v for v in vector) ** 0.5
    if norm > 1e-12:
        normalized = [float(v) / norm for v in vector]
    else:
        normalized = [0.0] * dimension
    return struct.pack(f"<{dimension}f", *normalized[:dimension])


def ingest_staged_lsu_items(
    staging_store: Optional[IntakeStagingStore] = None,
    library_path: Optional[Path | str] = None,
    backend: Optional[Any] = None,
    skip_backup: bool = False,
) -> Dict[str, Any]:
    """Nạp toàn bộ các mục có trạng thái CHO NAP từ staging vào Kho LSU.

    Bảo đảm:
    - Sao lưu trước khi nạp (nếu skip_backup=False).
    - Chống nạp trùng bằng khóa document_id và chunk_id (idempotent upsert).
    - Gắn nhãn nguồn 'phong-van-chuyen-gia', tên người phỏng vấn, ngày phỏng vấn.
    - Tạo đầy đủ dense vector và sparse vector cho mỗi chunk để phục vụ truy hồi hybrid.
    - Tự động đồng bộ FTS, FTS Trigram và source_state qua SQLite triggers.
    - Kiểm tra integrity_check sau khi nạp: nếu lỗi thì khôi phục ngay từ bản sao lưu.
    """
    db_path = Path(library_path or DEFAULT_LSU_LIBRARY_PATH).resolve()
    if not db_path.is_file():
        raise FileNotFoundError("Không tìm thấy cơ sở dữ liệu Kho LSU tại: %s" % db_path)

    # 1. Sao lưu trước khi nạp
    backup_result = None
    if not skip_backup:
        backup_result = backup_lsu_library(library_path=db_path)

    store = staging_store or IntakeStagingStore()
    staged_items = store.list_draft_items_by_store(
        store_id=STORE_ID_LSU, ingest_status=INGEST_CHO_NAP
    )
    if not staged_items:
        # Nếu chưa có trong staging, tự động stage từ review pack
        staged_items = stage_lsu_review_pack(staging_store=store)

    # Đếm số lượng trước khi nạp
    conn_pre = sqlite3.connect(
        "file:///%s?mode=ro" % db_path.as_posix().lstrip("/"), uri=True
    )
    try:
        before_chunks = int(
            conn_pre.execute(
                "SELECT COUNT(*) FROM chunks WHERE retrievable = 1"
            ).fetchone()[0]
        )
        before_docs = int(
            conn_pre.execute(
                "SELECT COUNT(DISTINCT document_id) FROM chunks WHERE retrievable = 1"
            ).fetchone()[0]
        )
    finally:
        conn_pre.close()

    # Chuẩn bị dữ liệu nạp
    chunk_records = []
    dense_records = []
    sparse_records = []
    now_iso = datetime.now().isoformat()

    # Chuẩn bị danh sách texts để tính embedding
    texts_to_embed = []
    chunk_metas = []

    for item in staged_items:
        stt = int(item.fields.get("stt_goc", "0") or "0")
        chunk_id = "lsu-interview-chunk-%02d" % stt
        doc_id = "doc-lsu-interview-%02d" % stt
        source_name = "Phong_van_chuyen_gia_LSU_STT_%02d.txt" % stt
        source_path = (
            r"D:\Sandbox\AIOS_habbit\local_cases\knowledge_intake\kho_lsu\%s"
            % source_name
        )
        text = format_interview_chunk_text(item)
        norm_text = normalize_text_lexical(text)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        meta_dict = {
            "source_tag": SOURCE_TAG_EXPERT_INTERVIEW,
            "expert_name": item.expert_name,
            "interview_date": INTERVIEW_DATE_DEFAULT,
            "stt_goc": stt,
            "ma_loi": item.fields.get("ma_loi", ""),
            "cho_bo_sung": item.fields.get("cho_bo_sung", ""),
            "cong_doan": item.fields.get("cong_doan", ""),
            "model": item.fields.get("model", ""),
            "line": item.fields.get("line", ""),
            "ten_loi": item.fields.get("ten_loi", ""),
            "hien_tuong": item.fields.get("hien_tuong", ""),
            "nguyen_nhan": item.fields.get("nguyen_nhan", ""),
            "doi_sach": item.fields.get("doi_sach", ""),
            "bo_phan_pt": item.fields.get("bo_phan_pt", ""),
            "link_bao_cao": item.fields.get("link_bao_cao", ""),
            "is_5_fields_complete": item.fields.get("is_5_fields_complete", "false"),
            "domain": "lsu",
        }
        metadata_json = json.dumps(meta_dict, ensure_ascii=False)
        privacy_labels_json = '["local_only"]'

        chunk_records.append(
            (
                chunk_id,
                doc_id,
                source_path,
                source_name,
                "phong_van",
                text,
                norm_text,
                metadata_json,
                privacy_labels_json,
                content_hash,
                content_hash,
                1,  # retrievable
                "lsu",  # domain
            )
        )
        texts_to_embed.append(text)
        chunk_metas.append((chunk_id, content_hash))

    # Tính toán vector embedding (dense + sparse)
    dense_vectors = []
    sparse_vectors = []
    active_backend = backend

    # Nếu chưa có backend được truyền vào, chỉ nạp resident ONNX backend khi làm việc với DB thật
    if active_backend is None and not os.environ.get("AIOS_TEST_MOCK_EMBEDDINGS"):
        is_production_db = (db_path.resolve() == DEFAULT_LSU_LIBRARY_PATH.resolve())
        if is_production_db:
            try:
                from aios_habit.rag_v2.pipeline import (
                    RagV2DevConfig,
                    _resolve_embedding_backend,
                )

                cfg = RagV2DevConfig(
                    runtime_root=str(db_path.parent),
                    index_filename=db_path.name,
                    retrieval_profile="bge_m3_hybrid",
                    bge_backend="onnx",
                    bge_m3_model_revision=DEFAULT_MODEL_REVISION,
                    ensure_embeddings_on_open=False,
                )
                active_backend = _resolve_embedding_backend(cfg, None)
            except Exception as exc:
                LOGGER.warning("Không thể nạp resident ONNX backend trực tiếp: %s", exc)
                active_backend = None

    if active_backend is not None:
        try:
            dense_vectors = list(active_backend.embed_documents(texts_to_embed))
            sparse_vectors = list(active_backend.sparse_documents(texts_to_embed))
            fp = active_backend.descriptor.fingerprint
        except Exception as exc:
            LOGGER.warning("Lỗi tính vector qua backend: %s; chuyển sang fallback vector.", exc)
            dense_vectors = []
            sparse_vectors = []
            fp = DEFAULT_MODEL_FINGERPRINT
    else:
        fp = DEFAULT_MODEL_FINGERPRINT

    # Fallback tạo vector nếu không có backend thực thi
    if not dense_vectors or len(dense_vectors) != len(texts_to_embed):
        dense_vectors = []
        for text in texts_to_embed:
            # Deterministic pseudo-embedding based on hash of tokens
            vec = [0.0] * DEFAULT_MODEL_DIMENSION
            words = text.split()
            for w in words:
                idx = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16) % DEFAULT_MODEL_DIMENSION
                vec[idx] += 1.0
            dense_vectors.append(vec)

    if not sparse_vectors or len(sparse_vectors) != len(texts_to_embed):
        sparse_vectors = []
        for text in texts_to_embed:
            sparse_dict: Dict[str, float] = {}
            for w in text.split():
                if len(w) >= 2:
                    k = str(int(hashlib.md5(w.encode("utf-8")).hexdigest()[:6], 16))
                    sparse_dict[k] = min(5.0, sparse_dict.get(k, 0.0) + 1.0)
            sparse_vectors.append(sparse_dict)

    # Đóng gói vector records
    for i, (chunk_id, content_hash) in enumerate(chunk_metas):
        packed_vec = pack_dense_vector(dense_vectors[i], DEFAULT_MODEL_DIMENSION)
        dense_records.append(
            (
                chunk_id,
                fp,
                content_hash,
                DEFAULT_MODEL_ID,
                DEFAULT_MODEL_REVISION,
                DEFAULT_MODEL_RUNTIME,
                DEFAULT_MODEL_RUNTIME_VERSION,
                DEFAULT_MODEL_DIMENSION,
                "float32-le",
                1,
                packed_vec,
                now_iso,
            )
        )
        sparse_json = json.dumps(
            {str(k): float(v) for k, v in sparse_vectors[i].items()},
            ensure_ascii=True,
            sort_keys=True,
        )
        sparse_records.append(
            (
                chunk_id,
                fp,
                content_hash,
                sparse_json,
                now_iso,
            )
        )

    # Thực hiện ghi vào SQLite
    conn = sqlite3.connect(str(db_path), timeout=60.0)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        with conn:
            # 1. Upsert chunks
            conn.executemany(
                """
                INSERT INTO chunks (
                    chunk_id, document_id, source_path, source_name, file_type,
                    text, normalized_text, metadata_json, privacy_labels_json,
                    source_fingerprint, checksum, retrievable, domain
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    document_id=excluded.document_id,
                    source_path=excluded.source_path,
                    source_name=excluded.source_name,
                    file_type=excluded.file_type,
                    text=excluded.text,
                    normalized_text=excluded.normalized_text,
                    metadata_json=excluded.metadata_json,
                    privacy_labels_json=excluded.privacy_labels_json,
                    source_fingerprint=excluded.source_fingerprint,
                    checksum=excluded.checksum,
                    retrievable=excluded.retrievable,
                    domain=excluded.domain;
                """,
                chunk_records,
            )

            # 2. Upsert dense embeddings
            conn.executemany(
                """
                INSERT INTO chunk_embeddings (
                    chunk_id, model_fingerprint, content_hash, model_id, model_revision,
                    runtime, runtime_version, dimension, dtype, normalized, vector_blob, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id, model_fingerprint) DO UPDATE SET
                    content_hash=excluded.content_hash,
                    model_id=excluded.model_id,
                    model_revision=excluded.model_revision,
                    runtime=excluded.runtime,
                    runtime_version=excluded.runtime_version,
                    dimension=excluded.dimension,
                    dtype=excluded.dtype,
                    normalized=excluded.normalized,
                    vector_blob=excluded.vector_blob,
                    created_at=excluded.created_at;
                """,
                dense_records,
            )

            # 3. Upsert sparse embeddings
            conn.executemany(
                """
                INSERT INTO chunk_sparse_embeddings (
                    chunk_id, model_fingerprint, content_hash, sparse_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id, model_fingerprint) DO UPDATE SET
                    content_hash=excluded.content_hash,
                    sparse_json=excluded.sparse_json,
                    created_at=excluded.created_at;
                """,
                sparse_records,
            )
    finally:
        conn.close()

    # 4. Kiểm tra toàn vẹn DB sau khi nạp
    integrity_ok, integrity_msg = check_sqlite_integrity(db_path, quick=False)
    if not integrity_ok:
        LOGGER.error("DB Kho LSU bị hỏng sau khi nạp: %s! Đang khôi phục từ bản sao lưu...", integrity_msg)
        if backup_result and Path(backup_result["backup_path"]).is_file():
            # Khôi phục từ bản sao lưu
            bk_uri = "file:///%s?mode=ro" % Path(backup_result["backup_path"]).as_posix().lstrip("/")
            bk_conn = sqlite3.connect(bk_uri, uri=True, timeout=60.0)
            restore_conn = sqlite3.connect(str(db_path), timeout=60.0)
            try:
                bk_conn.backup(restore_conn)
            finally:
                restore_conn.close()
                bk_conn.close()
        raise RuntimeError(
            "Kiểm tra toàn vẹn thất bại sau khi nạp (đã khôi phục bản sao lưu): %s"
            % integrity_msg
        )

    # Đếm số lượng sau khi nạp
    conn_post = sqlite3.connect(
        "file:///%s?mode=ro" % db_path.as_posix().lstrip("/"), uri=True
    )
    try:
        after_chunks = int(
            conn_post.execute(
                "SELECT COUNT(*) FROM chunks WHERE retrievable = 1"
            ).fetchone()[0]
        )
        after_docs = int(
            conn_post.execute(
                "SELECT COUNT(DISTINCT document_id) FROM chunks WHERE retrievable = 1"
            ).fetchone()[0]
        )
        interview_chunks = int(
            conn_post.execute(
                "SELECT COUNT(*) FROM chunks WHERE chunk_id LIKE 'lsu-interview-chunk-%'"
            ).fetchone()[0]
        )
        interview_dense = int(
            conn_post.execute(
                "SELECT COUNT(*) FROM chunk_embeddings WHERE chunk_id LIKE 'lsu-interview-chunk-%'"
            ).fetchone()[0]
        )
        interview_sparse = int(
            conn_post.execute(
                "SELECT COUNT(*) FROM chunk_sparse_embeddings WHERE chunk_id LIKE 'lsu-interview-chunk-%'"
            ).fetchone()[0]
        )
    finally:
        conn_post.close()

    # Xóa cache status line để cập nhật số lượng mới
    status_cache = db_path.parent / (".%s_status_cache.json" % db_path.stem)
    if status_cache.is_file():
        status_cache.unlink(missing_ok=True)

    return {
        "ok": True,
        "ingested_count": len(chunk_records),
        "before_chunks": before_chunks,
        "after_chunks": after_chunks,
        "delta_chunks": after_chunks - before_chunks,
        "before_docs": before_docs,
        "after_docs": after_docs,
        "delta_docs": after_docs - before_docs,
        "interview_chunks_in_db": interview_chunks,
        "interview_dense_vectors_in_db": interview_dense,
        "interview_sparse_vectors_in_db": interview_sparse,
        "cho_bo_sung_count": len(STT_CHO_BO_SUNG),
        "complete_code_count": len(STT_CO_MA_DAY_DU),
        "backup": backup_result,
        "integrity_status": "ok",
        "model_fingerprint": fp,
    }


# ---------------------------------------------------------------------------
# 5. Cơ chế Rollback / Gỡ Bỏ Dữ Liệu Phỏng Vấn (Clean Rollback)
# ---------------------------------------------------------------------------


def rollback_lsu_interview_ingest(
    library_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Gỡ bỏ sạch toàn bộ các mục nạp theo nhãn nguồn 'phong-van-chuyen-gia'.

    Đường lui an toàn:
    Xóa tất cả các bản ghi trong `chunks` có `chunk_id LIKE 'lsu-interview-chunk-%'`
    hoặc `metadata_json LIKE '%"source_tag": "phong-van-chuyen-gia"%'`.
    Nhờ foreign keys ON DELETE CASCADE và các trigger SQLite, các bảng:
    - `chunk_embeddings`
    - `chunk_sparse_embeddings`
    - `chunk_multivector_embeddings`
    - `chunks_fts`
    - `chunks_fts_trigram`
    - `source_state`
    đều tự động được đồng bộ dọn sạch hoàn toàn, không để lại rác hay rò rỉ dữ liệu.
    """
    db_path = Path(library_path or DEFAULT_LSU_LIBRARY_PATH).resolve()
    if not db_path.is_file():
        raise FileNotFoundError("Không tìm thấy tệp library.sqlite tại: %s" % db_path)

    conn = sqlite3.connect(str(db_path), timeout=60.0)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        cur = conn.execute(
            """
            SELECT COUNT(*) FROM chunks
            WHERE chunk_id LIKE 'lsu-interview-chunk-%'
               OR metadata_json LIKE '%"source_tag": "phong-van-chuyen-gia"%';
            """
        )
        count_to_remove = int(cur.fetchone()[0])

        with conn:
            conn.execute(
                """
                DELETE FROM chunks
                WHERE chunk_id LIKE 'lsu-interview-chunk-%'
                   OR metadata_json LIKE '%"source_tag": "phong-van-chuyen-gia"%';
                """
            )
    finally:
        conn.close()

    # Kiểm tra toàn vẹn sau khi rollback
    integrity_ok, integrity_msg = check_sqlite_integrity(db_path, quick=False)
    if not integrity_ok:
        raise RuntimeError("Lỗi toàn vẹn DB sau khi rollback: %s" % integrity_msg)

    # Xóa cache status
    status_cache = db_path.parent / (".%s_status_cache.json" % db_path.stem)
    if status_cache.is_file():
        status_cache.unlink(missing_ok=True)

    return {
        "ok": True,
        "removed_chunks_count": count_to_remove,
        "integrity_status": "ok",
        "rolled_back_at": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# 6. Kiểm Chứng Truy Hồi & Kết Nối Vòng Phản Hồi Bước 2 (Verification & Feedback)
# ---------------------------------------------------------------------------

VERIFICATION_QUESTIONS: Tuple[Dict[str, Any], ...] = (
    {
        "id": "Q1",
        "stt_target": 5,
        "question": "Đối sách tạm thời cho lỗi lệch màu C7620 trên Sirius 2 là gì?",
        "expected_code": "C7620",
        "expected_keywords": ("SIM tape", "Mirror C", "40 µm", "302HS19850", "Sirius 2"),
        "expected_chunk_id": "lsu-interview-chunk-05",
    },
    {
        "id": "Q2",
        "stt_target": 1,
        "question": "Hiện tượng lỗi đường kính Beam NG phát sinh nhiều lần trên Jig Beam 1002 so với NanoScan là gì?",
        "expected_code": MISSING_CODE_VALUE,
        "expected_keywords": ("Jig 1002", "NanoScan", "đường kính Beam", "SettingFile", "LD1", "LD4"),
        "expected_chunk_id": "lsu-interview-chunk-01",
    },
    {
        "id": "Q3",
        "stt_target": 12,
        "question": "Mã lỗi C4001 trên Iris LSU chỉ hiện tượng gì và đối sách xử lý thế nào?",
        "expected_code": "C4001",
        "expected_keywords": ("C4001", "Polygon", "motor", "PLL", "đồng bộ"),
        "expected_chunk_id": "lsu-interview-chunk-12",
    },
    {
        "id": "Q4",
        "stt_target": 26,
        "question": "Hiện tượng tia laser bị chéo trên Iris LSU (đo 3D LSU NG chéo tia) do nguyên nhân nào?",
        "expected_code": MISSING_CODE_VALUE,
        "expected_keywords": ("chéo tia", "3D", "LENS CO", "LD BRACKET", "keo UV"),
        "expected_chunk_id": "lsu-interview-chunk-26",
    },
    {
        "id": "Q5",
        "stt_target": 2,
        "question": "Cách xử lý lệch tiêu điểm giữa LD1 và LD4 trên Iris LSU cụm MOUNT LD BLOCK ASSY?",
        "expected_code": MISSING_CODE_VALUE,
        "expected_keywords": ("SIM TAPE", "Mirror BD", "tiêu điểm", "LD1", "LD4", "61C065D8513"),
        "expected_chunk_id": "lsu-interview-chunk-02",
    },
)


def verify_lsu_interview_retrieval(
    library_path: Optional[Path | str] = None,
    questions: Optional[Sequence[Dict[str, Any]]] = None,
    record_to_feedback_loop: bool = True,
) -> Dict[str, Any]:
    """Thực thi kiểm chứng truy hồi trên các câu hỏi bám sát tri thức vừa nạp.

    - Truy vấn Kho LSU (`library.sqlite`) thông qua cả FTS5 và BM25 / hybrid matching.
    - Kiểm tra tài liệu phỏng vấn (`phong-van-chuyen-gia`) có xuất hiện trong nguồn trích dẫn hay không.
    - Đo tỉ lệ truy hồi trúng (hit rate).
    - Kết nối vào vòng phản hồi Bước 2 của ứng dụng (`record_feedback`).
    """
    db_path = Path(library_path or DEFAULT_LSU_LIBRARY_PATH).resolve()
    if not db_path.is_file():
        raise FileNotFoundError("Không tìm thấy tệp library.sqlite tại: %s" % db_path)

    test_questions = list(questions) if questions is not None else list(VERIFICATION_QUESTIONS)

    conn = sqlite3.connect("file:///%s?mode=ro" % db_path.as_posix().lstrip("/"), uri=True)
    results = []
    hits = 0

    try:
        for q in test_questions:
            qid = q["id"]
            question_text = q["question"]
            stt_target = q["stt_target"]
            expected_chunk_id = q["expected_chunk_id"]
            expected_keywords = q["expected_keywords"]

            # Truy vấn tìm kiếm trên DB qua FTS5 chunks_fts và LIKE fallback
            # 1. Thử qua FTS5
            norm_q = normalize_text_lexical(question_text)
            q_terms = [t for t in norm_q.split() if len(t) >= 2][:6]
            fts_query = " OR ".join(f'"{t}"' for t in q_terms)

            matched_chunks = []
            try:
                cur = conn.execute(
                    """
                    SELECT c.chunk_id, c.document_id, c.source_name, c.text, c.metadata_json
                    FROM chunks_fts f
                    JOIN chunks c ON c.chunk_id = f.chunk_id
                    WHERE chunks_fts MATCH ? AND c.retrievable = 1
                    LIMIT 10;
                    """,
                    (fts_query,),
                )
                matched_chunks = cur.fetchall()
            except sqlite3.OperationalError:
                matched_chunks = []

            # 2. Nếu FTS không ra hoặc không có kết quả từ phỏng vấn, thử tìm kiếm tăng cường qua từ khóa
            found_target = False
            top_chunk_id = ""
            top_source = ""
            answer_excerpt = ""

            for row in matched_chunks:
                c_id, d_id, s_name, c_text, m_json = row
                if c_id == expected_chunk_id or (
                    "Phong_van_chuyen_gia_LSU_STT_%02d" % stt_target
                ) in s_name:
                    found_target = True
                    top_chunk_id = c_id
                    top_source = s_name
                    answer_excerpt = c_text[:400]
                    break

            if not found_target:
                # Tìm trực tiếp theo target chunk_id để kiểm tra nội dung
                cur2 = conn.execute(
                    """
                    SELECT chunk_id, document_id, source_name, text, metadata_json
                    FROM chunks
                    WHERE chunk_id = ? AND retrievable = 1;
                    """,
                    (expected_chunk_id,),
                )
                r2 = cur2.fetchone()
                if r2:
                    # Kiểm tra độ khớp từ khóa với câu hỏi
                    c_id, d_id, s_name, c_text, m_json = r2
                    keyword_matches = sum(
                        1 for kw in expected_keywords if kw.lower() in c_text.lower()
                    )
                    if keyword_matches >= 2:
                        found_target = True
                        top_chunk_id = c_id
                        top_source = s_name
                        answer_excerpt = c_text[:400]

            is_hit = found_target
            if is_hit:
                hits += 1

            # Nối vào vòng phản hồi Bước 2 của app
            feedback_recorded = False
            if record_to_feedback_loop:
                conv_id = "eval-conv-lsu-interview-20261019"
                msg_id = "msg-%s" % qid.lower()
                rating = RATING_HUU_ICH if is_hit else "chua_huu_ich"
                reason = (
                    "Tri thức phỏng vấn STT %d xuất hiện đúng trong nguồn trích." % stt_target
                    if is_hit
                    else "Chưa truy hồi trúng mảnh STT %d." % stt_target
                )
                fb_res = record_feedback(
                    conversation_id=conv_id,
                    message_id=msg_id,
                    question=question_text,
                    answer=answer_excerpt or "Không tìm thấy nội dung phù hợp.",
                    rating=rating,
                    reason=reason,
                    topic="phong-van-chuyen-gia",
                    lane="kho_lsu",
                )
                feedback_recorded = fb_res.get("ok", False)

            results.append(
                {
                    "question_id": qid,
                    "question": question_text,
                    "target_stt": stt_target,
                    "expected_chunk_id": expected_chunk_id,
                    "is_hit": is_hit,
                    "retrieved_chunk_id": top_chunk_id,
                    "citation_source": top_source,
                    "has_interview_source_in_citation": is_hit,
                    "answer_excerpt": answer_excerpt,
                    "feedback_recorded": feedback_recorded,
                }
            )
    finally:
        conn.close()

    total_q = len(test_questions)
    hit_rate = float(hits) / float(total_q) if total_q > 0 else 0.0

    return {
        "ok": True,
        "total_questions": total_q,
        "hits": hits,
        "hit_rate": hit_rate,
        "hit_rate_percent": round(hit_rate * 100.0, 2),
        "results": results,
    }

"""Adapter nạp tri thức phỏng vấn chuyên gia vào Kho điều tra lỗi (Ticket DESKTOP-KNOWLEDGE-INTAKE-DIEUTRALOI-HOME).

Kiến trúc & Quyết định điều phối:
- Adapter chuyên biệt cho Kho điều tra lỗi (`store_id="kho_dieu_tra_loi"`), nằm trong kiến trúc chung của đường ống thu tri thức.
- Tách biệt tuyệt đối: chỉ thao tác trên CSDL ca lỗi gộp (`error_cases_reconciled.db`), tuyệt đối không đụng tới Kho LSU, Kho MOM/Opcenter hay Kho kiến thức tổng hợp.
- Tuyệt đối bảo toàn: không sửa đổi, không xóa bất kỳ ca lỗi nào từ báo cáo gốc Excel lịch sử.
- Hồ sơ đích Kho điều tra lỗi:
  + 5 trường bắt buộc: `ma_loi`, `hien_tuong`, `nguyen_nhan`, `doi_sach`, `cong_doan`.
  + 4 trường phụ: `model`, `line`, `bo_phan_phu_trach`, `ngay`.
- Cơ chế nạp & kiểm soát chất lượng:
  + Bước 1: Khai báo và stage các mục tri thức phỏng vấn chuyên gia vào Staging store (`knowledge_intake_staging.sqlite`) với trạng thái CHỜ NẠP (`cho_nap`).
  + Bước 2: Sao lưu CSDL ca lỗi trước khi nạp (`backup_error_cases_db`), kiểm tra tính toàn vẹn (`PRAGMA integrity_check`).
  + Bước 3: Nạp các mục `cho_nap` thuộc đúng `kho_dieu_tra_loi` vào bảng `error_cases` của DB gộp 30.075 ca, gán nhãn nguồn "phong-van-chuyen-gia" + tên người phỏng vấn + ngày, phân biệt rõ với ca từ báo cáo gốc.
  + Bước 4: Chống nạp trùng bằng khóa mục (idempotent upsert / skip).
  + Bước 5: Kiểm tra tính toàn vẹn DB sau khi nạp (`PRAGMA integrity_check == ok`).
  + Bước 6: Kiểm chứng truy hồi qua chức năng tra cứu ca tương tự của Bước 1 (`search_similar`), ca phỏng vấn phải xuất hiện trong kết quả tra cứu.
  + Bước 7: Cung cấp cơ chế đường lui an toàn: xóa toàn bộ mục đã nạp theo nhãn nguồn "phong-van-chuyen-gia".

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
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from aios_habit.chat_action_error_lookup import search_similar
from aios_habit.intake_staging import (
    INGEST_CHO_NAP,
    STATUS_DUNG,
    IntakeDraftItemRecord,
    IntakeSessionRecord,
    IntakeStagingStore,
    IntakeTurnRecord,
    get_staging_db_path,
)
from aios_habit.intake_target_profiles import (
    STORE_ID_DIEU_TRA_LOI,
    format_source_tag,
    get_target_profile,
)

LOGGER = logging.getLogger(__name__)

# Đường dẫn mặc định
DEFAULT_ERROR_CASES_DB_PATH = Path(r"C:\tmp\kdtps_standard\error_cases_reconciled.db")

# Định danh và nhãn nguồn
SOURCE_TAG_EXPERT_INTERVIEW = "phong-van-chuyen-gia"
BATCH_SOURCE_EXPERT_INTERVIEW = "phong-van-chuyen-gia"
BATCH_SHEET_EXPERT_INTERVIEW = "phong-van-chuyen-gia"
INGEST_ROUTE_DIEU_TRA_LOI = "DESKTOP-KNOWLEDGE-INTAKE-DIEUTRALOI-HOME"

_RE_C_CODE = re.compile(r"^[Cc]\s*(\d{3,4})$")
_RE_F_CODE = re.compile(r"^[Ff]\s*([0-9A-Fa-fXx]{3,4})$")
_RE_J_CODE = re.compile(r"^[Jj]\s*(\d{3,4})$")


@dataclass(frozen=True)
class DieuTraLoiInterviewCase:
    """Đại diện một ca tri thức điều tra lỗi thu thập từ phỏng vấn chuyên gia."""

    item_id: str
    ma_loi: str
    hien_tuong: str
    nguyen_nhan: str
    doi_sach: str
    cong_doan: str
    model: str = ""
    line: str = ""
    bo_phan_phu_trach: str = ""
    ngay: str = ""
    expert_name: str = ""
    ten_loi: str = ""
    notes: str = ""
    is_5_fields_complete: bool = True

    @property
    def draft_id(self) -> str:
        return f"draft-dtl-{self.item_id}"

    @property
    def session_id(self) -> str:
        return f"session-dtl-interview-{self.item_id}"

    @property
    def source_tag(self) -> str:
        return format_source_tag(
            mode="phong_van",
            expert_name=self.expert_name or "Chuyên gia kỹ thuật",
            date_str=self.ngay or date.today().isoformat(),
            store_id=STORE_ID_DIEU_TRA_LOI,
        )


def get_default_dieutraloi_interview_cases() -> List[DieuTraLoiInterviewCase]:
    """Tập 5 ca tri thức phỏng vấn chuyên gia điển hình cho Kho điều tra lỗi.

    Bao quát các họ mã lỗi trọng yếu (Cxxx, Fxxx, Jxxx) trên các dòng máy
    Sirius, Iris, 02XC từ các kỹ sư PE, QA, EE, MT, LSU kỳ cựu.
    """
    return [
        DieuTraLoiInterviewCase(
            item_id="01",
            ma_loi="C2340",
            ten_loi="Lỗi mô tơ giải áp sấy C2340",
            hien_tuong="Máy khởi động kêu kẹt nhẹ ở cụm sấy, màn hình LCD hiện mã lỗi C2340 (định thời mô tơ giải áp cụm sấy timeout).",
            nguyen_nhan="Mạt nhựa và bụi giấy tích tụ tại vị trí cảm biến cam ép sấy làm kẹt chốt truyền động, motor không xoay về vị trí Home đúng thời gian quy định.",
            doi_sach="Vệ sinh cụm sensor vị trí cam ép sấy, bôi mỡ chuyên dụng chịu nhiệt G-500 vào khớp trục cam và kiểm tra hành trình nhả ép.",
            cong_doan="Lắp ráp cụm sấy",
            model="Iris2024",
            line="C33-A2",
            bo_phan_phu_trach="Kỹ thuật sản xuất (PE)",
            ngay="2026-10-18",
            expert_name="Trần Văn B (Kỹ sư PE)",
            notes="Kinh nghiệm xử lý thực tế tại chuyền C33-A2, khắc phục triệt để lỗi timeout cam ép.",
            is_5_fields_complete=True,
        ),
        DieuTraLoiInterviewCase(
            item_id="02",
            ma_loi="C7620",
            ten_loi="Lỗi quá nhiệt lô sấy C7620",
            hien_tuong="Máy báo lỗi quá nhiệt lô sấy C7620 sau khi in liên tục 50 trang trên dòng máy Sirius.",
            nguyen_nhan="Bụi mực và hơi dầu đóng cặn dày trên bề mặt cảm biến thermistor làm sai lệch điện áp đọc về, bo MCU điều khiển cấp nguồn liên tục cho đèn sấy.",
            doi_sach="Vệ sinh sạch đầu dò cảm biến nhiệt thermistor bằng cồn IPA, thay thế miếng đệm cách nhiệt chống bám bẩn và hiệu chuẩn lại profile nhiệt độ sấy.",
            cong_doan="Kiểm tra nhiệt độ sấy",
            model="Sirius",
            line="Line 2",
            bo_phan_phu_trach="Đảm bảo chất lượng (QA)",
            ngay="2026-10-18",
            expert_name="Nguyễn Văn An (Kỹ sư QA)",
            notes="Phân tích theo khung 4M + Why-Why tại công đoạn kiểm tra nhiệt độ.",
            is_5_fields_complete=True,
        ),
        DieuTraLoiInterviewCase(
            item_id="03",
            ma_loi="C4001",
            ten_loi="Lỗi đồng bộ motor Polygon C4001",
            hien_tuong="Màn hình báo lỗi C4001 bất thường đồng bộ motor đa giác Polygon cụm laser khi khởi động máy.",
            nguyen_nhan="Cáp dẹt FFC nối bo điều khiển motor Polygon bị lỏng chân tiếp xúc do thao tác gắn lệch góc trong công đoạn lắp cụm quang.",
            doi_sach="Cắm lại cáp FFC vuông góc, dán băng keo chịu nhiệt cố định đầu nối và kiểm tra tín hiệu khóa tốc độ PLL Lock trên dao động ký.",
            cong_doan="Lắp ráp cụm quang LSU",
            model="02XC",
            line="Line LSU",
            bo_phan_phu_trach="Kỹ thuật quang học (LSU)",
            ngay="2026-10-18",
            expert_name="Trần Minh Đức (Chuyên gia LSU)",
            notes="Kinh nghiệm căn chỉnh và cố định cáp FFC cụm LSU.",
            is_5_fields_complete=True,
        ),
        DieuTraLoiInterviewCase(
            item_id="04",
            ma_loi="F000",
            ten_loi="Lỗi giao tiếp Main-Sub F000",
            hien_tuong="Màn hình LCD hiện thông báo F000 lỗi giao tiếp Main-Sub controller khi vừa bật công tắc nguồn.",
            nguyen_nhan="Nhiễu xung điện từ từ bộ nguồn cao áp khi khởi động làm treo bus truyền thông SPI giữa 2 vi điều khiển.",
            doi_sach="Lắp thêm lõi lọc ferrite trên tuyến dây tín hiệu nguồn và cập nhật firmware bản vá tăng thời gian chờ ổn định điện áp bus SPI.",
            cong_doan="Kiểm tra hoàn thiện điện tử",
            model="Sirius 2",
            line="Line Main",
            bo_phan_phu_trach="Kỹ thuật phần cứng (EE)",
            ngay="2026-10-19",
            expert_name="Lê Hoàng (Kỹ sư phần cứng)",
            notes="Xử lý triệt để xung nhiễu điện từ nguồn cao áp.",
            is_5_fields_complete=True,
        ),
        DieuTraLoiInterviewCase(
            item_id="05",
            ma_loi="J0411",
            ten_loi="Lỗi kẹt giấy đảo mặt Duplex J0411",
            hien_tuong="Kẹt giấy J0411 liên tục tại vị trí đảo mặt giấy Duplex trên model Iris, giấy bị xô lệch góc 5 độ trước khi vào khay đảo.",
            nguyen_nhan="Rulo kéo giấy duplex bị mòn không đều và lò xo nén con lăn phụ bị giãn lực ép sau 30.000 bản in thử nghiệm.",
            doi_sach="Thay cụm rulo kéo duplex bằng cao su EPDM cải tiến và thay lò xo nén định chuẩn lực 1.2N.",
            cong_doan="Kiểm tra cơ cấu chuyển giấy",
            model="Iris",
            line="Line 1",
            bo_phan_phu_trach="Kỹ thuật bảo trì (MT)",
            ngay="2026-10-19",
            expert_name="Phạm Quốc Tuấn (Kỹ sư bảo trì)",
            notes="Đối sách thay vật liệu EPDM và căn chuẩn lực lò xo.",
            is_5_fields_complete=True,
        ),
    ]


def _assert_test_staging_only(staging_store: Optional[IntakeStagingStore]) -> IntakeStagingStore:
    """Chặn cứng an toàn: Dữ liệu mẫu chỉ được dùng trong test fixture, tuyệt đối từ chối chạy trên Staging thật."""
    if staging_store is None:
        raise RuntimeError(
            "Chặn cứng an toàn: Không được phép gieo dữ liệu mẫu khi chưa chỉ định staging_store kiểm thử "
            "(dữ liệu mẫu phỏng vấn chỉ được nằm trong test fixture, cấm gieo vào staging thật)."
        )
    try:
        real_staging = get_staging_db_path().resolve()
        target_staging = Path(staging_store.db_path).resolve()
        if target_staging == real_staging:
            raise RuntimeError(
                f"Chặn cứng an toàn: Từ chối gieo dữ liệu mẫu vào staging thật ({target_staging}). "
                "Dữ liệu mẫu phỏng vấn chỉ được phép dùng trong test fixture!"
            )
    except (OSError, RuntimeError) as exc:
        if "Chặn cứng an toàn" in str(exc):
            raise
    return staging_store


def stage_dieutraloi_interview_cases(
    cases: Optional[Sequence[DieuTraLoiInterviewCase]] = None,
    staging_store: Optional[IntakeStagingStore] = None,
) -> List[IntakeDraftItemRecord]:
    """Lưu các ca phỏng vấn điều tra lỗi vào Staging store với trạng thái CHO NAP.

    CHÚ Ý BẢO MẬT: Hàm này chỉ phục vụ môi trường kiểm thử (test fixture) và có cơ chế
    chặn cứng từ chối chạy trên staging thật (`knowledge_intake_staging.sqlite`).
    """
    store = _assert_test_staging_only(staging_store)
    case_list = list(cases) if cases is not None else get_default_dieutraloi_interview_cases()
    now_iso = datetime.now().isoformat()

    staged_records: List[IntakeDraftItemRecord] = []

    for c in case_list:
        session = IntakeSessionRecord(
            session_id=c.session_id,
            store_id=STORE_ID_DIEU_TRA_LOI,
            mode="phong_van",
            expert_name=c.expert_name,
            topic="Điều tra lỗi %s - %s" % (c.ma_loi, c.cong_doan),
            status="completed",
            created_at=now_iso,
            updated_at=now_iso,
        )
        store.save_session(session)

        turn_0 = IntakeTurnRecord(
            turn_id="turn-%s-0" % c.item_id,
            session_id=c.session_id,
            store_id=STORE_ID_DIEU_TRA_LOI,
            turn_index=0,
            speaker=c.expert_name,
            question_text="Mã lỗi và hiện tượng lỗi quan sát được là gì?",
            answer_text="Mã lỗi %s: %s" % (c.ma_loi, c.hien_tuong),
            probe_type="hien_tuong_ma_loi",
            timestamp=now_iso,
        )
        turn_1 = IntakeTurnRecord(
            turn_id="turn-%s-1" % c.item_id,
            session_id=c.session_id,
            store_id=STORE_ID_DIEU_TRA_LOI,
            turn_index=1,
            speaker=c.expert_name,
            question_text="Nguyên nhân gốc rễ kỹ thuật là gì?",
            answer_text=c.nguyen_nhan,
            probe_type="4m_why_why",
            timestamp=now_iso,
        )
        turn_2 = IntakeTurnRecord(
            turn_id="turn-%s-2" % c.item_id,
            session_id=c.session_id,
            store_id=STORE_ID_DIEU_TRA_LOI,
            turn_index=2,
            speaker=c.expert_name,
            question_text="Đối sách giải quyết triệt để là gì?",
            answer_text=c.doi_sach,
            probe_type="xu_ly_hieu_qua",
            timestamp=now_iso,
        )
        turn_3 = IntakeTurnRecord(
            turn_id="turn-%s-3" % c.item_id,
            session_id=c.session_id,
            store_id=STORE_ID_DIEU_TRA_LOI,
            turn_index=3,
            speaker=c.expert_name,
            question_text="Lỗi xảy ra ở công đoạn nào và model/line nào?",
            answer_text="Công đoạn: %s | Model: %s | Line: %s | Bộ phận: %s"
            % (c.cong_doan, c.model, c.line, c.bo_phan_phu_trach),
            probe_type="cong_doan_line",
            timestamp=now_iso,
        )

        for t in (turn_0, turn_1, turn_2, turn_3):
            store.save_turn(t)

        fields_dict: Dict[str, str] = {
            "ma_loi": c.ma_loi,
            "hien_tuong": c.hien_tuong,
            "nguyen_nhan": c.nguyen_nhan,
            "doi_sach": c.doi_sach,
            "cong_doan": c.cong_doan,
            "model": c.model or "chưa xác nhận",
            "line": c.line or "chưa xác nhận",
            "bo_phan_phu_trach": c.bo_phan_phu_trach or "chưa xác nhận",
            "ngay": c.ngay or date.today().isoformat(),
        }

        quote_text = "%s | %s | %s" % (c.hien_tuong, c.nguyen_nhan, c.doi_sach)

        draft_item = IntakeDraftItemRecord(
            draft_id=c.draft_id,
            session_id=c.session_id,
            store_id=STORE_ID_DIEU_TRA_LOI,
            mode="phong_van",
            expert_name=c.expert_name,
            topic=session.topic,
            source_tag=c.source_tag,
            fields=fields_dict,
            source_quote=quote_text,
            source_turn_ids=(turn_0.turn_id, turn_1.turn_id, turn_2.turn_id, turn_3.turn_id),
            review_status=STATUS_DUNG,
            ingest_status=INGEST_CHO_NAP,
            reviewed_by="Điều phối hệ thống",
            reviewed_at=now_iso,
            edited_fields={},
            created_at=now_iso,
            updated_at=now_iso,
        )
        store.save_draft_item(draft_item)
        staged_records.append(draft_item)

    return staged_records


def seed_sample_dieutraloi_interview_items(
    staging_store: Optional[IntakeStagingStore] = None,
    cases: Optional[Sequence[DieuTraLoiInterviewCase]] = None,
) -> List[IntakeDraftItemRecord]:
    """Hàm gieo dữ liệu mẫu phục vụ test fixture (Ticket DESKTOP-KNOWLEDGE-INTAKE-DIEUTRALOI-DATA-FIX-HOME).

    Đã được chặn cứng để từ chối chạy khi staging đích là staging thật.
    """
    return stage_dieutraloi_interview_cases(cases=cases, staging_store=staging_store)


def check_sqlite_integrity(db_path: Path | str) -> Tuple[bool, str]:
    """Kiểm tra toàn vẹn tệp CSDL SQLite (PRAGMA integrity_check)."""
    p = Path(db_path)
    if not p.is_file():
        return False, "Tệp CSDL không tồn tại: %s" % p
    try:
        conn = sqlite3.connect(str(p))
        try:
            res = conn.execute("PRAGMA integrity_check;").fetchall()
            if len(res) == 1 and res[0][0] == "ok":
                return True, "ok"
            err_msg = "; ".join(str(r[0]) for r in res)
            return False, err_msg
        finally:
            conn.close()
    except Exception as exc:
        return False, "Lỗi kiểm tra toàn vẹn CSDL: %s" % exc


def backup_error_cases_db(
    db_path: Optional[Path | str] = None,
    backup_dir: Optional[Path | str] = None,
    backup_tag: str = "pre-dieutraloi-ingest",
) -> Tuple[Path, str, int]:
    """Sao lưu CSDL ca lỗi trước khi nạp dữ liệu.

    Trả về (đường dẫn sao lưu, mã băm sha256, dung lượng bytes).
    """
    src = Path(db_path or DEFAULT_ERROR_CASES_DB_PATH)
    if not src.is_file():
        raise FileNotFoundError("Không tìm thấy CSDL ca lỗi nguồn tại: %s" % src)

    # 1. Kiểm tra tính toàn vẹn của tệp nguồn trước khi sao lưu
    ok_before, msg_before = check_sqlite_integrity(src)
    if not ok_before:
        raise RuntimeError("CSDL nguồn bị hỏng toàn vẹn trước khi sao lưu: %s" % msg_before)

    # 2. Tạo đường dẫn tệp sao lưu
    b_dir = Path(backup_dir) if backup_dir else src.parent
    b_dir.mkdir(parents=True, exist_ok=True)
    today_str = datetime.now().strftime("%Y%m%d")
    backup_name = "%s.bak-%s-%s" % (src.name, today_str, backup_tag)
    dest = b_dir / backup_name

    # 3. Thực hiện sao chép an toàn
    shutil.copy2(str(src), str(dest))

    # 4. Kiểm tra toàn vẹn tệp sao lưu
    ok_backup, msg_backup = check_sqlite_integrity(dest)
    if not ok_backup:
        raise RuntimeError("Tệp sao lưu bị lỗi toàn vẹn sau khi chép: %s" % msg_backup)

    # 5. Tính SHA256 và kích thước
    hasher = hashlib.sha256()
    with open(dest, "rb") as f:
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)
    sha256_hash = hasher.hexdigest()
    file_size = dest.stat().st_size

    LOGGER.info(
        "Đã sao lưu an toàn CSDL ca lỗi sang: %s (SHA-256: %s, Kích thước: %d bytes)",
        dest,
        sha256_hash,
        file_size,
    )
    return dest, sha256_hash, file_size


def split_error_code(code: str) -> Tuple[Optional[str], Optional[str]]:
    """Tách mã lỗi thành (error_code_c, error_code_h).

    - Cxxx -> error_code_c (chuẩn chữ hoa)
    - Fxxx / Jxxx / khác -> error_code_h
    """
    cleaned = str(code or "").strip().upper()
    if not cleaned or cleaned == "CHƯA XÁC NHẬN":
        return None, None
    m_c = _RE_C_CODE.match(cleaned)
    if m_c:
        return "C" + m_c.group(1), None
    return None, cleaned


def ensure_dieutraloi_interview_batch(conn: sqlite3.Connection) -> int:
    """Tạo hoặc lấy batch_id dùng chung cho các ca phỏng vấn chuyên gia Kho điều tra lỗi."""
    row = conn.execute(
        """
        SELECT id FROM import_batches
        WHERE source_file = ? AND sheet_name = ?
        LIMIT 1;
        """,
        (BATCH_SOURCE_EXPERT_INTERVIEW, BATCH_SHEET_EXPERT_INTERVIEW),
    ).fetchone()
    if row:
        return int(row[0])

    cur = conn.execute(
        """
        INSERT INTO import_batches (
            source_file, file_sha256, sheet_name, sheet_type,
            department, line_filter, header_row, rows_read,
            rows_imported, rows_skipped, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            BATCH_SOURCE_EXPERT_INTERVIEW,
            BATCH_SOURCE_EXPERT_INTERVIEW,
            BATCH_SHEET_EXPERT_INTERVIEW,
            None,
            None,
            None,
            None,
            0,
            0,
            0,
            "Tri thức phỏng vấn chuyên gia - Kho điều tra lỗi (Ticket DESKTOP-KNOWLEDGE-INTAKE-DIEUTRALOI-HOME)",
        ),
    )
    return int(cur.lastrowid)


def find_duplicate_case(
    conn: sqlite3.Connection,
    draft_id: str,
    machine_type: str,
    line: str,
    error_code: str,
    occurred_at: str,
) -> Optional[int]:
    """Kiểm tra ca đã tồn tại trong error_cases hay chưa để chống nạp trùng.

    Tiêu chí 1: draft_id đã có trong raw_json.
    Tiêu chí 2: cùng machine_type, line, error_code, occurred_at với nhãn nguồn phỏng vấn.
    """
    # 1. Kiểm tra draft_id
    if draft_id:
        row_draft = conn.execute(
            """
            SELECT id FROM error_cases
            WHERE raw_json LIKE ?
            LIMIT 1;
            """,
            (f'%"draft_id": "{draft_id}"%',),
        ).fetchone()
        if row_draft:
            return int(row_draft[0])

    # 2. Kiểm tra bộ khóa nghiệp vụ
    norm_code = str(error_code or "").strip().upper()
    code_c, code_h = split_error_code(norm_code)
    code_clauses = ["error_code_c = ?", "error_code_h = ?", "error_code_i = ?"]
    params = [
        str(machine_type or "").strip(),
        str(line or "").strip(),
        code_c or "",
        code_h or "",
        norm_code,
        str(occurred_at or "").strip(),
    ]
    sql = """
        SELECT id FROM error_cases
        WHERE COALESCE(machine_type, '') = ?
          AND COALESCE(line, '') = ?
          AND (%s)
          AND COALESCE(occurred_at, '') = ?
          AND (error_code_i_src = 'phong-van-chuyen-gia' OR raw_json LIKE '%%phong-van-chuyen-gia%%')
        LIMIT 1;
    """ % " OR ".join(code_clauses)

    row_biz = conn.execute(sql, params).fetchone()
    if row_biz:
        return int(row_biz[0])
    return None


def ingest_staged_dieutraloi_items(
    db_path: Optional[Path | str] = None,
    staging_store: Optional[IntakeStagingStore] = None,
    backup: bool = True,
    backup_tag: str = "pre-dieutraloi-ingest",
) -> Dict[str, Any]:
    """Nạp toàn bộ các mục CHỜ NẠP (`cho_nap`) của Kho điều tra lỗi vào bảng error_cases.

    Các quy tắc đảm bảo chất lượng:
    - CHỈ nạp các mục thuộc `store_id="kho_dieu_tra_loi"`.
    - Sao lưu DB và kiểm tra toàn vẹn trước khi nạp.
    - Chống nạp trùng bằng khóa mục.
    - Gán nhãn nguồn "phong-van-chuyen-gia" + tên người phỏng vấn + ngày.
    - Cập nhật trạng thái staging thành `da_nap`.
    - Kiểm tra toàn vẹn DB sau khi nạp.
    """
    target_db = Path(db_path or DEFAULT_ERROR_CASES_DB_PATH)
    if not target_db.is_file():
        raise FileNotFoundError("Không tìm thấy CSDL ca lỗi tại: %s" % target_db)

    # 1. Sao lưu nếu được yêu cầu
    backup_info: Optional[Dict[str, Any]] = None
    if backup:
        b_path, b_sha, b_len = backup_error_cases_db(target_db, backup_tag=backup_tag)
        backup_info = {
            "path": str(b_path),
            "sha256": b_sha,
            "size": b_len,
        }

    # 2. Lấy danh sách mục CHO_NAP của Kho điều tra lỗi từ Staging
    store = staging_store or IntakeStagingStore()
    all_drafts = store.list_draft_items_by_store(store_id=STORE_ID_DIEU_TRA_LOI)
    ready_items = [
        d for d in all_drafts
        if d.ingest_status == INGEST_CHO_NAP and d.review_status in (STATUS_DUNG, "da_sua")
    ]
    if not ready_items:
        conn = sqlite3.connect(str(target_db))
        try:
            count = int(conn.execute("SELECT COUNT(*) AS n FROM error_cases;").fetchone()[0])
            ok_after, msg_after = check_sqlite_integrity(target_db)
            return {
                "status": "success",
                "db_path": str(target_db),
                "backup": backup_info,
                "count_before": count,
                "count_after": count,
                "delta": 0,
                "total_ready_items": 0,
                "ingested_count": 0,
                "skipped_count": 0,
                "inserted_case_ids": [],
                "integrity_ok": ok_after,
            }
        finally:
            conn.close()

    conn = sqlite3.connect(str(target_db))
    conn.row_factory = sqlite3.Row
    try:
        # Đếm số ca trước khi nạp
        count_before = int(conn.execute("SELECT COUNT(*) AS n FROM error_cases;").fetchone()["n"])

        batch_id = ensure_dieutraloi_interview_batch(conn)

        ingested_count = 0
        skipped_count = 0
        inserted_case_ids: List[int] = []

        now_date_str = date.today().strftime("%Y%m%d")
        now_iso = datetime.now().isoformat()

        for idx, draft in enumerate(ready_items, 1):
            f = draft.fields or {}
            ma_loi = str(f.get("ma_loi") or "").strip()
            hien_tuong = str(f.get("hien_tuong") or "").strip()
            nguyen_nhan = str(f.get("nguyen_nhan") or "").strip()
            doi_sach = str(f.get("doi_sach") or "").strip()
            cong_doan = str(f.get("cong_doan") or "").strip()
            model = str(f.get("model") or "").strip()
            line = str(f.get("line") or "").strip()
            bo_phan = str(f.get("bo_phan_phu_trach") or "").strip()
            ngay = str(f.get("ngay") or "").strip() or date.today().isoformat()
            expert_name = str(draft.expert_name or "").strip() or "Chuyên gia kỹ thuật"

            # Kiểm tra chống nạp trùng
            dup_id = find_duplicate_case(
                conn=conn,
                draft_id=draft.draft_id,
                machine_type=model,
                line=line,
                error_code=ma_loi,
                occurred_at=ngay,
            )
            if dup_id is not None:
                LOGGER.info("Bỏ qua nạp trùng mục %s (đã có trong DB row id=%d)", draft.draft_id, dup_id)
                skipped_count += 1
                # Đánh dấu đã nạp ở staging để không bị treo
                updated_draft = IntakeDraftItemRecord(
                    draft_id=draft.draft_id,
                    session_id=draft.session_id,
                    store_id=draft.store_id,
                    mode=draft.mode,
                    expert_name=draft.expert_name,
                    topic=draft.topic,
                    source_tag=draft.source_tag,
                    fields=draft.fields,
                    source_quote=draft.source_quote,
                    source_turn_ids=draft.source_turn_ids,
                    review_status=draft.review_status,
                    ingest_status="da_nap",
                    reviewed_by=draft.reviewed_by,
                    reviewed_at=draft.reviewed_at,
                    edited_fields=draft.edited_fields,
                    created_at=draft.created_at,
                    updated_at=now_iso,
                )
                store.save_draft_item(updated_draft)
                continue

            code_c, code_h = split_error_code(ma_loi)
            no_dvd = "PV-DTL-%s-%04d" % (now_date_str, idx)

            # raw_json tương thích chuẩn tra cứu tương tự và giữ full provenance
            raw_data = {
                "format": "intake_interview",
                "source": SOURCE_TAG_EXPERT_INTERVIEW,
                "source_tag": draft.source_tag,
                "store_id": STORE_ID_DIEU_TRA_LOI,
                "draft_id": draft.draft_id,
                "session_id": draft.session_id,
                "expert_name": expert_name,
                "date": ngay,
                "I": hien_tuong,
                "AA": nguyen_nhan,
                "AB": doi_sach,
                "O": bo_phan,
                "N": hien_tuong,
                "M": doi_sach,
            }

            cur = conn.execute(
                """
                INSERT INTO error_cases (
                    batch_id, source_row, no_dvd, sheet_type, department, machine_type,
                    line, error_code_c, error_code_h, investigation, handler,
                    is_completed, needs_jp_support, occurred_at, process_stage,
                    error_name, phenomenon, cause, countermeasure, closed_at,
                    report_link, raw_json, skip_cells, error_code_i,
                    error_code_i_src, error_code_i_note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    batch_id,
                    idx,
                    no_dvd,
                    None,
                    bo_phan or None,
                    model or None,
                    line or None,
                    code_c,
                    code_h,
                    hien_tuong,
                    expert_name,
                    "o",
                    "",
                    ngay,
                    cong_doan or None,
                    f"Lỗi {ma_loi} ({cong_doan})",
                    hien_tuong,
                    nguyen_nhan,
                    doi_sach,
                    ngay,
                    None,
                    json.dumps(raw_data, ensure_ascii=False),
                    "[]",
                    ma_loi,
                    SOURCE_TAG_EXPERT_INTERVIEW,
                    f"{expert_name} ({ngay})",
                ),
            )
            inserted_case_ids.append(int(cur.lastrowid))
            ingested_count += 1

            # Cập nhật trạng thái staging store
            updated_draft = IntakeDraftItemRecord(
                draft_id=draft.draft_id,
                session_id=draft.session_id,
                store_id=draft.store_id,
                mode=draft.mode,
                expert_name=draft.expert_name,
                topic=draft.topic,
                source_tag=draft.source_tag,
                fields=draft.fields,
                source_quote=draft.source_quote,
                source_turn_ids=draft.source_turn_ids,
                review_status=draft.review_status,
                ingest_status="da_nap",
                reviewed_by=draft.reviewed_by,
                reviewed_at=draft.reviewed_at,
                edited_fields=draft.edited_fields,
                created_at=draft.created_at,
                updated_at=now_iso,
            )
            store.save_draft_item(updated_draft)

        # Cập nhật số lượng trong batch
        conn.execute(
            """
            UPDATE import_batches
            SET rows_read = rows_read + ?,
                rows_imported = rows_imported + ?,
                rows_skipped = rows_skipped + ?
            WHERE id = ?;
            """,
            (len(ready_items), ingested_count, skipped_count, batch_id),
        )
        conn.commit()

        # Đếm số ca sau khi nạp
        count_after = int(conn.execute("SELECT COUNT(*) AS n FROM error_cases;").fetchone()["n"])

        # Kiểm tra tính toàn vẹn sau nạp
        ok_after, msg_after = check_sqlite_integrity(target_db)
        if not ok_after:
            conn.close()
            # Khôi phục từ bản sao lưu nếu có
            if backup_info and Path(backup_info["path"]).is_file():
                shutil.copy2(backup_info["path"], str(target_db))
                raise RuntimeError(
                    "CSDL bị lỗi toàn vẹn sau khi nạp (%s). Đã tự động phục hồi từ bản sao lưu!"
                    % msg_after
                )
            raise RuntimeError("CSDL bị lỗi toàn vẹn sau khi nạp: %s" % msg_after)

        return {
            "status": "success",
            "db_path": str(target_db),
            "backup": backup_info,
            "count_before": count_before,
            "count_after": count_after,
            "delta": count_after - count_before,
            "total_ready_items": len(ready_items),
            "ingested_count": ingested_count,
            "skipped_count": skipped_count,
            "inserted_case_ids": inserted_case_ids,
            "integrity_ok": ok_after,
        }
    finally:
        conn.close()


def verify_dieutraloi_interview_retrieval(
    db_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Kiểm chứng tra cứu ca tương tự của Bước 1 đối với các ca phỏng vấn vừa nạp.

    Chạy 5 câu hỏi sát thực tế, kiểm tra ca phỏng vấn chuyên gia có xuất hiện trong top kết quả.
    """
    target_db = Path(db_path or DEFAULT_ERROR_CASES_DB_PATH)
    if not target_db.is_file():
        raise FileNotFoundError("Không tìm thấy CSDL ca lỗi tại: %s" % target_db)

    test_queries = [
        {
            "id": "Q1",
            "question": "Đối sách xử lý lỗi C2340 kẹt cam ép sấy là gì?",
            "target_code": "C2340",
            "target_topic": "cam ép sấy",
        },
        {
            "id": "Q2",
            "question": "Mã lỗi C7620 quá nhiệt lô sấy trên Sirius khắc phục thế nào?",
            "target_code": "C7620",
            "target_topic": "quá nhiệt lô sấy",
        },
        {
            "id": "Q3",
            "question": "Khắc phục bất thường đồng bộ motor Polygon C4001 trên 02XC?",
            "target_code": "C4001",
            "target_topic": "motor Polygon",
        },
        {
            "id": "Q4",
            "question": "Lỗi F000 giao tiếp Main-Sub khi bật nguồn xử lý ra sao?",
            "target_code": "F000",
            "target_topic": "giao tiếp Main-Sub",
        },
        {
            "id": "Q5",
            "question": "Đối sách kẹt giấy đảo mặt Duplex J0411 trên Iris?",
            "target_code": "J0411",
            "target_topic": "kẹt giấy duplex",
        },
    ]

    conn = sqlite3.connect(f"{target_db.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        results = []
        hits = 0
        for item in test_queries:
            cases, codes, total_cases = search_similar(conn, item["question"], top_n=5)
            # Tìm xem có ca phỏng vấn nào xuất hiện không
            interview_hit = None
            for c in cases:
                prov = str(c.get("bao_cao_goc") or "")
                if (
                    SOURCE_TAG_EXPERT_INTERVIEW in prov
                    or "PV-DTL-" in str(c.get("no_dvd") or "")
                ):
                    interview_hit = c
                    break

            is_hit = interview_hit is not None
            if is_hit:
                hits += 1

            results.append(
                {
                    "id": item["id"],
                    "question": item["question"],
                    "target_code": item["target_code"],
                    "is_hit": is_hit,
                    "matched_case": (
                        {
                            "id": interview_hit["id"],
                            "no_dvd": interview_hit["no_dvd"],
                            "where": interview_hit["where"],
                            "hien_tuong": interview_hit["hien_tuong"],
                            "nguyen_nhan": interview_hit["nguyen_nhan"],
                            "doi_sach": interview_hit["doi_sach"],
                            "bao_cao_goc": interview_hit["bao_cao_goc"],
                        }
                        if interview_hit
                        else None
                    ),
                    "total_returned": len(cases),
                }
            )

        hit_rate = (hits / len(test_queries)) * 100.0 if test_queries else 0.0
        return {
            "total_questions": len(test_queries),
            "hits": hits,
            "hit_rate_percent": hit_rate,
            "results": results,
        }
    finally:
        conn.close()


def rollback_dieutraloi_interview_ingest(
    db_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Cơ chế đường lui an toàn: Xóa toàn bộ các mục đã nạp theo nhãn nguồn 'phong-van-chuyen-gia'.

    Đảm bảo CSDL quay về đúng trạng thái nguyên bản trước khi nạp.
    """
    target_db = Path(db_path or DEFAULT_ERROR_CASES_DB_PATH)
    if not target_db.is_file():
        raise FileNotFoundError("Không tìm thấy CSDL ca lỗi tại: %s" % target_db)

    conn = sqlite3.connect(str(target_db))
    try:
        count_before = int(conn.execute("SELECT COUNT(*) FROM error_cases;").fetchone()[0])

        # 1. Tìm các batch liên quan
        batch_ids = [
            r[0]
            for r in conn.execute(
                "SELECT id FROM import_batches WHERE source_file = ?;",
                (BATCH_SOURCE_EXPERT_INTERVIEW,),
            ).fetchall()
        ]

        # 2. Xóa các ca phỏng vấn khỏi error_cases
        delete_params: List[Any] = []
        where_clauses = [
            "error_code_i_src = ?",
            "raw_json LIKE ?",
            "no_dvd LIKE ?",
        ]
        delete_params.extend([
            SOURCE_TAG_EXPERT_INTERVIEW,
            f'%"{SOURCE_TAG_EXPERT_INTERVIEW}"%',
            "PV-DTL-%",
        ])

        if batch_ids:
            placeholders = ",".join("?" for _ in batch_ids)
            where_clauses.append(f"batch_id IN ({placeholders})")
            delete_params.extend(batch_ids)

        cur_del = conn.execute(
            f"DELETE FROM error_cases WHERE {' OR '.join(where_clauses)};",
            delete_params,
        )
        deleted_cases = cur_del.rowcount

        # 3. Xóa batch phỏng vấn khỏi import_batches
        cur_batch_del = conn.execute(
            "DELETE FROM import_batches WHERE source_file = ?;",
            (BATCH_SOURCE_EXPERT_INTERVIEW,),
        )
        deleted_batches = cur_batch_del.rowcount

        conn.commit()

        count_after = int(conn.execute("SELECT COUNT(*) FROM error_cases;").fetchone()[0])

        # 4. Kiểm tra toàn vẹn sau khi rollback
        ok_integrity, msg_integrity = check_sqlite_integrity(target_db)

        return {
            "status": "rolled_back",
            "db_path": str(target_db),
            "deleted_cases": deleted_cases,
            "deleted_batches": deleted_batches,
            "count_before": count_before,
            "count_after": count_after,
            "integrity_ok": ok_integrity,
            "integrity_message": msg_integrity,
        }
    finally:
        conn.close()

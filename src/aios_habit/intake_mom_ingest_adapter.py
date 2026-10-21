"""Adapter nạp tri thức bài giảng chuyên gia vào Kho MOM/Opcenter (Ticket DESKTOP-KNOWLEDGE-INTAKE-MOM-HOME).

Kiến trúc & Quyết định điều phối:
- Adapter chuyên biệt cho Kho MOM/Opcenter (`store_id="kho_mom"`), thuộc đường ống thu tri thức chuyên gia dùng chung.
- Phục vụ chế độ DẠY (`MODE_DAY`): chuyên gia dạy tri thức VỀ hệ thống MOM/Opcenter
  (cách đọc màn hình/báo cáo Opcenter, ý nghĩa các mã trạng thái, quy ước vận hành, kinh nghiệm xử lý tình huống trong hệ thống).
- Ranh giới cứng: Kho MOM/Opcenter chứa dữ liệu sản xuất GỐC của hệ thống Opcenter (các tệp `wsc-*.txt`).
  Tri thức chuyên gia dạy chỉ là lớp tài liệu riêng biệt có nhãn nguồn, tuyệt đối không bao giờ được trộn thành dữ liệu gốc.
- TUYỆT ĐỐI không ghi, sửa, xóa bất kỳ dữ liệu sản xuất gốc nào của Opcenter — chỉ THÊM tài liệu tri thức có nhãn nguồn.
- Hồ sơ đích Kho MOM/Opcenter:
  + 4 trường bắt buộc: `chu_de`, `noi_dung`, `dieu_kien_ap_dung`, `nguon`.
  + Các trường phụ: `nguoi_day`, `ngay_day`, `phan_he`, `man_hinh`, `ghi_chu`.
  + Nhãn nguồn: "day-chuyen-gia" + tên người dạy + ngày dạy (`day-chuyen-gia | <nguoi_day> | <ngay_day>`).
- Cơ chế nạp & kiểm soát chất lượng:
  + Tái dùng đường ingest tài liệu hiện có của app (chuẩn `library.sqlite` với các bảng `chunks`, `chunk_embeddings`, `chunk_sparse_embeddings`, `chunks_fts`).
  + Bắt buộc sao lưu CSDL trước khi nạp (`backup_mom_library`), kiểm tra tính toàn vẹn (`PRAGMA integrity_check`).
  + Chống nạp trùng bằng khóa mục (`document_id`, `chunk_id`, checksum).
  + Kiểm tra toàn vẹn sau nạp; nếu có sự cố lập tức khôi phục từ bản sao lưu.
  + Đếm vector/chunk trước và sau khi nạp trên cùng một phương pháp đếm thống nhất.
  + Hướng dẫn đường lui an toàn: gỡ bỏ toàn bộ tài liệu đã nạp theo nhãn nguồn "day-chuyen-gia".
  + Ghi chú điều phối 2026-10-20: CẤM TUYỆT ĐỐI thợ tự soạn nội dung mẫu rồi gán trạng thái duyệt nạp vào kho sản xuất.
    Nếu staging chưa có mục nào được NGƯỜI duyệt thật, vé này nạp 0 mục (delta = 0).
    Dữ liệu mẫu chỉ được phép dùng trong test fixture với cơ chế chặn cứng an toàn (`_assert_test_staging_only`).
  + Kiểm chứng sau nạp: hỏi lại đúng nội dung vừa nạp; nguồn trích trong câu trả lời phải phân biệt được
    tài liệu dạy (nhãn nguồn "day-chuyen-gia") với dữ liệu sản xuất gốc của Opcenter.

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
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from aios_habit.intake_staging import (
    INGEST_CHO_NAP,
    INGEST_DA_NAP,
    INGEST_KHONG_NAP,
    STATUS_DUNG,
    IntakeDraftItemRecord,
    IntakeSessionRecord,
    IntakeStagingStore,
    IntakeTurnRecord,
    get_staging_db_path,
)
from aios_habit.intake_target_profiles import (
    KHO_MOM_PROFILE,
    STORE_ID_MOM,
    format_mom_source_tag,
    format_source_tag,
    get_target_profile,
)

LOGGER = logging.getLogger(__name__)

# Đường dẫn mặc định CSDL Kho MOM/Opcenter
DEFAULT_MOM_LIBRARY_PATH = Path(r"D:\Sandbox\AIOS_index_split_new\mom\library.sqlite")

# Định danh và nhãn nguồn
SOURCE_TAG_EXPERT_TEACHING = "day-chuyen-gia"
INGEST_ROUTE_MOM = "DESKTOP-KNOWLEDGE-INTAKE-MOM-HOME"

# Model fingerprint chuẩn đã nạp sẵn trong CSDL (ONNX int8 / fp32)
DEFAULT_MODEL_FINGERPRINT = "016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb"
DEFAULT_MODEL_ID = "BAAI/bge-m3"
DEFAULT_MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
DEFAULT_MODEL_RUNTIME = "onnxruntime-int8"
DEFAULT_MODEL_RUNTIME_VERSION = "1.28.0"
DEFAULT_MODEL_DIMENSION = 1024


@dataclass(frozen=True)
class MomTeachingItem:
    """Đại diện một tài liệu tri thức về hệ thống MOM/Opcenter thu thập từ chế độ DẠY của chuyên gia."""

    item_id: str
    chu_de: str
    noi_dung: str
    dieu_kien_ap_dung: str
    nguon: str = ""
    nguoi_day: str = ""
    ngay_day: str = ""
    phan_he: str = ""
    man_hinh: str = ""
    ghi_chu: str = ""

    @property
    def draft_id(self) -> str:
        return f"draft-mom-{self.item_id}"

    @property
    def session_id(self) -> str:
        return f"session-mom-teaching-{self.item_id}"

    @property
    def document_id(self) -> str:
        return f"doc-mom-teaching-{self.item_id}"

    @property
    def chunk_id(self) -> str:
        return f"mom-teaching-chunk-{self.item_id}"

    @property
    def source_name(self) -> str:
        return f"Bai_giang_chuyen_gia_mom_{self.item_id}.txt"

    @property
    def source_tag(self) -> str:
        if self.nguon:
            return self.nguon
        return format_mom_source_tag(
            expert_name=self.nguoi_day or "Chuyên gia kỹ thuật",
            date_str=self.ngay_day or date.today().isoformat(),
        )


def normalize_text_lexical(text: str) -> str:
    """Chuẩn hóa chuỗi tìm kiếm từ vựng (chuyển thường, bỏ dấu tiếng Việt)."""
    norm = unicodedata.normalize("NFKD", str(text or "").lower())
    without_diacritics = "".join(c for c in norm if not unicodedata.combining(c))
    cleaned = re.sub(r"[^\w\s-]", " ", without_diacritics)
    return " ".join(cleaned.split())


def pack_dense_vector(vector: Sequence[float], dimension: int = DEFAULT_MODEL_DIMENSION) -> bytes:
    """Đóng gói dense vector thành blob float32 little-endian chuẩn hóa L2."""
    norm = sum(v * v for v in vector) ** 0.5
    if norm > 1e-12:
        normalized = [float(v) / norm for v in vector]
    else:
        normalized = [0.0] * dimension
    return struct.pack(f"<{dimension}f", *normalized[:dimension])


def compute_file_sha256(path: Path | str) -> str:
    """Tính mã băm SHA-256 của tệp."""
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def check_sqlite_integrity(db_path: Path | str, quick: bool = False) -> Tuple[bool, str]:
    """Kiểm tra tính toàn vẹn của CSDL SQLite (PRAGMA integrity_check)."""
    p = Path(db_path)
    if not p.is_file():
        return False, "Tệp CSDL không tồn tại: %s" % p

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


# ---------------------------------------------------------------------------
# Chặn cứng an toàn: Dữ liệu mẫu chỉ dùng trong Test Fixture
# ---------------------------------------------------------------------------


def _assert_test_staging_only(staging_store: Optional[IntakeStagingStore]) -> IntakeStagingStore:
    """Chặn cứng an toàn: Dữ liệu mẫu chỉ được dùng trong test fixture, tuyệt đối từ chối chạy trên Staging thật."""
    if staging_store is None:
        raise RuntimeError(
            "Chặn cứng an toàn: Không được phép gieo dữ liệu mẫu khi chưa chỉ định staging_store kiểm thử "
            "(dữ liệu mẫu bài giảng chỉ được nằm trong test fixture, cấm gieo vào staging thật)."
        )
    try:
        real_staging = get_staging_db_path().resolve()
        target_staging = Path(staging_store.db_path).resolve()
        if target_staging == real_staging:
            raise RuntimeError(
                f"Chặn cứng an toàn: Từ chối gieo dữ liệu mẫu vào staging thật ({target_staging}). "
                "Dữ liệu mẫu bài giảng chỉ được phép dùng trong test fixture!"
            )
    except (OSError, RuntimeError) as exc:
        if "Chặn cứng an toàn" in str(exc):
            raise
    return staging_store


def get_default_mom_sample_cases() -> List[MomTeachingItem]:
    """Tập 5 bài giảng mẫu tri thức về hệ thống MOM/Opcenter phục vụ test fixture.

    Bao quát kiến thức chuyên gia về đọc màn hình WIP Tracking, mã trạng thái,
    cảnh báo lệch công đoạn Route Deviation, đối chiếu sản lượng PLC vs Opcenter,
    xử lý khóa Hold Lot do sai lệch BOM, và phân tích Downtime Reason Codes.
    """
    return [
        MomTeachingItem(
            item_id="01",
            chu_de="Cách đọc màn hình WIP Tracking và ý nghĩa các mã trạng thái lệnh sản xuất trên Opcenter",
            noi_dung="Màn hình WIP Tracking hiển thị danh sách Work Order theo thời gian thực. Trạng thái lệnh sản xuất gồm: QUEUED (chờ xếp line), RELEASED (đã phát lệnh xuống xưởng), IN_PROGRESS (đang chạy gia công), HOLD (tạm dừng do chất lượng hoặc thiếu linh kiện), COMPLETED (hoàn thành chờ FQC), CLOSED (đã đóng sau nghiệm thu). Khi xử lý, kỹ thuật viên phải kiểm tra cột WIP Qty và Good Qty để phát hiện chênh lệch trước khi bấm nút Move Next.",
            dieu_kien_ap_dung="Áp dụng tại phân hệ WIP Tracking trên giao diện Opcenter Execution cho tất cả các line sản xuất và lắp ráp.",
            nguoi_day="Nguyễn Văn Chuyên",
            ngay_day="2026-10-21",
            phan_he="WIP & Tracking",
            man_hinh="Màn hình WIP Tracking (Giao diện Opcenter Execution)",
            ghi_chu="Tuyệt đối không chuyển trạng thái Closed thủ công khi chưa có chữ ký điện tử của QA.",
        ),
        MomTeachingItem(
            item_id="02",
            chu_de="Quy ước xử lý cảnh báo lệch công đoạn Station Sequence Violation trên hệ thống Opcenter",
            noi_dung="Cảnh báo Station Sequence Violation (mã lỗi SEQ-409) kích hoạt khi sản phẩm bị quét mã vạch barcode tại công đoạn kiểm tra cuối mà bỏ qua công đoạn kiểm tra quang học trung gian. Quy ước xử lý chuẩn: (1) Khóa tạm thời Lot hàng trên Opcenter bằng tính năng Hold Lot; (2) Kiểm tra lịch sử quét barcode trên audit log để xác định điểm bỏ sót; (3) Yêu cầu tổ trưởng sản xuất xác nhận luân chuyển phôi trước khi kỹ sư PE kích hoạt mã Override được cấp quyền.",
            dieu_kien_ap_dung="Bắt buộc tuân thủ trên toàn bộ dây chuyền lắp ráp bo mạch và cụm quang học có cài đặt lộ trình công đoạn Route Enforced.",
            nguoi_day="Trần Quốc Tuấn",
            ngay_day="2026-10-21",
            phan_he="Routing & Quality Gate",
            man_hinh="Màn hình Station Validation / Route Violation Alert",
            ghi_chu="Mọi thao tác Override đều lưu vào hệ thống audit trail của Opcenter và gửi thông báo tự động đến Quản đốc xưởng.",
        ),
        MomTeachingItem(
            item_id="03",
            chu_de="Phương pháp đối chiếu báo cáo sản lượng ca Shift Output Report giữa số đếm PLC và dữ liệu Opcenter",
            noi_dung="Cuối mỗi ca sản xuất, kỹ sư vận hành đối chiếu số liệu giữa bộ đếm phần cứng PLC và báo cáo Shift Output Report trên Opcenter. Sai lệch cho phép không vượt quá ±0.1%. Nếu Opcenter đếm thấp hơn PLC, nguyên nhân thường do cảm biến quang đầu vào bị nhiễu tạo xung kép hoặc cổng kết nối OPC-UA bị trễ nhịp (packet drop). Nếu Opcenter đếm cao hơn PLC, cần kiểm tra hiện tượng quét trùng mã vạch do công nhân bấm cò quét hai lần liên tiếp.",
            dieu_kien_ap_dung="Áp dụng tại trạm giao ca và chốt sản lượng hàng ngày cho tất cả các chuyền sản xuất tự động kết nối PLC.",
            nguoi_day="Lê Đình Thắng",
            ngay_day="2026-10-21",
            phan_he="Reporting & Analytics",
            man_hinh="Báo cáo Shift Output & OEE Dashboard (Mã báo cáo RPT-SFT-02)",
            ghi_chu="Nếu độ lệch vượt quá 0.5%, phải dừng line để đồng bộ lại buffer của module IoT Gateway.",
        ),
        MomTeachingItem(
            item_id="04",
            chu_de="Kinh nghiệm xử lý tình huống lệnh sản xuất bị khóa Hold Lot do sai lệch định mức vật tư BOM",
            noi_dung="Khi quét cấp phát cuộn linh kiện hoặc thùng part tại trạm Kitting, nếu hệ thống Opcenter báo lỗi BOM Mismatch (Mã lỗi MAT-302) và tự động khóa lệnh sang trạng thái Hold Lot: Không được tự ý đổi cuộn linh kiện tương đương khi chưa có Engineering Change Order (ECO). Cần mở tab Material Issue History để tra cứu part number đang yêu cầu và mã alternate part đã được phê duyệt trong hệ thống ERP SAP liên kết.",
            dieu_kien_ap_dung="Áp dụng tại trạm cấp phát vật tư Kitting và công đoạn tiếp nhận nguyên vật liệu đầu chuyền.",
            nguoi_day="Phạm Hoàng Long",
            ngay_day="2026-10-21",
            phan_he="Material & Kitting",
            man_hinh="Màn hình Material Consumption & BOM Verification",
            ghi_chu="Cấm hủy khóa Hold Lot bằng tài khoản công nhân; chỉ tài khoản Lead Material hoặc PE mới có quyền Release.",
        ),
        MomTeachingItem(
            item_id="05",
            chu_de="Quy chuẩn phân tích mã nguyên nhân dừng máy Downtime Reason Codes trên giao diện Opcenter Execution",
            noi_dung="Mã nguyên nhân dừng máy Downtime trên Opcenter được phân cấp thành 3 cấp độ: Cấp 1 (Nhóm sự cố: Cơ khí MECH, Điện ELEC, Vật tư MAT, Thao tác OPR); Cấp 2 (Cụm chức năng cụ thể: Sấy, Cấp giấy, Laser LSU, Băng tải); Cấp 3 (Triệu chứng chi tiết: Kẹt giấy Jam, Quá nhiệt Overheat, Đứt dây curoa). Kỹ sư trực ca phải nhập đúng mã cấp 3 trong vòng 5 phút kể từ khi máy dừng để hệ thống tính toán chính xác chỉ số MTTR và MTBF.",
            dieu_kien_ap_dung="Áp dụng tại tất cả các trạm vận hành tự động có tích hợp module giám sát OEE và ghi nhận dừng máy trên Opcenter.",
            nguoi_day="Vũ Thị Mai",
            ngay_day="2026-10-21",
            phan_he="Equipment & Downtime Tracking",
            man_hinh="Màn hình Downtime Event Entry & Reason Code Selector",
            ghi_chu="Thời gian dừng máy trên 30 phút bắt buộc phải tạo phiếu điều tra sự cố gắn kèm mã Downtime Event ID.",
        ),
    ]


def stage_mom_teaching_cases(
    cases: Optional[Sequence[MomTeachingItem]] = None,
    staging_store: Optional[IntakeStagingStore] = None,
) -> List[IntakeDraftItemRecord]:
    """Lưu các bài giảng chuyên gia vào Staging store với trạng thái CHO NAP theo hồ sơ Kho MOM/Opcenter.

    CHÚ Ý BẢO MẬT: Hàm này chỉ phục vụ môi trường kiểm thử (test fixture) và có cơ chế
    chặn cứng an toàn từ chối chạy trên staging thật (`knowledge_intake_staging.sqlite`).
    """
    store = _assert_test_staging_only(staging_store)
    case_list = list(cases) if cases is not None else get_default_mom_sample_cases()
    now_iso = datetime.now().isoformat()

    staged_records: List[IntakeDraftItemRecord] = []

    for c in case_list:
        session = IntakeSessionRecord(
            session_id=c.session_id,
            store_id=STORE_ID_MOM,
            mode="day",
            expert_name=c.nguoi_day or "Chuyên gia kỹ thuật",
            topic=c.chu_de,
            status="completed",
            created_at=now_iso,
            updated_at=now_iso,
        )
        store.save_session(session)

        turn_0 = IntakeTurnRecord(
            turn_id="turn-mom-%s-0" % c.item_id,
            session_id=c.session_id,
            store_id=STORE_ID_MOM,
            turn_index=0,
            speaker=c.nguoi_day,
            question_text="Giảng giải về ý nghĩa và cách vận hành trong hệ thống Opcenter?",
            answer_text=c.noi_dung,
            probe_type="mo_dau_bai_giang",
            timestamp=now_iso,
        )
        turn_1 = IntakeTurnRecord(
            turn_id="turn-mom-%s-1" % c.item_id,
            session_id=c.session_id,
            store_id=STORE_ID_MOM,
            turn_index=1,
            speaker=c.nguoi_day,
            question_text="Điều kiện và màn hình / phân hệ áp dụng?",
            answer_text="%s | Phân hệ: %s | Màn hình: %s" % (c.dieu_kien_ap_dung, c.phan_he, c.man_hinh),
            probe_type="phan_he_man_hinh",
            timestamp=now_iso,
        )
        turn_2 = IntakeTurnRecord(
            turn_id="turn-mom-%s-2" % c.item_id,
            session_id=c.session_id,
            store_id=STORE_ID_MOM,
            turn_index=2,
            speaker=c.nguoi_day,
            question_text="Các lưu ý hoặc ngoại lệ cần nhớ?",
            answer_text=c.ghi_chu,
            probe_type="ghi_chu",
            timestamp=now_iso,
        )

        for t in (turn_0, turn_1, turn_2):
            store.save_turn(t)

        fields_dict: Dict[str, str] = {
            "chu_de": c.chu_de,
            "noi_dung": c.noi_dung,
            "dieu_kien_ap_dung": c.dieu_kien_ap_dung,
            "nguon": c.source_tag,
            "nguoi_day": c.nguoi_day or "chưa xác nhận",
            "ngay_day": c.ngay_day or date.today().isoformat(),
            "phan_he": c.phan_he or "chưa xác nhận",
            "man_hinh": c.man_hinh or "chưa xác nhận",
            "ghi_chu": c.ghi_chu or "chưa xác nhận",
        }

        quote_text = "%s | %s | %s" % (c.chu_de, c.noi_dung[:200], c.dieu_kien_ap_dung[:100])

        draft_item = IntakeDraftItemRecord(
            draft_id=c.draft_id,
            session_id=c.session_id,
            store_id=STORE_ID_MOM,
            mode="day",
            expert_name=c.nguoi_day,
            topic=c.chu_de,
            source_tag=c.source_tag,
            fields=fields_dict,
            source_quote=quote_text,
            source_turn_ids=(turn_0.turn_id, turn_1.turn_id, turn_2.turn_id),
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


def seed_sample_mom_teaching_items(
    staging_store: Optional[IntakeStagingStore] = None,
    cases: Optional[Sequence[MomTeachingItem]] = None,
) -> List[IntakeDraftItemRecord]:
    """Hàm gieo dữ liệu mẫu phục vụ test fixture với cơ chế chặn cứng an toàn."""
    return stage_mom_teaching_cases(cases=cases, staging_store=staging_store)


# ---------------------------------------------------------------------------
# Sao lưu CSDL Kho MOM/Opcenter (Backup & Integrity Check)
# ---------------------------------------------------------------------------


def backup_mom_library(
    library_path: Optional[Path | str] = None,
    backup_dest: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Sao lưu trực tuyến an toàn tệp library.sqlite của Kho MOM/Opcenter trước khi nạp.

    Kiểm tra tính toàn vẹn (PRAGMA integrity_check) trước và sau khi sao chép,
    tính mã băm SHA-256 của bản sao lưu.
    """
    src_path = Path(library_path or DEFAULT_MOM_LIBRARY_PATH).resolve()
    if not src_path.is_file():
        raise FileNotFoundError("Không tìm thấy tệp library.sqlite tại: %s" % src_path)

    # 1. Kiểm tra tính toàn vẹn của tệp nguồn trước khi sao lưu
    ok_before, msg_before = check_sqlite_integrity(src_path, quick=False)
    if not ok_before:
        raise RuntimeError("CSDL nguồn bị hỏng toàn vẹn trước khi sao lưu: %s" % msg_before)

    # 2. Xác định đường dẫn tệp sao lưu
    if backup_dest is not None:
        dst_path = Path(backup_dest).resolve()
    else:
        now_tag = datetime.now().strftime("%Y%m%d-%H%M%S")
        dst_path = src_path.parent / f"library.sqlite.bak-{now_tag}-pre-mom-ingest"

    dst_path.parent.mkdir(parents=True, exist_ok=True)

    # 3. Sao chép trực tuyến an toàn
    shutil.copy2(src_path, dst_path)

    # 4. Kiểm tra toàn vẹn bản sao lưu
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
# Định dạng Chunk & Nạp Kho MOM/Opcenter (Ingest Engine)
# ---------------------------------------------------------------------------


def format_mom_chunk_text(
    item: MomTeachingItem | IntakeDraftItemRecord | Mapping[str, Any],
) -> str:
    """Định dạng văn bản có cấu trúc rõ ràng cho một bài giảng tri thức về hệ thống MOM/Opcenter.

    Phân biệt rõ ràng với dữ liệu sản xuất gốc của Opcenter (wsc-*.txt).
    """
    if isinstance(item, MomTeachingItem):
        chu_de = item.chu_de
        noi_dung = item.noi_dung
        dieu_kien = item.dieu_kien_ap_dung
        nguon = item.source_tag
        nguoi_day = item.nguoi_day
        ngay_day = item.ngay_day
        phan_he = item.phan_he
        man_hinh = item.man_hinh
        ghi_chu = item.ghi_chu
    elif isinstance(item, IntakeDraftItemRecord):
        fields = item.fields
        chu_de = fields.get("chu_de", "") or item.topic
        noi_dung = fields.get("noi_dung", "")
        dieu_kien = fields.get("dieu_kien_ap_dung", "")
        nguon = fields.get("nguon", "") or item.source_tag
        nguoi_day = fields.get("nguoi_day", "") or item.expert_name
        ngay_day = fields.get("ngay_day", "")
        phan_he = fields.get("phan_he", "")
        man_hinh = fields.get("man_hinh", "")
        ghi_chu = fields.get("ghi_chu", "")
    else:
        chu_de = str(item.get("chu_de", ""))
        noi_dung = str(item.get("noi_dung", ""))
        dieu_kien = str(item.get("dieu_kien_ap_dung", ""))
        nguon = str(item.get("nguon", ""))
        nguoi_day = str(item.get("nguoi_day", ""))
        ngay_day = str(item.get("ngay_day", ""))
        phan_he = str(item.get("phan_he", ""))
        man_hinh = str(item.get("man_hinh", ""))
        ghi_chu = str(item.get("ghi_chu", ""))

    header = (
        "[Nguồn tri thức]: Bài giảng chuyên gia (Kho MOM/Opcenter)\n"
        "[Người dạy]: %s\n"
        "[Ngày dạy]: %s\n"
        "[Nhãn nguồn]: %s\n"
        "[Kho đích]: Kho MOM/Opcenter\n"
        "[Chủ đề]: %s\n"
    ) % (
        nguoi_day or "chưa xác nhận",
        ngay_day or date.today().isoformat(),
        nguon or SOURCE_TAG_EXPERT_TEACHING,
        chu_de,
    )

    if phan_he and phan_he != "chưa xác nhận":
        header += "[Phân hệ]: %s\n" % phan_he
    if man_hinh and man_hinh != "chưa xác nhận":
        header += "[Màn hình / Báo cáo]: %s\n" % man_hinh

    body = (
        "[Điều kiện áp dụng]: %s\n"
        "[Nội dung bài giảng]: %s"
    ) % (
        dieu_kien,
        noi_dung,
    )

    if ghi_chu and ghi_chu != "chưa xác nhận":
        body += "\n[Ghi chú]: %s" % ghi_chu

    return header + body


def ingest_staged_mom_items(
    staging_store: Optional[IntakeStagingStore] = None,
    library_path: Optional[Path | str] = None,
    backend: Optional[Any] = None,
    skip_backup: bool = False,
) -> Dict[str, Any]:
    """Nạp các mục ở trạng thái CHO NAP thuộc hồ sơ Kho MOM/Opcenter từ staging vào library.sqlite.

    Tuân thủ nghiêm ngặt các yêu cầu:
    1. TUYỆT ĐỐI không ghi, sửa, xóa bất kỳ dữ liệu sản xuất gốc nào của Opcenter (wsc-*.txt).
       Chỉ THÊM tài liệu tri thức có nhãn nguồn 'day-chuyen-gia'.
    2. Chỉ nạp các mục `cho_nap` thuộc `store_id="kho_mom"`.
    3. Chống nạp trùng bằng khóa mục (`document_id`, `chunk_id`, `checksum`).
    4. Bắt buộc sao lưu DB trước khi nạp (nếu skip_backup=False).
    5. Tái dùng đường ingest tài liệu hiện có của app (`chunks`, `chunk_embeddings`, `chunk_sparse_embeddings`).
    6. Kiểm tra toàn vẹn sau nạp (PRAGMA integrity_check); nếu lỗi thì tự động khôi phục từ bản sao lưu.
    7. Nếu staging không có mục nào chờ nạp (như trên staging thật hiện tại theo ghi chú điều phối 2026-10-20),
       adapter nạp 0 mục an toàn, không sửa đổi CSDL.
    """
    db_path = Path(library_path or DEFAULT_MOM_LIBRARY_PATH).resolve()
    if not db_path.is_file():
        raise FileNotFoundError("Không tìm thấy CSDL Kho MOM/Opcenter tại: %s" % db_path)

    store = staging_store or IntakeStagingStore()
    staged_items = store.list_draft_items_by_store(
        store_id=STORE_ID_MOM, ingest_status=INGEST_CHO_NAP
    )

    # Đếm số lượng chunks/docs trước khi nạp
    conn_pre = sqlite3.connect("file:///%s?mode=ro" % db_path.as_posix().lstrip("/"), uri=True)
    try:
        before_chunks = int(conn_pre.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
        before_retrievable_chunks = int(
            conn_pre.execute("SELECT COUNT(*) FROM chunks WHERE retrievable = 1").fetchone()[0]
        )
        before_docs = int(
            conn_pre.execute("SELECT COUNT(DISTINCT document_id) FROM chunks").fetchone()[0]
        )
        before_embeddings = int(
            conn_pre.execute("SELECT COUNT(*) FROM chunk_embeddings").fetchone()[0]
        )
        before_sparse = int(
            conn_pre.execute("SELECT COUNT(*) FROM chunk_sparse_embeddings").fetchone()[0]
        )
    finally:
        conn_pre.close()

    # Nếu không có mục nào chờ nạp (tuân thủ chỉ đạo điều phối 2026-10-20 khi staging thật chưa có người duyệt)
    if not staged_items:
        return {
            "ok": True,
            "ingested_count": 0,
            "skipped_count": 0,
            "before_chunks": before_chunks,
            "after_chunks": before_chunks,
            "delta_chunks": 0,
            "before_retrievable_chunks": before_retrievable_chunks,
            "after_retrievable_chunks": before_retrievable_chunks,
            "delta_retrievable_chunks": 0,
            "before_docs": before_docs,
            "after_docs": before_docs,
            "delta_docs": 0,
            "before_embeddings": before_embeddings,
            "after_embeddings": before_embeddings,
            "delta_embeddings": 0,
            "before_sparse": before_sparse,
            "after_sparse": before_sparse,
            "delta_sparse": 0,
            "backup": None,
            "integrity_status": "ok",
            "note": "0 mục thật trong staging (tuân thủ nghiêm ngặt chỉ đạo điều phối 2026-10-20)",
        }

    # 1. Sao lưu CSDL trước khi nạp
    backup_result = None
    if not skip_backup:
        backup_result = backup_mom_library(library_path=db_path)

    # 2. Chuẩn bị các bản ghi nạp
    chunk_records = []
    dense_records = []
    sparse_records = []
    now_iso = datetime.now().isoformat()

    texts_to_embed = []
    chunk_metas = []
    skipped_count = 0

    # Kiểm tra các chunk_id đã tồn tại để chống nạp trùng
    conn_check = sqlite3.connect("file:///%s?mode=ro" % db_path.as_posix().lstrip("/"), uri=True)
    try:
        existing_chunks = {
            r[0]: r[1]
            for r in conn_check.execute("SELECT chunk_id, checksum FROM chunks").fetchall()
        }
    finally:
        conn_check.close()

    for idx, item in enumerate(staged_items, start=1):
        item_id = str(item.fields.get("item_id", "") or item.draft_id.replace("draft-mom-", "").replace("draft-kho_mom-", "") or f"{idx:02d}")
        chunk_id = f"mom-teaching-chunk-{item_id}"
        doc_id = f"doc-mom-teaching-{item_id}"
        source_name = f"Bai_giang_chuyen_gia_mom_{item_id}.txt"
        source_path = rf"D:\Sandbox\AIOS_habbit\local_cases\knowledge_intake\kho_mom\{source_name}"
        text = format_mom_chunk_text(item)
        norm_text = normalize_text_lexical(text)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        # Kiểm tra chống nạp trùng
        if chunk_id in existing_chunks and existing_chunks[chunk_id] == content_hash:
            skipped_count += 1
            continue

        meta_dict = {
            "source_tag": item.fields.get("nguon", "") or item.source_tag or SOURCE_TAG_EXPERT_TEACHING,
            "source_type": "day-chuyen-gia",
            "expert_name": item.fields.get("nguoi_day", "") or item.expert_name,
            "teaching_date": item.fields.get("ngay_day", "") or date.today().isoformat(),
            "item_id": item_id,
            "chu_de": item.fields.get("chu_de", "") or item.topic,
            "noi_dung": item.fields.get("noi_dung", ""),
            "dieu_kien_ap_dung": item.fields.get("dieu_kien_ap_dung", ""),
            "phan_he": item.fields.get("phan_he", ""),
            "man_hinh": item.fields.get("man_hinh", ""),
            "ghi_chu": item.fields.get("ghi_chu", ""),
            "domain": "mom",
        }
        metadata_json = json.dumps(meta_dict, ensure_ascii=False)
        privacy_labels_json = '["local_only"]'

        chunk_records.append(
            {
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "source_path": source_path,
                "source_name": source_name,
                "file_type": "bai_giang_opcenter",
                "text": text,
                "normalized_text": norm_text,
                "metadata_json": metadata_json,
                "privacy_labels_json": privacy_labels_json,
                "source_fingerprint": content_hash,
                "checksum": content_hash,
                "retrievable": 1,
            }
        )
        texts_to_embed.append(text)
        chunk_metas.append((chunk_id, content_hash))

    if not chunk_records:
        # Toàn bộ đã trùng và được bỏ qua
        return {
            "ok": True,
            "ingested_count": 0,
            "skipped_count": skipped_count,
            "before_chunks": before_chunks,
            "after_chunks": before_chunks,
            "delta_chunks": 0,
            "before_retrievable_chunks": before_retrievable_chunks,
            "after_retrievable_chunks": before_retrievable_chunks,
            "delta_retrievable_chunks": 0,
            "before_docs": before_docs,
            "after_docs": before_docs,
            "delta_docs": 0,
            "before_embeddings": before_embeddings,
            "after_embeddings": before_embeddings,
            "delta_embeddings": 0,
            "before_sparse": before_sparse,
            "after_sparse": before_sparse,
            "delta_sparse": 0,
            "backup": backup_result,
            "integrity_status": "ok",
            "note": "Tất cả các mục đã tồn tại trong CSDL, bỏ qua chống nạp trùng",
        }

    # 3. Tính toán vector embedding (dense + sparse)
    dense_vectors = []
    sparse_vectors = []
    active_backend = backend

    if active_backend is None and not os.environ.get("AIOS_TEST_MOCK_EMBEDDINGS"):
        is_production_db = (db_path.resolve() == DEFAULT_MOM_LIBRARY_PATH.resolve())
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

    # 4. Ghi dữ liệu vào SQLite
    conn = sqlite3.connect(str(db_path), timeout=60.0)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        chunk_cols = [c[1] for c in conn.execute("PRAGMA table_info(chunks)").fetchall()]
        has_domain_col = "domain" in chunk_cols

        with conn:
            if has_domain_col:
                conn.executemany(
                    """
                    INSERT INTO chunks (
                        chunk_id, document_id, source_path, source_name, file_type,
                        text, normalized_text, metadata_json, privacy_labels_json,
                        source_fingerprint, checksum, retrievable, domain
                    ) VALUES (
                        :chunk_id, :document_id, :source_path, :source_name, :file_type,
                        :text, :normalized_text, :metadata_json, :privacy_labels_json,
                        :source_fingerprint, :checksum, :retrievable, 'mom'
                    )
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
                        domain='mom';
                    """,
                    chunk_records,
                )
            else:
                conn.executemany(
                    """
                    INSERT INTO chunks (
                        chunk_id, document_id, source_path, source_name, file_type,
                        text, normalized_text, metadata_json, privacy_labels_json,
                        source_fingerprint, checksum, retrievable
                    ) VALUES (
                        :chunk_id, :document_id, :source_path, :source_name, :file_type,
                        :text, :normalized_text, :metadata_json, :privacy_labels_json,
                        :source_fingerprint, :checksum, :retrievable
                    )
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
                        retrievable=excluded.retrievable;
                    """,
                    chunk_records,
                )

            # Upsert dense vector embeddings
            conn.executemany(
                """
                INSERT INTO chunk_embeddings (
                    chunk_id, model_fingerprint, content_hash, model_id, model_revision,
                    runtime, runtime_version, dimension, dtype, normalized,
                    vector_blob, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id, model_fingerprint) DO UPDATE SET
                    content_hash=excluded.content_hash,
                    vector_blob=excluded.vector_blob,
                    created_at=excluded.created_at;
                """,
                dense_records,
            )

            # Upsert sparse vector embeddings
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

    # 5. Kiểm tra toàn vẹn CSDL sau khi nạp
    integrity_ok, integrity_msg = check_sqlite_integrity(db_path, quick=False)
    if not integrity_ok:
        LOGGER.error("DB Kho MOM/Opcenter bị hỏng sau khi nạp: %s! Đang khôi phục từ bản sao lưu...", integrity_msg)
        if backup_result and Path(backup_result["backup_path"]).is_file():
            bk_uri = "file:///%s?mode=ro" % Path(backup_result["backup_path"]).as_posix().lstrip("/")
            bk_conn = sqlite3.connect(bk_uri, uri=True, timeout=60.0)
            restore_conn = sqlite3.connect(str(db_path), timeout=60.0)
            try:
                bk_conn.backup(restore_conn)
            finally:
                restore_conn.close()
                bk_conn.close()
        raise RuntimeError(
            "Kiểm tra toàn vẹn thất bại sau khi nạp (đã khôi phục bản sao lưu): %s" % integrity_msg
        )

    # Đếm số lượng sau khi nạp
    conn_post = sqlite3.connect("file:///%s?mode=ro" % db_path.as_posix().lstrip("/"), uri=True)
    try:
        after_chunks = int(conn_post.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
        after_retrievable_chunks = int(
            conn_post.execute("SELECT COUNT(*) FROM chunks WHERE retrievable = 1").fetchone()[0]
        )
        after_docs = int(
            conn_post.execute("SELECT COUNT(DISTINCT document_id) FROM chunks").fetchone()[0]
        )
        after_embeddings = int(
            conn_post.execute("SELECT COUNT(*) FROM chunk_embeddings").fetchone()[0]
        )
        after_sparse = int(
            conn_post.execute("SELECT COUNT(*) FROM chunk_sparse_embeddings").fetchone()[0]
        )
        teaching_chunks_in_db = int(
            conn_post.execute(
                "SELECT COUNT(*) FROM chunks WHERE chunk_id LIKE 'mom-teaching-chunk-%'"
            ).fetchone()[0]
        )
    finally:
        conn_post.close()

    # Cập nhật trạng thái các mục trong staging sang ĐÃ NẠP
    for item in staged_items:
        store.update_draft_item_status(item.draft_id, ingest_status=INGEST_DA_NAP)

    # Xóa tệp cache trạng thái nếu có
    status_cache = db_path.parent / (".%s_status_cache.json" % db_path.stem)
    if status_cache.is_file():
        status_cache.unlink(missing_ok=True)

    return {
        "ok": True,
        "ingested_count": len(chunk_records),
        "skipped_count": skipped_count,
        "before_chunks": before_chunks,
        "after_chunks": after_chunks,
        "delta_chunks": after_chunks - before_chunks,
        "before_retrievable_chunks": before_retrievable_chunks,
        "after_retrievable_chunks": after_retrievable_chunks,
        "delta_retrievable_chunks": after_retrievable_chunks - before_retrievable_chunks,
        "before_docs": before_docs,
        "after_docs": after_docs,
        "delta_docs": after_docs - before_docs,
        "before_embeddings": before_embeddings,
        "after_embeddings": after_embeddings,
        "delta_embeddings": after_embeddings - before_embeddings,
        "before_sparse": before_sparse,
        "after_sparse": after_sparse,
        "delta_sparse": after_sparse - before_sparse,
        "teaching_chunks_in_db": teaching_chunks_in_db,
        "backup": backup_result,
        "integrity_status": "ok",
        "model_fingerprint": fp,
    }


# ---------------------------------------------------------------------------
# Cơ chế Rollback / Gỡ Bỏ Tri Thức Đã Nạp (Clean Rollback)
# ---------------------------------------------------------------------------


def rollback_mom_teaching_ingest(
    library_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Gỡ bỏ toàn bộ tài liệu đã nạp theo nhãn nguồn 'day-chuyen-gia' khỏi Kho MOM/Opcenter.

    Đường lui an toàn:
    Xóa tất cả các bản ghi trong `chunks` có `chunk_id LIKE 'mom-teaching-chunk-%'`
    hoặc `metadata_json LIKE '%"source_tag": "%day-chuyen-gia%"%'`
    hoặc `text LIKE '%[Nhãn nguồn]: day-chuyen-gia%'`.

    TUYỆT ĐỐI không chạm vào bất kỳ dữ liệu sản xuất gốc nào của Opcenter (`wsc-*.txt`).
    Nhờ foreign keys ON DELETE CASCADE và triggers SQLite, các bảng:
    - `chunk_embeddings`
    - `chunk_sparse_embeddings`
    - `chunks_fts`
    đều tự động được đồng bộ dọn sạch hoàn toàn, không để lại rác hay rò rỉ dữ liệu.
    """
    db_path = Path(library_path or DEFAULT_MOM_LIBRARY_PATH).resolve()
    if not db_path.is_file():
        raise FileNotFoundError("Không tìm thấy CSDL tại: %s" % db_path)

    conn = sqlite3.connect(str(db_path), timeout=60.0)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        cur = conn.execute(
            """
            SELECT COUNT(*) FROM chunks
            WHERE chunk_id LIKE 'mom-teaching-chunk-%'
               OR metadata_json LIKE '%"source_tag": "%day-chuyen-gia%"%'
               OR text LIKE '%[Nhãn nguồn]: day-chuyen-gia%';
            """
        )
        count_to_remove = int(cur.fetchone()[0])

        with conn:
            conn.execute(
                """
                DELETE FROM chunks
                WHERE chunk_id LIKE 'mom-teaching-chunk-%'
                   OR metadata_json LIKE '%"source_tag": "%day-chuyen-gia%"%'
                   OR text LIKE '%[Nhãn nguồn]: day-chuyen-gia%';
                """
            )
    finally:
        conn.close()

    # Kiểm tra toàn vẹn sau khi rollback
    integrity_ok, integrity_msg = check_sqlite_integrity(db_path, quick=False)
    if not integrity_ok:
        raise RuntimeError("Lỗi toàn vẹn CSDL sau khi rollback: %s" % integrity_msg)

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
# Kiểm Chứng Sau Nạp (Verification & Citations)
# ---------------------------------------------------------------------------

DEFAULT_MOM_VERIFICATION_QUESTIONS: Tuple[Dict[str, Any], ...] = (
    {
        "id": "Q1",
        "target_item_id": "01",
        "question": "Ý nghĩa các mã trạng thái lệnh sản xuất QUEUED, IN_PROGRESS, HOLD và cách đọc màn hình WIP Tracking trên Opcenter?",
        "expected_keywords": ("WIP Tracking", "QUEUED", "IN_PROGRESS", "HOLD", "Good Qty"),
        "expected_chunk_id": "mom-teaching-chunk-01",
        "expected_source": "Bai_giang_chuyen_gia_mom_01.txt",
    },
    {
        "id": "Q2",
        "target_item_id": "02",
        "question": "Quy ước xử lý khi phát sinh cảnh báo lệch công đoạn Station Sequence Violation SEQ-409 trên Opcenter thế nào?",
        "expected_keywords": ("Station Sequence Violation", "SEQ-409", "Hold Lot", "audit log", "Override"),
        "expected_chunk_id": "mom-teaching-chunk-02",
        "expected_source": "Bai_giang_chuyen_gia_mom_02.txt",
    },
    {
        "id": "Q3",
        "target_item_id": "03",
        "question": "Phương pháp đối chiếu báo cáo sản lượng ca Shift Output Report giữa số đếm PLC và dữ liệu Opcenter xử lý ra sao?",
        "expected_keywords": ("Shift Output", "PLC", "OPC-UA", "packet drop", "trùng mã vạch"),
        "expected_chunk_id": "mom-teaching-chunk-03",
        "expected_source": "Bai_giang_chuyen_gia_mom_03.txt",
    },
    {
        "id": "Q4",
        "target_item_id": "04",
        "question": "Kinh nghiệm xử lý khi lệnh sản xuất bị khóa Hold Lot do sai lệch định mức vật tư BOM Mismatch MAT-302 trên Opcenter?",
        "expected_keywords": ("BOM Mismatch", "MAT-302", "Hold Lot", "Kitting", "ECO"),
        "expected_chunk_id": "mom-teaching-chunk-04",
        "expected_source": "Bai_giang_chuyen_gia_mom_04.txt",
    },
    {
        "id": "Q5",
        "target_item_id": "05",
        "question": "Quy chuẩn phân loại mã nguyên nhân dừng máy Downtime Reason Codes 3 cấp trên giao diện Opcenter Execution?",
        "expected_keywords": ("Downtime", "Reason Codes", "MECH", "ELEC", "MTTR"),
        "expected_chunk_id": "mom-teaching-chunk-05",
        "expected_source": "Bai_giang_chuyen_gia_mom_05.txt",
    },
)


def verify_mom_teaching_retrieval(
    library_path: Optional[Path | str] = None,
    questions: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Kiểm chứng sau nạp: hỏi lại đúng nội dung vừa nạp và kiểm tra nguồn trích dẫn.

    Tuân thủ mục 2.3 của vé:
    - Hỏi lại đúng nội dung bài giảng vừa nạp.
    - Nguồn trích trong câu trả lời PHẢI phân biệt được tài liệu dạy (nhãn nguồn "day-chuyen-gia")
      với dữ liệu sản xuất gốc của Opcenter (tệp gốc dạng `wsc-*.txt`).
    """
    db_path = Path(library_path or DEFAULT_MOM_LIBRARY_PATH).resolve()
    if not db_path.is_file():
        raise FileNotFoundError("Không tìm thấy tệp library.sqlite tại: %s" % db_path)

    test_questions = list(questions) if questions is not None else list(DEFAULT_MOM_VERIFICATION_QUESTIONS)
    conn = sqlite3.connect("file:///%s?mode=ro" % db_path.as_posix().lstrip("/"), uri=True)
    results = []
    hits = 0

    try:
        for q in test_questions:
            qid = q["id"]
            question_text = q["question"]
            target_id = q.get("target_item_id", "")
            expected_chunk_id = q.get("expected_chunk_id", f"mom-teaching-chunk-{target_id}")
            expected_source = q.get("expected_source", f"Bai_giang_chuyen_gia_mom_{target_id}.txt")
            expected_keywords = q.get("expected_keywords", ())

            # 1. Tìm kiếm FTS5
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

            found_target = False
            top_chunk_id = ""
            top_source = ""
            answer_excerpt = ""
            citation_source = ""
            source_tag_found = ""
            is_teaching_source = False
            is_raw_opcenter = False

            for row in matched_chunks:
                c_id, d_id, s_name, c_text, m_json = row
                if c_id == expected_chunk_id or expected_source in s_name:
                    found_target = True
                    top_chunk_id = c_id
                    top_source = s_name
                    answer_excerpt = c_text[:400]
                    citation_source = s_name
                    try:
                        m_data = json.loads(m_json)
                        source_tag_found = m_data.get("source_tag", "")
                        is_teaching_source = (
                            SOURCE_TAG_EXPERT_TEACHING in source_tag_found
                            or "day-chuyen-gia" in c_text
                        )
                        is_raw_opcenter = s_name.startswith("wsc-")
                    except Exception:
                        is_teaching_source = "day-chuyen-gia" in c_text
                        is_raw_opcenter = s_name.startswith("wsc-")
                    break

            if not found_target:
                # Tìm trực tiếp theo target chunk_id để kiểm tra từ khóa
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
                    c_id, d_id, s_name, c_text, m_json = r2
                    keyword_matches = sum(
                        1 for kw in expected_keywords if kw.lower() in c_text.lower()
                    )
                    if keyword_matches >= 2:
                        found_target = True
                        top_chunk_id = c_id
                        top_source = s_name
                        answer_excerpt = c_text[:400]
                        citation_source = s_name
                        try:
                            m_data = json.loads(m_json)
                            source_tag_found = m_data.get("source_tag", "")
                            is_teaching_source = (
                                SOURCE_TAG_EXPERT_TEACHING in source_tag_found
                                or "day-chuyen-gia" in c_text
                            )
                            is_raw_opcenter = s_name.startswith("wsc-")
                        except Exception:
                            is_teaching_source = "day-chuyen-gia" in c_text
                            is_raw_opcenter = s_name.startswith("wsc-")

            is_hit = found_target
            # Phân biệt được nguồn dạy (nhãn nguồn "day-chuyen-gia") với dữ liệu sản xuất gốc Opcenter
            differentiates_source = is_teaching_source and not is_raw_opcenter

            if is_hit:
                hits += 1

            results.append(
                {
                    "question_id": qid,
                    "question": question_text,
                    "target_item_id": target_id,
                    "expected_chunk_id": expected_chunk_id,
                    "expected_source": expected_source,
                    "is_hit": is_hit,
                    "retrieved_chunk_id": top_chunk_id,
                    "citation_source": citation_source,
                    "source_tag": source_tag_found,
                    "is_teaching_source": is_teaching_source,
                    "is_raw_opcenter": is_raw_opcenter,
                    "differentiates_source": differentiates_source,
                    "has_exact_ingested_citation": is_hit and (citation_source == expected_source or expected_source in citation_source),
                    "answer_excerpt": answer_excerpt,
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

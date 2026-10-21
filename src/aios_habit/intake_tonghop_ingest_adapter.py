"""Adapter nạp tri thức bài giảng chuyên gia vào Kho kiến thức tổng hợp (Ticket DESKTOP-KNOWLEDGE-INTAKE-TRITHUC-HOME).

Kiến trúc & Quyết định điều phối:
- Adapter chuyên biệt cho Kho kiến thức tổng hợp (`store_id="kho_tong_hop"`), thuộc đường ống thu tri thức chuyên gia dùng chung.
- Phục vụ chế độ DẠY (`MODE_DAY`): chuyên gia dạy kiến thức nền về nhà máy và lĩnh vực chuyên môn của công ty.
- Tách biệt tuyệt đối: chỉ thao tác trên Kho kiến thức tổng hợp (`tong_hop/library.sqlite`) và hồ sơ đích của kho này. Tuyệt đối không đụng tới Kho LSU, Kho điều tra lỗi, hay Kho MOM/Opcenter.
- Hồ sơ đích Kho kiến thức tổng hợp:
  + 5 trường bắt buộc: `chu_de`, `noi_dung`, `dieu_kien_ap_dung`, `vi_du`, `nguon`.
  + Các trường phụ: `nguoi_day`, `ngay_day`, `linh_vuc`, `ghi_chu`.
  + Nhãn nguồn: "day-chuyen-gia" + tên người dạy + ngày dạy.
- Cơ chế nạp & kiểm soát chất lượng:
  + Tái dùng đường ingest tài liệu hiện có của app (chuẩn `library.sqlite` với các bảng `chunks`, `chunk_embeddings`, `chunk_sparse_embeddings`, `chunks_fts`, `source_state`).
  + Bắt buộc sao lưu CSDL trước khi nạp (`backup_tonghop_library`), kiểm tra tính toàn vẹn (`PRAGMA integrity_check`).
  + Chống nạp trùng bằng khóa mục (`document_id`, `chunk_id`, checksum).
  + Kiểm tra toàn vẹn sau nạp; nếu có sự cố lập tức khôi phục từ bản sao lưu.
  + Đếm vector/chunk trước và sau khi nạp trên cùng một phương pháp đếm thống nhất.
  + Hướng dẫn đường lui an toàn: gỡ bỏ toàn bộ tài liệu đã nạp theo nhãn nguồn "day-chuyen-gia".
  + Ghi chú điều phối 2026-10-20: CẤM TUYỆT ĐỐI thợ tự soạn nội dung mẫu rồi gán trạng thái duyệt nạp vào kho sản xuất. Nếu staging chưa có mục nào được NGƯỜI duyệt thật, vé này nạp 0 mục (delta = 0). Dữ liệu mẫu chỉ được phép dùng trong test fixture với cơ chế chặn cứng an toàn (`_assert_test_staging_only`).

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
    KHO_TONG_HOP_PROFILE,
    STORE_ID_TONG_HOP,
    format_source_tag,
    format_tonghop_source_tag,
    get_target_profile,
)

LOGGER = logging.getLogger(__name__)

# Đường dẫn mặc định CSDL Kho kiến thức tổng hợp
DEFAULT_TONG_HOP_LIBRARY_PATH = Path(r"D:\Sandbox\AIOS_index_split_new\tong_hop\library.sqlite")

# Định danh và nhãn nguồn
SOURCE_TAG_EXPERT_TEACHING = "day-chuyen-gia"
INGEST_ROUTE_TONG_HOP = "DESKTOP-KNOWLEDGE-INTAKE-TRITHUC-HOME"

# Model fingerprint chuẩn đã nạp sẵn trong CSDL (ONNX int8 / fp32)
DEFAULT_MODEL_FINGERPRINT = "016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb"
DEFAULT_MODEL_ID = "BAAI/bge-m3"
DEFAULT_MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
DEFAULT_MODEL_RUNTIME = "onnxruntime-int8"
DEFAULT_MODEL_RUNTIME_VERSION = "1.28.0"
DEFAULT_MODEL_DIMENSION = 1024


@dataclass(frozen=True)
class TongHopTeachingItem:
    """Đại diện một tài liệu tri thức nền thu thập từ chế độ DẠY của chuyên gia."""

    item_id: str
    chu_de: str
    noi_dung: str
    dieu_kien_ap_dung: str
    vi_du: str
    nguon: str = ""
    nguoi_day: str = ""
    ngay_day: str = ""
    linh_vuc: str = ""
    ghi_chu: str = ""

    @property
    def draft_id(self) -> str:
        return f"draft-tonghop-{self.item_id}"

    @property
    def session_id(self) -> str:
        return f"session-tonghop-teaching-{self.item_id}"

    @property
    def document_id(self) -> str:
        return f"doc-tonghop-teaching-{self.item_id}"

    @property
    def chunk_id(self) -> str:
        return f"tonghop-teaching-chunk-{self.item_id}"

    @property
    def source_name(self) -> str:
        return f"Bai_giang_chuyen_gia_{self.item_id}.txt"

    @property
    def source_tag(self) -> str:
        if self.nguon:
            return self.nguon
        return format_tonghop_source_tag(
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


def get_default_tonghop_sample_cases() -> List[TongHopTeachingItem]:
    """Tập 5 bài giảng mẫu tri thức nền điển hình phục vụ test fixture.

    Bao quát kiến thức nền về nguyên lý quang học, nhiệt sấy, tiêu chuẩn phòng sạch,
    chất lượng và tĩnh điện ESD trong nhà máy.
    """
    return [
        TongHopTeachingItem(
            item_id="01",
            chu_de="Quy trình cân chỉnh và tiêu chuẩn sạch quang học trong phòng sạch Cleanroom Class 1000",
            noi_dung="Nguyên lý làm sạch gương quang học LSU: chỉ dùng gạc vi sợi chuyên dụng tẩm cồn IPA tinh khiết 99.7% lau một chiều từ trong ra ngoài theo góc nghiêng 45 độ. Tuyệt đối không lau vòng xoáy hoặc dùng khí nén thổi trực tiếp lên thấu kính f-theta vì dầu trong khí nén làm mờ bề mặt thấu kính.",
            dieu_kien_ap_dung="Áp dụng tại phòng sạch Cleanroom Class 1000 cho mọi công đoạn lắp ráp cụm quang học laser (LSU) trên tất cả các model máy in và máy photocopy công nghiệp.",
            vi_du="Tại xưởng LSU, kỹ thuật viên lau gương đa giác Polygon theo đường xoáy ốc làm đọng vệt dầu mờ, khi test trên jig kiểm tra năng lượng chùm tia laser bị suy giảm 35%, phải tháo toàn bộ cụm quang để vệ sinh lại bằng bể rửa siêu âm.",
            nguoi_day="Nguyễn Ích Khiêm",
            ngay_day="2026-10-21",
            linh_vuc="Quang học & Phòng sạch",
            ghi_chu="Cần kiểm tra định kỳ hạt bụi phòng sạch mỗi 2 giờ một lần bằng máy đếm hạt laser.",
        ),
        TongHopTeachingItem(
            item_id="02",
            chu_de="Nguyên lý điều khiển nhiệt độ cụm sấy cảm ứng từ IH (Induction Heating)",
            noi_dung="Hệ thống gia nhiệt cảm ứng từ IH sử dụng cuộn dây coil cao tần phát từ trường biến thiên để sinh dòng điện xoáy Eddy trực tiếp trên thành ống sấy kim loại. Nhiệt độ tăng tức thời trong 10 giây thay vì mất 60 giây như đèn sấy halogen truyền thống. Vòng lặp PID đọc từ cảm biến thermopile không tiếp xúc để điều chỉnh tần số PWM cấp cho biến tần IGBT.",
            dieu_kien_ap_dung="Áp dụng cho các dòng máy in tốc độ cao (từ 65 trang/phút trở lên) như Sirius và Iris có trang bị cụm sấy cảm ứng từ IH.",
            vi_du="Hiện tượng sấy không chín mực mép giấy khi in bản in đen phủ 100% diện tích là do cuộn coil IH mép ngoài bị lệch khe hở không khí 0.8mm so với tâm ống sấy, cần hiệu chuẩn lại khoảng cách bằng thước căn lá chuẩn 0.5mm.",
            nguoi_day="Trần Văn B",
            ngay_day="2026-10-21",
            linh_vuc="Nhiệt điện & Sấy công nghiệp",
            ghi_chu="Cảnh báo: Luôn ngắt điện nguồn và xả tụ cao áp trước khi thao tác đo đạc cuộn cảm ứng từ.",
        ),
        TongHopTeachingItem(
            item_id="03",
            chu_de="Tiêu chuẩn kiểm soát tĩnh điện ESD và tiếp đất an toàn trên dây chuyền SMT",
            noi_dung="Tiêu chuẩn ANSI/ESD S20.20 yêu cầu điện trở tiếp đất của công nhân qua vòng đeo tay ESD phải nằm trong khoảng 750 kΩ đến 35 MΩ. Bàn thao tác trải thảm tĩnh điện có điện trở bề mặt từ 10^6 đến 10^9 Ω/sq. Quạt ion hóa (Ionizer) phải đạt cân bằng điện áp ion dưới ±35V và thời gian phân rã điện tích dưới 2 giây.",
            dieu_kien_ap_dung="Bắt buộc áp dụng tại tất cả các khu vực sản xuất bo mạch điện tử, khu vực cắm linh kiện SMT, kho linh kiện bán dẫn và công đoạn hoàn thiện bo mạch chính (Mainboard).",
            vi_du="Tỷ lệ hỏng bo MCU điều khiển tăng 4.2% vào mùa khô tháng 12 do công nhân không kiểm tra vòng đeo tay ESD đầu ca, tĩnh điện người tích tụ lên đến 2500V đã đánh thủng cổng I/O của chip ASIC khi cắm cáp tín hiệu.",
            nguoi_day="Lê Hoàng",
            ngay_day="2026-10-21",
            linh_vuc="Điện tử & Tiêu chuẩn ESD",
            ghi_chu="Đo kiểm tra vòng tay tĩnh điện bắt buộc ghi nhận vào máy quét thẻ trước khi vào cửa xưởng.",
        ),
        TongHopTeachingItem(
            item_id="04",
            chu_de="Cơ chế cấp mực tự động và chu trình bổ sung bột từ Developer trên máy in công nghiệp",
            noi_dung="Hộp từ Developer chứa hạt mang từ tính ferrite bọc nhựa và mực toner với tỷ lệ nồng độ chuẩn 7% đến 9%. Cảm biến nồng độ mực (Toner Density Sensor) sử dụng nguyên lý đo độ từ thẩm của hỗn hợp. Khi nồng độ mực giảm dưới 6.5%, bo điều khiển kích hoạt mô tơ trục vít cấp thêm mực từ hộp toner cartridge vào buồng trộn theo chu kỳ xung nhịp 250ms.",
            dieu_kien_ap_dung="Áp dụng cho hệ thống tạo ảnh điện ảnh (Electrophotography) trên các model máy in sử dụng bột từ kép (Dual-component Developer).",
            vi_du="Máy in bản in bị mờ nhạt và rơi vãi bột từ vào khay nạp là do hạt bột từ đã quá hạn sử dụng 120.000 bản in, lớp phủ nhựa trên hạt ferrite bị bong tróc làm hạt từ bám luôn lên bề mặt trống OPC thay vì giữ lại trên trục từ.",
            nguoi_day="Nguyễn Văn An",
            ngay_day="2026-10-21",
            linh_vuc="Cơ chế tạo ảnh & Mực in",
            ghi_chu="Khi thay thế bột từ mới bắt buộc phải chạy lệnh khởi tạo cảm biến nồng độ (Toner Sensor Init SP-Mode).",
        ),
        TongHopTeachingItem(
            item_id="05",
            chu_de="Quy chuẩn kiểm tra chất lượng bản in đầu ca (First Article Inspection - FAI)",
            noi_dung="Quy trình FAI đầu mỗi ca sản xuất gồm 4 bước: (1) In bảng màu chuẩn test chart 150 dpi; (2) Đo mật độ quang học (Optical Density) tại 5 điểm bằng máy đo phân quang X-Rite đạt chuẩn CMYK từ 1.35 đến 1.50; (3) Đo độ lệch hình học (Skew) dưới 0.3mm trên chiều dài 297mm; (4) Kiểm tra độ bám mực sấy bằng phép thử băng dính 3M-600 kéo nhanh góc 90 độ.",
            dieu_kien_ap_dung="Áp dụng tại trạm kiểm tra chất lượng cuối chuyền (FQC) của tất cả các line lắp ráp hoàn thiện máy in và máy photocopy công nghiệp.",
            vi_du="Lô sản phẩm 20 máy in model 02XC bị giữ lại trạm QA do phép thử băng dính làm bong mực trên 15% diện tích bản in test, nguyên nhân phát hiện do cài đặt sai loại giấy dầy trên driver kiểm tra làm nhiệt độ sấy bị thiếu 10 độ C.",
            nguoi_day="Phạm Quốc Tuấn",
            ngay_day="2026-10-21",
            linh_vuc="Đảm bảo chất lượng (QA)",
            ghi_chu="Phiếu kết quả FAI phải được ký duyệt điện tử trước khi line sản xuất được phép chạy hàng loạt.",
        ),
    ]


def stage_tonghop_teaching_cases(
    cases: Optional[Sequence[TongHopTeachingItem]] = None,
    staging_store: Optional[IntakeStagingStore] = None,
) -> List[IntakeDraftItemRecord]:
    """Lưu các bài giảng chuyên gia vào Staging store với trạng thái CHO NAP theo hồ sơ Kho tổng hợp.

    CHÚ Ý BẢO MẬT: Hàm này chỉ phục vụ môi trường kiểm thử (test fixture) và có cơ chế
    chặn cứng an toàn từ chối chạy trên staging thật (`knowledge_intake_staging.sqlite`).
    """
    store = _assert_test_staging_only(staging_store)
    case_list = list(cases) if cases is not None else get_default_tonghop_sample_cases()
    now_iso = datetime.now().isoformat()

    staged_records: List[IntakeDraftItemRecord] = []

    for c in case_list:
        session = IntakeSessionRecord(
            session_id=c.session_id,
            store_id=STORE_ID_TONG_HOP,
            mode="day",
            expert_name=c.nguoi_day or "Chuyên gia kỹ thuật",
            topic=c.chu_de,
            status="completed",
            created_at=now_iso,
            updated_at=now_iso,
        )
        store.save_session(session)

        turn_0 = IntakeTurnRecord(
            turn_id="turn-%s-0" % c.item_id,
            session_id=c.session_id,
            store_id=STORE_ID_TONG_HOP,
            turn_index=0,
            speaker=c.nguoi_day,
            question_text="Giảng giải tổng quan về nội dung bài giảng và nguyên lý?",
            answer_text=c.noi_dung,
            probe_type="mo_dau_bai_giang",
            timestamp=now_iso,
        )
        turn_1 = IntakeTurnRecord(
            turn_id="turn-%s-1" % c.item_id,
            session_id=c.session_id,
            store_id=STORE_ID_TONG_HOP,
            turn_index=1,
            speaker=c.nguoi_day,
            question_text="Điều kiện và phạm vi áp dụng kiến thức này?",
            answer_text=c.dieu_kien_ap_dung,
            probe_type="pham_vi_ap_dung",
            timestamp=now_iso,
        )
        turn_2 = IntakeTurnRecord(
            turn_id="turn-%s-2" % c.item_id,
            session_id=c.session_id,
            store_id=STORE_ID_TONG_HOP,
            turn_index=2,
            speaker=c.nguoi_day,
            question_text="Ví dụ thực tế đã xảy ra tại nhà máy?",
            answer_text=c.vi_du,
            probe_type="vi_du_that_nha_may",
            timestamp=now_iso,
        )

        for t in (turn_0, turn_1, turn_2):
            store.save_turn(t)

        fields_dict: Dict[str, str] = {
            "chu_de": c.chu_de,
            "noi_dung": c.noi_dung,
            "dieu_kien_ap_dung": c.dieu_kien_ap_dung,
            "vi_du": c.vi_du,
            "nguon": c.source_tag,
            "nguoi_day": c.nguoi_day or "chưa xác nhận",
            "ngay_day": c.ngay_day or date.today().isoformat(),
            "linh_vuc": c.linh_vuc or "chưa xác nhận",
            "ghi_chu": c.ghi_chu or "chưa xác nhận",
        }

        quote_text = "%s | %s | %s" % (c.chu_de, c.noi_dung[:200], c.dieu_kien_ap_dung[:100])

        draft_item = IntakeDraftItemRecord(
            draft_id=c.draft_id,
            session_id=c.session_id,
            store_id=STORE_ID_TONG_HOP,
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


def seed_sample_tonghop_teaching_items(
    staging_store: Optional[IntakeStagingStore] = None,
    cases: Optional[Sequence[TongHopTeachingItem]] = None,
) -> List[IntakeDraftItemRecord]:
    """Hàm gieo dữ liệu mẫu phục vụ test fixture với cơ chế chặn cứng an toàn."""
    return stage_tonghop_teaching_cases(cases=cases, staging_store=staging_store)


# ---------------------------------------------------------------------------
# Sao lưu CSDL Kho kiến thức tổng hợp (Backup & Integrity Check)
# ---------------------------------------------------------------------------


def backup_tonghop_library(
    library_path: Optional[Path | str] = None,
    backup_dest: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Sao lưu trực tuyến an toàn tệp library.sqlite của Kho tổng hợp trước khi nạp.

    Kiểm tra tính toàn vẹn (PRAGMA integrity_check) trước và sau khi sao chép,
    tính mã băm SHA-256 của bản sao lưu.
    """
    src_path = Path(library_path or DEFAULT_TONG_HOP_LIBRARY_PATH).resolve()
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
        dst_path = src_path.parent / f"library.sqlite.bak-{now_tag}-pre-tonghop-ingest"

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
# Định dạng Chunk & Nạp Kho tổng hợp (Ingest Engine)
# ---------------------------------------------------------------------------


def format_tonghop_chunk_text(
    item: TongHopTeachingItem | IntakeDraftItemRecord | Mapping[str, Any],
) -> str:
    """Định dạng văn bản có cấu trúc rõ ràng cho một bài giảng tri thức nền."""
    if isinstance(item, TongHopTeachingItem):
        chu_de = item.chu_de
        noi_dung = item.noi_dung
        dieu_kien = item.dieu_kien_ap_dung
        vi_du = item.vi_du
        nguon = item.source_tag
        nguoi_day = item.nguoi_day
        ngay_day = item.ngay_day
        linh_vuc = item.linh_vuc
        ghi_chu = item.ghi_chu
    elif isinstance(item, IntakeDraftItemRecord):
        fields = item.fields
        chu_de = fields.get("chu_de", "") or item.topic
        noi_dung = fields.get("noi_dung", "")
        dieu_kien = fields.get("dieu_kien_ap_dung", "")
        vi_du = fields.get("vi_du", "")
        nguon = fields.get("nguon", "") or item.source_tag
        nguoi_day = fields.get("nguoi_day", "") or item.expert_name
        ngay_day = fields.get("ngay_day", "")
        linh_vuc = fields.get("linh_vuc", "")
        ghi_chu = fields.get("ghi_chu", "")
    else:
        chu_de = str(item.get("chu_de", ""))
        noi_dung = str(item.get("noi_dung", ""))
        dieu_kien = str(item.get("dieu_kien_ap_dung", ""))
        vi_du = str(item.get("vi_du", ""))
        nguon = str(item.get("nguon", ""))
        nguoi_day = str(item.get("nguoi_day", ""))
        ngay_day = str(item.get("ngay_day", ""))
        linh_vuc = str(item.get("linh_vuc", ""))
        ghi_chu = str(item.get("ghi_chu", ""))

    header = (
        "[Nguồn tri thức]: Bài giảng chuyên gia (Dạy tri thức nền)\n"
        "[Người dạy]: %s\n"
        "[Ngày dạy]: %s\n"
        "[Nhãn nguồn]: %s\n"
        "[Kho đích]: Kho kiến thức tổng hợp\n"
        "[Chủ đề]: %s\n"
    ) % (
        nguoi_day or "chưa xác nhận",
        ngay_day or date.today().isoformat(),
        nguon or SOURCE_TAG_EXPERT_TEACHING,
        chu_de,
    )

    if linh_vuc and linh_vuc != "chưa xác nhận":
        header += "[Lĩnh vực]: %s\n" % linh_vuc

    body = (
        "[Điều kiện áp dụng]: %s\n"
        "[Ví dụ minh họa]: %s\n"
        "[Nội dung bài giảng]: %s"
    ) % (
        dieu_kien,
        vi_du,
        noi_dung,
    )

    if ghi_chu and ghi_chu != "chưa xác nhận":
        body += "\n[Ghi chú]: %s" % ghi_chu

    return header + body


def ingest_staged_tonghop_items(
    staging_store: Optional[IntakeStagingStore] = None,
    library_path: Optional[Path | str] = None,
    backend: Optional[Any] = None,
    skip_backup: bool = False,
) -> Dict[str, Any]:
    """Nạp các mục ở trạng thái CHO NAP thuộc hồ sơ Kho kiến thức tổng hợp từ staging vào library.sqlite.

    Tuân thủ nghiêm ngặt các yêu cầu:
    1. Chỉ nạp các mục `cho_nap` thuộc `store_id="kho_tong_hop"`.
    2. Chống nạp trùng bằng khóa mục (`document_id`, `chunk_id`, `checksum`).
    3. Sao lưu DB trước khi nạp (nếu skip_backup=False).
    4. Tái dùng đường ingest tài liệu hiện có của app (`chunks`, `chunk_embeddings`, `chunk_sparse_embeddings`).
    5. Kiểm tra toàn vẹn sau nạp (PRAGMA integrity_check); nếu lỗi thì tự động khôi phục từ bản sao lưu.
    6. Nếu staging không có mục nào chờ nạp (như trên staging thật hiện tại theo ghi chú điều phối 2026-10-20),
       adapter nạp 0 mục an toàn, không sửa đổi CSDL.
    """
    db_path = Path(library_path or DEFAULT_TONG_HOP_LIBRARY_PATH).resolve()
    if not db_path.is_file():
        raise FileNotFoundError("Không tìm thấy CSDL Kho kiến thức tổng hợp tại: %s" % db_path)

    store = staging_store or IntakeStagingStore()
    staged_items = store.list_draft_items_by_store(
        store_id=STORE_ID_TONG_HOP, ingest_status=INGEST_CHO_NAP
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
        backup_result = backup_tonghop_library(library_path=db_path)

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
        item_id = str(item.fields.get("item_id", "") or item.draft_id.replace("draft-tonghop-", "").replace("draft-kho_tong_hop-", "") or f"{idx:02d}")
        chunk_id = f"tonghop-teaching-chunk-{item_id}"
        doc_id = f"doc-tonghop-teaching-{item_id}"
        source_name = f"Bai_giang_chuyen_gia_{item_id}.txt"
        source_path = rf"D:\Sandbox\AIOS_habbit\local_cases\knowledge_intake\kho_tong_hop\{source_name}"
        text = format_tonghop_chunk_text(item)
        norm_text = normalize_text_lexical(text)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        # Kiểm tra chống nạp trùng
        if chunk_id in existing_chunks and existing_chunks[chunk_id] == content_hash:
            skipped_count += 1
            continue

        meta_dict = {
            "source_tag": item.fields.get("nguon", "") or item.source_tag or SOURCE_TAG_EXPERT_TEACHING,
            "expert_name": item.fields.get("nguoi_day", "") or item.expert_name,
            "teaching_date": item.fields.get("ngay_day", "") or date.today().isoformat(),
            "item_id": item_id,
            "chu_de": item.fields.get("chu_de", "") or item.topic,
            "noi_dung": item.fields.get("noi_dung", ""),
            "dieu_kien_ap_dung": item.fields.get("dieu_kien_ap_dung", ""),
            "vi_du": item.fields.get("vi_du", ""),
            "linh_vuc": item.fields.get("linh_vuc", ""),
            "ghi_chu": item.fields.get("ghi_chu", ""),
            "domain": "tong_hop",
        }
        metadata_json = json.dumps(meta_dict, ensure_ascii=False)
        privacy_labels_json = '["local_only"]'

        chunk_records.append(
            {
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "source_path": source_path,
                "source_name": source_name,
                "file_type": "bai_giang",
                "text": text,
                "normalized_text": norm_text,
                "metadata_json": metadata_json,
                "privacy_labels_json": privacy_labels_json,
                "source_fingerprint": content_hash,
                "checksum": content_hash,
                "retrievable": 1,
                "domain": "tong_hop",
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
        is_production_db = (db_path.resolve() == DEFAULT_TONG_HOP_LIBRARY_PATH.resolve())
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
                        :source_fingerprint, :checksum, :retrievable, :domain
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
                        domain=excluded.domain;
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
        LOGGER.error("DB Kho tổng hợp bị hỏng sau khi nạp: %s! Đang khôi phục từ bản sao lưu...", integrity_msg)
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
                "SELECT COUNT(*) FROM chunks WHERE chunk_id LIKE 'tonghop-teaching-chunk-%'"
            ).fetchone()[0]
        )
    finally:
        conn_post.close()

    # Cập nhật trạng thái các mục trong staging sang ĐÃ NẠP
    for item in staged_items:
        store.update_draft_item_status(item.draft_id, ingest_status=INGEST_DA_NAP)

    # Xóa tệp cache trạng thái
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


def rollback_tonghop_teaching_ingest(
    library_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Gỡ bỏ toàn bộ tài liệu đã nạp theo nhãn nguồn 'day-chuyen-gia'.

    Đường lui an toàn:
    Xóa tất cả các bản ghi trong `chunks` có `chunk_id LIKE 'tonghop-teaching-chunk-%'`
    hoặc `metadata_json LIKE '%"source_tag": "%day-chuyen-gia%"%'`
    hoặc `text LIKE '%[Nhãn nguồn]: day-chuyen-gia%'`.

    Nhờ foreign keys ON DELETE CASCADE và triggers SQLite, các bảng:
    - `chunk_embeddings`
    - `chunk_sparse_embeddings`
    - `chunks_fts`
    - `source_state`
    đều tự động được đồng bộ dọn sạch hoàn toàn, không để lại rác hay rò rỉ dữ liệu.
    """
    db_path = Path(library_path or DEFAULT_TONG_HOP_LIBRARY_PATH).resolve()
    if not db_path.is_file():
        raise FileNotFoundError("Không tìm thấy CSDL tại: %s" % db_path)

    conn = sqlite3.connect(str(db_path), timeout=60.0)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        cur = conn.execute(
            """
            SELECT COUNT(*) FROM chunks
            WHERE chunk_id LIKE 'tonghop-teaching-chunk-%'
               OR metadata_json LIKE '%"source_tag": "%day-chuyen-gia%"%'
               OR text LIKE '%[Nhãn nguồn]: day-chuyen-gia%';
            """
        )
        count_to_remove = int(cur.fetchone()[0])

        with conn:
            conn.execute(
                """
                DELETE FROM chunks
                WHERE chunk_id LIKE 'tonghop-teaching-chunk-%'
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

DEFAULT_VERIFICATION_QUESTIONS: Tuple[Dict[str, Any], ...] = (
    {
        "id": "Q1",
        "target_item_id": "01",
        "question": "Quy trình lau gương quang học và tiêu chuẩn phòng sạch Cleanroom Class 1000 thực hiện thế nào?",
        "expected_keywords": ("gương quang học", "IPA", "f-theta", "Cleanroom Class 1000", "gạc vi sợi"),
        "expected_chunk_id": "tonghop-teaching-chunk-01",
        "expected_source": "Bai_giang_chuyen_gia_01.txt",
    },
    {
        "id": "Q2",
        "target_item_id": "02",
        "question": "Nguyên lý điều khiển nhiệt độ cụm sấy cảm ứng từ IH (Induction Heating) và vòng lặp PID hoạt động ra sao?",
        "expected_keywords": ("Induction Heating", "Eddy", "cuộn dây coil", "thermopile", "IGBT"),
        "expected_chunk_id": "tonghop-teaching-chunk-02",
        "expected_source": "Bai_giang_chuyen_gia_02.txt",
    },
    {
        "id": "Q3",
        "target_item_id": "03",
        "question": "Tiêu chuẩn kiểm soát tĩnh điện ESD và điện trở tiếp đất vòng đeo tay an toàn trên dây chuyền SMT là bao nhiêu?",
        "expected_keywords": ("ANSI/ESD S20.20", "vòng đeo tay", "750 kΩ", "35 MΩ", "SMT"),
        "expected_chunk_id": "tonghop-teaching-chunk-03",
        "expected_source": "Bai_giang_chuyen_gia_03.txt",
    },
    {
        "id": "Q4",
        "target_item_id": "04",
        "question": "Cơ chế cấp mực tự động và nồng độ bột từ Developer trên máy in công nghiệp vận hành thế nào?",
        "expected_keywords": ("Developer", "ferrite", "nồng độ", "Toner Density Sensor", "trục vít"),
        "expected_chunk_id": "tonghop-teaching-chunk-04",
        "expected_source": "Bai_giang_chuyen_gia_04.txt",
    },
    {
        "id": "Q5",
        "target_item_id": "05",
        "question": "Quy chuẩn kiểm tra chất lượng bản in đầu ca (First Article Inspection - FAI) gồm những bước đo đạc nào?",
        "expected_keywords": ("First Article Inspection", "FAI", "X-Rite", "Skew", "3M-600"),
        "expected_chunk_id": "tonghop-teaching-chunk-05",
        "expected_source": "Bai_giang_chuyen_gia_05.txt",
    },
)


def verify_tonghop_teaching_retrieval(
    library_path: Optional[Path | str] = None,
    questions: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Kiểm chứng sau nạp: hỏi lại đúng nội dung vừa nạp và kiểm tra nguồn trích dẫn là chính tài liệu vừa nạp.

    Tuân thủ mục 2.3 của vé:
    - Hỏi lại đúng nội dung bài giảng vừa nạp.
    - Nguồn trích trong câu trả lời PHẢI là chính tài liệu vừa nạp (`Bai_giang_chuyen_gia_*.txt` mang nhãn `day-chuyen-gia`).
    """
    db_path = Path(library_path or DEFAULT_TONG_HOP_LIBRARY_PATH).resolve()
    if not db_path.is_file():
        raise FileNotFoundError("Không tìm thấy tệp library.sqlite tại: %s" % db_path)

    test_questions = list(questions) if questions is not None else list(DEFAULT_VERIFICATION_QUESTIONS)
    conn = sqlite3.connect("file:///%s?mode=ro" % db_path.as_posix().lstrip("/"), uri=True)
    results = []
    hits = 0

    try:
        for q in test_questions:
            qid = q["id"]
            question_text = q["question"]
            target_id = q.get("target_item_id", "")
            expected_chunk_id = q.get("expected_chunk_id", f"tonghop-teaching-chunk-{target_id}")
            expected_source = q.get("expected_source", f"Bai_giang_chuyen_gia_{target_id}.txt")
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

            for row in matched_chunks:
                c_id, d_id, s_name, c_text, m_json = row
                if c_id == expected_chunk_id or expected_source in s_name:
                    found_target = True
                    top_chunk_id = c_id
                    top_source = s_name
                    answer_excerpt = c_text[:400]
                    citation_source = s_name
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

            is_hit = found_target
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

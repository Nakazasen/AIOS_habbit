"""Cơ chế Hồ sơ đích (Target Profile) theo kho tri thức.

Kiến trúc: MỘT đường ống thu tri thức chuyên gia dùng chung cho MỌI kho.
Mỗi kho khai báo một HỒ SƠ ĐÍCH độc lập:
- Khuôn tổng hợp (các trường bắt buộc + trường phụ).
- Đường nạp (ingest route identifier).
- Tiền tố nhãn nguồn (source prefix) và nhãn nguồn thống nhất:
  loại (phong-van / day) + tên người + ngày + kho đích.

Thêm kho mới = thêm một hồ sơ khai báo vào Registry, không sửa lõi bộ máy.
Hồ sơ mẫu đầu tiên: Kho LSU (5 trường bắt buộc Bước 0 + trường phụ).

Tương thích Python 3.11: không dùng f-string nhiều dòng (PEP 701), không type statement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class TargetFieldSpec:
    """Khai báo một trường trong khuôn tổng hợp của hồ sơ đích."""

    name: str
    label_vi: str
    is_mandatory: bool = False
    description_vi: str = ""
    guidance_vi: str = ""
    default_value: str = "chưa xác nhận"

    def clean_value(self, raw: Any) -> str:
        """Chuẩn hóa giá trị trường; nếu trống thì trả về giá trị mặc định."""
        text = str(raw or "").strip()
        if not text:
            return self.default_value
        return text


@dataclass(frozen=True)
class TargetProfile:
    """Hồ sơ đích khai báo cho một kho tri thức."""

    store_id: str
    display_name: str
    description: str
    ingest_route: str
    source_prefix: str
    fields: Tuple[TargetFieldSpec, ...] = field(default_factory=tuple)

    @property
    def required_fields(self) -> Tuple[str, ...]:
        """Danh sách tên các trường bắt buộc."""
        return tuple(f.name for f in self.fields if f.is_mandatory)

    @property
    def optional_fields(self) -> Tuple[str, ...]:
        """Danh sách tên các trường phụ (không bắt buộc)."""
        return tuple(f.name for f in self.fields if not f.is_mandatory)

    @property
    def field_map(self) -> Dict[str, TargetFieldSpec]:
        """Tra cứu nhanh trường theo tên."""
        return {f.name: f for f in self.fields}

    def validate_record(self, record: Mapping[str, Any]) -> Tuple[bool, List[str]]:
        """Kiểm tra một bản ghi có đủ các trường bắt buộc không.

        Trả về (ok, missing_fields).
        """
        missing: List[str] = []
        for req_name in self.required_fields:
            val = str(record.get(req_name) or "").strip()
            if not val or val.lower() == "chưa xác nhận":
                spec = self.field_map.get(req_name)
                label = spec.label_vi if spec else req_name
                missing.append(label)
        return len(missing) == 0, missing

    def calculate_completeness(self, record: Mapping[str, Any]) -> float:
        """Tính tỉ lệ hoàn thiện các trường bắt buộc (0.0 đến 1.0)."""
        reqs = self.required_fields
        if not reqs:
            return 1.0
        filled = 0
        for req_name in reqs:
            val = str(record.get(req_name) or "").strip()
            if val and val.lower() != "chưa xác nhận":
                filled += 1
        return filled / float(len(reqs))


# ---------------------------------------------------------------------------
# Hồ sơ mẫu 1: Kho LSU (5 trường bắt buộc Bước 0 + trường phụ)
# ---------------------------------------------------------------------------

STORE_ID_LSU = "kho_lsu"
INGEST_ROUTE_LSU = "DESKTOP-LSU-EXPERT-INTERVIEW-INGEST-HOME"

KHO_LSU_FIELDS: Tuple[TargetFieldSpec, ...] = (
    # 5 trường bắt buộc của Bước 0
    TargetFieldSpec(
        name="ma_loi",
        label_vi="Mã lỗi",
        is_mandatory=True,
        description_vi="Mã lỗi tiêu chuẩn (ví dụ C7620, C3501, F000)",
        guidance_vi="Mã lỗi quan sát được trên máy hoặc hệ thống",
    ),
    TargetFieldSpec(
        name="hien_tuong",
        label_vi="Hiện tượng",
        is_mandatory=True,
        description_vi="Hiện tượng vật lý / dấu hiệu phát sinh lỗi",
        guidance_vi="Mô tả cụ thể hiện tượng lỗi xảy ra như thế nào",
    ),
    TargetFieldSpec(
        name="nguyen_nhan",
        label_vi="Nguyên nhân",
        is_mandatory=True,
        description_vi="Nguyên nhân gốc rễ theo phân tích kỹ thuật 4M/Why-Why",
        guidance_vi="Căn nguyên kỹ thuật trực tiếp gây ra lỗi",
    ),
    TargetFieldSpec(
        name="doi_sach",
        label_vi="Đối sách",
        is_mandatory=True,
        description_vi="Biện pháp xử lý / khắc phục đã kiểm chứng",
        guidance_vi="Hành động cụ thể đã làm để giải quyết triệt để lỗi",
    ),
    TargetFieldSpec(
        name="cong_doan",
        label_vi="Công đoạn",
        is_mandatory=True,
        description_vi="Vị trí hoặc công đoạn phát sinh lỗi trong dây chuyền",
        guidance_vi="Tên công đoạn sản xuất nơi xảy ra sự cố",
    ),
    # Các trường phụ
    TargetFieldSpec(
        name="model",
        label_vi="Model máy",
        is_mandatory=False,
        description_vi="Dòng máy / model sản phẩm liên quan",
        guidance_vi="Tên model máy (ví dụ C7620, C3501, Sirius)",
    ),
    TargetFieldSpec(
        name="line",
        label_vi="Line sản xuất",
        is_mandatory=False,
        description_vi="Line sản xuất nơi xảy ra sự việc",
        guidance_vi="Số hoặc tên line (ví dụ Line 1, Line 3)",
    ),
    TargetFieldSpec(
        name="dau_hieu_som",
        label_vi="Dấu hiệu sớm",
        is_mandatory=False,
        description_vi="Dấu hiệu nhận biết sớm trước khi lỗi phát sinh",
        guidance_vi="Hiện tượng báo trước giúp phòng ngừa",
    ),
    TargetFieldSpec(
        name="ghi_chu",
        label_vi="Ghi chú",
        is_mandatory=False,
        description_vi="Ghi chú thêm về điều kiện vận hành, cảnh báo đặc biệt",
        guidance_vi="Thông tin bổ sung từ kinh nghiệm thực tế",
    ),
)

KHO_LSU_PROFILE = TargetProfile(
    store_id=STORE_ID_LSU,
    display_name="Kho LSU",
    description="Kho tri thức ca lỗi LSU (5 trường bắt buộc Bước 0 + trường phụ)",
    ingest_route=INGEST_ROUTE_LSU,
    source_prefix="kho_lsu",
    fields=KHO_LSU_FIELDS,
)


# ---------------------------------------------------------------------------
# Hồ sơ mẫu 2: Kho điều tra lỗi (DESKTOP-KNOWLEDGE-INTAKE-DIEUTRALOI-HOME)
# Khuôn ca gồm 5 trường bắt buộc (mã lỗi, hiện tượng, nguyên nhân, đối sách,
# công đoạn) cộng các trường phụ (model, line, bộ phận phụ trách, ngày).
# ---------------------------------------------------------------------------

STORE_ID_DIEU_TRA_LOI = "kho_dieu_tra_loi"
INGEST_ROUTE_DIEU_TRA_LOI = "DESKTOP-KNOWLEDGE-INTAKE-DIEUTRALOI-HOME"

KHO_DIEU_TRA_LOI_FIELDS: Tuple[TargetFieldSpec, ...] = (
    # 5 trường bắt buộc theo vé DESKTOP-KNOWLEDGE-INTAKE-DIEUTRALOI-HOME
    TargetFieldSpec(
        name="ma_loi",
        label_vi="Mã lỗi",
        is_mandatory=True,
        description_vi="Mã lỗi tiêu chuẩn (ví dụ C7620, C2340, C4001, F000, J0411)",
        guidance_vi="Mã lỗi kỹ thuật quan sát được trên máy hoặc hệ thống",
    ),
    TargetFieldSpec(
        name="hien_tuong",
        label_vi="Hiện tượng",
        is_mandatory=True,
        description_vi="Hiện tượng vật lý / dấu hiệu phát sinh lỗi",
        guidance_vi="Mô tả cụ thể hiện tượng lỗi xảy ra như thế nào",
    ),
    TargetFieldSpec(
        name="nguyen_nhan",
        label_vi="Nguyên nhân",
        is_mandatory=True,
        description_vi="Nguyên nhân gốc rễ theo phân tích kỹ thuật 4M / Why-Why",
        guidance_vi="Căn nguyên kỹ thuật trực tiếp gây ra lỗi",
    ),
    TargetFieldSpec(
        name="doi_sach",
        label_vi="Đối sách",
        is_mandatory=True,
        description_vi="Biện pháp xử lý / đối sách khắc phục đã kiểm chứng",
        guidance_vi="Hành động cụ thể đã làm để giải quyết triệt để lỗi",
    ),
    TargetFieldSpec(
        name="cong_doan",
        label_vi="Công đoạn",
        is_mandatory=True,
        description_vi="Công đoạn sản xuất / vị trí phát sinh lỗi trong dây chuyền",
        guidance_vi="Tên công đoạn sản xuất nơi xảy ra sự cố",
    ),
    # 4 trường phụ theo vé
    TargetFieldSpec(
        name="model",
        label_vi="Model",
        is_mandatory=False,
        description_vi="Dòng máy / model sản phẩm liên quan",
        guidance_vi="Tên model máy (ví dụ Sirius, Iris, 02XC)",
    ),
    TargetFieldSpec(
        name="line",
        label_vi="Line",
        is_mandatory=False,
        description_vi="Line sản xuất nơi xảy ra sự việc",
        guidance_vi="Số hoặc tên line (ví dụ Line 1, Line 2, C33-A2)",
    ),
    TargetFieldSpec(
        name="bo_phan_phu_trach",
        label_vi="Bộ phận phụ trách",
        is_mandatory=False,
        description_vi="Bộ phận chuyên môn phụ trách điều tra hoặc khắc phục",
        guidance_vi="Tên bộ phận (ví dụ PE, QA, EE, MT, LSU)",
    ),
    TargetFieldSpec(
        name="ngay",
        label_vi="Ngày",
        is_mandatory=False,
        description_vi="Ngày phát sinh hoặc ngày phỏng vấn chuyên gia (YYYY-MM-DD)",
        guidance_vi="Ngày tháng theo định dạng chuẩn ISO YYYY-MM-DD",
    ),
)

KHO_DIEU_TRA_LOI_PROFILE = TargetProfile(
    store_id=STORE_ID_DIEU_TRA_LOI,
    display_name="Kho điều tra lỗi",
    description="Kho tri thức ca điều tra lỗi (5 trường bắt buộc + 4 trường phụ)",
    ingest_route=INGEST_ROUTE_DIEU_TRA_LOI,
    source_prefix="kho_dieu_tra_loi",
    fields=KHO_DIEU_TRA_LOI_FIELDS,
)


# ---------------------------------------------------------------------------
# Hồ sơ mẫu 3: Kho kiến thức tổng hợp (DESKTOP-KNOWLEDGE-INTAKE-TRITHUC-HOME)
# Phục vụ chế độ DẠY: chuyên gia dạy kiến thức nền về nhà máy và lĩnh vực công ty.
# Khuôn tài liệu tri thức gồm 5 trường bắt buộc:
#   chủ đề, nội dung, điều kiện áp dụng, ví dụ, nguồn.
# Cộng các trường phụ bổ trợ: người dạy, ngày dạy, lĩnh vực, ghi chú.
# ---------------------------------------------------------------------------

STORE_ID_TONG_HOP = "kho_tong_hop"
INGEST_ROUTE_TONG_HOP = "DESKTOP-KNOWLEDGE-INTAKE-TRITHUC-HOME"

KHO_TONG_HOP_FIELDS: Tuple[TargetFieldSpec, ...] = (
    # 5 trường bắt buộc theo vé DESKTOP-KNOWLEDGE-INTAKE-TRITHUC-HOME
    TargetFieldSpec(
        name="chu_de",
        label_vi="Chủ đề",
        is_mandatory=True,
        description_vi="Chủ đề hoặc tiêu đề bài học tri thức nền",
        guidance_vi="Chủ đề kiến thức nền về nhà máy hoặc lĩnh vực chuyên môn của công ty",
    ),
    TargetFieldSpec(
        name="noi_dung",
        label_vi="Nội dung",
        is_mandatory=True,
        description_vi="Nội dung chi tiết của bài giảng / kiến thức chuyên gia",
        guidance_vi="Mô tả nguyên lý, khái niệm, bản chất kỹ thuật, quy trình tiêu chuẩn",
    ),
    TargetFieldSpec(
        name="dieu_kien_ap_dung",
        label_vi="Điều kiện áp dụng",
        is_mandatory=True,
        description_vi="Điều kiện, phạm vi hoặc trường hợp áp dụng kiến thức này",
        guidance_vi="Các dòng máy, công đoạn, môi trường hoặc điều kiện kỹ thuật phù hợp",
    ),
    TargetFieldSpec(
        name="vi_du",
        label_vi="Ví dụ",
        is_mandatory=True,
        description_vi="Ví dụ thực tế hoặc tình huống minh họa cụ thể",
        guidance_vi="Tình huống thực tế đã xảy ra tại nhà máy làm rõ cho bài học",
    ),
    TargetFieldSpec(
        name="nguon",
        label_vi="Nguồn",
        is_mandatory=True,
        description_vi="Nguồn gốc tri thức: chuyên gia giảng dạy, tài liệu hoặc quy chuẩn",
        guidance_vi="Gắn nhãn định danh nguồn day-chuyen-gia + tên người dạy + ngày dạy",
    ),
    # Các trường phụ hỗ trợ metadata
    TargetFieldSpec(
        name="nguoi_day",
        label_vi="Người dạy",
        is_mandatory=False,
        description_vi="Tên chuyên gia hoặc giảng viên chia sẻ kiến thức",
        guidance_vi="Họ tên chuyên gia hoặc kỹ sư phụ trách bài giảng",
    ),
    TargetFieldSpec(
        name="ngay_day",
        label_vi="Ngày dạy",
        is_mandatory=False,
        description_vi="Ngày tháng thực hiện bài giảng (YYYY-MM-DD)",
        guidance_vi="Ngày tháng theo định dạng chuẩn ISO YYYY-MM-DD",
    ),
    TargetFieldSpec(
        name="linh_vuc",
        label_vi="Lĩnh vực",
        is_mandatory=False,
        description_vi="Lĩnh vực kiến thức nền (ví dụ: Cơ khí, Quang học, Điện tử, QA, Sản xuất)",
        guidance_vi="Phân loại lĩnh vực chuyên môn trong nhà máy",
    ),
    TargetFieldSpec(
        name="ghi_chu",
        label_vi="Ghi chú",
        is_mandatory=False,
        description_vi="Các điểm lưu ý, cảnh báo sai sót thường gặp hoặc thông tin bổ sung",
        guidance_vi="Kinh nghiệm thực tiễn hoặc điều kiện ngoại lệ",
    ),
)

KHO_TONG_HOP_PROFILE = TargetProfile(
    store_id=STORE_ID_TONG_HOP,
    display_name="Kho kiến thức tổng hợp",
    description="Kho tri thức nền tổng hợp phục vụ chế độ DẠY (khuôn: chủ đề, nội dung, điều kiện áp dụng, ví dụ, nguồn)",
    ingest_route=INGEST_ROUTE_TONG_HOP,
    source_prefix="kho_tong_hop",
    fields=KHO_TONG_HOP_FIELDS,
)

# ---------------------------------------------------------------------------
# Hồ sơ mẫu 4: Kho MOM/Opcenter (DESKTOP-KNOWLEDGE-INTAKE-MOM-HOME)
# Phục vụ chế độ DẠY: chuyên gia dạy tri thức về hệ thống MOM/Opcenter
# (cách đọc màn hình/báo cáo Opcenter, ý nghĩa các mã trạng thái, quy ước vận hành,
# kinh nghiệm xử lý tình huống trong hệ thống).
# Khuôn tài liệu tri thức gồm 4 trường bắt buộc:
#   chủ đề, nội dung, điều kiện áp dụng, nguồn.
# Cộng các trường phụ bổ trợ: người dạy, ngày dạy, phân hệ, màn hình, ghi chú.
# ---------------------------------------------------------------------------

STORE_ID_MOM = "kho_mom"
INGEST_ROUTE_MOM = "DESKTOP-KNOWLEDGE-INTAKE-MOM-HOME"

KHO_MOM_FIELDS: Tuple[TargetFieldSpec, ...] = (
    # 4 trường bắt buộc theo vé DESKTOP-KNOWLEDGE-INTAKE-MOM-HOME
    TargetFieldSpec(
        name="chu_de",
        label_vi="Chủ đề",
        is_mandatory=True,
        description_vi="Chủ đề bài học về hệ thống MOM/Opcenter (đọc màn hình/báo cáo, ý nghĩa mã trạng thái, quy ước vận hành)",
        guidance_vi="Chủ đề hoặc kỹ năng vận hành hệ thống MOM/Opcenter",
    ),
    TargetFieldSpec(
        name="noi_dung",
        label_vi="Nội dung",
        is_mandatory=True,
        description_vi="Nội dung chi tiết bài giảng của chuyên gia về hệ thống MOM/Opcenter",
        guidance_vi="Giải thích cách đọc, phân tích dữ liệu, quy ước và các bước thao tác trên Opcenter",
    ),
    TargetFieldSpec(
        name="dieu_kien_ap_dung",
        label_vi="Điều kiện áp dụng",
        is_mandatory=True,
        description_vi="Điều kiện, màn hình, phân hệ hoặc phạm vi áp dụng trong hệ thống Opcenter",
        guidance_vi="Màn hình, phân hệ sản xuất, dòng máy hoặc tình huống áp dụng cụ thể",
    ),
    TargetFieldSpec(
        name="nguon",
        label_vi="Nguồn",
        is_mandatory=True,
        description_vi="Nguồn gốc tri thức: chuyên gia giảng dạy về hệ thống MOM/Opcenter",
        guidance_vi="Gắn nhãn định danh nguồn day-chuyen-gia + tên người dạy + ngày dạy",
    ),
    # Các trường phụ hỗ trợ metadata
    TargetFieldSpec(
        name="nguoi_day",
        label_vi="Người dạy",
        is_mandatory=False,
        description_vi="Tên chuyên gia hoặc kỹ sư đào tạo hệ thống",
        guidance_vi="Họ tên chuyên gia hoặc kỹ sư phụ trách bài giảng",
    ),
    TargetFieldSpec(
        name="ngay_day",
        label_vi="Ngày dạy",
        is_mandatory=False,
        description_vi="Ngày tháng thực hiện bài giảng (YYYY-MM-DD)",
        guidance_vi="Ngày tháng theo định dạng chuẩn ISO YYYY-MM-DD",
    ),
    TargetFieldSpec(
        name="phan_he",
        label_vi="Phân hệ",
        is_mandatory=False,
        description_vi="Phân hệ chức năng trong MOM/Opcenter (WIP, Tracking, Quality, Dispatching, Material)",
        guidance_vi="Tên phân hệ hoặc module nghiệp vụ trên hệ thống",
    ),
    TargetFieldSpec(
        name="man_hinh",
        label_vi="Màn hình / Báo cáo",
        is_mandatory=False,
        description_vi="Tên màn hình, giao diện chức năng hoặc mã báo cáo Opcenter",
        guidance_vi="Màn hình thao tác hoặc mã báo cáo liên quan",
    ),
    TargetFieldSpec(
        name="ghi_chu",
        label_vi="Ghi chú",
        is_mandatory=False,
        description_vi="Lưu ý vận hành, quy ước phối hợp hoặc cảnh báo sai lệch",
        guidance_vi="Kinh nghiệm thực tiễn hoặc điều kiện ngoại lệ",
    ),
)

KHO_MOM_PROFILE = TargetProfile(
    store_id=STORE_ID_MOM,
    display_name="Kho MOM/Opcenter",
    description="Kho tri thức về hệ thống MOM/Opcenter phục vụ chế độ DẠY (khuôn: chủ đề, nội dung, điều kiện áp dụng, nguồn)",
    ingest_route=INGEST_ROUTE_MOM,
    source_prefix="kho_mom",
    fields=KHO_MOM_FIELDS,
)



# ---------------------------------------------------------------------------
# Nhãn nguồn thống nhất (Source Tag Formatter)
# Format: loai (phong-van / day) + ten nguoi + ngay + kho dich
# ---------------------------------------------------------------------------


def normalize_slug(text: str) -> str:
    """Chuẩn hóa chuỗi dùng cho định danh nhãn nguồn."""
    cleaned = re.sub(r"[^\w\s-]", "", str(text or "")).strip()
    return re.sub(r"[\s_]+", "_", cleaned).lower() or "khong_ro"


def format_source_tag(
    mode: str,
    expert_name: str,
    date_str: Optional[str] = None,
    store_id: str = STORE_ID_LSU,
) -> str:
    """Định dạng nhãn nguồn thống nhất cho mọi mục tri thức.

    Cấu trúc chuẩn: `<loai> | <ten_nguoi> | <ngay> | <kho_dich>`
    Ví dụ: `phong-van | Nguyen Van A | 2026-10-18 | kho_lsu`
    Hoặc chế độ dạy: `day-chuyen-gia | Nguyen Van A | 2026-10-21 | kho_tong_hop`
    """
    m_raw = str(mode or "").strip().lower()
    if m_raw in ("day", "teaching", "day-chuyen-gia"):
        m = "day-chuyen-gia" if str(store_id or "").strip() == STORE_ID_TONG_HOP else "day"
    else:
        m = "phong-van"
    exp = str(expert_name or "").strip() or "chưa xác nhận"
    d = str(date_str or "").strip() or date.today().isoformat()
    st = str(store_id or "").strip() or STORE_ID_LSU
    return "%s | %s | %s | %s" % (m, exp, d, st)


def format_tonghop_source_tag(
    expert_name: str,
    date_str: Optional[str] = None,
) -> str:
    """Nhãn nguồn định danh chuẩn cho Kho kiến thức tổng hợp: 'day-chuyen-gia | <ten_nguoi_day> | <ngay_day>'."""
    exp = str(expert_name or "").strip() or "chưa xác nhận"
    d = str(date_str or "").strip() or date.today().isoformat()
    return "day-chuyen-gia | %s | %s" % (exp, d)


def format_mom_source_tag(
    expert_name: str,
    date_str: Optional[str] = None,
) -> str:
    """Nhãn nguồn định danh chuẩn cho Kho MOM/Opcenter: 'day-chuyen-gia | <ten_nguoi_day> | <ngay_day>'."""
    exp = str(expert_name or "").strip() or "chưa xác nhận"
    d = str(date_str or "").strip() or date.today().isoformat()
    return "day-chuyen-gia | %s | %s" % (exp, d)


def parse_source_tag(tag: str) -> Dict[str, str]:
    """Phân rã nhãn nguồn thống nhất thành các thành phần."""
    parts = [p.strip() for p in str(tag or "").split("|")]
    if len(parts) >= 4:
        return {
            "mode": parts[0],
            "expert_name": parts[1],
            "date": parts[2],
            "store_id": parts[3],
        }
    if len(parts) == 3 and parts[0] == "day-chuyen-gia":
        guessed_store = STORE_ID_MOM if any(k in tag.lower() for k in ("mom", "opcenter")) else STORE_ID_TONG_HOP
        return {
            "mode": parts[0],
            "expert_name": parts[1],
            "date": parts[2],
            "store_id": guessed_store,
        }
    return {
        "mode": parts[0] if len(parts) > 0 else "phong-van",
        "expert_name": parts[1] if len(parts) > 1 else "chưa xác nhận",
        "date": parts[2] if len(parts) > 2 else "",
        "store_id": parts[3] if len(parts) > 3 else STORE_ID_LSU,
    }


# ---------------------------------------------------------------------------
# Registry quản lý hồ sơ đích theo kho
# ---------------------------------------------------------------------------


class TargetProfileRegistry:
    """Registry khai báo các hồ sơ đích.

    Thêm kho mới sau này chỉ cần gọi `register()` hồ sơ mới,
    không cần thay đổi mã nguồn bộ máy thu tri thức.
    """

    def __init__(self) -> None:
        self._profiles: Dict[str, TargetProfile] = {}
        self.reset()

    def register(self, profile: TargetProfile) -> None:
        """Đăng ký một hồ sơ đích mới hoặc cập nhật hồ sơ hiện có."""
        sid = str(profile.store_id or "").strip()
        if not sid:
            raise ValueError("Hồ sơ đích phải có store_id hợp lệ.")
        self._profiles[sid] = profile

    def get(self, store_id: str) -> Optional[TargetProfile]:
        """Lấy hồ sơ đích theo store_id."""
        return self._profiles.get(str(store_id or "").strip())

    def list_profiles(self) -> Tuple[TargetProfile, ...]:
        """Liệt kê toàn bộ hồ sơ đích đã đăng ký."""
        return tuple(self._profiles.values())

    def has_profile(self, store_id: str) -> bool:
        """Kiểm tra kho đã có hồ sơ đích chưa."""
        return str(store_id or "").strip() in self._profiles

    def clear(self) -> None:
        """Xóa toàn bộ hồ sơ (dùng trong test cách ly)."""
        self._profiles.clear()

    def reset(self) -> None:
        """Khôi phục lại cấu hình mặc định (hồ sơ mẫu Kho LSU, Kho điều tra lỗi, Kho kiến thức tổng hợp)."""
        self._profiles.clear()
        self.register(KHO_LSU_PROFILE)
        self.register(KHO_DIEU_TRA_LOI_PROFILE)
        self.register(KHO_TONG_HOP_PROFILE)
        self.register(KHO_MOM_PROFILE)


# Global registry instance
_REGISTRY = TargetProfileRegistry()


def get_target_profile(store_id: str) -> Optional[TargetProfile]:
    """Lấy hồ sơ đích từ registry toàn cục."""
    return _REGISTRY.get(store_id)


def register_target_profile(profile: TargetProfile) -> None:
    """Đăng ký hồ sơ đích mới vào registry toàn cục."""
    _REGISTRY.register(profile)


def list_target_profiles() -> Tuple[TargetProfile, ...]:
    """Danh sách các hồ sơ đích đã đăng ký."""
    return _REGISTRY.list_profiles()


def reset_target_profiles() -> None:
    """Khôi phục registry toàn cục về mặc định (Kho LSU)."""
    _REGISTRY.reset()

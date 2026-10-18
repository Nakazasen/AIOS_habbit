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
# Hồ sơ mẫu: Kho LSU (5 trường bắt buộc Bước 0 + trường phụ)
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
    """
    m = "day" if str(mode or "").strip().lower() in ("day", "teaching") else "phong-van"
    exp = str(expert_name or "").strip() or "chưa xác nhận"
    d = str(date_str or "").strip() or date.today().isoformat()
    st = str(store_id or "").strip() or STORE_ID_LSU
    return "%s | %s | %s | %s" % (m, exp, d, st)


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
        """Khôi phục lại cấu hình mặc định (hồ sơ mẫu Kho LSU)."""
        self._profiles.clear()
        self.register(KHO_LSU_PROFILE)


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

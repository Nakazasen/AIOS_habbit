"""Module xử lý lệnh chat /huongdan (DESKTOP-HOME-HUONGDAN-COMMAND).

Cung cấp tính năng tra cứu cẩm nang Hướng dẫn sử dụng AIOS trực tiếp trong khung chat:
- Gõ `/huongdan` (không tham số): hiển thị danh mục các phần (Giới thiệu, Phần A-G, Phụ lục, Toàn bộ)
  dưới dạng chip gợi ý.
- Bấm chip hoặc gõ `/huongdan <mục>` (vd: `/huongdan A1`, `/huongdan C4`, `/huongdan B`, `/huongdan tat-ca`):
  hiển thị đầy đủ nội dung mục đó với đầy đủ chữ và ảnh minh họa được nhúng trực tiếp (base64 data URI).
- Chọn 'Toàn bộ' (`/huongdan tat-ca`): hiển thị toàn bộ 7 phần + phụ lục không cắt xén.
- Xử lý cục bộ 100%: không gọi backend AI/C-Agent, không tạo lượt hỏi-đáp giả trong lịch sử SQLite.
- Ghi nhận metrics cục bộ (Vòng lặp cải thiện liên tục) vào `local_cases/huongdan_events.jsonl`
  và `local_cases/huongdan_metrics.json`.
"""

from __future__ import annotations

import base64
import datetime
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

_MANUAL_CACHE: Optional[Dict[str, Any]] = None
_IMAGE_B64_CACHE: Dict[str, str] = {}


def _get_project_root() -> Path:
    """Trả về thư mục gốc của repository code AIOS_habbit."""
    return Path(__file__).resolve().parent.parent.parent


def _get_local_cases_dir() -> Path:
    """Trả về thư mục local_cases để lưu metrics và logs cục bộ."""
    env_dir = os.environ.get("AIOS_LOCAL_CASES_DIR")
    if env_dir and Path(env_dir).is_dir():
        return Path(env_dir)
    p = _get_project_root() / "local_cases"
    p.mkdir(parents=True, exist_ok=True)
    return p


def resolve_manual_path() -> Path:
    """Xác định đường dẫn tệp cẩm nang hướng dẫn sử dụng."""
    env_path = os.environ.get("AIOS_MANUAL_PATH")
    if env_path and Path(env_path).is_file():
        return Path(env_path)

    default_path = _get_project_root() / "docs" / "huong-dan-su-dung" / "HUONG-DAN-SU-DUNG-AIOS.md"
    if default_path.is_file():
        return default_path

    # Fallback dự phòng kho điều phối nếu có
    coor_path = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua\huong-dan-su-dung\HUONG-DAN-SU-DUNG-AIOS.md")
    if coor_path.is_file():
        return coor_path

    return default_path


def resolve_images_dir() -> Path:
    """Xác định đường dẫn thư mục ảnh minh họa."""
    env_img = os.environ.get("AIOS_MANUAL_IMAGES_DIR")
    if env_img and Path(env_img).is_dir():
        return Path(env_img)

    default_dir = _get_project_root() / "docs" / "huong-dan-su-dung" / "images"
    if default_dir.is_dir():
        return default_dir

    coor_dir = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua\huong-dan-su-dung\images")
    if coor_dir.is_dir():
        return coor_dir

    return default_dir


def _get_image_b64(rel_path: str, img_dir: Path) -> Optional[str]:
    """Đọc ảnh PNG và chuyển thành base64 data URI (có cache trong bộ nhớ)."""
    if rel_path in _IMAGE_B64_CACHE:
        return _IMAGE_B64_CACHE[rel_path]

    filename = Path(rel_path).name
    target_file = img_dir / filename
    if not target_file.is_file():
        return None

    try:
        data = target_file.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        data_uri = f"data:image/png;base64,{b64}"
        _IMAGE_B64_CACHE[rel_path] = data_uri
        return data_uri
    except Exception:
        return None


def embed_images_as_base64(markdown_text: str, img_dir: Path) -> str:
    """Thay thế tất cả đường dẫn ảnh `images/*.png` thành base64 data URI."""
    def _repl(match: re.Match) -> str:
        alt = match.group(1)
        src = match.group(2)
        b64_uri = _get_image_b64(src, img_dir)
        if b64_uri:
            return f"![{alt}]({b64_uri})"
        return match.group(0)

    return re.sub(r"!\[(.*?)\]\((images/[^)]+)\)", _repl, markdown_text)


def load_and_parse_manual() -> Dict[str, Any]:
    """Đọc và bóc tách toàn bộ cẩm nang theo từng phần và từng mục."""
    global _MANUAL_CACHE
    if _MANUAL_CACHE is not None:
        return _MANUAL_CACHE

    doc_path = resolve_manual_path()
    img_dir = resolve_images_dir()

    if not doc_path.is_file():
        return {
            "title": "Cẩm nang hướng dẫn sử dụng AIOS",
            "danh_muc": "⚠️ Không tìm thấy tệp cẩm nang hướng dẫn tại docs/huong-dan-su-dung/",
            "sections": {},
            "subsections": {},
            "toan_bo": "Không tìm thấy nội dung cẩm nang.",
        }

    raw_text = doc_path.read_text(encoding="utf-8")
    full_embedded = embed_images_as_base64(raw_text, img_dir)

    # 1. Bóc tách các phần chính
    sections: Dict[str, str] = {}

    idx_intro = full_embedded.find("## 1. GIỚI THIỆU CHUNG")
    idx_p1 = full_embedded.find("## PHẦN 1: NHÓM A")
    idx_p2 = full_embedded.find("## PHẦN 2: NHÓM B")
    idx_p3 = full_embedded.find("## PHẦN 3: NHÓM C")
    idx_p4 = full_embedded.find("## PHẦN 4: NHÓM D")
    idx_p5 = full_embedded.find("## PHẦN 5: NHÓM E")
    idx_p6 = full_embedded.find("## PHẦN 6: NHÓM F")
    idx_p7 = full_embedded.find("## PHẦN 7: NHÓM G")
    idx_app = full_embedded.find("## 8. PHỤ LỤC:")

    if idx_intro != -1 and idx_p1 != -1:
        sections["gioi_thieu"] = full_embedded[idx_intro:idx_p1].strip()
    if idx_p1 != -1 and idx_p2 != -1:
        sections["A"] = full_embedded[idx_p1:idx_p2].strip()
    if idx_p2 != -1 and idx_p3 != -1:
        sections["B"] = full_embedded[idx_p2:idx_p3].strip()
    if idx_p3 != -1 and idx_p4 != -1:
        sections["C"] = full_embedded[idx_p3:idx_p4].strip()
    if idx_p4 != -1 and idx_p5 != -1:
        sections["D"] = full_embedded[idx_p4:idx_p5].strip()
    if idx_p5 != -1 and idx_p6 != -1:
        sections["E"] = full_embedded[idx_p5:idx_p6].strip()
    if idx_p6 != -1 and idx_p7 != -1:
        sections["F"] = full_embedded[idx_p6:idx_p7].strip()
    if idx_p7 != -1 and idx_app != -1:
        sections["G"] = full_embedded[idx_p7:idx_app].strip()
    if idx_app != -1:
        sections["phu_luc"] = full_embedded[idx_app:].strip()

    # 2. Bóc tách 44 tiểu mục (A1-A5, B1-B5, C1-C4, D1-D4, E1-E6, F1-F2, G1-G18)
    subsections: Dict[str, str] = {}
    matches = list(re.finditer(r"(### ([A-Ga-g]\d+)\..*?)(?=(?:\n### [A-Ga-g]\d+\.)|(?:\n## )|\Z)", full_embedded, re.DOTALL))
    for m in matches:
        key = m.group(2).upper()
        subsections[key] = m.group(1).strip()

    # 3. Tạo văn bản danh mục tổng quan
    danh_muc_text = (
        "## 📖 CẨM NANG HƯỚNG DẪN SỬ DỤNG SỔ CÁI AIOS\n\n"
        "Hệ thống trợ lý điều tra sự cố & giám sát sản xuất thông minh đã sẵn sàng. "
        "Bấm vào các nút gợi ý bên dưới hoặc gõ trực tiếp lệnh `/huongdan <mục>` "
        "(ví dụ: `/huongdan A1`, `/huongdan C4`, `/huongdan B`, `/huongdan tat-ca`):\n\n"
        "| Ký hiệu | Tên phân đoạn hướng dẫn | Phạm vi nội dung cốt lõi |\n"
        "| :--- | :--- | :--- |\n"
        "| **Giới thiệu** | Giới thiệu chung & Quy trình tác nghiệp | 3 nguyên tắc nền tảng & quy trình 5 bước |\n"
        "| **Phần A** | Nhóm A — Đường gửi & Khung chat | Chống gửi lặp, bấm chip khi nạp, sổ lạnh, bẫy nhịp người, thẻ 3 bước |\n"
        "| **Phần B** | Nhóm B — Hỏi đáp theo kho & Tra cứu số liệu | 4 kho tài liệu, Ground Truth, chuẩn hoá 'Vụ', cửa sổ thời gian, thuần Việt |\n"
        "| **Phần C** | Nhóm C — Nghiệp vụ điều tra sự cố Bước 1-5 | Cây 4M, log JIG SMA(20), báo cáo xu hướng định kỳ, thẻ cảnh báo tái phát C7620 |\n"
        "| **Phần D** | Nhóm D — Phản hồi đánh giá & Tự học | Thích/Không thích kèm lý do, hàng đợi chuyên gia, bản thảo, quản trị tự học |\n"
        "| **Phần E** | Nhóm E — Chế độ tìm kiếm & Hiển thị | Nấc thang 5 bậc, hỏi AI ngoài, Source Viewer, streaming, Command Code |\n"
        "| **Phần F** | Nhóm F — Quản lý sổ tay & Hội thoại | Tạo sổ/hội thoại mới, tiếp nối hội thoại cũ, quản lý đa luồng |\n"
        "| **Phần G** | Nhóm G — 18 tính năng nâng cao bổ sung | Đính kèm 64MB, OCR Indra, phỏng vấn LSU, Log Chart Builder, CSDL 30.075 ca |\n"
        "| **Phụ lục** | Bảng tra cứu nhanh các thao tác cốt lõi | Bảng tổng hợp thao tác, cú pháp lệnh và trạng thái xử lý |\n"
        "| **Toàn bộ** | Toàn bộ cẩm nang hướng dẫn | Xem liền mạch toàn bộ 7 phần và phụ lục (kèm 57 ảnh minh họa) |\n"
    )

    _MANUAL_CACHE = {
        "title": "Cẩm nang Hướng dẫn Sử dụng AIOS",
        "danh_muc": danh_muc_text,
        "sections": sections,
        "subsections": subsections,
        "toan_bo": full_embedded,
    }
    return _MANUAL_CACHE


def clear_manual_cache() -> None:
    """Test hook: xóa cache nội dung cẩm nang."""
    global _MANUAL_CACHE, _IMAGE_B64_CACHE
    _MANUAL_CACHE = None
    _IMAGE_B64_CACHE.clear()


def is_huongdan_command(text: str) -> bool:
    """Kiểm tra câu chat có phải là lệnh /huongdan hay không."""
    clean = str(text or "").strip()
    if not clean:
        return False
    # 1. Bắt đầu bằng /huongdan, /huong-dan, /help, /guide
    if re.match(r"^/(?:huongdan|huong-dan|guide|help)\b", clean, re.IGNORECASE):
        return True

    # 2. Các cụm từ lệnh tiếng Việt chính xác (không dấu hoặc có dấu)
    from aios_habit.chat_intent_router import _khong_dau
    from aios_habit.chat_action import is_document_lookup_query
    if is_document_lookup_query(clean):
        return False

    norm = _khong_dau(clean)
    if norm in (
        "huong dan", "huong dan su dung", "cam nang huong dan",
        "huong dan su dung aios", "cam nang aios", "xem huong dan",
        "huong dan aios", "mo huong dan", "danh muc huong dan",
    ):
        return True

    if norm.startswith(("huong dan ", "cam nang ")):
        sub = norm.split(maxsplit=2)[1] if len(norm.split()) >= 2 else ""
        if sub in ("a", "b", "c", "d", "e", "f", "g", "phu luc", "tat ca", "toan bo", "gioi thieu") or re.match(r"^[a-g]\d+$", sub):
            return True

    return False


def parse_huongdan_args(text: str) -> str:
    """Trích xuất mã phân đoạn hoặc mục từ lệnh /huongdan.

    Trả về:
    - "danh_muc": gõ `/huongdan` không tham số
    - "tat_ca": xem toàn bộ
    - "gioi_thieu": xem phần giới thiệu
    - "phu_luc": xem phụ lục
    - "A", "B", "C", "D", "E", "F", "G": xem cả phần
    - "A1", ..., "G18": xem từng tiểu mục cụ thể
    - "dong": đóng cẩm nang
    """
    clean = str(text or "").strip()
    m = re.match(r"^/(?:huongdan|huong-dan|guide|help)\s*(.*)$", clean, re.IGNORECASE)
    if m:
        arg = m.group(1).strip()
    else:
        from aios_habit.chat_intent_router import _khong_dau
        norm = _khong_dau(clean)
        for pref in ("huong dan su dung aios", "huong dan su dung", "cam nang huong dan", "huong dan aios", "huong dan", "cam nang"):
            if norm.startswith(pref):
                arg = norm[len(pref):].strip()
                break
        else:
            arg = ""

    arg_norm = arg.lower().replace("-", " ").replace("_", " ").strip()
    if not arg_norm or arg_norm in ("danh muc", "menu", "list", "muc luc"):
        return "danh_muc"

    if arg_norm in ("tat ca", "toan bo", "all", "full"):
        return "tat_ca"

    if arg_norm in ("gioi thieu", "intro", "mo dau", "quy trinh"):
        return "gioi_thieu"

    if arg_norm in ("phu luc", "appendix"):
        return "phu_luc"

    if arg_norm in ("dong", "close", "tat", "exit", "quit"):
        return "dong"

    # Kiểm tra tiểu mục A1..G18
    sub_m = re.match(r"^([a-g]\d{1,2})$", arg_norm)
    if sub_m:
        return sub_m.group(1).upper()

    # Kiểm tra phần chính A..G
    part_m = re.match(r"^(?:phan\s+|nhom\s+)?([a-g])$", arg_norm)
    if part_m:
        return part_m.group(1).upper()

    return "danh_muc"


def get_chips_for_section(section_key: str) -> List[Tuple[str, str]]:
    """Tạo danh sách các chip gợi ý điều hướng theo cơ chế chip hiện có."""
    if section_key == "danh_muc":
        return [
            ("📖 Giới thiệu", "/huongdan gioi-thieu"),
            ("🅰️ Phần A (Khung chat)", "/huongdan A"),
            ("🅱️ Phần B (Tra cứu & Kho)", "/huongdan B"),
            ("🅲 Phần C (Điều tra sự cố)", "/huongdan C"),
            ("🅳 Phần D (Đánh giá & Tự học)", "/huongdan D"),
            ("🅴 Phần E (Tìm kiếm & Hiển thị)", "/huongdan E"),
            ("🅵 Phần F (Quản lý sổ tay)", "/huongdan F"),
            ("🅶 Phần G (Tính năng nâng cao)", "/huongdan G"),
            ("📑 Phụ lục", "/huongdan phu-luc"),
            ("📚 Toàn bộ", "/huongdan tat-ca"),
        ]

    if section_key == "A":
        return [
            ("A1. Chống gửi lặp", "/huongdan A1"),
            ("A2. Bấm chip khi nạp", "/huongdan A2"),
            ("A3. Sổ lạnh giữ chữ", "/huongdan A3"),
            ("A4. Bẫy nhịp người", "/huongdan A4"),
            ("A5. Thẻ 3 bước", "/huongdan A5"),
            ("📖 Danh mục", "/huongdan"),
            ("📚 Toàn bộ", "/huongdan tat-ca"),
        ]

    if section_key == "B":
        return [
            ("B1. 4 kho tri thức", "/huongdan B1"),
            ("B2. Ground Truth", "/huongdan B2"),
            ("B3. Nhãn Vụ chuẩn", "/huongdan B3"),
            ("B4. Cửa sổ thời gian", "/huongdan B4"),
            ("B5. Thuần Việt", "/huongdan B5"),
            ("📖 Danh mục", "/huongdan"),
            ("📚 Toàn bộ", "/huongdan tat-ca"),
        ]

    if section_key == "C":
        return [
            ("C1. Phân tầng B3", "/huongdan C1"),
            ("C2. Log JIG SMA20", "/huongdan C2"),
            ("C3. Báo cáo định kỳ", "/huongdan C3"),
            ("C4. Cảnh báo tái phát C7620", "/huongdan C4"),
            ("📖 Danh mục", "/huongdan"),
            ("📚 Toàn bộ", "/huongdan tat-ca"),
        ]

    if section_key == "D":
        return [
            ("D1. Thích/Không thích", "/huongdan D1"),
            ("D2. Hàng đợi chuyên gia", "/huongdan D2"),
            ("D3. Tầng bản thảo", "/huongdan D3"),
            ("D4. Quản trị tự học", "/huongdan D4"),
            ("📖 Danh mục", "/huongdan"),
            ("📚 Toàn bộ", "/huongdan tat-ca"),
        ]

    if section_key == "E":
        return [
            ("E1. 5 bậc trả lời", "/huongdan E1"),
            ("E2. Chế độ AI ngoài", "/huongdan E2"),
            ("E3. Source Viewer", "/huongdan E3"),
            ("E4. Streaming", "/huongdan E4"),
            ("E5. 3 chế độ tìm", "/huongdan E5"),
            ("E6. Command Code", "/huongdan E6"),
            ("📖 Danh mục", "/huongdan"),
            ("📚 Toàn bộ", "/huongdan tat-ca"),
        ]

    if section_key == "F":
        return [
            ("F1. Tạo sổ & hội thoại", "/huongdan F1"),
            ("F2. Tiếp nối hội thoại", "/huongdan F2"),
            ("📖 Danh mục", "/huongdan"),
            ("📚 Toàn bộ", "/huongdan tat-ca"),
        ]

    if section_key == "G":
        return [
            ("G1. Đính kèm 64MB", "/huongdan G1"),
            ("G2. Tạo ca điều tra", "/huongdan G2"),
            ("G6. Log Chart Builder", "/huongdan G6"),
            ("G7. Cảnh báo RT", "/huongdan G7"),
            ("G17. Định tuyến lỗi", "/huongdan G17"),
            ("G18. CSDL 30.075 ca", "/huongdan G18"),
            ("📖 Danh mục", "/huongdan"),
            ("📚 Toàn bộ", "/huongdan tat-ca"),
        ]

    if section_key == "gioi_thieu":
        return [
            ("🅰️ Xem Phần A", "/huongdan A"),
            ("📖 Về danh mục", "/huongdan"),
            ("📚 Xem Toàn bộ", "/huongdan tat-ca"),
        ]

    if section_key == "phu_luc":
        return [
            ("📖 Về danh mục", "/huongdan"),
            ("📚 Xem Toàn bộ", "/huongdan tat-ca"),
        ]

    if section_key == "tat_ca":
        return [
            ("📖 Về danh mục", "/huongdan"),
            ("🅰️ Phần A", "/huongdan A"),
            ("🅱️ Phần B", "/huongdan B"),
            ("🅲 Phần C", "/huongdan C"),
            ("🅶 Phần G", "/huongdan G"),
        ]

    # Tiểu mục cụ thể (vd C4)
    part_letter = section_key[0] if section_key else "A"
    return [
        ("📖 Về danh mục", "/huongdan"),
        (f"Trở lại Phần {part_letter}", f"/huongdan {part_letter}"),
        ("📚 Xem Toàn bộ", "/huongdan tat-ca"),
    ]


class HuongDanResult:
    """Kết quả xử lý lệnh /huongdan."""

    def __init__(self, section_key: str, markdown_content: str, chips: List[Tuple[str, str]]):
        self.section_key = section_key
        self.markdown_content = markdown_content
        self.chips = chips
        self.is_close = (section_key == "dong")


def record_huongdan_metric(cmd: str, section_key: str, conversation_id: str = "") -> None:
    """Ghi nhận sự kiện gọi lệnh /huongdan vào local_cases (Vòng lặp cải thiện liên tục)."""
    try:
        lc_dir = _get_local_cases_dir()
        events_file = lc_dir / "huongdan_events.jsonl"
        metrics_file = lc_dir / "huongdan_metrics.json"

        now_iso = datetime.datetime.now().astimezone().isoformat()
        evt = {
            "timestamp": now_iso,
            "command": cmd,
            "section": section_key,
            "conversation_id": conversation_id,
        }

        with open(events_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(evt, ensure_ascii=False) + "\n")

        # Cập nhật số liệu tích lũy
        metrics = {"total_calls": 0, "by_section": {}, "last_called_at": now_iso}
        if metrics_file.is_file():
            try:
                metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        metrics["total_calls"] = metrics.get("total_calls", 0) + 1
        sec_dict = metrics.setdefault("by_section", {})
        sec_dict[section_key] = sec_dict.get(section_key, 0) + 1
        metrics["last_called_at"] = now_iso

        metrics_file.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def get_huongdan_metrics() -> Dict[str, Any]:
    """Đọc số liệu thống kê lượt sử dụng lệnh /huongdan."""
    metrics_file = _get_local_cases_dir() / "huongdan_metrics.json"
    if metrics_file.is_file():
        try:
            return json.loads(metrics_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"total_calls": 0, "by_section": {}}


def handle_huongdan_command(text: str, conversation_id: str = "") -> HuongDanResult:
    """Xử lý lệnh /huongdan và trả về nội dung hoàn chỉnh kèm chip điều hướng."""
    target_key = parse_huongdan_args(text)
    record_huongdan_metric(text, target_key, conversation_id)

    if target_key == "dong":
        return HuongDanResult(
            section_key="dong",
            markdown_content="*Đã đóng cẩm nang hướng dẫn sử dụng.*",
            chips=[],
        )

    parsed = load_and_parse_manual()
    chips = get_chips_for_section(target_key)

    if target_key == "danh_muc":
        content = parsed["danh_muc"]
    elif target_key == "tat_ca":
        content = (
            "# 📚 TOÀN BỘ CẨM NANG HƯỚNG DẪN SỬ DỤNG SỔ CÁI AIOS\n\n"
            "*Hiển thị đầy đủ tất cả các phần tác nghiệp và 57 ảnh chụp minh họa thực tế.*\n\n---\n\n"
            + parsed["toan_bo"]
        )
    elif target_key in parsed["sections"]:
        content = parsed["sections"][target_key]
    elif target_key in parsed["subsections"]:
        content = parsed["subsections"][target_key]
    else:
        content = (
            f"⚠️ Không tìm thấy mục `{target_key}` trong cẩm nang hướng dẫn.\n\n"
            + parsed["danh_muc"]
        )
        target_key = "danh_muc"
        chips = get_chips_for_section("danh_muc")

    return HuongDanResult(
        section_key=target_key,
        markdown_content=content,
        chips=chips,
    )


def register() -> None:
    """Tự đăng ký với khung chat_action (khả năng tương thích mở rộng)."""
    try:
        from aios_habit.chat_action import (
            BLOCK_MARKDOWN,
            ChatAction,
            ChatActionBlock,
            ChatActionOutcome,
            ChatActionRequest,
            register_action,
        )

        def _action_handler(req: ChatActionRequest) -> Optional[ChatActionOutcome]:
            res = handle_huongdan_command(req.question, conversation_id=req.conversation_id)
            return ChatActionOutcome(
                action="huong_dan",
                title="Cẩm nang Hướng dẫn sử dụng AIOS",
                blocks=(ChatActionBlock(kind=BLOCK_MARKDOWN, text=res.markdown_content),),
            )

        register_action(
            ChatAction(
                name="huong_dan",
                title="Cẩm nang Hướng dẫn sử dụng AIOS",
                hints=(
                    "/huongdan",
                    "/huong-dan",
                    "huong dan su dung aios",
                    "cam nang aios",
                    "danh muc huong dan",
                ),
                handler=_action_handler,
                description="Tra cứu cẩm nang hướng dẫn sử dụng AIOS",
            )
        )
    except Exception:
        pass

"""Module xử lý lệnh chat hướng dẫn sử dụng 3 ngôn ngữ Việt/Trung/Nhật (DESKTOP-HOME-HUONGDAN-I18N).

Cung cấp tính năng tra cứu cẩm nang Hướng dẫn sử dụng AIOS trực tiếp trong khung chat theo 3 ngôn ngữ:
- Gõ `/huongdan` (tiếng Việt): hiển thị cẩm nang tiếng Việt (HUONG-DAN-SU-DUNG-AIOS.md).
- Gõ `/使用指南` (tiếng Trung): hiển thị cẩm nang tiếng Trung (HUONG-DAN-SU-DUNG-AIOS-ZH.md).
- Gõ `/使い方` (tiếng Nhật): hiển thị cẩm nang tiếng Nhật (HUONG-DAN-SU-DUNG-AIOS-JA.md).
- Bấm chip hoặc gõ `<lệnh> <mục>` (vd: `/huongdan C4`, `/使い方 C4`, `/使用指南 C4`):
  hiển thị đầy đủ nội dung mục đó bằng ngôn ngữ tương ứng kèm ảnh minh họa nhúng trực tiếp (base64 data URI).
- Xem toàn bộ (`tat-ca`, `toan-bo`, `全体`, `全部`): hiển thị toàn bộ 7 phần + phụ lục kèm 57 ảnh minh họa.
- Xử lý cục bộ 100%: không gọi backend AI/C-Agent, không tạo lượt hỏi-đáp giả trong lịch sử SQLite.
- Ghi nhận metrics cục bộ có trường ngôn ngữ vào `local_cases/huongdan_events.jsonl`
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

_MANUAL_CACHE: Dict[str, Dict[str, Any]] = {}
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


def resolve_manual_path(lang: str = "vi") -> Path:
    """Xác định đường dẫn tệp cẩm nang hướng dẫn sử dụng theo ngôn ngữ."""
    norm_lang = (lang or "vi").strip().lower()
    if norm_lang == "ja":
        fname = "HUONG-DAN-SU-DUNG-AIOS-JA.md"
        env_var = "AIOS_MANUAL_PATH_JA"
    elif norm_lang == "zh":
        fname = "HUONG-DAN-SU-DUNG-AIOS-ZH.md"
        env_var = "AIOS_MANUAL_PATH_ZH"
    else:
        fname = "HUONG-DAN-SU-DUNG-AIOS.md"
        env_var = "AIOS_MANUAL_PATH"

    env_path = os.environ.get(env_var)
    if env_path and Path(env_path).is_file():
        return Path(env_path)

    default_path = _get_project_root() / "docs" / "huong-dan-su-dung" / fname
    if default_path.is_file():
        return default_path

    # Fallback dự phòng kho điều phối nếu có
    coor_path = Path(rf"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua\huong-dan-su-dung\{fname}")
    if coor_path.is_file():
        return coor_path

    return default_path


def resolve_images_dir() -> Path:
    """Xác định đường dẫn thư mục ảnh minh họa (dùng chung 57 ảnh cho cả 3 ngôn ngữ)."""
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


def detect_huongdan_language(text: str) -> str:
    """Phát hiện ngôn ngữ được yêu cầu dựa trên tiền tố câu lệnh."""
    clean = str(text or "").strip()
    if clean.startswith(("/使い方", "使い方")) or clean.startswith(("/つかいかた", "つかいかた")):
        return "ja"
    if clean.startswith(("/使用指南", "使用指南")):
        return "zh"
    return "vi"


def load_and_parse_manual(lang: str = "vi") -> Dict[str, Any]:
    """Đọc và bóc tách toàn bộ cẩm nang theo ngôn ngữ chỉ định."""
    global _MANUAL_CACHE
    norm_lang = (lang or "vi").strip().lower()
    if norm_lang not in ("vi", "zh", "ja"):
        norm_lang = "vi"

    if norm_lang in _MANUAL_CACHE:
        return _MANUAL_CACHE[norm_lang]

    doc_path = resolve_manual_path(norm_lang)
    img_dir = resolve_images_dir()

    if not doc_path.is_file():
        fallback_titles = {
            "vi": "Cẩm nang hướng dẫn sử dụng AIOS",
            "zh": "AIOS 台账综合使用指南",
            "ja": "AIOS台帳 総合利用マニュアル",
        }
        fallback_errors = {
            "vi": "⚠️ Không tìm thấy tệp cẩm nang hướng dẫn tại docs/huong-dan-su-dung/",
            "zh": "⚠️ 未在 docs/huong-dan-su-dung/ 找到使用指南文件",
            "ja": "⚠️ docs/huong-dan-su-dung/ にマニュアルファイルが見つかりません",
        }
        return {
            "title": fallback_titles.get(norm_lang, fallback_titles["vi"]),
            "danh_muc": fallback_errors.get(norm_lang, fallback_errors["vi"]),
            "sections": {},
            "subsections": {},
            "toan_bo": fallback_errors.get(norm_lang, fallback_errors["vi"]),
            "language": norm_lang,
        }

    raw_text = doc_path.read_text(encoding="utf-8")
    full_embedded = embed_images_as_base64(raw_text, img_dir)

    # 1. Bóc tách các phần chính theo thẻ tiêu đề chuẩn của từng ngôn ngữ
    sections: Dict[str, str] = {}
    if norm_lang == "ja":
        tag_intro = "## 1. 概要と作業手順"
        tag_p1 = "## 第1部：グループA"
        tag_p2 = "## 第2部：グループB"
        tag_p3 = "## 第3部：グループC"
        tag_p4 = "## 第4部：グループD"
        tag_p5 = "## 第5部：グループE"
        tag_p6 = "## 第6部：グループF"
        tag_p7 = "## 第7部：グループG"
        tag_app = "## 8. 付録"
        tag_cmd = "## 9. システムコマンド一覧"
    elif norm_lang == "zh":
        tag_intro = "## 1. 综合介绍与作业流程"
        tag_p1 = "## 第1部分:A组"
        tag_p2 = "## 第2部分:B组"
        tag_p3 = "## 第3部分:C组"
        tag_p4 = "## 第4部分:D组"
        tag_p5 = "## 第5部分:E组"
        tag_p6 = "## 第6部分:F组"
        tag_p7 = "## 第7部分:G组"
        tag_app = "## 8. 附录:"
        tag_cmd = "## 9. 系统命令目录"
    else:
        tag_intro = "## 1. GIỚI THIỆU CHUNG"
        tag_p1 = "## PHẦN 1: NHÓM A"
        tag_p2 = "## PHẦN 2: NHÓM B"
        tag_p3 = "## PHẦN 3: NHÓM C"
        tag_p4 = "## PHẦN 4: NHÓM D"
        tag_p5 = "## PHẦN 5: NHÓM E"
        tag_p6 = "## PHẦN 6: NHÓM F"
        tag_p7 = "## PHẦN 7: NHÓM G"
        tag_app = "## 8. PHỤ LỤC:"
        tag_cmd = "## 9. DANH MỤC LỆNH HỆ THỐNG"

    idx_intro = full_embedded.find(tag_intro)
    idx_p1 = full_embedded.find(tag_p1)
    idx_p2 = full_embedded.find(tag_p2)
    idx_p3 = full_embedded.find(tag_p3)
    idx_p4 = full_embedded.find(tag_p4)
    idx_p5 = full_embedded.find(tag_p5)
    idx_p6 = full_embedded.find(tag_p6)
    idx_p7 = full_embedded.find(tag_p7)
    idx_app = full_embedded.find(tag_app)
    idx_cmd = full_embedded.find(tag_cmd)

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
        if idx_cmd != -1:
            sections["phu_luc"] = full_embedded[idx_app:idx_cmd].strip()
            sections["lenh"] = full_embedded[idx_cmd:].strip()
        else:
            sections["phu_luc"] = full_embedded[idx_app:].strip()

    if "lenh" not in sections:
        from aios_habit.slash_command_catalog import generate_manual_commands_markdown
        sections["lenh"] = generate_manual_commands_markdown(norm_lang)
    sections["H"] = sections["lenh"]

    # 2. Bóc tách 44 tiểu mục (A1-A5, B1-B5, C1-C4, D1-D4, E1-E6, F1-F2, G1-G18)
    subsections: Dict[str, str] = {}
    matches = list(re.finditer(r"(### ([A-Ga-g]\d+)\..*?)(?=(?:\n### [A-Ga-g]\d+\.)|(?:\n## )|\Z)", full_embedded, re.DOTALL))
    for m in matches:
        key = m.group(2).upper()
        subsections[key] = m.group(1).strip()

    # 3. Tạo văn bản danh mục tổng quan theo ngôn ngữ
    if norm_lang == "ja":
        title_text = "AIOS台帳 総合利用マニュアル"
        danh_muc_text = (
            "## 📖 AIOS台帳 総合利用マニュアル\n\n"
            "スマート障害調査・生産監視アシスタントシステムが準備完了しました。"
            "下の候補ボタンをタップするか、直接コマンド `/使い方 <項目>` を入力してください"
            "（例：`/使い方 A1`、`/使い方 C4`、`/使い方 B`、`/使い方 tat-ca`）：\n\n"
            "| 記号 | ガイド区分 | コア内容範囲 |\n"
            "| :--- | :--- | :--- |\n"
            "| **概要** | 概要と作業手順 | 3つの基本原則と5ステップの業務手順 |\n"
            "| **グループA** | グループA ― 送信経路とチャット画面 | 重複送信防止、ロード中のチップタップ、コールドノート、人の入力リズム、3ステップカード |\n"
            "| **グループB** | グループB ― リポジトリ別Q&Aと標準数値の照会 | 4つの専門リポジトリ、Ground Truth、標準ラベル「件」、期間ウィンドウ、純粋言語正規化 |\n"
            "| **グループC** | グループC ― 障害調査業務ステップ1〜5 | 4Mツリー、JIG SMA(20)ログ、定期トレンドレポート、C7620再発警告カード |\n"
            "| **グループD** | グループD ― フィードバック評価と自己学習 | 高評価/低評価と4つの理由、専門家キュー、下書き層、自己学習管理 |\n"
            "| **グループE** | グループE ― 検索モードとスマート表示 | 5段階の回答ステップ、外部AI、Source Viewer、ストリーミング、Command Code |\n"
            "| **グループF** | グループF ― ノートと会話の管理 | 新規ノート/会話作成、過去の会話の再開、マルチスレッド管理 |\n"
            "| **グループG** | グループG ― 18の追加高度機能 | 64MB添付、Indra OCR、LSUインタビュー、Log Chart Builder、30.075件DB |\n"
            "| **付録** | コア操作クイックリファレンス表 | 操作一覧、コマンド構文、処理ステータスまとめ |\n"
            "| **コマンド一覧** | システムコマンド一覧（スラッシュコマンド） | 全8つのスラッシュコマンド、同等の自然言語、用途、必要なコンテキスト |\n"
            "| **全体** | マニュアル全体を表示 | 全7部および付録（57枚の実例図付き）をシームレスに表示 |\n"
        )
    elif norm_lang == "zh":
        title_text = "AIOS 台账综合使用指南"
        danh_muc_text = (
            "## 📖 AIOS 台账综合使用指南\n\n"
            "故障调查与智能生产监控辅助系统已就绪。"
            "点击下方建议按钮或直接输入命令 `/使用指南 <项目>`"
            "（例如：`/使用指南 A1`、`/使用指南 C4`、`/使用指南 B`、`/使用指南 tat-ca`）：\n\n"
            "| 符号 | 指南分段名称 | 核心内容范围 |\n"
            "| :--- | :--- | :--- |\n"
            "| **综合介绍** | 综合介绍与作业流程 | 3 项基础原则与 5 步作业流程 |\n"
            "| **A组** | A组 — 发送通道与聊天框 | 防重复发送、加载时点击建议、冷台账、真人输入节奏、三步等待卡片 |\n"
            "| **B组** | B组 — 按库问答与标准数据查询 | 4 大专业知识库、Ground Truth、标准标签\"Vụ\"、时间窗口、规范化语言 |\n"
            "| **C组** | C组 — 故障调查业务第1步至第5步 | 4M 分析树、JIG SMA(20) 日志、定期趋势报告、C7620 复发预警卡片 |\n"
            "| **D组** | D组 — 反馈评价与习惯自学习 | 点赞/点踩与 4 项理由、专家队列、草稿层、习惯自学习管理 |\n"
            "| **E组** | E组 — 智能搜索与显示模式 | 5 级答复阶梯、外部 AI、Source Viewer、流式显示、Command Code |\n"
            "| **F组** | F组 — 台账与会话管理 | 新建台账/会话、延续旧会话、多台账管理 |\n"
            "| **G组** | G组 — 18 项高级扩展功能 | 64MB 附件、Indra OCR、LSU 访谈、Log Chart Builder、30.075 起合并数据库 |\n"
            "| **附录** | 核心操作快速查询表 | 核心操作汇总表、命令语法与处理状态 |\n"
            "| **命令目录** | 系统命令目录（斜杠命令 Slash Commands） | 全部8组斜杠命令、等效自然语言语句、用途及适用上下文 |\n"
            "| **全部** | 完整使用指南 | 连续查看完整 7 大部分及附录（附 57 张实际操作插图） |\n"
        )
    else:
        title_text = "Cẩm nang Hướng dẫn Sử dụng AIOS"
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
            "| **Danh mục lệnh** | Danh mục lệnh hệ thống (Slash Commands) | Toàn bộ 8 nhóm lệnh /, câu tự nhiên tương đương, công dụng & ngữ cảnh |\n"
            "| **Toàn bộ** | Toàn bộ cẩm nang hướng dẫn | Xem liền mạch toàn bộ 7 phần và phụ lục (kèm 57 ảnh minh họa) |\n"
        )

    parsed_obj = {
        "title": title_text,
        "danh_muc": danh_muc_text,
        "sections": sections,
        "subsections": subsections,
        "toan_bo": full_embedded,
        "language": norm_lang,
    }
    _MANUAL_CACHE[norm_lang] = parsed_obj
    return parsed_obj


def clear_manual_cache() -> None:
    """Test hook: xóa cache nội dung cẩm nang."""
    global _MANUAL_CACHE, _IMAGE_B64_CACHE
    _MANUAL_CACHE.clear()
    _IMAGE_B64_CACHE.clear()


def is_huongdan_command(text: str) -> bool:
    """Kiểm tra câu chat có phải là lệnh cẩm nang hướng dẫn hay không (hỗ trợ cả 3 ngôn ngữ)."""
    clean = str(text or "").strip()
    if not clean:
        return False

    # 1. Tiếng Nhật: bắt đầu bằng /使い方, /つかいかた hoặc đúng chữ 使い方
    if clean.startswith(("/使い方", "/つかいかた")):
        return True
    if clean == "使い方" or clean.startswith("使い方 "):
        return True

    # 2. Tiếng Trung: bắt đầu bằng /使用指南 hoặc đúng cụm 使用指南
    if clean.startswith("/使用指南"):
        return True
    if clean == "使用指南" or clean.startswith("使用指南 "):
        return True

    # 3. Tiếng Việt & chung: bắt đầu bằng /huongdan, /huong-dan
    if re.match(r"^/(?:huongdan|huong-dan)(?:\s|$)", clean, re.IGNORECASE):
        return True

    # 4. Kiểm tra các cụm từ lệnh tiếng Việt chính xác (không dấu hoặc có dấu)
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


def parse_huongdan_args(text: str, lang: Optional[str] = None) -> str:
    """Trích xuất mã phân đoạn hoặc mục từ lệnh cẩm nang (dùng chung cho cả 3 ngôn ngữ).

    Trả về:
    - "danh_muc": gõ lệnh không tham số hoặc từ khóa danh mục
    - "tat_ca": xem toàn bộ
    - "gioi_thieu": xem phần giới thiệu
    - "phu_luc": xem phụ lục
    - "A", "B", "C", "D", "E", "F", "G": xem cả phần
    - "A1", ..., "G18": xem từng tiểu mục cụ thể
    - "dong": đóng cẩm nang
    """
    clean = str(text or "").strip()
    arg = ""

    # 1. Trích xuất đối số theo tiền tố ngôn ngữ
    if clean.startswith("/使い方"):
        arg = clean[len("/使い方"):].strip()
    elif clean.startswith("使い方"):
        arg = clean[len("使い方"):].strip()
    elif clean.startswith("/つかいかた"):
        arg = clean[len("/つかいかた"):].strip()
    elif clean.startswith("/使用指南"):
        arg = clean[len("/使用指南"):].strip()
    elif clean.startswith("使用指南"):
        arg = clean[len("使用指南"):].strip()
    else:
        m = re.match(r"^/(?:huongdan|huong-dan)\s*(.*)$", clean, re.IGNORECASE)
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
    if not arg_norm or arg_norm in ("danh muc", "menu", "list", "muc luc", "目次", "目录"):
        return "danh_muc"

    if arg_norm in ("tat ca", "toan bo", "all", "full", "全体", "全部", "zenbu"):
        return "tat_ca"

    if arg_norm in ("gioi thieu", "intro", "mo dau", "quy trinh", "概要", "综合介绍", "介绍", "gaiyou"):
        return "gioi_thieu"

    if arg_norm in ("phu luc", "appendix", "付録", "附录", "furoku"):
        return "phu_luc"

    if arg_norm in ("lenh", "danh muc lenh", "commands", "slash commands", "h", "phan h", "nhom h", "グループh", "h组", "第8部", "第8部分", "コマンド", "命令", "slash", "danh muc lenh he thong", "slash command", "slash-commands", "command"):
        return "lenh"

    if arg_norm in ("dong", "close", "tat", "exit", "quit", "閉じる", "关闭", "tojiru"):
        return "dong"

    # Kiểm tra tiểu mục A1..G18 (dùng chung cho cả 3 ngôn ngữ)
    sub_m = re.match(r"^([a-g]\d{1,2})$", arg_norm)
    if sub_m:
        return sub_m.group(1).upper()

    # Kiểm tra phần chính A..G (hỗ trợ cả tiền tố phân đoạn tiếng Nhật / Trung / Việt)
    part_m = re.match(r"^(?:phan\s+|nhom\s+|グループ\s*|第?[1-7]?部?：?|组\s*)?([a-g])$", arg_norm)
    if part_m:
        return part_m.group(1).upper()

    return "danh_muc"


def get_chips_for_section(section_key: str, lang: str = "vi") -> List[Tuple[str, str]]:
    """Tạo danh sách các chip gợi ý điều hướng theo ngôn ngữ tương ứng."""
    norm_lang = (lang or "vi").strip().lower()
    cmd_prefix = "/使い方" if norm_lang == "ja" else ("/使用指南" if norm_lang == "zh" else "/huongdan")

    if norm_lang == "ja":
        if section_key == "danh_muc":
            return [
                ("📖 概要", f"{cmd_prefix} gioi-thieu"),
                ("🅰️ グループA（チャット画面）", f"{cmd_prefix} A"),
                ("🅱️ グループB（リポジトリ照会）", f"{cmd_prefix} B"),
                ("🅲 グループC（障害調査業務）", f"{cmd_prefix} C"),
                ("🅳 グループD（評価と自己学習）", f"{cmd_prefix} D"),
                ("🅴 グループE（検索と表示）", f"{cmd_prefix} E"),
                ("🅵 グループF（ノート管理）", f"{cmd_prefix} F"),
                ("🅶 グループG（高度機能）", f"{cmd_prefix} G"),
                ("📑 付録", f"{cmd_prefix} phu-luc"),
                ("⌨️ コマンド一覧", f"{cmd_prefix} lenh"),
                ("📚 全体", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "A":
            return [
                ("A1. 重複送信防止", f"{cmd_prefix} A1"),
                ("A2. ロード中チップタップ", f"{cmd_prefix} A2"),
                ("A3. コールドノート待機", f"{cmd_prefix} A3"),
                ("A4. 人の入力リズム", f"{cmd_prefix} A4"),
                ("A5. 3ステップカード", f"{cmd_prefix} A5"),
                ("📖 目次", f"{cmd_prefix}"),
                ("📚 全体", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "B":
            return [
                ("B1. 4つのリポジトリ", f"{cmd_prefix} B1"),
                ("B2. Ground Truth", f"{cmd_prefix} B2"),
                ("B3. 標準ラベル「件」", f"{cmd_prefix} B3"),
                ("B4. 期間ウィンドウ", f"{cmd_prefix} B4"),
                ("B5. 言語正規化", f"{cmd_prefix} B5"),
                ("📖 目次", f"{cmd_prefix}"),
                ("📚 全体", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "C":
            return [
                ("C1. ステップ3階層化", f"{cmd_prefix} C1"),
                ("C2. JIG SMA20ログ", f"{cmd_prefix} C2"),
                ("C3. 定期レポート", f"{cmd_prefix} C3"),
                ("C4. C7620再発警告", f"{cmd_prefix} C4"),
                ("📖 目次", f"{cmd_prefix}"),
                ("📚 全体", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "D":
            return [
                ("D1. 高評価/低評価", f"{cmd_prefix} D1"),
                ("D2. 専門家キュー", f"{cmd_prefix} D2"),
                ("D3. 下書き層", f"{cmd_prefix} D3"),
                ("D4. 自己学習管理", f"{cmd_prefix} D4"),
                ("📖 目次", f"{cmd_prefix}"),
                ("📚 全体", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "E":
            return [
                ("E1. 5段階回答", f"{cmd_prefix} E1"),
                ("E2. 外部AIモード", f"{cmd_prefix} E2"),
                ("E3. Source Viewer", f"{cmd_prefix} E3"),
                ("E4. ストリーミング", f"{cmd_prefix} E4"),
                ("E5. 3つの検索モード", f"{cmd_prefix} E5"),
                ("E6. Command Code", f"{cmd_prefix} E6"),
                ("📖 目次", f"{cmd_prefix}"),
                ("📚 全体", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "F":
            return [
                ("F1. ノート・会話作成", f"{cmd_prefix} F1"),
                ("F2. 会話の再開", f"{cmd_prefix} F2"),
                ("📖 目次", f"{cmd_prefix}"),
                ("📚 全体", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "G":
            return [
                ("G1. 64MB添付", f"{cmd_prefix} G1"),
                ("G2. 障害ケース作成", f"{cmd_prefix} G2"),
                ("G6. Log Chart Builder", f"{cmd_prefix} G6"),
                ("G7. リアルタイム警告", f"{cmd_prefix} G7"),
                ("G17. ルーティング", f"{cmd_prefix} G17"),
                ("G18. 30.075件DB", f"{cmd_prefix} G18"),
                ("📖 目次", f"{cmd_prefix}"),
                ("📚 全体", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "gioi_thieu":
            return [
                ("🅰️ グループAを見る", f"{cmd_prefix} A"),
                ("📖 目次に戻る", f"{cmd_prefix}"),
                ("📚 全体を見る", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "phu_luc":
            return [
                ("📖 目次に戻る", f"{cmd_prefix}"),
                ("📚 全体を見る", f"{cmd_prefix} tat-ca"),
            ]
        if section_key in ("lenh", "H"):
            return [
                ("📖 目次に戻る", f"{cmd_prefix}"),
                ("📚 全体を見る", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "tat_ca":
            return [
                ("📖 目次に戻る", f"{cmd_prefix}"),
                ("🅰️ グループA", f"{cmd_prefix} A"),
                ("🅱️ グループB", f"{cmd_prefix} B"),
                ("🅲 グループC", f"{cmd_prefix} C"),
                ("🅶 グループG", f"{cmd_prefix} G"),
                ("⌨️ コマンド一覧", f"{cmd_prefix} lenh"),
            ]
        part_letter = section_key[0] if section_key else "A"
        return [
            ("📖 目次に戻る", f"{cmd_prefix}"),
            (f"グループ{part_letter}に戻る", f"{cmd_prefix} {part_letter}"),
            ("📚 全体を見る", f"{cmd_prefix} tat-ca"),
        ]

    elif norm_lang == "zh":
        if section_key == "danh_muc":
            return [
                ("📖 综合介绍", f"{cmd_prefix} gioi-thieu"),
                ("🅰️ A组（聊天框）", f"{cmd_prefix} A"),
                ("🅱️ B组（按库查询）", f"{cmd_prefix} B"),
                ("🅲 C组（故障调查）", f"{cmd_prefix} C"),
                ("🅳 D组（反馈自学习）", f"{cmd_prefix} D"),
                ("🅴 E组（搜索与显示）", f"{cmd_prefix} E"),
                ("🅵 F组（台账管理）", f"{cmd_prefix} F"),
                ("🅶 G组（高级功能）", f"{cmd_prefix} G"),
                ("📑 附录", f"{cmd_prefix} phu-luc"),
                ("⌨️ 命令目录", f"{cmd_prefix} lenh"),
                ("📚 全部", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "A":
            return [
                ("A1. 防重复发送", f"{cmd_prefix} A1"),
                ("A2. 加载时点击建议", f"{cmd_prefix} A2"),
                ("A3. 冷台账自动解锁", f"{cmd_prefix} A3"),
                ("A4. 真人输入节奏", f"{cmd_prefix} A4"),
                ("A5. 三步等待卡片", f"{cmd_prefix} A5"),
                ("📖 目录", f"{cmd_prefix}"),
                ("📚 全部", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "B":
            return [
                ("B1. 4大知识库", f"{cmd_prefix} B1"),
                ("B2. Ground Truth", f"{cmd_prefix} B2"),
                ("B3. 标准标签'Vụ'", f"{cmd_prefix} B3"),
                ("B4. 时间窗口", f"{cmd_prefix} B4"),
                ("B5. 语言规范化", f"{cmd_prefix} B5"),
                ("📖 目录", f"{cmd_prefix}"),
                ("📚 全部", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "C":
            return [
                ("C1. 第3步分层", f"{cmd_prefix} C1"),
                ("C2. JIG SMA20日志", f"{cmd_prefix} C2"),
                ("C3. 定期趋势报告", f"{cmd_prefix} C3"),
                ("C4. C7620复发预警", f"{cmd_prefix} C4"),
                ("📖 目录", f"{cmd_prefix}"),
                ("📚 全部", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "D":
            return [
                ("D1. 点赞/点踩评价", f"{cmd_prefix} D1"),
                ("D2. 专家队列", f"{cmd_prefix} D2"),
                ("D3. 草稿来源层", f"{cmd_prefix} D3"),
                ("D4. 自学习管理", f"{cmd_prefix} D4"),
                ("📖 目录", f"{cmd_prefix}"),
                ("📚 全部", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "E":
            return [
                ("E1. 5级答复阶梯", f"{cmd_prefix} E1"),
                ("E2. 外部AI模式", f"{cmd_prefix} E2"),
                ("E3. Source Viewer", f"{cmd_prefix} E3"),
                ("E4. 流式显示", f"{cmd_prefix} E4"),
                ("E5. 3种搜索模式", f"{cmd_prefix} E5"),
                ("E6. Command Code", f"{cmd_prefix} E6"),
                ("📖 目录", f"{cmd_prefix}"),
                ("📚 全部", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "F":
            return [
                ("F1. 新建台账与会话", f"{cmd_prefix} F1"),
                ("F2. 延续旧会话", f"{cmd_prefix} F2"),
                ("📖 目录", f"{cmd_prefix}"),
                ("📚 全部", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "G":
            return [
                ("G1. 64MB附件", f"{cmd_prefix} G1"),
                ("G2. 新建故障案例", f"{cmd_prefix} G2"),
                ("G6. Log Chart Builder", f"{cmd_prefix} G6"),
                ("G7. 实时预警", f"{cmd_prefix} G7"),
                ("G17. 故障路由", f"{cmd_prefix} G17"),
                ("G18. 30.075起DB", f"{cmd_prefix} G18"),
                ("📖 目录", f"{cmd_prefix}"),
                ("📚 全部", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "gioi_thieu":
            return [
                ("🅰️ 查看A组", f"{cmd_prefix} A"),
                ("📖 返回目录", f"{cmd_prefix}"),
                ("📚 查看全部", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "phu_luc":
            return [
                ("📖 返回目录", f"{cmd_prefix}"),
                ("📚 查看全部", f"{cmd_prefix} tat-ca"),
            ]
        if section_key in ("lenh", "H"):
            return [
                ("📖 返回目录", f"{cmd_prefix}"),
                ("📚 查看全部", f"{cmd_prefix} tat-ca"),
            ]
        if section_key == "tat_ca":
            return [
                ("📖 返回目录", f"{cmd_prefix}"),
                ("🅰️ A组", f"{cmd_prefix} A"),
                ("🅱️ B组", f"{cmd_prefix} B"),
                ("🅲 C组", f"{cmd_prefix} C"),
                ("🅶 G组", f"{cmd_prefix} G"),
                ("⌨️ 命令目录", f"{cmd_prefix} lenh"),
            ]
        part_letter = section_key[0] if section_key else "A"
        return [
            ("📖 返回目录", f"{cmd_prefix}"),
            (f"返回{part_letter}组", f"{cmd_prefix} {part_letter}"),
            ("📚 查看全部", f"{cmd_prefix} tat-ca"),
        ]

    # Mặc định: tiếng Việt
    if section_key == "danh_muc":
        return [
            ("📖 Giới thiệu", f"{cmd_prefix} gioi-thieu"),
            ("🅰️ Phần A (Khung chat)", f"{cmd_prefix} A"),
            ("🅱️ Phần B (Tra cứu & Kho)", f"{cmd_prefix} B"),
            ("🅲 Phần C (Điều tra sự cố)", f"{cmd_prefix} C"),
            ("🅳 Phần D (Đánh giá & Tự học)", f"{cmd_prefix} D"),
            ("🅴 Phần E (Tìm kiếm & Hiển thị)", f"{cmd_prefix} E"),
            ("🅵 Phần F (Quản lý sổ tay)", f"{cmd_prefix} F"),
            ("🅶 Phần G (Tính năng nâng cao)", f"{cmd_prefix} G"),
            ("📑 Phụ lục", f"{cmd_prefix} phu-luc"),
            ("⌨️ Danh mục lệnh", f"{cmd_prefix} lenh"),
            ("📚 Toàn bộ", f"{cmd_prefix} tat-ca"),
        ]

    if section_key == "A":
        return [
            ("A1. Chống gửi lặp", f"{cmd_prefix} A1"),
            ("A2. Bấm chip khi nạp", f"{cmd_prefix} A2"),
            ("A3. Sổ lạnh giữ chữ", f"{cmd_prefix} A3"),
            ("A4. Bẫy nhịp người", f"{cmd_prefix} A4"),
            ("A5. Thẻ 3 bước", f"{cmd_prefix} A5"),
            ("📖 Danh mục", f"{cmd_prefix}"),
            ("📚 Toàn bộ", f"{cmd_prefix} tat-ca"),
        ]

    if section_key == "B":
        return [
            ("B1. 4 kho tri thức", f"{cmd_prefix} B1"),
            ("B2. Ground Truth", f"{cmd_prefix} B2"),
            ("B3. Nhãn Vụ chuẩn", f"{cmd_prefix} B3"),
            ("B4. Cửa sổ thời gian", f"{cmd_prefix} B4"),
            ("B5. Thuần Việt", f"{cmd_prefix} B5"),
            ("📖 Danh mục", f"{cmd_prefix}"),
            ("📚 Toàn bộ", f"{cmd_prefix} tat-ca"),
        ]

    if section_key == "C":
        return [
            ("C1. Phân tầng B3", f"{cmd_prefix} C1"),
            ("C2. Log JIG SMA20", f"{cmd_prefix} C2"),
            ("C3. Báo cáo định kỳ", f"{cmd_prefix} C3"),
            ("C4. Cảnh báo tái phát C7620", f"{cmd_prefix} C4"),
            ("📖 Danh mục", f"{cmd_prefix}"),
            ("📚 Toàn bộ", f"{cmd_prefix} tat-ca"),
        ]

    if section_key == "D":
        return [
            ("D1. Thích/Không thích", f"{cmd_prefix} D1"),
            ("D2. Hàng đợi chuyên gia", f"{cmd_prefix} D2"),
            ("D3. Tầng bản thảo", f"{cmd_prefix} D3"),
            ("D4. Quản trị tự học", f"{cmd_prefix} D4"),
            ("📖 Danh mục", f"{cmd_prefix}"),
            ("📚 Toàn bộ", f"{cmd_prefix} tat-ca"),
        ]

    if section_key == "E":
        return [
            ("E1. 5 bậc trả lời", f"{cmd_prefix} E1"),
            ("E2. Chế độ AI ngoài", f"{cmd_prefix} E2"),
            ("E3. Source Viewer", f"{cmd_prefix} E3"),
            ("E4. Streaming", f"{cmd_prefix} E4"),
            ("E5. 3 chế độ tìm", f"{cmd_prefix} E5"),
            ("E6. Command Code", f"{cmd_prefix} E6"),
            ("📖 Danh mục", f"{cmd_prefix}"),
            ("📚 Toàn bộ", f"{cmd_prefix} tat-ca"),
        ]

    if section_key == "F":
        return [
            ("F1. Tạo sổ & hội thoại", f"{cmd_prefix} F1"),
            ("F2. Tiếp nối hội thoại", f"{cmd_prefix} F2"),
            ("📖 Danh mục", f"{cmd_prefix}"),
            ("📚 Toàn bộ", f"{cmd_prefix} tat-ca"),
        ]

    if section_key == "G":
        return [
            ("G1. Đính kèm 64MB", f"{cmd_prefix} G1"),
            ("G2. Tạo ca điều tra", f"{cmd_prefix} G2"),
            ("G6. Log Chart Builder", f"{cmd_prefix} G6"),
            ("G7. Cảnh báo RT", f"{cmd_prefix} G7"),
            ("G17. Định tuyến lỗi", f"{cmd_prefix} G17"),
            ("G18. CSDL 30.075 ca", f"{cmd_prefix} G18"),
            ("📖 Danh mục", f"{cmd_prefix}"),
            ("📚 Toàn bộ", f"{cmd_prefix} tat-ca"),
        ]

    if section_key == "gioi_thieu":
        return [
            ("🅰️ Xem Phần A", f"{cmd_prefix} A"),
            ("📖 Về danh mục", f"{cmd_prefix}"),
            ("📚 Xem Toàn bộ", f"{cmd_prefix} tat-ca"),
        ]

    if section_key == "phu_luc":
        return [
            ("📖 Về danh mục", f"{cmd_prefix}"),
            ("📚 Xem Toàn bộ", f"{cmd_prefix} tat-ca"),
        ]

    if section_key in ("lenh", "H"):
        return [
            ("📖 Về danh mục", f"{cmd_prefix}"),
            ("📚 Xem Toàn bộ", f"{cmd_prefix} tat-ca"),
        ]

    if section_key == "tat_ca":
        return [
            ("📖 Về danh mục", f"{cmd_prefix}"),
            ("🅰️ Phần A", f"{cmd_prefix} A"),
            ("🅱️ Phần B", f"{cmd_prefix} B"),
            ("🅲 Phần C", f"{cmd_prefix} C"),
            ("🅶 Phần G", f"{cmd_prefix} G"),
            ("⌨️ Danh mục lệnh", f"{cmd_prefix} lenh"),
        ]

    # Tiểu mục cụ thể (vd C4)
    part_letter = section_key[0] if section_key else "A"
    return [
        ("📖 Về danh mục", f"{cmd_prefix}"),
        (f"Trở lại Phần {part_letter}", f"{cmd_prefix} {part_letter}"),
        ("📚 Xem Toàn bộ", f"{cmd_prefix} tat-ca"),
    ]


class HuongDanResult:
    """Kết quả xử lý lệnh cẩm nang hướng dẫn."""

    def __init__(
        self,
        section_key: str,
        markdown_content: str,
        chips: List[Tuple[str, str]],
        language: str = "vi",
    ):
        self.section_key = section_key
        self.markdown_content = markdown_content
        self.chips = chips
        self.language = language
        self.is_close = (section_key == "dong")


def record_huongdan_metric(
    cmd: str,
    section_key: str,
    conversation_id: str = "",
    language: Optional[str] = None,
) -> None:
    """Ghi nhận sự kiện gọi lệnh cẩm nang vào local_cases (Vòng lặp cải thiện liên tục)."""
    try:
        norm_lang = (language or detect_huongdan_language(cmd)).strip().lower()
        lc_dir = _get_local_cases_dir()
        events_file = lc_dir / "huongdan_events.jsonl"
        metrics_file = lc_dir / "huongdan_metrics.json"

        now_iso = datetime.datetime.now().astimezone().isoformat()
        evt = {
            "timestamp": now_iso,
            "command": cmd,
            "section": section_key,
            "language": norm_lang,
            "conversation_id": conversation_id,
        }

        with open(events_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(evt, ensure_ascii=False) + "\n")

        # Cập nhật số liệu tích lũy
        metrics = {
            "total_calls": 0,
            "by_section": {},
            "by_language": {},
            "last_called_at": now_iso,
        }
        if metrics_file.is_file():
            try:
                metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        metrics["total_calls"] = metrics.get("total_calls", 0) + 1
        sec_dict = metrics.setdefault("by_section", {})
        sec_dict[section_key] = sec_dict.get(section_key, 0) + 1

        lang_dict = metrics.setdefault("by_language", {})
        lang_dict[norm_lang] = lang_dict.get(norm_lang, 0) + 1

        metrics["last_called_at"] = now_iso

        metrics_file.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def get_huongdan_metrics() -> Dict[str, Any]:
    """Đọc số liệu thống kê lượt sử dụng cẩm nang hướng dẫn."""
    metrics_file = _get_local_cases_dir() / "huongdan_metrics.json"
    if metrics_file.is_file():
        try:
            return json.loads(metrics_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"total_calls": 0, "by_section": {}, "by_language": {}}


def handle_huongdan_command(
    text: str,
    conversation_id: str = "",
    language: Optional[str] = None,
) -> HuongDanResult:
    """Xử lý lệnh cẩm nang và trả về nội dung hoàn chỉnh kèm chip điều hướng theo ngôn ngữ."""
    norm_lang = (language or detect_huongdan_language(text)).strip().lower()
    target_key = parse_huongdan_args(text, lang=norm_lang)
    record_huongdan_metric(text, target_key, conversation_id, language=norm_lang)

    if target_key == "dong":
        close_texts = {
            "vi": "*Đã đóng cẩm nang hướng dẫn sử dụng.*",
            "ja": "*利用マニュアルを閉じました。*",
            "zh": "*已关闭使用指南。*",
        }
        return HuongDanResult(
            section_key="dong",
            markdown_content=close_texts.get(norm_lang, close_texts["vi"]),
            chips=[],
            language=norm_lang,
        )

    parsed = load_and_parse_manual(lang=norm_lang)
    chips = get_chips_for_section(target_key, lang=norm_lang)

    if target_key == "danh_muc":
        content = parsed["danh_muc"]
    elif target_key == "tat_ca":
        headers_all = {
            "ja": (
                "# 📚 AIOS台帳 総合利用マニュアル（全体表示）\n\n"
                "*すべての作業グループと57枚の実際のスクリーンショット画像を完全に表示します。*\n\n---\n\n"
            ),
            "zh": (
                "# 📚 AIOS 台账综合使用指南（完整版）\n\n"
                "*完整显示所有作业分组及 57 张实际操作插图。*\n\n---\n\n"
            ),
            "vi": (
                "# 📚 TOÀN BỘ CẨM NANG HƯỚNG DẪN SỬ DỤNG SỔ CÁI AIOS\n\n"
                "*Hiển thị đầy đủ tất cả các phần tác nghiệp và 57 ảnh chụp minh họa thực tế.*\n\n---\n\n"
            ),
        }
        content = headers_all.get(norm_lang, headers_all["vi"]) + parsed["toan_bo"]
    elif target_key in parsed["sections"]:
        content = parsed["sections"][target_key]
    elif target_key in parsed["subsections"]:
        content = parsed["subsections"][target_key]
    else:
        not_found_texts = {
            "ja": f"⚠️ 利用マニュアル内に項目 `{target_key}` が見つかりませんでした。\n\n",
            "zh": f"⚠️ 在使用指南中未找到项目 `{target_key}`。\n\n",
            "vi": f"⚠️ Không tìm thấy mục `{target_key}` trong cẩm nang hướng dẫn.\n\n",
        }
        content = not_found_texts.get(norm_lang, not_found_texts["vi"]) + parsed["danh_muc"]
        target_key = "danh_muc"
        chips = get_chips_for_section("danh_muc", lang=norm_lang)

    return HuongDanResult(
        section_key=target_key,
        markdown_content=content,
        chips=chips,
        language=norm_lang,
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
            titles = {
                "ja": "AIOS台帳 総合利用マニュアル",
                "zh": "AIOS 台账综合使用指南",
                "vi": "Cẩm nang Hướng dẫn sử dụng AIOS",
            }
            return ChatActionOutcome(
                action="huong_dan",
                title=titles.get(res.language, titles["vi"]),
                blocks=(ChatActionBlock(kind=BLOCK_MARKDOWN, text=res.markdown_content),),
            )

        register_action(
            ChatAction(
                name="huong_dan",
                title="Cẩm nang Hướng dẫn sử dụng AIOS",
                hints=(
                    "/huongdan",
                    "/huong-dan",
                    "/使い方",
                    "/使用指南",
                    "huong dan su dung aios",
                    "cam nang aios",
                    "danh muc huong dan",
                    "使い方",
                    "使用指南",
                ),
                handler=_action_handler,
                description="Tra cứu cẩm nang hướng dẫn sử dụng AIOS (Việt/Trung/Nhật)",
            )
        )
    except Exception:
        pass

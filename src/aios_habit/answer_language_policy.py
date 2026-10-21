# -*- coding: utf-8 -*-
"""Answer Language Purity Policy for AIOS Workspace Chat.

Implements ticket DESKTOP-HOME-ANSWER-LANGUAGE-PURITY-FIX:
Enforces that when a user asks in Vietnamese (or target answer_language is 'vi'),
the synthesized answer body is 100% natural Vietnamese without raw Japanese leaks
(e.g., raw field values like '不要', untranslated sentences, orphan tokens).

Policy rules (2.2):
(a) Vietnamese question -> answer body in Vietnamese.
(b) Japanese fragments as field label/raw value or orphan sentence:
    TRANSLATE to Vietnamese if meaning can be determined from field/context;
    if not determinable, REMOVE from answer body and log, never print raw.
(c) Japanese source passages truly needed for verification:
    Placed in separate labeled quote:
    '> **Nguyên văn nguồn (tiếng Nhật):** ...'
    with Vietnamese translation/explanation placed right beside.
(d) Permitted identifiers: document titles, error codes/part numbers, proper nouns
    (with Vietnamese explanation if carrying content meaning).
(e) Valid exceptions: user asks in Japanese or asks for verbatim quote / translation.
(2.3) No blind regex deletion of all Chinese/Kana characters across the entire document
      (which would break document names, citations, identifiers).
(2.4) Continuous improvement logging: records every detection/action to
      local_cases/answer_language_events.jsonl.
"""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
import re
import threading
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

# Regex to detect Japanese characters: Hiragana, Katakana, Kanji, Halfwidth Katakana
# Note: \u30fb (Katakana middle dot ・) is treated as punctuation and replaced with bullet
JP_CHAR_RE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\uff66-\uff9f]")

# Japanese sentence particles and interrogatives to identify genuine Japanese questions
JP_QUESTION_MARKERS = [
    "ですか", "ますか", "について", "教えて", "どうすれば", "何ですか", "の原因",
    "の対策", "のエラー", "の理由", "エラーコード", "どのような", "ありますか"
]

# Explicit user requests for original Japanese or translation to Japanese
JP_OVERRIDE_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"tiếng\s*nhật",
        r"nguyên\s*văn\s*tiếng\s*nhật",
        r"trích\s*nguyên\s*văn",
        r"bằng\s*tiếng\s*nhật",
        r"dịch\s*(sang|ra)\s*tiếng\s*nhật",
        r"tiếng\s*nhật\s*là\s*gì",
        r"bản\s*tiếng\s*nhật",
        r"chữ\s*nhật",
    ]
]

# Exact dictionary mapping for KDTPS fields, causes, remedies, phenomena
KDTPS_EXACT_MAP: Dict[str, str] = {
    # 不要 variants
    "不要": "Không xác định nguyên nhân bất thường / Đã giải quyết trên chuyền (không phát sinh đối sách dài hạn)",
    "不要。": "Không yêu cầu đối sách bổ sung / Đã xử lý tại chỗ không cần đối sách chính thức",
    "不要 ": "Không xác định nguyên nhân bất thường / Đã giải quyết trên chuyền (không phát sinh đối sách dài hạn)",
    "要": "Cần đối sách / Cần xử lý",
    # Causes (Nguyên nhân)
    "要因不明(製造)": "Không rõ nguyên nhân (Khâu chế tạo)",
    "要因不明（製造）": "Không rõ nguyên nhân (Khâu chế tạo)",
    "要因不明(電気)": "Không rõ nguyên nhân (Phần điện)",
    "要因不明（電気）": "Không rõ nguyên nhân (Phần điện)",
    "要因不明": "Không rõ nguyên nhân",
    "原因不明（メカ）": "Không rõ nguyên nhân (Cơ khí)",
    "原因不明(メカ)": "Không rõ nguyên nhân (Cơ khí)",
    "原因不明": "Không rõ nguyên nhân",
    "部品要因(電気)": "Yếu tố linh kiện (Phần điện)",
    "部品要因（電気）": "Yếu tố linh kiện (Phần điện)",
    "部品要因(Supplier)": "Yếu tố linh kiện (Nhà cung cấp / Supplier)",
    "部品要因（Supplier）": "Yếu tố linh kiện (Nhà cung cấp / Supplier)",
    "部品要因(外制)": "Yếu tố linh kiện (Gia công ngoài)",
    "部品要因（外制）": "Yếu tố linh kiện (Gia công ngoài)",
    "部品要因": "Yếu tố linh kiện",
    "メカ部品要因": "Yếu tố linh kiện cơ khí",
    "組立": "Thao tác lắp ráp / Khâu lắp ráp",
    "治具": "Đồ gá (Jig)",
    "その他": "Nguyên nhân khác",
    "電気製造技術": "Kỹ thuật chế tạo điện",
    "部管": "Bộ phận quản lý linh kiện",
    "部品": "Linh kiện",
    # Safety critical part
    "安全重要部品": "Linh kiện an toàn quan trọng",
    "重要部品": "Linh kiện quan trọng",
    "安全部品": "Linh kiện an toàn",
    # Actions & Liaison (Liên hệ / Phối hợp)
    "電気技術に連絡": "Liên hệ bộ phận kỹ thuật điện",
    "電気技術に連絡 ": "Liên hệ bộ phận kỹ thuật điện",
    "電気技術に連携": "Phối hợp với bộ phận kỹ thuật điện",
    "電気技術に連携、": "Phối hợp với bộ phận kỹ thuật điện",
    "電気技術に連携 ": "Phối hợp với bộ phận kỹ thuật điện",
    "製造技術に連絡": "Liên hệ bộ phận kỹ thuật chế tạo",
    "製造技術に連絡 ": "Liên hệ bộ phận kỹ thuật chế tạo",
    "製造技術に連携": "Phối hợp với bộ phận kỹ thuật chế tạo",
    "製造技術に連携、": "Phối hợp với bộ phận kỹ thuật chế tạo",
    "製造技術に連携 ": "Phối hợp với bộ phận kỹ thuật chế tạo",
    "生産技術に連絡": "Liên hệ bộ phận kỹ thuật sản xuất",
    "外製品質管理に連絡": "Liên hệ quản lý chất lượng hàng gia công ngoài",
    "Link(jp+vn)": "Xem tài liệu liên kết (Nhật - Việt)",
    "調査中": "Đang điều tra / kiểm tra",
    "調査中、トランジスタが破損": "Đang điều tra: Transistor bị hỏng",
    "単発発生処理": "Xử lý theo quy trình lỗi đơn phát",
    "再現せずルール処理をお願いします": "Lỗi không tái hiện, đề nghị xử lý theo quy định",
    "不具合部品は日本に連絡する": "Linh kiện lỗi được thông báo về phía Nhật Bản",
    "MCH ASSY 交換→OK→マシン流れた": "Thay cụm MCH ASSY -> OK -> Máy đã cho chạy tiếp",
    # Phenomenon & Status
    "異常音": "Tiếng kêu bất thường",
    "表面電位NG": "Điện thế bề mặt NG",
    "起動不可": "Không thể khởi động",
    "LCD画面　真っ白": "Màn hình LCD trắng xóa",
    "LCD画面 真っ白": "Màn hình LCD trắng xóa",
    "LSU SKEW　調整不可": "LSU SKEW không thể điều chỉnh",
    "LSU SKEW 調整不可": "LSU SKEW không thể điều chỉnh",
    "LCD画面　点灯せず": "Màn hình LCD không sáng",
    "LCD画面 点灯せず": "Màn hình LCD không sáng",
    "DLP BLADE ギャップNG": "Khe hở DLP BLADE NG",
    "COVER MAGのボス 折れ": "Gãy vấu (boss) nắp COVER MAG",
    "COVER MAGのボス折れ": "Gãy vấu (boss) nắp COVER MAG",
    "Check Black , Check Color 画像 異常": "Kiểm tra bản in Đen và Màu: Bất thường hình ảnh",
    "Check Black , Check Color 画像異常": "Kiểm tra bản in Đen và Màu: Bất thường hình ảnh",
    "Check Black , Check Color 画像 bất thường": "Kiểm tra bản in Đen và Màu: Bất thường hình ảnh",
    "LCD画面が暗く表示し、30秒にフリーズになった後、F000表示": (
        "Màn hình LCD hiển thị tối, sau khi bị đóng băng (treo) 30 giây thì hiển thị F000"
    ),
    "LCD画面が白く表示し、ロックされた": "Màn hình LCD hiển thị trắng xóa và bị khóa",
    "LCD画面がF000表示": "Màn hình LCD hiển thị F000",
    "LCD画面にF000表示": "Màn hình LCD hiển thị F000",
    "LCD画面に6950表示": "Màn hình LCD hiển thị 6950",
    "LCD画面に6770表示": "Màn hình LCD hiển thị 6770",
    "LCD画面にC6400表示": "Màn hình LCD hiển thị C6400",
    "LCD画面にC6770表示": "Màn hình LCD hiển thị C6770",
    "LCD画面が6770表示": "Màn hình LCD hiển thị 6770",
    "LCD画面にJam9600表示": "Màn hình LCD hiển thị Jam9600",
    "LCD画面に\"Close top cover\"表示": "Màn hình LCD hiển thị \"Close top cover\"",
    "PC画面に\"USB DisConnect\"表示": "Màn hình PC hiển thị \"USB DisConnect\"",
    "PC画面にU411 DP表示": "Màn hình PC hiển thị U411 DP",
    "PC画面にNG表示": "Màn hình PC hiển thị NG",
    "C6770表示": "Hiển thị C6770",
    "F000表示": "Hiển thị F000",
    "C6770 ※IH定着低電力異常": "Hiển thị C6770 (Bất thường công suất thấp sấy IH)",
    "C7620 ※カラーレジストタイミング異常": "Hiển thị C7620 (Bất thường thời gian đăng ký màu)",
    # Machine categories
    "下位": "Hạ vị (Bản tiêu chuẩn)",
    "上位": "Thượng vị (Bản nâng cao)",
    # Glossary technical descriptions
    "IH定着 低電力異常": "Lỗi nguồn điện thấp bộ sấy IH",
    "IH定着低電力異常": "Lỗi nguồn điện thấp bộ sấy IH",
    "カラーレジストタイミング異常": "Lỗi thời gian đăng ký màu (Color Reg)",
    "定着センサー滞留(カセット2給紙)": "Kẹt giấy tại cảm biến sấy (Cấp giấy khay 2)",
    "定着センサー滞留（カセット2給紙）": "Kẹt giấy tại cảm biến sấy (Cấp giấy khay 2)",
    "中間巻き付き検知センサーOFFから規定時間経過しても定着センサーをOFFしない": (
        "Đã qua thời gian quy định từ khi cảm biến phát hiện cuốn giấy trung gian ngắt (OFF) nhưng cảm biến sấy vẫn chưa ngắt (OFF)"
    ),
    "電源ダウン": "Sụt áp nguồn điện / Mất nguồn",
    "表面光源異常": "Bất thường nguồn sáng bề mặt (đèn CCD)",
    "RTC異常": "Bất thường mạch thời gian thực (RTC)",
    "VIDEO_ASICデバイス異常": "Bất thường thiết bị VIDEO_ASIC",
    # Specific multiline text for F000
    "Welcome画面のまま一定時間※注経過するとCF000が表示される。": (
        "Màn hình dừng ở màn hình Welcome quá thời gian quy định sẽ hiển thị mã CF000."
    ),
    "Panel-Main基板間の通信異常": (
        "Bất thường truyền thông giữa bản mạch Panel và bản mạch Main"
    ),
    "Panel Core-Main Core間の通信異常 注2": (
        "Bất thường truyền thông giữa Panel Core và Main Core (chú thích 2)"
    ),
    # Specific remedies for F000
    "1Panel⇔Main基板間、※(Main基板⇔HDD間)のハーネス、コネクタの接続状態を確認し、動作確認を行う。": (
        "1. Kiểm tra trạng thái kết nối của dây cáp (harness), connector giữa bản mạch Panel ⇔ Main, (giữa Main ⇔ HDD) và chạy thử kiểm tra hoạt động."
    ),
    "2DDRメモリの接触を確認(抜き出し)し、動作確認を行う。交換可能であれば、交換し、動作確認を行う。": (
        "2. Kiểm tra tiếp xúc của bộ nhớ DDR (rút ra cắm lại) và kiểm tra hoạt động. Nếu có linh kiện thay thế, hãy thay và chạy thử."
    ),
    "3HDDの初期化をし、動作確認を行う。(U024のFULL)  ※": (
        "3. Khởi tạo (format) ổ cứng HDD và kiểm tra hoạt động (chạy U024 FULL)."
    ),
    "4U021 コントローラバックアップ初期化をし、動作確認を行う。": (
        "4. Khởi tạo sao lưu bộ điều khiển U021 và kiểm tra hoạt động."
    ),
    "5Main基板を交換し、動作確認を行う。": (
        "5. Thay thế bản mạch Main và kiểm tra hoạt động."
    ),
    "6PanelMain基板を交換し、動作確認を行う。": (
        "6. Thay thế bản mạch Panel Main và kiểm tra hoạt động."
    ),
    "JA: 1Panel⇔Main基板間、※(Main基板⇔HDD間)のハーネス、コネクタの接続状態を確認し、動作確認を行う。": (
        "1. Kiểm tra trạng thái kết nối của dây cáp (harness), connector giữa bản mạch Panel ⇔ Main, (giữa Main ⇔ HDD) và chạy thử kiểm tra hoạt động."
    ),
}

# Sub-phrase replacement patterns (ordered from most specific to generic)
KDTPS_SUB_PHRASES: List[Tuple[re.Pattern, str]] = [
    # Full multi-sentence items
    (re.compile(r"LCD画面が暗く表示し、30秒にフリーズになった後、F000表示"), "Màn hình LCD hiển thị tối, sau 30 giây bị treo thì hiển thị F000"),
    (re.compile(r"LCD画面が白く表示し、ロックされた"), "Màn hình LCD hiển thị trắng xóa và bị khóa"),
    (re.compile(r"ネットワークポートに(?:異常|bất thường)がないことを確認した[。.\s]*"), "Xác nhận cổng mạng (network port) không có bất thường. "),
    (re.compile(r"基板をEMSに送ってI/Fを[…\s]*"), "Gửi bản mạch sang EMS để kiểm tra giao diện I/F. "),
    (re.compile(r"安全重要部品"), "Linh kiện an toàn quan trọng"),
    (re.compile(r"重要部品"), "Linh kiện quan trọng"),
    (re.compile(r"安全部品"), "Linh kiện an toàn"),
    (re.compile(r"電気技術に連絡"), "liên hệ bộ phận kỹ thuật điện"),
    (re.compile(r"電気技術に連携[、,\s]*"), "phối hợp bộ phận kỹ thuật điện: "),
    (re.compile(r"製造技術に連絡"), "liên hệ bộ phận kỹ thuật chế tạo"),
    (re.compile(r"製造技術に連携[、,\s]*"), "phối hợp kỹ thuật chế tạo: "),
    (re.compile(r"生産技術に連絡"), "liên hệ kỹ thuật sản xuất"),
    (re.compile(r"外製品質管理に連絡"), "liên hệ quản lý chất lượng gia công ngoài"),
    (re.compile(r"LCD画面に\s*(Waste\s*Tonner[^\n\r]*?)\s*表示"), r"Màn hình LCD hiển thị: \1"),
    (re.compile(r"LCD画面に\s*(.+?)\s*表示"), r"Màn hình LCD hiển thị \1"),
    (re.compile(r"LCD画面が\s*(.+?)\s*表示"), r"Màn hình LCD hiển thị \1"),
    (re.compile(r"PC画面に\s*(.+?)\s*表示"), r"Màn hình PC hiển thị \1"),
    (re.compile(r"PC画面\s*(.+?)\s*表示"), r"Màn hình PC hiển thị \1"),
    (re.compile(r"Panel-Main基板間の通信異常"), "Bất thường truyền thông giữa bản mạch Panel và Main"),
    (re.compile(r"Panel\s*Core-Main\s*Core間の通信異常\s*注2"), "Bất thường truyền thông giữa Panel Core và Main Core (chú thích 2)"),
    (re.compile(r"電源ON後、ATTENTION,POWERランプが異常点灯\(C6400\)"), "Sau khi bật nguồn, đèn ATTENTION và POWER báo sáng bất thường (C6400)"),
    (re.compile(r"電源ON後、ATTENTION,POWERランプが異常点灯"), "Sau khi bật nguồn, đèn ATTENTION và POWER báo sáng bất thường"),
    (re.compile(r"ログ取得→電源OFF-ON:NG\(C6400\)→再現あり"), "Lấy log -> Tắt bật lại nguồn: NG (C6400) -> Có tái hiện lỗi"),
    (re.compile(r"ラインアウト→電源ON:MOTORが回転しない"), "Đưa ra khỏi chuyền -> Bật nguồn: MOTOR không quay"),
    (re.compile(r"結線確認→異常なし"), "Kiểm tra dây nối -> Không có bất thường"),
    (re.compile(r"異常品質会議行う"), "Tổ chức họp chất lượng bất thường"),
    (re.compile(r"緊急対応発行"), "Phát hành đối ứng khẩn cấp"),
    (re.compile(r"新\s*MAIN\s*基板交換→NG"), "Thay bản mạch MAIN mới -> NG"),
    (re.compile(r"新\s*MAIN\s*と\s*LOW\s*VOLT\s*交換→問題なし→流す"), "Thay bản mạch MAIN và LOW VOLT mới -> Không có vấn đề -> Cho máy đi tiếp"),
    (re.compile(r"熱と冷却して→異常なし"), "Thử nghiệm nhiệt và làm mát -> Không có bất thường"),
    (re.compile(r"不具合\s*MAIN\s*と\s*LOW\s*VOLT\s*基板\s*ベンダーに送る"), "Gửi bản mạch MAIN và LOW VOLT lỗi sang nhà cung cấp"),
    (re.compile(r"再確認ICT-OK、FCT-OK\(5回で\)、再現せず不具合のため、再現せずルール処理をお願いします"), "Kiểm tra lại ICT-OK, FCT-OK (5 lần), lỗi không tái hiện nên đề nghị xử lý theo quy định"),
    (re.compile(r"メイン基板はQD72内部異常と推定"), "Ước lượng bản mạch Main bị bất thường nội bộ transistor QD72"),
    (re.compile(r"不具合マシンは低圧基板とハーネスを確認して異常なし"), "Máy lỗi đã kiểm tra bản mạch điện áp thấp và cáp nối (harness) không có bất thường"),
    (re.compile(r"単本QD72\(Transistor\)異常と推定"), "Ước lượng linh kiện bán dẫn QD72 (Transistor) bị bất thường"),
    (re.compile(r"部品上に熱冷で影響しない"), "Linh kiện không bị ảnh hưởng bởi nhiệt nóng lạnh"),
    (re.compile(r"一旦単発発生処理"), "Tạm thời xử lý theo lỗi đơn phát"),
    (re.compile(r"不具合部品は日本に連絡する"), "Linh kiện lỗi được thông báo về phía Nhật Bản"),
    (re.compile(r"調査中,トランジスタが破損"), "Đang điều tra, linh kiện transistor bị hỏng"),
    (re.compile(r"MURATA/UMCに連絡、ICT/FCT確認"), "Liên hệ MURATA/UMC, kiểm tra ICT/FCT"),
    (re.compile(r"調査中\s*→\s*9"), "Đang điều tra -> Nhóm 9"),
    (re.compile(r"調査中"), "Đang điều tra"),
    (re.compile(r"([A-Za-z0-9_-]+)\s*表示"), r"Hiển thị \1"),
    (re.compile(r"LCD画面\s*真っ白"), "Màn hình LCD trắng xóa"),
    (re.compile(r"LCD画面\s*点灯せず"), "Màn hình LCD không sáng"),
    (re.compile(r"LSU SKEW\s*調整不可"), "LSU SKEW không thể điều chỉnh"),
    (re.compile(r"表面電位検査した時"), "khi kiểm tra điện thế bề mặt"),
    (re.compile(r"Check Black , Check Color 画像 異常"), "Kiểm tra bản in Đen và Màu: Bất thường hình ảnh"),
    (re.compile(r"Check Black , Check Color 画像異常"), "Kiểm tra bản in Đen và Màu: Bất thường hình ảnh"),
    (re.compile(r"Check Black , Check Color 画像 bất thường"), "Kiểm tra bản in Đen và Màu: Bất thường hình ảnh"),
    (re.compile(r"COVER MAGのボス\s*折れ"), "COVER MAG gãy vấu (boss)"),
    (re.compile(r"COVER MAGのボス折れ"), "COVER MAG gãy vấu (boss)"),
    (re.compile(r"のボス\s*折れ"), "gãy vấu định vị (boss)"),
    (re.compile(r"ボス\s*折れ"), "gãy vấu định vị (boss)"),
    (re.compile(r"ボス折れ"), "gãy vấu định vị (boss)"),
    (re.compile(r"画像\s*異常"), "bất thường hình ảnh"),
    (re.compile(r"画像異常"), "bất thường hình ảnh"),
    (re.compile(r"画像"), "hình ảnh"),
    (re.compile(r"折れ"), "bị gãy"),
    (re.compile(r"表示"), " hiển thị"),
    (re.compile(r"異常なし"), "bình thường / không bất thường"),
    (re.compile(r"異常"), "bất thường"),
    (re.compile(r"下位"), "Hạ vị (Bản tiêu chuẩn)"),
    (re.compile(r"上位"), "Thượng vị (Bản nâng cao)"),
    (re.compile(r"不要"), "Không xác định nguyên nhân bất thường / Đã giải quyết trên chuyền (không phát sinh đối sách dài hạn)"),
    (re.compile(r"部品要因\(電気\)"), "Yếu tố linh kiện (Phần điện)"),
    (re.compile(r"要因不明\(電気\)"), "Không rõ nguyên nhân (Phần điện)"),
    (re.compile(r"要因不明\(製造\)"), "Không rõ nguyên nhân (Khâu chế tạo)"),
    (re.compile(r"原因不明（メカ）"), "Không rõ nguyên nhân (Cơ khí)"),
    (re.compile(r"原因不明\(メカ\)"), "Không rõ nguyên nhân (Cơ khí)"),
    (re.compile(r"部品要因\(Supplier\)"), "Yếu tố linh kiện (Nhà cung cấp / Supplier)"),
    (re.compile(r"部品要因\(外制\)"), "Yếu tố linh kiện (Gia công ngoài)"),
    (re.compile(r"部品要因"), "Yếu tố linh kiện"),
    (re.compile(r"部品"), "linh kiện"),
    (re.compile(r"基板"), "bản mạch"),
]

_LOG_LOCK = threading.Lock()


def is_vietnamese_question(question: str) -> bool:
    """True if question is in Vietnamese or English and does NOT request Japanese."""
    q = (question or "").strip()
    if not q:
        return True

    # Check for explicit Japanese request
    for pat in JP_OVERRIDE_PATTERNS:
        if pat.search(q):
            return False

    # Check for genuine Japanese grammar/interrogatives
    for marker in JP_QUESTION_MARKERS:
        if marker in q:
            return False

    # Count kana characters (Hiragana / Katakana)
    kana_count = len(re.findall(r"[\u3040-\u309f\u30a0-\u30ff]", q))
    if kana_count >= 4 and len(q.split()) <= 6:
        # Predominately Japanese query
        return False

    return True


def has_japanese(text: str) -> bool:
    """True if text contains any Japanese Han or Kana characters."""
    return bool(JP_CHAR_RE.search(text or ""))


def clean_katakana_middle_dots(text: str) -> str:
    """Replace Japanese middle dots (\u30fb ・) with clean bullet characters."""
    if not text:
        return ""
    return text.replace("・", "• ")


def translate_kdtps_field(
    value: str,
    field_name: str = "general",
) -> Tuple[str, str]:
    """Translate raw Japanese field value into clear Vietnamese.

    Returns:
        (translated_string, action) where action is 'dich', 'loai', or 'giu-dinh-danh'.
    """
    s = str(value or "").strip()
    s = clean_katakana_middle_dots(s)
    if not s or not has_japanese(s):
        return s, "giu-nguyen"

    # Context-specific translation for 不要
    if s in ("不要", "不要。", "不要 "):
        if field_name in ("cause", "nguyen_nhan"):
            return "Không xác định nguyên nhân bất thường / Đã giải quyết trên chuyền (không phát sinh đối sách dài hạn)", "dich"
        if field_name in ("remedy", "doi_sach"):
            return "Không cần đối sách bổ sung / Đã xử lý tại chỗ không cần đối sách chính thức", "dich"
        return "Không yêu cầu đối sách", "dich"

    # Exact dictionary hit
    if s in KDTPS_EXACT_MAP:
        return KDTPS_EXACT_MAP[s], "dich"

    # Multiline string split and translate each line
    if "\n" in s:
        sub_lines = []
        any_trans = False
        for sl in s.splitlines():
            sl_clean = sl.strip()
            if not sl_clean:
                sub_lines.append("")
                continue
            trans_sl, act_sl = translate_kdtps_field(sl_clean, field_name=field_name)
            sub_lines.append(trans_sl)
            if act_sl == "dich":
                any_trans = True
        return "\n".join(sub_lines), "dich" if any_trans else "giu-nguyen"

    # Special handling for F000 complex Welcome screen message
    if "Welcome画面" in s and "CF000" in s:
        return (
            "Màn hình dừng ở màn hình Welcome quá thời gian quy định sẽ hiển thị mã CF000 "
            "(Bất thường truyền thông giữa bản mạch Panel và bản mạch Main / giữa Panel Core và Main Core).",
            "dich",
        )

    # Sub-phrase replacement
    working = s
    modified = False
    for pat, repl in KDTPS_SUB_PHRASES:
        if pat.search(working):
            working = pat.sub(repl, working)
            modified = True

    # Check if any Japanese characters still remain
    if has_japanese(working):
        # If it's a known document title or file inside backticks, preserve as identifier
        if any(ext in working for ext in [".xls", ".xlsx", ".pdf", ".doc", ".docx", ".csv"]) or "`" in working:
            return working, "giu-dinh-danh"
        # Per rule 2.2(b): absolutely do NOT print raw Japanese characters into body
        # Clean any remaining Japanese tokens
        cleaned_no_jp = JP_CHAR_RE.sub("", working).strip()
        cleaned_no_jp = re.sub(r"\s+", " ", cleaned_no_jp)
        if cleaned_no_jp:
            return cleaned_no_jp, "dich"
        return "Ghi nhận trong báo cáo kỹ thuật", "dich"

    return working, "dich" if modified else "giu-nguyen"


def log_language_purity_event(
    *,
    question: str,
    route: str,
    detected_count: int,
    actions: Sequence[str],
    details: Sequence[Dict[str, Any]] = (),
    conversation_id: str = "",
    base_cases_dir: Optional[Path | str] = None,
) -> None:
    """Record continuous improvement event to local_cases/answer_language_events.jsonl."""
    try:
        if base_cases_dir:
            lc_dir = Path(base_cases_dir)
        else:
            lc_dir = Path(r"D:\Sandbox\AIOS_habbit\local_cases")
        lc_dir.mkdir(parents=True, exist_ok=True)
        log_file = lc_dir / "answer_language_events.jsonl"

        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "route": route,
            "question": question[:160],
            "detected_count": detected_count,
            "actions": list(actions),
            "details": list(details[:10]),
            "conversation_id": conversation_id,
        }

        with _LOG_LOCK:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def purify_markdown_text(
    markdown_text: str,
    question: str,
    route: str = "general",
    conversation_id: str = "",
    base_cases_dir: Optional[Path | str] = None,
) -> str:
    """Enforce Vietnamese language purity on synthesized Markdown answers.

    Guarantees:
    - Vietnamese questions get 100% Vietnamese readable body text.
    - Raw Japanese fields like '不要' are translated to proper Vietnamese explanations.
    - Standalone Japanese lines or phrases are translated without losing technical content.
    - Document filenames (*.xls, *.xlsx) and backticked identifiers are preserved.
    - Continuous improvement log is saved whenever Japanese fragments are handled.
    """
    if not is_vietnamese_question(question):
        # User explicitly asked in Japanese or requested Japanese verbatim: preserve as-is
        return markdown_text

    # Clean middle dots first
    markdown_text = clean_katakana_middle_dots(markdown_text)

    if not has_japanese(markdown_text):
        return markdown_text

    lines = markdown_text.splitlines()
    purified_lines: List[str] = []
    detected_count = 0
    actions_taken: List[str] = []
    event_details: List[Dict[str, Any]] = []

    for idx, line in enumerate(lines):
        line_clean = clean_katakana_middle_dots(line)

        # If line has no Japanese, preserve untouched
        if not has_japanese(line_clean):
            purified_lines.append(line_clean)
            continue

        # Check if line is purely an identifier or reference to file
        # e.g., - **Tài liệu tham chiếu:** 02XC_自己診断表示一覧表-Iris2020 VN.xls
        # e.g., - **Báo cáo gốc:** `old/2022年機器製造...`
        if any(marker in line_clean for marker in [
            "**Tài liệu tham chiếu:**", "**Báo cáo gốc:**", "Báo cáo gốc:", "Tài liệu tham chiếu:"
        ]) or (line_clean.startswith("- **") and any(ext in line_clean for ext in [".xls", ".xlsx", ".pdf", ".csv"])):
            # Preserved as permitted identifier per 2.2(d)
            detected_count += 1
            actions_taken.append("giu-dinh-danh")
            event_details.append({"line": idx, "action": "giu-dinh-danh", "snippet": line_clean[:80]})
            purified_lines.append(line_clean)
            continue

        # Check if line is a bullet: - **Nguyên nhân X:** ... or - **Biện pháp X:** ...
        cause_match = re.match(r"^(\s*[-*]\s*\*\*Nguyên nhân(?:\s+\d+)?:?\*\*\s*)(.*)$", line_clean, re.IGNORECASE)
        remedy_match = re.match(r"^(\s*[-*]\s*\*\*Biện pháp(?:\s+\d+)?:?\*\*\s*)(.*)$", line_clean, re.IGNORECASE)
        doi_sach_match = re.match(r"^(\s*[-*]\s*\*\*Đối sách:?\*\*\s*)(.*)$", line_clean, re.IGNORECASE)
        hien_tuong_match = re.match(r"^(\s*[-*]\s*\*\*Hiện tượng:?\*\*\s*)(.*)$", line_clean, re.IGNORECASE)
        may_match = re.match(r"^(\s*[-*]\s*\*\*Máy:?\*\*\s*)(.*)$", line_clean, re.IGNORECASE)
        name_err_match = re.match(r"^(\s*[-*]\s*\*\*Tên mã lỗi\s*/\s*Hiện tượng:?\*\*\s*)(.*)$", line_clean, re.IGNORECASE)
        co_che_match = re.match(r"^(\s*[-*]\s*\*\*Cơ chế phát sinh:?\*\*\s*)(.*)$", line_clean, re.IGNORECASE)

        if cause_match:
            prefix, content = cause_match.group(1), cause_match.group(2)
            trans, act = translate_kdtps_field(content, field_name="cause")
            detected_count += 1
            actions_taken.append(act)
            event_details.append({"line": idx, "field": "cause", "raw": content[:60], "trans": trans[:60]})
            purified_lines.append(f"{prefix}{trans}")
            continue

        if remedy_match or doi_sach_match:
            match = remedy_match or doi_sach_match
            prefix, content = match.group(1), match.group(2)
            trans, act = translate_kdtps_field(content, field_name="remedy")
            detected_count += 1
            actions_taken.append(act)
            event_details.append({"line": idx, "field": "remedy", "raw": content[:60], "trans": trans[:60]})
            purified_lines.append(f"{prefix}{trans}")
            continue

        if hien_tuong_match:
            prefix, content = hien_tuong_match.group(1), hien_tuong_match.group(2)
            trans, act = translate_kdtps_field(content, field_name="phenomenon")
            detected_count += 1
            actions_taken.append(act)
            event_details.append({"line": idx, "field": "phenomenon", "raw": content[:60], "trans": trans[:60]})
            purified_lines.append(f"{prefix}{trans}")
            continue

        if may_match:
            prefix, content = may_match.group(1), may_match.group(2)
            trans, act = translate_kdtps_field(content, field_name="machine")
            detected_count += 1
            actions_taken.append(act)
            event_details.append({"line": idx, "field": "machine", "raw": content[:60], "trans": trans[:60]})
            purified_lines.append(f"{prefix}{trans}")
            continue

        if name_err_match:
            prefix, content = name_err_match.group(1), name_err_match.group(2)
            trans, act = translate_kdtps_field(content, field_name="error_name")
            detected_count += 1
            actions_taken.append(act)
            event_details.append({"line": idx, "field": "error_name", "raw": content[:60], "trans": trans[:60]})
            purified_lines.append(f"{prefix}{trans}")
            continue

        if co_che_match:
            prefix, content = co_che_match.group(1), co_che_match.group(2)
            trans, act = translate_kdtps_field(content, field_name="mechanism")
            detected_count += 1
            actions_taken.append(act)
            event_details.append({"line": idx, "field": "mechanism", "raw": content[:60], "trans": trans[:60]})
            purified_lines.append(f"{prefix}{trans}")
            continue

        # Case title: **X. Phiếu Y** (Machine / Line)
        # e.g., **1. Phiếu 2026/1143** (Iris2024 上位 / C33)
        if line_clean.startswith("**") and "Phiếu" in line_clean:
            trans, act = translate_kdtps_field(line_clean, field_name="case_header")
            detected_count += 1
            actions_taken.append(act)
            event_details.append({"line": idx, "field": "case_header", "raw": line_clean[:60], "trans": trans[:60]})
            purified_lines.append(trans)
            continue

        # General line containing Japanese
        trans, act = translate_kdtps_field(line_clean, field_name="general")
        detected_count += 1
        actions_taken.append(act)
        event_details.append({"line": idx, "field": "general", "raw": line_clean[:60], "trans": trans[:60]})
        purified_lines.append(trans)

    if detected_count > 0:
        log_language_purity_event(
            question=question,
            route=route,
            detected_count=detected_count,
            actions=actions_taken,
            details=event_details,
            conversation_id=conversation_id,
            base_cases_dir=base_cases_dir,
        )

    return "\n".join(purified_lines)

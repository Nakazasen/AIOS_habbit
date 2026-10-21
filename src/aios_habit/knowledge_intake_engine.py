"""Bộ máy thu tri thức chuyên gia không phụ thuộc kho tri thức (Knowledge Intake Engine).

Kiến trúc:
1. Độc lập kho đích: phiên hoạt động theo Hồ sơ đích (Target Profile) đã chọn.
2. Hai chế độ vận hành:
   (a) Chế độ PHỎNG VẤN (Interview Mode - `phong_van`):
       AI dẫn hỏi từng câu một theo khung 4M + Why-Why. Khi câu trả lời chung chung
       hoặc thiếu thông tin, AI tự động đào sâu:
       - Dấu hiệu nhận biết sớm (`dau_hieu_som`)
       - Cách phân biệt với lỗi gần giống (`phan_biet_loi_gan_giong`)
       - Xử lý nào đã hiệu quả (`xu_ly_hieu_qua`)
       - Xử lý nào đã thử mà không hiệu quả (`xu_ly_khong_hieu_qua`)
       - Điều kiện phát sinh (`dieu_kien_phat_sinh`)
       - Model / line liên quan (`model_line`)
   (b) Chế độ DẠY (Teaching Mode - `day`):
       Chuyên gia là người giảng, AI đóng vai người học và hỏi lại để làm rõ:
       - Phạm vi áp dụng (`pham_vi_ap_dung`)
       - Trường hợp ngoại lệ (`truong_hop_ngoai_le`)
       - Ví dụ thật ở nhà máy (`vi_du_that_nha_may`)
       - Chỗ người mới hay hiểu sai (`cho_nguoi_moi_hay_hieu_sai`)
3. Tổng hợp & Truy vết nguồn nguyên văn:
   - Mỗi mục nháp trích NGUYÊN VĂN câu trả lời làm căn cứ nguồn.
   - Dẫn chiếu chính xác turn ID và nhãn nguồn thống nhất.
4. Chống bịa đặt (Anti-Hallucination):
   - Thông tin chuyên gia không nhắc tới: để trống hoặc ghi "chưa xác nhận".
   - Tuyệt đối không tự suy diễn thành tri thức.

Tương thích Python 3.11: không dùng f-string nhiều dòng (PEP 701), không type statement.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from aios_habit.intake_staging import (
    INGEST_CHO_NAP,
    INGEST_KHONG_NAP,
    STATUS_CHO_DUYET,
    IntakeDraftItemRecord,
    IntakeSessionRecord,
    IntakeStagingStore,
    IntakeTurnRecord,
)
from aios_habit.intake_target_profiles import (
    STORE_ID_LSU,
    STORE_ID_TONG_HOP,
    TargetProfile,
    format_source_tag,
    format_tonghop_source_tag,
    get_target_profile,
)

# Chế độ thu tri thức
MODE_PHONG_VAN = "phong_van"
MODE_DAY = "day"

# Các loại câu hỏi đào sâu trong chế độ Phỏng vấn
PROBE_4M_WHY = "4m_why_why"
PROBE_DAU_HIEU_SOM = "dau_hieu_som"
PROBE_PHAN_BIET_LOI = "phan_biet_loi_gan_giong"
PROBE_XU_LY_HIEU_QUA = "xu_ly_hieu_qua"
PROBE_XU_LY_KHONG_HIEU_QUA = "xu_ly_khong_hieu_qua"
PROBE_DIEU_KIEN_PHAT_SINH = "dieu_kien_phat_sinh"
PROBE_MODEL_LINE = "model_line"

# Các loại câu hỏi làm rõ trong chế độ Dạy
CLARIFY_PHAM_VI = "pham_vi_ap_dung"
CLARIFY_NGOAI_LE = "truong_hop_ngoai_le"
CLARIFY_VI_DU_THAT = "vi_du_that_nha_may"
CLARIFY_HIEU_SAI = "cho_nguoi_moi_hay_hieu_sai"


# ---------------------------------------------------------------------------
# Cấu trúc câu hỏi định sẵn theo khung
# ---------------------------------------------------------------------------

INTERVIEW_BASE_QUESTIONS: Tuple[Tuple[str, str], ...] = (
    (
        "hien_tuong_ma_loi",
        "Chào anh/chị, chúng ta bắt đầu thu thập tri thức về chủ đề “{topic}”. "
        "Trước tiên, mã lỗi cụ thể là gì và hiện tượng lỗi quan sát được trên máy diễn ra như thế nào?",
    ),
    (
        PROBE_4M_WHY,
        "Theo khung phân tích 4M (Con người - Máy móc - Nguyên vật liệu - Phương pháp) "
        "kết hợp chuỗi Tại sao - Tại sao (Why-Why), nguyên nhân gốc rễ kỹ thuật gây ra lỗi này là gì?",
    ),
    (
        PROBE_XU_LY_HIEU_QUA,
        "Đối sách xử lý nào đã thực sự giải quyết được lỗi triệt để?",
    ),
    (
        "cong_doan_line",
        "Lỗi này xảy ra ở công đoạn nào trong dây chuyền sản xuất, và thuộc model máy / line nào?",
    ),
)

TEACHING_BASE_QUESTIONS: Tuple[Tuple[str, str], ...] = (
    (
        "mo_dau_bai_giang",
        "Em chào anh/chị. Em rất mong được học hỏi kinh nghiệm về chủ đề “{topic}”. "
        "Anh/chị giảng giải giúp em tổng quan về nội dung này và nguyên lý hoạt động thực tế với ạ?",
    ),
    (
        CLARIFY_PHAM_VI,
        "Dạ em hiểu rồi ạ. Cho em hỏi thêm: kiến thức này áp dụng cho những dòng máy, "
        "công đoạn hoặc điều kiện cụ thể nào tại nhà máy mình ạ?",
    ),
    (
        CLARIFY_VI_DU_THAT,
        "Anh/chị có thể chia sẻ cho em một ví dụ thực tế cụ thể đã từng xảy ra ở nhà máy "
        "liên quan đến bài học này được không ạ?",
    ),
    (
        CLARIFY_HIEU_SAI,
        "Đối với kiến thức này, những người mới vào hoặc kỹ thuật viên mới thường hay "
        "hiểu sai hoặc làm sai ở những điểm nào nhất ạ?",
    ),
)


# ---------------------------------------------------------------------------
# Data Models của phiên đang hoạt động
# ---------------------------------------------------------------------------


@dataclass
class ActiveTurn:
    turn_id: str
    turn_index: int
    speaker: str
    question_text: str
    answer_text: str = ""
    probe_type: str = "general"
    timestamp: str = ""


@dataclass
class KnowledgeIntakeSession:
    """Phiên thu tri thức đang diễn ra trong bộ nhớ chat."""

    session_id: str
    store_id: str
    mode: str
    expert_name: str
    topic: str
    profile: TargetProfile
    created_at: str = ""
    status: str = "in_progress"
    turns: List[ActiveTurn] = field(default_factory=list)
    pending_probes: List[Tuple[str, str]] = field(default_factory=list)
    draft_items: List[IntakeDraftItemRecord] = field(default_factory=list)

    @property
    def is_completed(self) -> bool:
        return self.status in ("ended", "reviewed")


# ---------------------------------------------------------------------------
# Logic đánh giá câu trả lời & tạo câu hỏi đào sâu
# ---------------------------------------------------------------------------


def detect_missing_aspects_interview(answer_text: str) -> List[str]:
    """Phát hiện các khía cạnh còn thiếu hoặc chung chung trong câu trả lời phỏng vấn.

    Quy chuẩn nhận diện khía cạnh đã có:
    - Chỉ tính là 'đã có' khi chứa cụm từ đặc hiệu (ngữ cảnh rõ ràng),
      tuyệt đối không đánh dấu đã có chỉ vì một từ đơn lẻ / chuỗi con ngẫu nhiên
      (ví dụ: từ 'nhiệt' trong 'quá nhiệt' không được tính là dấu hiệu sớm;
       từ 'dòng' trong 'dòng điện' không được tính là model/line;
       từ 'không được' trong mệnh lệnh cấm không được tính là xử lý không hiệu quả).
    """
    clean = str(answer_text or "").strip().lower()
    missing: List[str] = []

    # 1. Kiểm tra dấu hiệu sớm: cụm từ chỉ dấu hiệu / cảnh báo trước
    dau_hieu_keywords = (
        "dấu hiệu",
        "dau hieu",
        "nhận biết sớm",
        "nhan biet som",
        "báo trước",
        "bao truoc",
        "trước khi",
        "truoc khi",
        "triệu chứng sớm",
        "trieu chung som",
        "dấu hiệu sớm",
        "dau hieu som",
    )
    if not any(k in clean for k in dau_hieu_keywords):
        missing.append(PROBE_DAU_HIEU_SOM)

    # 2. Kiểm tra phân biệt lỗi gần giống: cụm từ so sánh / phân biệt / tránh nhầm lẫn
    phan_biet_keywords = (
        "khác với",
        "khac voi",
        "phân biệt",
        "phan biet",
        "dễ nhầm",
        "de nham",
        "nhầm lẫn",
        "nham lan",
        "gần giống",
        "gan giong",
        "tránh nhầm",
        "tranh nham",
        "so với lỗi",
        "so voi loi",
    )
    if not any(k in clean for k in phan_biet_keywords):
        missing.append(PROBE_PHAN_BIET_LOI)

    # 3. Kiểm tra xử lý đã thử mà không hiệu quả: cụm từ nêu rõ thử nghiệm thất bại
    khong_hieu_qua_keywords = (
        "không hiệu quả",
        "khong hieu qua",
        "chưa hiệu quả",
        "chua hieu qua",
        "không có tác dụng",
        "khong co tac dung",
        "đã thử nhưng",
        "da thu nhung",
        "thử nhưng không",
        "thu nhung khong",
        "thử nhưng chưa",
        "thu nhung chua",
        "xử lý không hết",
        "xu ly khong het",
        "thay thử nhưng vẫn",
        "thay thu nhung van",
    )
    if not any(k in clean for k in khong_hieu_qua_keywords):
        missing.append(PROBE_XU_LY_KHONG_HIEU_QUA)

    # 4. Kiểm tra điều kiện phát sinh: cụm từ chỉ điều kiện môi trường / bối cảnh cụ thể
    dieu_kien_keywords = (
        "điều kiện",
        "dieu kien",
        "thời tiết",
        "thoi tiet",
        "môi trường làm việc",
        "moi truong lam viec",
        "môi trường xung quanh",
        "nhiệt độ môi trường",
        "nhiet do moi truong",
        "nhiệt độ phòng",
        "nhiet do phong",
        "độ ẩm môi trường",
        "do am moi truong",
        "độ ẩm cao",
        "do am cao",
        "chạy liên tục",
        "chay lien tuc",
        "hoàn cảnh phát sinh",
        "thời điểm phát sinh",
        "khi vào ca",
        "sau khi thay",
        "mùa đông",
        "mua dong",
        "mùa hè",
        "mua he",
        "trời nồm",
        "sau khi bảo dưỡng",
        "sau khi bao duong",
    )
    if not any(k in clean for k in dieu_kien_keywords):
        missing.append(PROBE_DIEU_KIEN_PHAT_SINH)

    # 5. Kiểm tra model/line: cụm từ hoặc mẫu định danh model / dây chuyền cụ thể
    model_line_phrases = (
        "model",
        "dòng máy",
        "dong may",
        "dây chuyền",
        "day chuyen",
        "line sản xuất",
        "line san xuat",
    )
    has_model_phrase = any(k in clean for k in model_line_phrases)
    has_line_num = bool(re.search(r"\b(line\s*\d+|dây chuyền\s*\d+)\b", clean))
    has_known_model = bool(re.search(r"\b(sirius|iris|6tha3|a3|a4|dmt|pmt)\b", clean))
    if not (has_model_phrase or has_line_num or has_known_model):
        missing.append(PROBE_MODEL_LINE)

    return missing


def build_deep_probe_question(probe_type: str, topic: str) -> str:
    """Tạo câu hỏi đào sâu tương ứng cho chế độ phỏng vấn."""
    if probe_type == PROBE_DAU_HIEU_SOM:
        return (
            "Dấu hiệu nhận biết sớm trước khi lỗi này phát sinh là gì? "
            "(Ví dụ: âm thanh bất thường, nhiệt độ thay đổi, cảm biến chập chờn?)"
        )
    if probe_type == PROBE_PHAN_BIET_LOI:
        return (
            "Lỗi này dễ bị nhầm lẫn với lỗi nào khác trong xưởng, "
            "và cách phân biệt cụ thể bằng mắt hoặc thông số đo đạc là gì?"
        )
    if probe_type == PROBE_XU_LY_KHONG_HIEU_QUA:
        return (
            "Trong quá khứ, những cách xử lý nào đã từng thử qua nhưng KHÔNG mang lại hiệu quả "
            "để anh em kỹ thuật sau này tránh lặp lại?"
        )
    if probe_type == PROBE_DIEU_KIEN_PHAT_SINH:
        return (
            "Điều kiện phát sinh lỗi cụ thể là gì? "
            "(Nhiệt độ, độ ẩm cao, chạy liên tục nhiều ca, hay sau khi thay vật tư mới?)"
        )
    if probe_type == PROBE_MODEL_LINE:
        return (
            "Hiện tượng này có xảy ra đồng loạt hay chỉ đặc thù trên một số model / line sản xuất cụ thể nào?"
        )
    return "Anh/chị có thể chia sẻ chi tiết thêm về khía cạnh kỹ thuật này được không ạ?"


def build_teaching_clarification(probe_type: str, topic: str) -> str:
    """Tạo câu hỏi làm rõ trong chế độ Dạy."""
    if probe_type == CLARIFY_PHAM_VI:
        return (
            "Em xin làm rõ: kiến thức này áp dụng cho phạm vi những model máy, "
            "công đoạn hoặc thiết bị nào tại nhà máy mình ạ?"
        )
    if probe_type == CLARIFY_NGOAI_LE:
        return (
            "Có trường hợp ngoại lệ nào mà quy tắc hoặc nguyên lý này không đúng "
            "hoặc phải xử lý theo cách khác không ạ?"
        )
    if probe_type == CLARIFY_VI_DU_THAT:
        return (
            "Anh/chị có thể cho em một ví dụ thực tế đã từng xảy ra ở nhà máy "
            "để em và mọi người dễ hình dung không ạ?"
        )
    if probe_type == CLARIFY_HIEU_SAI:
        return (
            "Ở chỗ này, những người mới vào nghề hoặc kỹ thuật viên mới thường hay "
            "hiểu sai hoặc thao tác nhầm điều gì nhất ạ?"
        )
    return "Dạ anh/chị giảng thêm giúp em phần này được không ạ?"


# ---------------------------------------------------------------------------
# Trích xuất dữ liệu không bịa (Anti-Hallucination Extraction)
# ---------------------------------------------------------------------------


def _extract_error_code(text: str) -> str:
    """Tìm mã lỗi tiêu chuẩn như C7620, C3501, F000, JAM4709."""
    match = re.search(r"\b([CFJcfj]\s*-?\d{3,4}|JAM\s*-?\d{3,4}|[A-Z]\d{3,4})\b", text)
    if match:
        return match.group(1).upper().replace(" ", "").replace("-", "")
    return ""


def _extract_model(text: str) -> str:
    """Trích xuất model máy nếu có trong văn bản."""
    match_explicit = re.search(
        r"(?:model|dòng máy|dong may)\s+([A-Za-z0-9_-]{2,20})\b",
        text,
        re.IGNORECASE,
    )
    if match_explicit:
        return match_explicit.group(1).strip()
    match = re.search(r"\b(Sirius|Iris|6thA3|A3|A4|DMT|PMT)\b", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def _extract_line(text: str) -> str:
    """Trích xuất line sản xuất."""
    match = re.search(r"\b(line\s*\d+|dây chuyền\s*\d+)\b", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def _extract_cong_doan(text: str) -> str:
    """Trích xuất tên công đoạn sản xuất chỉ khi được nêu rõ (không tự suy diễn từ tên linh kiện)."""
    match = re.search(
        r"(?:công đoạn|cong doan|khâu|khau|trạm|tram)\s+([A-ZÀ-Ỹa-zà-ỹ0-9\s]{2,30}?)(?=[,\.\n;]|va\b|và\b|trên\b|tren\b|thuộc\b|thuoc\b|ở\b|o\b|$)",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip().title()
    return ""


def synthesize_draft_items(session: KnowledgeIntakeSession) -> List[IntakeDraftItemRecord]:
    """Tổng hợp toàn bộ lượt hỏi-đáp của phiên thành các mục nháp theo Hồ sơ đích.

    Quy tắc đạo đức & chất lượng bắt buộc:
    1. Trích NGUYÊN VĂN câu trả lời làm căn cứ nguồn (source_quote).
    2. Dẫn chiếu rõ ràng turn IDs tham gia.
    3. Nhãn nguồn thống nhất: loai + ten nguoi + ngay + kho dich.
    4. TUYỆT ĐỐI KHÔNG BỊA ĐẶT: trường nào người dùng không nói thì để trống
       hoặc ghi rõ "chưa xác nhận".
    """
    answers = [t for t in session.turns if t.answer_text.strip()]
    if not answers:
        return []

    combined_text = "\n\n".join(
        "Lượt %d (%s): %s" % (t.turn_index, t.probe_type, t.answer_text)
        for t in answers
    )
    full_verbatim = " | ".join(t.answer_text.strip() for t in answers)
    source_turn_ids = tuple(t.turn_id for t in answers)
    now_iso = datetime.now().isoformat()
    today_str = datetime.now().strftime("%Y-%m-%d")

    source_tag = format_source_tag(
        mode=session.mode,
        expert_name=session.expert_name,
        date_str=today_str,
        store_id=session.store_id,
    )

    profile = session.profile
    draft_id = "draft-%s-%s" % (session.store_id, uuid.uuid4().hex[:8])

    fields: Dict[str, str] = {}

    if session.store_id == STORE_ID_LSU:
        # Áp dụng khuôn Kho LSU
        detected_code = _extract_error_code(combined_text) or _extract_error_code(session.topic)
        detected_model = _extract_model(combined_text) or _extract_model(session.topic)
        detected_line = _extract_line(combined_text)
        detected_cong_doan = _extract_cong_doan(combined_text)

        hien_tuong_val = ""
        nguyen_nhan_val = ""
        doi_sach_val = ""
        dau_hieu_val = ""
        ghi_chu_pieces: List[str] = []

        for t in answers:
            pt = t.probe_type
            ans = t.answer_text.strip()
            low_ans = ans.lower()
            if pt in ("hien_tuong_ma_loi", "mo_dau_bai_giang") and not hien_tuong_val:
                hien_tuong_val = ans
            elif pt == PROBE_4M_WHY and not nguyen_nhan_val:
                nguyen_nhan_val = ans
            elif pt == PROBE_XU_LY_HIEU_QUA and not doi_sach_val:
                doi_sach_val = ans
            elif pt == PROBE_DAU_HIEU_SOM and not dau_hieu_val:
                dau_hieu_val = ans
            elif pt in (
                PROBE_PHAN_BIET_LOI,
                PROBE_XU_LY_KHONG_HIEU_QUA,
                PROBE_DIEU_KIEN_PHAT_SINH,
                CLARIFY_HIEU_SAI,
                CLARIFY_VI_DU_THAT,
                CLARIFY_NGOAI_LE,
                CLARIFY_PHAM_VI,
            ):
                ghi_chu_pieces.append("[%s]: %s" % (pt, ans))

            # Nếu trong câu trả lời bất kỳ chuyên gia đã nêu rõ nguyên nhân / đối sách / dấu hiệu sớm
            if (
                not nguyen_nhan_val
                and any(k in low_ans for k in ("nguyên nhân", "nguyen nhan", "4m", "why-why"))
                and not any(
                    neg in low_ans
                    for neg in ("chưa rõ nguyên nhân", "chua ro nguyen nhan", "không rõ nguyên nhân")
                )
            ):
                nguyen_nhan_val = ans
            if not doi_sach_val and any(
                k in low_ans
                for k in ("đối sách", "doi sach", "xử lý hiệu quả", "xu ly hieu qua", "khắc phục")
            ):
                doi_sach_val = ans
            if not dau_hieu_val and any(
                k in low_ans for k in ("dấu hiệu nhận biết sớm", "dấu hiệu sớm", "dau hieu som")
            ):
                dau_hieu_val = ans

        # Nếu chưa phân tách rõ, lấy câu đầu làm hiện tượng
        if not hien_tuong_val and answers:
            hien_tuong_val = answers[0].answer_text.strip()

        # 5 trường bắt buộc
        fields["ma_loi"] = detected_code if detected_code else "chưa xác nhận"
        fields["hien_tuong"] = hien_tuong_val if hien_tuong_val else "chưa xác nhận"
        fields["nguyen_nhan"] = nguyen_nhan_val if nguyen_nhan_val else "chưa xác nhận"
        fields["doi_sach"] = doi_sach_val if doi_sach_val else "chưa xác nhận"
        fields["cong_doan"] = detected_cong_doan if detected_cong_doan else "chưa xác nhận"

        # Các trường phụ
        fields["model"] = detected_model if detected_model else "chưa xác nhận"
        fields["line"] = detected_line if detected_line else "chưa xác nhận"
        fields["dau_hieu_som"] = dau_hieu_val if dau_hieu_val else "chưa xác nhận"
        fields["ghi_chu"] = (
            " ".join(ghi_chu_pieces).strip() if ghi_chu_pieces else "chưa xác nhận"
        )
    elif session.store_id == STORE_ID_TONG_HOP:
        # Áp dụng khuôn Kho kiến thức tổng hợp (chủ đề, nội dung, điều kiện áp dụng, ví dụ, nguồn)
        chu_de_val = session.topic if session.topic else ""
        noi_dung_val = ""
        dieu_kien_val = ""
        vi_du_val = ""
        ghi_chu_pieces: List[str] = []

        for t in answers:
            pt = t.probe_type
            ans = t.answer_text.strip()
            low_ans = ans.lower()
            if pt in ("mo_dau_bai_giang", "general") and not noi_dung_val:
                noi_dung_val = ans
            elif pt in (CLARIFY_PHAM_VI, "cong_doan_line", "dieu_kien_ap_dung") and not dieu_kien_val:
                dieu_kien_val = ans
            elif pt in (CLARIFY_VI_DU_THAT, "vi_du") and not vi_du_val:
                vi_du_val = ans
            elif pt in (CLARIFY_HIEU_SAI, CLARIFY_NGOAI_LE, "ghi_chu"):
                ghi_chu_pieces.append("[%s]: %s" % (pt, ans))

            # Tìm kiếm heuristic nếu câu trả lời chứa từ khóa
            if not dieu_kien_val and any(k in low_ans for k in ("áp dụng cho", "ap dung cho", "điều kiện", "dieu kien", "dòng máy", "dong may", "công đoạn")):
                dieu_kien_val = ans
            if not vi_du_val and any(k in low_ans for k in ("ví dụ", "vi du", "thực tế", "thuc te", "đã từng", "da tung")):
                vi_du_val = ans

        if not noi_dung_val and answers:
            noi_dung_val = answers[0].answer_text.strip()

        source_label = format_tonghop_source_tag(session.expert_name, today_str)

        # 5 trường bắt buộc
        fields["chu_de"] = chu_de_val if chu_de_val else "chưa xác nhận"
        fields["noi_dung"] = noi_dung_val if noi_dung_val else "chưa xác nhận"
        fields["dieu_kien_ap_dung"] = dieu_kien_val if dieu_kien_val else "chưa xác nhận"
        fields["vi_du"] = vi_du_val if vi_du_val else "chưa xác nhận"
        fields["nguon"] = source_label

        # Các trường phụ
        fields["nguoi_day"] = session.expert_name if session.expert_name else "chưa xác nhận"
        fields["ngay_day"] = today_str
        fields["linh_vuc"] = session.topic if session.topic else "chưa xác nhận"
        fields["ghi_chu"] = (
            " ".join(ghi_chu_pieces).strip() if ghi_chu_pieces else "chưa xác nhận"
        )
    else:
        # Kho thông thường khác: điền theo field specs
        for f in profile.fields:
            fields[f.name] = "chưa xác nhận"

    # Trích xuất câu trả lời đại diện làm căn cứ nguồn nguyên văn (tối đa 400 ký tự)
    source_quote = full_verbatim[:400] + ("…" if len(full_verbatim) > 400 else "")

    draft_record = IntakeDraftItemRecord(
        draft_id=draft_id,
        session_id=session.session_id,
        store_id=session.store_id,
        mode=session.mode,
        expert_name=session.expert_name,
        topic=session.topic,
        source_tag=source_tag,
        fields=fields,
        source_quote=source_quote,
        source_turn_ids=source_turn_ids,
        review_status=STATUS_CHO_DUYET,
        ingest_status=INGEST_KHONG_NAP,
        reviewed_by="",
        reviewed_at="",
        edited_fields={},
        created_at=now_iso,
        updated_at=now_iso,
    )
    return [draft_record]


# ---------------------------------------------------------------------------
# Bộ điều phối vòng đời phiên (Engine Controller)
# ---------------------------------------------------------------------------


class KnowledgeIntakeEngine:
    """Lõi điều phối quy trình thu tri thức cho mọi kho."""

    def __init__(self, staging_store: Optional[IntakeStagingStore] = None) -> None:
        self.staging = staging_store or IntakeStagingStore()

    def start_session(
        self,
        store_id: str = STORE_ID_LSU,
        mode: str = MODE_PHONG_VAN,
        topic: str = "",
        expert_name: str = "chuyên gia",
    ) -> KnowledgeIntakeSession:
        """Khởi tạo một phiên thu tri thức mới theo hồ sơ đích và chế độ."""
        profile = get_target_profile(store_id)
        if profile is None:
            raise ValueError(
                "Kho đích “%s” chưa có Hồ sơ đích được khai báo trong hệ thống." % store_id
            )

        sid = "intake-%s-%s" % (profile.source_prefix, uuid.uuid4().hex[:8])
        now_iso = datetime.now().isoformat()
        clean_topic = topic.strip() or "Tri thức kinh nghiệm vận hành"
        clean_expert = expert_name.strip() or "chuyên gia"
        clean_mode = MODE_DAY if mode == MODE_DAY else MODE_PHONG_VAN

        session = KnowledgeIntakeSession(
            session_id=sid,
            store_id=profile.store_id,
            mode=clean_mode,
            expert_name=clean_expert,
            topic=clean_topic,
            profile=profile,
            created_at=now_iso,
            status="in_progress",
        )

        # Lưu session vào staging
        self.staging.save_session(
            IntakeSessionRecord(
                session_id=sid,
                store_id=profile.store_id,
                mode=clean_mode,
                expert_name=clean_expert,
                topic=clean_topic,
                status="in_progress",
                created_at=now_iso,
                updated_at=now_iso,
            )
        )

        # Khởi tạo câu hỏi đầu tiên
        base_questions = (
            TEACHING_BASE_QUESTIONS if clean_mode == MODE_DAY else INTERVIEW_BASE_QUESTIONS
        )
        first_probe, first_template = base_questions[0]
        q_text = first_template.format(topic=clean_topic)

        turn_id = "turn-%s-0" % sid
        first_turn = ActiveTurn(
            turn_id=turn_id,
            turn_index=0,
            speaker="ai",
            question_text=q_text,
            probe_type=first_probe,
            timestamp=now_iso,
        )
        session.turns.append(first_turn)

        # Nạp sẵn các câu hỏi nền tiếp theo vào hàng đợi
        for p_type, tpl in base_questions[1:]:
            session.pending_probes.append((p_type, tpl.format(topic=clean_topic)))

        self.staging.save_turn(
            IntakeTurnRecord(
                turn_id=first_turn.turn_id,
                session_id=sid,
                store_id=profile.store_id,
                turn_index=first_turn.turn_index,
                speaker=first_turn.speaker,
                question_text=first_turn.question_text,
                answer_text="",
                probe_type=first_turn.probe_type,
                timestamp=now_iso,
            )
        )

        return session

    def submit_answer(
        self, session: KnowledgeIntakeSession, answer_text: str
    ) -> Tuple[bool, str, Optional[ActiveTurn]]:
        """Ghi nhận câu trả lời của chuyên gia và sinh câu hỏi tiếp theo.

        Nếu câu trả lời chung chung hoặc thiếu thông tin, tự động chèn câu hỏi đào sâu.
        Trả về: (đã_hết_câu_hỏi, thông_báo, lượt_hỏi_mới).
        """
        if session.is_completed:
            return True, "Phiên thu tri thức đã kết thúc.", None

        clean_ans = str(answer_text or "").strip()
        if not clean_ans:
            return False, "Vui lòng nhập nội dung câu trả lời.", None

        now_iso = datetime.now().isoformat()
        current_turn = session.turns[-1]
        current_turn.answer_text = clean_ans
        current_turn.speaker = "expert"

        # Cập nhật turn trong staging store với nội dung nguyên văn
        self.staging.save_turn(
            IntakeTurnRecord(
                turn_id=current_turn.turn_id,
                session_id=session.session_id,
                store_id=session.store_id,
                turn_index=current_turn.turn_index,
                speaker="expert",
                question_text=current_turn.question_text,
                answer_text=clean_ans,
                probe_type=current_turn.probe_type,
                timestamp=now_iso,
            )
        )

        # Phân tích đào sâu dựa trên chế độ (không chèn trùng câu hỏi đã hỏi/đang chờ)
        already_seen = {t.probe_type for t in session.turns} | {
            p[0] for p in session.pending_probes
        }
        if session.mode == MODE_PHONG_VAN:
            # Phát hiện các khía cạnh cần đào sâu chưa từng hỏi
            missing = [
                m
                for m in detect_missing_aspects_interview(clean_ans)
                if m not in already_seen
            ]
            for m in reversed(missing[:2]):  # Chèn tối đa 2 câu đào sâu cấp thiết nhất
                probe_q = build_deep_probe_question(m, session.topic)
                session.pending_probes.insert(0, (m, probe_q))
                already_seen.add(m)
        elif session.mode == MODE_DAY:
            # Ở chế độ dạy: nếu chuyên gia giảng dài, chủ động hỏi làm rõ trường hợp ngoại lệ
            if len(clean_ans) > 100 and CLARIFY_NGOAI_LE not in already_seen:
                clarify_q = build_teaching_clarification(CLARIFY_NGOAI_LE, session.topic)
                session.pending_probes.insert(1, (CLARIFY_NGOAI_LE, clarify_q))
                already_seen.add(CLARIFY_NGOAI_LE)

        # Kiểm tra còn câu hỏi tiếp theo không
        if not session.pending_probes:
            # Đã hết câu hỏi -> Tự động tổng hợp nháp
            drafts = self.end_and_synthesize(session)
            return True, "Đã hoàn thành các câu hỏi và tổng hợp %d mục nháp." % len(drafts), None

        # Rút câu hỏi tiếp theo từ hàng đợi
        next_probe, next_q = session.pending_probes.pop(0)
        next_turn_idx = len(session.turns)
        next_turn_id = "turn-%s-%d" % (session.session_id, next_turn_idx)

        next_turn = ActiveTurn(
            turn_id=next_turn_id,
            turn_index=next_turn_idx,
            speaker="ai",
            question_text=next_q,
            probe_type=next_probe,
            timestamp=now_iso,
        )
        session.turns.append(next_turn)

        self.staging.save_turn(
            IntakeTurnRecord(
                turn_id=next_turn.turn_id,
                session_id=session.session_id,
                store_id=session.store_id,
                turn_index=next_turn.turn_index,
                speaker="ai",
                question_text=next_turn.question_text,
                answer_text="",
                probe_type=next_turn.probe_type,
                timestamp=now_iso,
            )
        )

        return False, "Đã ghi nhận câu trả lời.", next_turn

    def end_and_synthesize(
        self, session: KnowledgeIntakeSession
    ) -> List[IntakeDraftItemRecord]:
        """Dừng phiên thu tri thức và tổng hợp các mục nháp theo Hồ sơ đích."""
        session.status = "ended"
        now_iso = datetime.now().isoformat()

        # Lưu trạng thái kết thúc vào staging
        self.staging.save_session(
            IntakeSessionRecord(
                session_id=session.session_id,
                store_id=session.store_id,
                mode=session.mode,
                expert_name=session.expert_name,
                topic=session.topic,
                status="ended",
                created_at=session.created_at,
                updated_at=now_iso,
            )
        )

        # Tổng hợp các mục nháp
        drafts = synthesize_draft_items(session)
        session.draft_items = drafts

        # Lưu các mục nháp vào staging store
        self.staging.save_draft_items(drafts)
        return drafts

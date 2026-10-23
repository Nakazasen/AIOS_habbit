"""Chat-first intent router (UX-CHAT-CORE).

Replaces the 3-branch "Navigation" radio: every chat sentence is classified
here and the app routes it to the existing handler. The user NEVER has to
pick a branch.

Algorithm: Vietnamese keyword matching (diacritics-insensitive), fully
deterministic, no LLM call -> testable and works offline.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, Optional, Tuple

# Recognized intents. "hoi_tai_lieu" is the default fallback.
# Skill creation and management intents (DESKTOP-HOME-USER-SKILL-CREATE)
KYNANG_DANH_SACH = "kynang_danh_sach"    # list user personal skills
KYNANG_TAO = "kynang_tao"                # create skill via short interview
KYNANG_XEM = "kynang_xem"                # view skill SKILL.md and files
KYNANG_LUU_TRU = "kynang_luu_tru"        # archive skill to .archive/
PHONG_VAN_CHUYEN_GIA = "phong_van_chuyen_gia"  # expert interview session
THONG_KE_HE_THONG = "thong_ke_he_thong"        # system operational stats & KPI
TRANG_THAI_HE_THONG = "trang_thai_he_thong"    # health status & service connectivity
BAO_CAO_DIEU_TRA = "bao_cao_dieu_tra"  # investigation report export (.docx)
DUYET_BAN_NHAP = "duyet_ban_nhap"      # expert review draft queue
NAP_TAI_LIEU = "nap_tai_lieu"          # knowledge / doc intake into store
DU_DOAN_RUI_RO = "du_doan_rui_ro"      # shadow-risk / recurrence prediction
BAN_DO_TRI_THUC = "ban_do_tri_thuc"    # knowledge graph & visual maps
CANH_BAO_NGUONG = "canh_bao_nguong"      # threshold alert request
HUONG_DAN = "huong_dan"                  # user guide manual request (DESKTOP-HOME-HUONGDAN-COMMAND)
BAO_CAO_XU_HUONG = "bao_cao_xu_huong"    # periodic trend report (Step 4)
XU_HUONG_LOG_TINH = "xu_huong_log_tinh"  # static log SMA trend analysis request
XEM_PHAN_HOI = "xem_phan_hoi"            # feedback review summary request (DESKTOP-FEEDBACK-REVIEW-CHATCMD-HOME)
VE_BIEU_DO = "ve_bieu_do"                # chart request (runs the JIG chart branch)
XEM_TIEN_DO_VU = "xem_tien_do_vu"        # view progress of active case
HUONG_DIEU_TRA = "huong_dieu_tra"      # step 3 4M + Why-Why investigation tree plan
LAP_CAY_4M_VU = "lap_cay_4m_vu"          # build 4M + Why-Why tree for active case
DONG_VU = "dong_vu"                      # close investigation case with mandatory cause & remedy gate (Step 2)
TAO_VU_DIEU_TRA = "tao_vu_dieu_tra"      # create an investigation case via chat
TAO_SO = "tao_so"                        # create a notebook
MO_SO = "mo_so"                          # open a notebook
HO_SO_DIEU_TRA = "ho_so_dieu_tra"        # open the investigation case workspace
CONG_CU_NANG_CAO = "cong_cu_nang_cao"    # open the advanced JIG analysis tools
DANH_GIA_NHAN = "danh_gia_nhan"          # inline rating for auto-classified labels (Step 5)
DANH_GIA_DIEU_TRA = "danh_gia_dieu_tra"  # inline rating for investigation tree (Step 3)
HOI_DAP_CHUNG = "hoi_dap_chung"          # small talk / greeting
HOI_TAI_LIEU = "hoi_tai_lieu"            # document Q&A (RAG) fallback
DU_LIEU_DAN = "du_lieu_dan"              # pasted CSV/log block in the message

TAT_CA_Y_DINH = (
    PHONG_VAN_CHUYEN_GIA,
    THONG_KE_HE_THONG,
    TRANG_THAI_HE_THONG,
    BAO_CAO_DIEU_TRA,
    DUYET_BAN_NHAP,
    NAP_TAI_LIEU,
    DU_DOAN_RUI_RO,
    BAN_DO_TRI_THUC,

    KYNANG_DANH_SACH,
    KYNANG_TAO,
    KYNANG_XEM,
    KYNANG_LUU_TRU,
    DANH_GIA_DIEU_TRA,
    DANH_GIA_NHAN,
    CANH_BAO_NGUONG,
    HUONG_DAN,
    BAO_CAO_XU_HUONG,
    XU_HUONG_LOG_TINH,
    XEM_PHAN_HOI,
    VE_BIEU_DO,
    XEM_TIEN_DO_VU,
    HUONG_DIEU_TRA,
    LAP_CAY_4M_VU,
    DONG_VU,
    TAO_VU_DIEU_TRA,
    TAO_SO,
    MO_SO,
    HO_SO_DIEU_TRA,
    CONG_CU_NANG_CAO,
    HOI_DAP_CHUNG,
    HOI_TAI_LIEU,
    DU_LIEU_DAN,
)



def _khong_dau(text: str) -> str:
    """Lowercase + strip Vietnamese diacritics for keyword matching."""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip()


def _la_lenh_xem_phan_hoi(clean: str, norm: str) -> bool:
    """Kiểm tra câu chat có phải là lệnh xem phản hồi hay không."""
    c_low = clean.strip().lower()
    if c_low.startswith(("/分類確認", "/分类确认", "/調査確認", "/调查确认", "/フィードバック", "/系统反馈")):
        return True
    if any(k in clean for k in ("分類フィードバック確認", "查看分类反馈", "調査フィードバック確認", "查看调查反馈", "回答フィードバック確認", "查看回答反馈")):
        return True
    if norm.startswith(("/xemphanhoi", "/phanhoi", "/phanloai", "/phanloai-phanhoi", "/phanloai-duyet", "/dieutra-phanhoi", "/dieutra-duyet", "/dieutra", "lenh: xem phan hoi")):
        return True
    if any(c in norm for c in ("xem phan hoi dieu tra", "thong ke cay dieu tra", "thong ke dieu tra", "bao cao phan hoi dieu tra", "phan hoi cay dieu tra", "danh gia cay dieu tra", "xem phan hoi bieu do", "thong ke bieu do", "phan hoi bieu do", "danh gia bieu do")):
        return True
    # Chứa mã lỗi máy (VD: C7620, JAM4709, F000) -> câu hỏi tra cứu, không phải lệnh
    if re.search(r"\b(?:[cfj]\s*-?\d{3,4}|jam\s*-?\d{3,4})\b", norm, re.IGNORECASE):
        return False
    # Từ ngữ máy móc, kỹ thuật, nghiệp vụ RAG
    tu_ngu_rag = (
        "sensor", "cam bien", "nhiet do", "ap suat", "ket giay", "muc", "may in",
        "khach hang", "ban hang", "san pham", "line", "chuyen", "tin hieu",
        "bo mach", "motor", "dong co", "lsu", "jig", "mom", "mes", "opcenter", "dieu tra"
    )
    if any(t in norm for t in tu_ngu_rag):
        return False
    # Từ nghi vấn, hướng dẫn, quy trình tài liệu
    tu_hoi = (
        "la gi", "nhu the nao", "the nao", "tai sao", "o dau", "lam sao", "sao",
        "khong?", "ra sao", "cach", "quy trinh", "huong dan", "tai lieu"
    )
    if any(t in norm for t in tu_hoi):
        return False
    # Giới từ liên kết đối tượng
    if any(g in norm for g in ("phan hoi cua", "phan hoi ve", "phan hoi tu", "phan hoi cho")):
        return False
    # Độ dài câu: lệnh xem phản hồi ngắn gọn
    if len(norm) >= 60:
        return False
    cum_lenh = (
        "xem phan hoi", "xem lai phan hoi", "thong ke phan hoi", "bao cao phan hoi",
        "tom tat phan hoi", "tong hop phan hoi", "xem danh gia phan hoi",
        "xem cac phan hoi", "xem phan hoi gan day", "kiem tra phan hoi",
        "xem phan hoi phan loai", "thong ke phan loai", "bao cao phan loai",
        "danh gia phan loai", "phan hoi phan loai",
        "xem phan hoi dieu tra", "thong ke cay dieu tra", "bao cao phan hoi dieu tra",
        "danh gia cay dieu tra", "thong ke dieu tra",
    )
    return any(c in norm for c in cum_lenh)


# Priority order: specific intents first, generic ones last.
_QUY_TAC: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        PHONG_VAN_CHUYEN_GIA,
        (
            "/phongvan", "/phong-van",
            "/インタビュー", "/专家访谈", "/采访",
            "phong van chuyen gia", "phỏng vấn chuyên gia",
            "chay phong van chuyen gia", "chạy phỏng vấn chuyên gia",
            "bat dau phong van chuyen gia", "bắt đầu phỏng vấn chuyên gia",
            "bat dau phong van", "bắt đầu phỏng vấn",
            "専門家インタビュー", "专家访谈",
        ),
    ),
    (
        THONG_KE_HE_THONG,
        (
            "/thongke", "/thong-ke",
            "/統計", "/统计", "/kpi",
            "thong ke van hanh", "thống kê vận hành",
            "thong ke he thong", "thống kê hệ thống",
            "thong ke tinh hinh van hanh", "thống kê tình hình vận hành",
            "thong ke so lieu van hanh", "thống kê số liệu vận hành",
            "bao cao thong ke", "báo cáo thống kê",
            "運用統計", "运营统计", "系统统计",
        ),
    ),
    (
        TRANG_THAI_HE_THONG,
        (
            "/trangthai", "/trang-thai",
            "/ステータス", "/状态", "/系统状态",
            "kiem tra trang thai he thong", "kiểm tra trạng thái hệ thống",
            "trang thai he thong", "trạng thái hệ thống",
            "suc khoe dich vu", "sức khỏe dịch vụ",
            "trang thai ket noi", "trạng thái kết nối",
            "kiem tra suc khoe he thong", "kiểm tra sức khỏe hệ thống",
            "システム状態確認", "检查系统状态", "系统状态",
        ),
    ),
    (
        BAO_CAO_DIEU_TRA,
        (
            "/baocaodieutra", "/bao-cao-dieu-tra", "/baocao-dieutra",
            "/調査報告書", "/调查报告",
            "lap bao cao dieu tra", "lập báo cáo điều tra",
            "tao bao cao dieu tra", "tạo báo cáo điều tra",
            "xuat bao cao dieu tra", "xuất báo cáo điều tra",
            "viet bao cao dieu tra", "viết báo cáo điều tra",
            "lap bao cao cho ca", "lập báo cáo cho ca",
            "bao cao dieu tra cho ca", "báo cáo điều tra cho ca",
            "調査報告書作成", "生成调查报告",
        ),
    ),
    (
        DUYET_BAN_NHAP,
        (
            "/duyet", "/duyet-ban-nhap",
            "/承認", "/下書き承認", "/审批", "/草稿审核",
            "liet ke ban thao chua duyet", "liệt kê bản thảo chưa duyệt",
            "ban thao chua duyet", "bản thảo chưa duyệt",
            "danh sach ban thao chua duyet", "danh sách bản thảo chưa duyệt",
            "duyet ban thao", "duyệt bản thảo",
            "duyet ban nhap", "duyệt bản nháp",
            "未承認下書き一覧", "列出未审批草稿",
        ),
    ),
    (
        NAP_TAI_LIEU,
        (
            "/naptailieu", "/nap-tai-lieu", "/naptri-thuc",
            "/資料取込", "/知識取込", "/导入资料", "/知识录入",
            "thu tri thuc", "thu tri thức",
            "phong van tri thuc", "phỏng vấn tri thức",
            "day kien thuc", "dạy kiến thức",
            "mo phien thu tri thuc", "mở phiên thu tri thức",
            "bat dau thu tri thuc", "bắt đầu thu tri thức",
            "xem muc cho nap", "xem mục chờ nạp",
            "muc cho nap", "mục chờ nạp",
            "danh sach cho nap", "danh sách chờ nạp",
            "thong ke thu tri thuc", "thống kê thu tri thức",
            "kiem tra muc cho nap", "kiểm tra mục chờ nạp",
            "phien day kien thuc", "phiên dạy kiến thức",
            "phien phong van tri thuc", "phiên phỏng vấn tri thức",
            "専門家知識取込", "录入专家知识",
        ),
    ),
    (
        DU_DOAN_RUI_RO,
        (
            "/dudoan", "/du-doan",
            "/再発予測", "/リスク予測", "/预测", "/复发预测",
            "du doan rui ro", "dự đoán rủi ro",
            "du doan tai phat", "dự đoán tái phát",
            "nguy co tai phat", "nguy cơ tái phát",
            "du doan", "dự đoán",
            "リスク予測", "风险预测",
        ),
    ),
    (
        BAN_DO_TRI_THUC,
        (
            "/bando", "/ban-do",
            "/ナレッジマップ", "/知識マップ", "/知识地图", "/关系图",
            "ban do tri thuc", "bản đồ tri thức",
            "so do tri thuc", "sơ đồ tri thức",
            "ban do ho so", "bản đồ hồ sơ",
            "do thi bang chung", "đồ thị bằng chứng",
            "so do bang chung", "sơ đồ bằng chứng",
            "ナレッジマップ表示", "显示知识地图",
        ),
    ),

    (
        HUONG_DAN,
        (
            "/huongdan", "/huong-dan",
            "/使い方", "/使用指南", "使い方", "使用指南",
            "/つかいかた", "つかいかた",
            "huong dan su dung aios", "cam nang huong dan",
            "cam nang aios", "huong dan aios", "danh muc huong dan",
        ),
    ),
    (
        XEM_PHAN_HOI,
        (
            "xem phan hoi", "xem lai phan hoi",
            "thong ke phan hoi", "bao cao phan hoi",
            "tom tat phan hoi", "tong hop phan hoi",
            "xem danh gia phan hoi", "xem cac phan hoi",
            "xem phan hoi gan day", "kiem tra phan hoi",
            "xem phan hoi phan loai", "thong ke phan loai",
            "bao cao phan loai", "danh gia phan loai",
            "xem phan hoi dieu tra", "thong ke cay dieu tra",
            "bao cao phan hoi dieu tra", "phan hoi cay dieu tra",
            "danh gia cay dieu tra", "thong ke dieu tra",
            "/xemphanhoi", "/phanhoi",
            "/phanloai", "/phanloai-phanhoi", "/phanloai-duyet",
            "/分類確認", "/分类确认",
            "/dieutra-phanhoi", "/dieutra-duyet", "/dieutra",
            "/調査確認", "/调查确认",
            "/フィードバック", "/系统反馈",
            "分類フィードバック確認", "查看分类反馈",
            "調査フィードバック確認", "查看调查反馈",
            "回答フィードバック確認", "查看回答反馈",
        ),
    ),
    (
        DANH_GIA_DIEU_TRA,
        (
            "cay dieu tra dung huong",
            "dieu tra dung huong",
            "cay dieu tra thieu nhanh",
            "dieu tra thieu nhanh",
            "cay dieu tra khong huu ich",
            "dieu tra khong huu ich",
            "phan hoi dieu tra:",
            "gop y dieu tra:",
            "/danhgiadieutra",
            "/調査評価", "/调查评价",
            "調査ツリー方向性良好", "调查树方向正确",
        ),
    ),
    (
        DANH_GIA_NHAN,
        (
            "dung nhan", "sai nhan", "mot phan nhan",
            "danh gia dung nhan", "danh gia sai nhan",
            "sua nhan thanh", "sua nhan:", "sua nhan",
            "/danhgianhan",
            "/ラベル評価", "/标签评价",
            "ラベル正確性評価", "评价正确标签",
        ),
    ),
    (
        BAO_CAO_XU_HUONG,
        (
            "bao cao xu huong dinh ky",
            "báo cáo xu hướng định kỳ",
            "sinh bao cao xu huong dinh ky",
            "sinh báo cáo xu hướng định kỳ",
            "xuat bao cao xu huong dinh ky",
            "xuất báo cáo xu hướng định kỳ",
            "bao cao xu huong tuan",
            "báo cáo xu hướng tuần",
            "bao cao dinh ky tuan",
            "báo cáo định kỳ tuần",
            "sinh bao cao xu huong",
            "sinh báo cáo xu hướng",
            "xuat bao cao xu huong",
            "xuất báo cáo xu hướng",
            "bao cao xu huong",
            "báo cáo xu hướng",
            "bao cao dinh ky",
            "báo cáo định kỳ",
            "/baocaoxuhuong",
            "/baocaodinhky",
            "/定期レポート", "/定期报告",
            "定期トレンドレポート", "定期趋势报告",
        ),
    ),
    (
        XU_HUONG_LOG_TINH,
        (
            "canh bao xu huong", "phan tich xu huong",
            "xu huong sma", "canh bao sma",
            "cong sma", "sma(20)", "sma 20",
            "xu huong log tinh", "canh bao log tinh", "quet log tinh",
            "chieu cong", "chieu xu huong",
            "doan troi", "bat thuong lien tiep",
            "diem bat thuong don le",
        ),
    ),
    (
        CANH_BAO_NGUONG,
        (
            "/canhbao", "/canh-bao", "/アラート", "/警告", "/预警",
            "canh bao nguong", "cảnh báo ngưỡng", "しきい値アラート", "阈值预警",
            "canh bao khi", "dat nguong", "thiet lap nguong",
            "thiet lap canh bao", "canh bao vuot", "nguong canh bao",
            "liet ke canh bao", "xoa canh bao", "tat canh bao",
        ),
    ),
    (
        VE_BIEU_DO,
        (
            "/bieudo", "/bieu-do", "/グラフ", "/チャート", "/图表",
            "グラフ作成", "绘制图表",
            "ve bieu do",
            "chon bieu do",
            "tao bieu do",
            "bieu do log",
            "them duong sma",
            "bat sma",
            "tat sma",
            "bo sma",
            "chi xem line",
            "chi xem ca",
            "chi xem dong ng",
            "chi dong ng",
            "loc ng",
            "loc dong ng",
            "doi sang pareto",
            "bieu do pareto",
            "bieu do xu huong",
            "bieu do spc",
            "kiem soat spc",
            "bieu do cot nhom",
            "bieu do donut",
            "bieu do histogram",
            "bieu do scatter",
            "bieu do phan tan",
            "bieu do box plot",
            "bieu do hop",
            "bieu do heatmap",
            "ban do nhiet",
            "bieu do stacked bar",
            "cot chong theo thoi gian",
            "doi truc x",
            "doi truc y",
            "xem tat ca dong",
            "huy loc",
            "bo loc",
        ),
    ),
    (
        XEM_TIEN_DO_VU,
        (
            "xem tien do vu",
            "tien do vu",
            "tien do ca",
            "xem tien do ca",
            "trang thai vu",
            "xem trang thai vu",
            "xem tien do",
            "tien do vu dieu tra",
        ),
    ),
    (
        HUONG_DIEU_TRA,
        (
            "huong dieu tra",
            "hướng điều tra",
            "cay dieu tra",
            "cây điều tra",
            "ke hoach dieu tra",
            "kế hoạch điều tra",
            "lap ke hoach dieu tra",
            "lập kế hoạch điều tra",
            "lap cay dieu tra",
            "lập cây điều tra",
            "goi y huong dieu tra",
            "gợi ý hướng điều tra",
            "dieu tra buoc dau",
            "điều tra bước đầu",
            "bat dau dieu tra",
            "bắt đầu điều tra",
        ),
    ),
    (
        LAP_CAY_4M_VU,
        (
            "lap cay 4m",
            "cay 4m",
            "cay dieu tra 4m",
            "lap cay dieu tra 4m",
            "phan tich 4m",
            "5 why",
            "why why",
            "lap cay why why",
            "cay why why",
        ),
    ),
    (
        DONG_VU,
        (
            "dong vu dieu tra",
            "dong vu",
            "dong ca loi",
            "dong ca",
            "dong phieu loi",
            "dong phieu",
            "dong ho so dieu tra",
            "dong ho so",
            "chot vu dieu tra",
            "chot vu",
            "chot ca",
            "ket thuc vu",
            "ket thuc ca",
            "/dongvu",
            "/dong-vu",
            "/ケース終了", "/关闭案例",
            "障害ケース終了", "关闭调查案例",
        ),
    ),
    (
        TAO_VU_DIEU_TRA,
        (
            "/taovu", "/tao-vu", "/新規調査", "/新規ケース", "/新建调查", "/创建案例",
            "新規障害調査作成", "创建调查案例",
            "tao vu dieu tra",
            "tao ho so dieu tra",
            "lap vu dieu tra",
            "mo vu dieu tra",
            "tao ca loi",
            "ghi nhan loi",
            "bao loi moi",
            "su co line",
            "loi line",
        ),
    ),
    (
        TAO_SO,
        ("tao so", "tao so tai lieu", "tao so moi", "lap so"),
    ),
    (
        MO_SO,
        ("mo so",),
    ),
    (
        HO_SO_DIEU_TRA,
        (
            "mo ho so", "ho so dieu tra",
            "day aios", "phong van chuyen gia",
        ),
    ),
    (
        CONG_CU_NANG_CAO,
        (
            "cong cu nang cao", "mo lsu", "cong cu jig",
        ),
    ),
    (
        HOI_DAP_CHUNG,
        (
            "xin chao", "chao ban", "chao aios", "hello",
            "cam on", "thank", "ban la ai", "gioi thieu",
        ),
    ),
)



def _nhan_dien_y_dinh_kynang(clean: str, norm: str) -> Optional[Tuple[str, Dict[str, str]]]:
    """Nhận diện các lệnh /kynang và câu tự nhiên tương đương (VI, JA, ZH)."""
    c_strip = clean.strip()
    c_lower = c_strip.lower()

    # 1. Kỹ năng tạo (/kynang tao)
    if c_lower.startswith(("/kynang tao", "/kynang-tao", "/スキル作成", "/创建技能")):
        raw_tail = re.sub(r"^(?:/kynang\s+tao|/kynang-tao|/スキル作成|/创建技能)[:\s]*", "", c_strip, flags=re.IGNORECASE).strip()
        return (KYNANG_TAO, {"raw_input": raw_tail})
    if any(k in norm for k in ("tao ky nang moi", "tao ky nang", "muon tao ky nang", "muon tu tao skill", "tao skill moi")):
        return (KYNANG_TAO, {"raw_input": clean})
    if any(k in clean for k in ("新規スキル作成", "スキル作成", "创建新技能", "创建技能")):
        return (KYNANG_TAO, {"raw_input": clean})

    # 2. Kỹ năng xem (/kynang xem <ten>)
    if c_lower.startswith(("/kynang xem", "/kynang-xem", "/スキル確認", "/查看技能")):
        target = re.sub(r"^(?:/kynang\s+xem|/kynang-xem|/スキル確認|/查看技能)[:\s]*", "", c_strip, flags=re.IGNORECASE).strip()
        return (KYNANG_XEM, {"skill_name": target})
    if "xem chi tiet ky nang" in norm or "chi tiet ky nang" in norm or "スキル詳細確認" in clean or "查看技能详情" in clean:
        target = re.sub(r"^(?:xem\s+chi\s+tiet\s+ky\s+nang|chi\s+tiet\s+ky\s+nang|スキル詳細確認|查看技能详情)[:\s]*", "", norm, flags=re.IGNORECASE).strip()
        return (KYNANG_XEM, {"skill_name": target})

    # 3. Kỹ năng lưu trữ (/kynang luu-tru <ten>)
    if c_lower.startswith(("/kynang luu-tru", "/kynang-luu-tru", "/kynang luutru", "/kynang-luutru", "/スキルアーカイブ", "/归档技能")):
        target = re.sub(r"^(?:/kynang\s+luu-tru|/kynang-luu-tru|/kynang\s+luutru|/kynang-luutru|/スキルアーカイブ|/归档技能)[:\s]*", "", c_strip, flags=re.IGNORECASE).strip()
        return (KYNANG_LUU_TRU, {"skill_name": target})
    if any(k in norm for k in ("luu tru ky nang", "dong bang ky nang", "dong ky nang")) or "スキルをアーカイブ" in clean or "归档此技能" in clean or "归档技能" in clean:
        target = re.sub(r"^(?:luu\s+tru\s+ky\s+nang|dong\s+bang\s+ky\s+nang|スキルをアーカイブ|归档此技能|归档技能)[:\s]*", "", norm, flags=re.IGNORECASE).strip()
        return (KYNANG_LUU_TRU, {"skill_name": target})

    # 4. Kỹ năng danh sách (/kynang)
    if c_lower in ("/kynang", "/ky-nang", "/スキル", "/技能") or c_lower.startswith(("/kynang ", "/ky-nang ")):
        return (KYNANG_DANH_SACH, {})
    if any(k in norm for k in ("xem ky nang cua toi", "ky nang cua toi", "danh sach ky nang", "xem danh sach ky nang", "cac ky nang cua toi")):
        return (KYNANG_DANH_SACH, {})
    if any(k in clean for k in ("私のスキル一覧", "スキル一覧", "查看我的技能", "技能列表")):
        return (KYNANG_DANH_SACH, {})

    return None


def classify_intent(text: str) -> str:
    """Classify one chat sentence. Always returns a valid intent."""
    intents = classify_all_intents(text)
    return intents[0][0] if intents else HOI_TAI_LIEU


def _co_khoi_du_lieu_dan(text: str) -> bool:
    """True when the message carries a pasted CSV/log block.

    Imported lazily so this router stays dependency-free for unit tests.
    """
    try:
        from aios_habit.chat_action_data_paste import extract_pasted_block
    except Exception:
        return False
    try:
        return extract_pasted_block(text or "") is not None
    except Exception:
        return False


def classify_all_intents(text: str) -> list:
    """Classify ALL intents present in one chat message.

    A single message may carry several intents (e.g. pasted CSV + a chart
    request + a threshold alert). Returns a list of (intent, slots) in
    priority order; the caller is expected to run every one of them.
    The single-intent ``classify_intent`` keeps returning the first entry,
    so existing callers are unaffected.
    """
    clean = text or ""
    norm = _khong_dau(clean)
    if not norm:
        return [(HOI_DAP_CHUNG, {})]
        # Kiểm tra bộ lệnh kỹ năng cá nhân (DESKTOP-HOME-USER-SKILL-CREATE)
    res_kn = _nhan_dien_y_dinh_kynang(clean, norm)
    if res_kn is not None:
        return [res_kn]

    try:
        from aios_habit.huongdan_command import is_huongdan_command, parse_huongdan_args, detect_huongdan_language
        if is_huongdan_command(clean):
            lang = detect_huongdan_language(clean)
            return [(HUONG_DAN, {"muc": parse_huongdan_args(clean, lang=lang), "language": lang})]
    except Exception:
        pass
    ngan = len(norm) < 80
    clean_lower = clean.strip().lower()
    found: list = []
    for y_dinh, cum_tu in _QUY_TAC:
        if y_dinh in (HO_SO_DIEU_TRA, CONG_CU_NANG_CAO) and not ngan:
            continue
        if y_dinh == VE_BIEU_DO and "gui mail" in norm:
            # "bieu do gui mail" belongs to alert-config commands, not charting.
            continue
        if y_dinh == XEM_PHAN_HOI and not _la_lenh_xem_phan_hoi(clean, norm):
            continue
        for cum in cum_tu:
            c_low = cum.lower()
            if (cum in norm) or (c_low in clean_lower) or (_khong_dau(cum) in norm):
                # Avoid "mo so" misfiring on "mo ho so".
                if y_dinh == MO_SO and "mo ho so" in norm:
                    continue
                found.append((y_dinh, extract_slots(clean, y_dinh)))
                break
    # Pasted data is orthogonal to keywords: a pasted CSV/log block is its
    # own intent even when the sentence also asks for an alert or a chart.
    if _co_khoi_du_lieu_dan(clean):
        found.insert(0, (DU_LIEU_DAN, {}))
    if not found:
        found.append((HOI_TAI_LIEU, {}))
    return found


def extract_case_entities(text: str) -> Dict[str, str]:
    """Extract case entities (phenomenon, error_code, line, machine_type) from Vietnamese chat."""
    clean = (text or "").strip()
    if not clean:
        return {
            "phenomenon": "",
            "error_code": "",
            "line": "",
            "machine_type": "",
        }

    # 1. Error code (C, F, J, or JAM + 3-4 digits)
    code_match = re.search(
        r"\b(?:(JAM)\s*-?\s*(\d{3,4})|([CFJcfj])\s*-?\s*(\d{3,4}))\b",
        clean,
    )
    error_code = ""
    if code_match:
        if code_match.group(1):
            error_code = f"{code_match.group(1).upper()}{code_match.group(2)}"
        elif code_match.group(3):
            error_code = f"{code_match.group(3).upper()}{code_match.group(4)}"

    # 2. Line (Line, Chuyen, Day chuyen + ID)
    line_match = re.search(
        r"(?:ở\s+|tai\s+|tại\s+)?\b(?:line|chuyền|chuyen|dây\s*chuyền|day\s*chuyen)\s*([A-Za-z0-9_-]+)",
        clean,
        re.IGNORECASE,
    )
    line = ""
    if line_match:
        line_val = line_match.group(1).strip()
        line = f"Line {line_val.upper()}"

    # 3. Machine / Model
    machine_type = ""
    m_match = re.search(
        r"\b(máy\s+in|may\s+in|máy\s+photo|may\s+photo|máy\s+dán|may\s+dan|máy\s+hàn|may\s+han|máy\s+quét|may\s+quet|máy\s+đóng\s+gói|may\s+dong\s+goi|iris[A-Za-z0-9_-]*|polaris[A-Za-z0-9_-]*|kairos[A-Za-z0-9_-]*|virgo[A-Za-z0-9_-]*|bizhub[A-Za-z0-9_-]*)\b",
        clean,
        re.IGNORECASE,
    )
    if m_match:
        machine_type = m_match.group(1).strip()
    else:
        m_exp = re.search(
            r"(?:model|dòng\s*máy|dong\s*may|thiết\s*bị|thiet\s*bi|máy|may)\s*[:\s]\s*([A-Za-z0-9_-]+)",
            clean,
            re.IGNORECASE,
        )
        if m_exp:
            machine_type = m_exp.group(1).strip()

    # 4. Phenomenon: strip intent prefix and line clause
    prefix_re = re.compile(
        r"^(?:(?:tạo|lap|lập|mở|mo)\s+(?:vụ|vu|hồ\s+sơ|ho\s+so|ca|yêu\s+cầu|yeu\s+cau)?(?:\s+(?:điều\s+tra|dieu\s+tra))?(?:\s+(?:lỗi|loi))?(?:\s+(?:mới|moi))?|(?:ghi\s+nhận|báo|bao)\s+lỗi(?:\s+mới)?|sự\s+cố|su\s+co)\s*[:,-]?\s*",
        re.IGNORECASE,
    )
    remainder = prefix_re.sub("", clean).strip()
    if line_match:
        remainder = re.sub(
            r"(?:ở\s+|tai\s+|tại\s+)?\b(?:line|chuyền|chuyen|dây\s*chuyền|day\s*chuyen)\s*[A-Za-z0-9_-]+",
            "",
            remainder,
            flags=re.IGNORECASE,
        ).strip()
    phenomenon = re.sub(r"\s+", " ", remainder).strip(" :,-.")
    if not phenomenon:
        phenomenon = clean

    return {
        "phenomenon": phenomenon,
        "error_code": error_code,
        "line": line,
        "machine_type": machine_type,
    }


def extract_case_id_from_text(text: str) -> str:
    """Extract CASE-XXXX id if explicitly referenced in text."""
    clean = str(text or "").strip()
    m = re.search(r"\b(CASE-[A-Za-z0-9_-]+)\b", clean, re.IGNORECASE)
    return m.group(1).upper() if m else ""


def extract_slots(text: str, intent: str) -> Dict[str, str]:
    if intent == KYNANG_XEM:
        target = re.sub(r"^(?:/kynang\s+xem|/kynang-xem|/スキル確認|/查看技能|xem chi tiet ky nang|xem chi tiết kỹ năng|xem ky nang|xem kỹ năng)[:\s]*", "", text, flags=re.IGNORECASE).strip()
        return {"skill_name": target}
    if intent == KYNANG_LUU_TRU:
        target = re.sub(r"^(?:/kynang\s+luu-tru|/kynang-luu-tru|/kynang-luutru|/スキルアーカイブ|/归档技能|luu tru ky nang|lưu trữ kỹ năng|dong bang ky nang)[:\s]*", "", text, flags=re.IGNORECASE).strip()
        return {"skill_name": target}
    if intent == KYNANG_TAO:
        target = re.sub(r"^(?:/kynang\s+tao|/kynang-tao|/スキル作成|/创建技能|tao ky nang moi|tạo kỹ năng mới|tao ky nang|tạo kỹ năng)[:\s]*", "", text, flags=re.IGNORECASE).strip()
        return {"raw_input": target}
    if intent == KYNANG_DANH_SACH:
        return {}

    """Extract simple slots for a few intents (notebook title, case entities...)."""
    slots: Dict[str, str] = {}
    clean = (text or "").strip()
    if intent == HUONG_DAN:
        from aios_habit.huongdan_command import parse_huongdan_args, detect_huongdan_language
        lang = detect_huongdan_language(clean)
        return {"muc": parse_huongdan_args(clean, lang=lang), "language": lang}
    elif intent == TAO_VU_DIEU_TRA:
        return extract_case_entities(clean)
    elif intent in (XEM_TIEN_DO_VU, LAP_CAY_4M_VU):
        cid = extract_case_id_from_text(clean)
        return {"case_id": cid} if cid else {}
    elif intent == DONG_VU:
        slots_dv: Dict[str, str] = {}
        cid = extract_case_id_from_text(clean)
        if cid:
            slots_dv["case_id"] = cid

        m_cause = re.search(
            r"(?:nguyên\s*nhân(?:\s*thật)?|nguyen\s*nhan(?:\s*that)?|lý\s*do(?:\s*thật)?|ly\s*do(?:\s*that)?|root\s*cause|cause)\s*[:=-]\s*(.*?)(?=(?:,\s*|\s*;\s*|\n)(?:đối\s*sách|doi\s*sach|biện\s*pháp|bien\s*phap|remedy|countermeasure)|$)",
            clean,
            re.IGNORECASE,
        )
        if m_cause:
            slots_dv["actual_cause"] = m_cause.group(1).strip()

        m_remedy = re.search(
            r"(?:đối\s*sách(?:\s*thật)?|doi\s*sach(?:\s*that)?|biện\s*pháp(?:\s*thật)?|bien\s*phap(?:\s*that)?|phòng\s*ngừa|phong\s*ngua|hướng\s*xử\s*lý|countermeasure|remedy)\s*[:=-]\s*(.*?)(?=(?:,\s*|\s*;\s*|\n)(?:nguyên\s*nhân|nguyen\s*nhan|root\s*cause)|$)",
            clean,
            re.IGNORECASE,
        )
        if m_remedy:
            slots_dv["actual_countermeasure"] = m_remedy.group(1).strip()

        return slots_dv

    elif intent == TAO_SO:
        mau = re.compile(
            r"(?:tạo|tao)\s+sổ(?:\s+tài\s+liệu)?\s+(.+)$",
            re.IGNORECASE,
        )
        m = mau.search(clean)
        if m:
            slots["ten_so"] = m.group(1).strip().strip("\"'")
    elif intent == MO_SO:
        mau = re.compile(r"mở\s+sổ\s+(.+)$", re.IGNORECASE)
        m = mau.search(clean)
        if m:
            slots["ten_so"] = m.group(1).strip().strip("\"'")
    elif intent == DANH_GIA_DIEU_TRA:
        slots_dt: Dict[str, str] = {}
        norm_c = _khong_dau(clean)
        if "thieu" in norm_c or "nhanh" in norm_c:
            slots_dt["rating"] = "thiếu nhánh"
        elif "khong" in norm_c or "kem" in norm_c or "sai" in norm_c:
            slots_dt["rating"] = "không hữu ích"
        else:
            slots_dt["rating"] = "đúng hướng"

        m_note = re.search(r"phan\s*hoi\s*dieu\s*tra\s*:\s*(.+)$", clean, re.IGNORECASE)
        if m_note:
            slots_dt["note"] = m_note.group(1).strip()
        cid = extract_case_id_from_text(clean)
        if cid:
            slots_dt["case_id"] = cid
        return slots_dt
    elif intent == DANH_GIA_NHAN:
        slots_dg: Dict[str, str] = {}
        norm_c = _khong_dau(clean)
        if "dung" in norm_c:
            slots_dg["rating"] = "đúng"
        elif "mot phan" in norm_c:
            slots_dg["rating"] = "một phần"
        elif "sai" in norm_c:
            slots_dg["rating"] = "sai"
        else:
            slots_dg["rating"] = "đúng"

        for grp, vi in (
            ("linh_kien", "linh kien"),
            ("lap_rap", "lap rap"),
            ("thiet_ke", "thiet ke"),
            ("khac", "khac"),
        ):
            if vi in norm_c:
                slots_dg["correction"] = grp
                break
        cid = extract_case_id_from_text(clean)
        if cid:
            slots_dg["case_id"] = cid
        return slots_dg
    elif intent == XEM_PHAN_HOI:
        norm_c = _khong_dau(clean)
        if "phan loai" in norm_c or "phanloai" in norm_c:
            return {"loai_phan_hoi": "phan_loai"}
        if "dieu tra" in norm_c or "cay 4m" in norm_c or "dieutra" in norm_c:
            return {"loai_phan_hoi": "dieu_tra"}
        return {}
    elif intent == XU_HUONG_LOG_TINH:
        slots_trend: Dict[str, str] = {}
        m_csv = re.search(r'"([^"]+\.csv)"|(\S+\.csv)', clean, re.IGNORECASE)
        if m_csv:
            slots_trend["tep_csv"] = m_csv.group(1) or m_csv.group(2)
        norm_c = _khong_dau(clean)
        if "chieu cong" in norm_c or "don le" in norm_c:
            slots_trend["chieu_kiem_tra"] = "chieu_cong"
        elif "chieu xu huong" in norm_c or "lien tiep" in norm_c or "doan troi" in norm_c:
            slots_trend["chieu_kiem_tra"] = "chieu_xu_huong"
        return slots_trend
    return slots


def route(text: str) -> Tuple[str, Dict[str, str]]:
    """Single entry point: (intent, slots)."""
    intent = classify_intent(text)
    return intent, extract_slots(text, intent)


def giai_thich_y_dinh(intent: str) -> str:
    """Short Vietnamese note shown in chat so the user sees what the app understood."""
    return {
        DANH_GIA_DIEU_TRA: "Tôi hiểu bạn muốn đánh giá gợi ý cây điều tra 4M.",
        DANH_GIA_NHAN: "Tôi hiểu bạn muốn đánh giá nhãn phân loại tự động.",
        HUONG_DAN: "Tôi mở cẩm nang hướng dẫn sử dụng AIOS.",
        CANH_BAO_NGUONG: "Tôi hiểu đây là yêu cầu cảnh báo ngưỡng.",
        XU_HUONG_LOG_TINH: "Tôi hiểu bạn muốn phân tích xu hướng SMA(20) trên log tĩnh.",
        XEM_PHAN_HOI: "Tôi hiểu bạn muốn xem lại tóm tắt phản hồi đáp án.",
        VE_BIEU_DO: "Tôi hiểu bạn muốn vẽ biểu đồ.",
        XEM_TIEN_DO_VU: "Tôi hiểu bạn muốn xem tiến độ vụ điều tra.",
        LAP_CAY_4M_VU: "Tôi hiểu bạn muốn lập cây điều tra 4M và chuỗi Why-Why.",
        DONG_VU: "Tôi hiểu bạn muốn đóng vụ điều tra lỗi.",
        TAO_VU_DIEU_TRA: "Tôi hiểu bạn muốn tạo vụ điều tra lỗi mới.",
        TAO_SO: "Tôi hiểu bạn muốn tạo sổ tài liệu mới.",
        MO_SO: "Tôi hiểu bạn muốn mở một sổ tài liệu.",
        HO_SO_DIEU_TRA: "Tôi hiểu bạn muốn mở hồ sơ điều tra.",
        CONG_CU_NANG_CAO: "Tôi hiểu bạn muốn mở công cụ phân tích JIG.",
        DU_LIEU_DAN: "Tôi thấy bạn đã dán dữ liệu, tôi sẽ phân tích ngay.",
        HOI_DAP_CHUNG: "",
        HOI_TAI_LIEU: "",
    }.get(intent, "")


def nhan_y_dinh(intent: str) -> str:
    """Short Vietnamese label for one intent (section header in a merged reply)."""
    return {
        PHONG_VAN_CHUYEN_GIA: "Phỏng vấn chuyên gia",
        THONG_KE_HE_THONG: "Thống kê vận hành",
        TRANG_THAI_HE_THONG: "Trạng thái hệ thống",
        BAO_CAO_DIEU_TRA: "Báo cáo điều tra",
        DUYET_BAN_NHAP: "Duyệt bản nháp",
        NAP_TAI_LIEU: "Thu nạp tri thức",
        DU_DOAN_RUI_RO: "Dự đoán rủi ro",
        BAN_DO_TRI_THUC: "Bản đồ tri thức",
        DANH_GIA_DIEU_TRA: "Đánh giá cây điều tra",
        DANH_GIA_NHAN: "Đánh giá nhãn phân loại",
        HUONG_DAN: "Cẩm nang hướng dẫn",
        CANH_BAO_NGUONG: "Cảnh báo ngưỡng",
        XU_HUONG_LOG_TINH: "Phân tích xu hướng SMA(20)",
        XEM_PHAN_HOI: "Xem lại phản hồi",
        VE_BIEU_DO: "Vẽ biểu đồ",
        XEM_TIEN_DO_VU: "Tiến độ vụ điều tra",
        LAP_CAY_4M_VU: "Cây điều tra 4M & Why-Why",
        DONG_VU: "Đóng vụ điều tra",
        TAO_VU_DIEU_TRA: "Tạo vụ điều tra",
        TAO_SO: "Tạo sổ",

        MO_SO: "Mở sổ",
        HO_SO_DIEU_TRA: "Hồ sơ điều tra",
        CONG_CU_NANG_CAO: "Công cụ JIG",
        DU_LIEU_DAN: "Phân tích dữ liệu vừa dán",
        HOI_DAP_CHUNG: "Trò chuyện",
        HOI_TAI_LIEU: "Hỏi tài liệu",
    }.get(intent, "")

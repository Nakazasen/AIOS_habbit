"""Danh mục lệnh hệ thống dùng chung (Single Source of Truth) - DESKTOP-HOME-SLASH-COMMAND-PALETTE.

Cung cấp danh mục duy nhất cho mọi lệnh slash (/) trong AIOS:
- Bảng gợi ý khi gõ "/" trong ô chat (workspace_chat_app.py) đọc từ đây.
- Mục danh mục lệnh trong cẩm nang (huongdan_command.py & HUONG-DAN-SU-DUNG-AIOS*.md) đọc từ đây.
- Định tuyến ý định (chat_intent_router.py) đồng bộ chặt chẽ với danh mục này.
- Ghi nhận sự kiện bảng gợi ý (mở, chọn lệnh) vào local_cases/palette_events.jsonl và palette_metrics.json.
"""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def _get_project_root() -> Path:
    """Trả về thư mục gốc của repo AIOS_habbit."""
    return Path(__file__).resolve().parent.parent.parent


def _get_local_cases_dir() -> Path:
    """Trả về thư mục local_cases để lưu metrics và logs cục bộ."""
    env_dir = os.environ.get("AIOS_LOCAL_CASES_DIR")
    if env_dir and Path(env_dir).is_dir():
        return Path(env_dir)
    p = _get_project_root() / "local_cases"
    p.mkdir(parents=True, exist_ok=True)
    return p


# BẢNG DANH MỤC LỆNH CHUẨN (NGUỒN SỰ THẬT DUY NHẤT)
# Mỗi bản ghi đại diện cho một lệnh slash hệ thống đang sống trong AIOS.
_SLASH_COMMANDS_CATALOG: Tuple[Dict[str, Any], ...] = (
    {
        "command": "/huongdan",
        "aliases": ["/huong-dan", "/使い方", "/つかいかた", "/使用指南"],
        "category": "Hướng dẫn sử dụng",
        "category_ja": "利用ガイド",
        "category_zh": "使用指南",
        "description": "Mở cẩm nang hướng dẫn sử dụng AIOS (hỗ trợ 3 ngôn ngữ Việt/Nhật/Trung)",
        "description_ja": "AIOS台帳利用マニュアルを開く（日・越・中3言語対応）",
        "description_zh": "打开 AIOS 台账使用指南（支持越/中/日三语）",
        "natural_query": "hướng dẫn sử dụng aios",
        "natural_query_ja": "使い方",
        "natural_query_zh": "使用指南",
        "context_required": "Bất kỳ sổ nào",
        "context_required_ja": "すべてのノート",
        "context_required_zh": "任意台账",
        "intent": "huong_dan",
    },
    {
        "command": "/bieudo",
        "aliases": ["/bieu-do", "/グラフ", "/チャート", "/图表"],
        "category": "Biểu đồ & Xu hướng",
        "category_ja": "チャート・トレンド",
        "category_zh": "图表与趋势",
        "description": "Dựng biểu đồ phân tích trực quan từ dữ liệu log hoặc dây chuyền sản xuất LSU",
        "description_ja": "ログデータまたはLSUラインから可視化分析チャートを作成",
        "description_zh": "根据日志数据或LSU产线生成可视化分析图表",
        "natural_query": "vẽ biểu đồ",
        "natural_query_ja": "グラフ作成",
        "natural_query_zh": "绘制图表",
        "context_required": "Bất kỳ sổ nào hoặc phiên phân tích log",
        "context_required_ja": "すべてのノートまたはログ分析セッション",
        "context_required_zh": "任意台账或日志分析会话",
        "intent": "ve_bieu_do",
    },
    {
        "command": "/baocaodinhky",
        "aliases": ["/baocaoxuhuong", "/定期レポート", "/定期报告"],
        "category": "Báo cáo & Xu hướng",
        "category_ja": "レポート・トレンド",
        "category_zh": "报告与趋势",
        "description": "Xuất báo cáo xu hướng định kỳ tình hình lỗi theo dây chuyền và tuần sản xuất",
        "description_ja": "生産ライン別および週別の障害トレンド定期レポートを出力（ステップ4）",
        "description_zh": "导出按产线和周期的故障趋势定期报告（第4步）",
        "natural_query": "báo cáo xu hướng định kỳ",
        "natural_query_ja": "定期トレンドレポート",
        "natural_query_zh": "定期趋势报告",
        "context_required": "Bất kỳ sổ nào",
        "context_required_ja": "すべてのノート",
        "context_required_zh": "任意台账",
        "intent": "bao_cao_xu_huong",
    },
    {
        "command": "/baocaodieutra",
        "aliases": ["/bao-cao-dieu-tra", "/baocao-dieutra", "/調査報告書", "/调查报告"],
        "category": "Báo cáo & Xu hướng",
        "category_ja": "レポート・トレンド",
        "category_zh": "报告与趋势",
        "description": "Tổng hợp và xuất báo cáo điều tra sự cố chuẩn .docx kèm cây 4M, biểu đồ và đối sách",
        "description_ja": "4Mツリー、傾向チャート、対策を含む標準.docx障害調査報告書を出力",
        "description_zh": "导出包含 4M 树、趋势图及对策的标准 .docx 故障调查报告",
        "natural_query": "lập báo cáo điều tra",
        "natural_query_ja": "調査報告書作成",
        "natural_query_zh": "生成调查报告",
        "context_required": "Sổ Điều tra lỗi (kèm mã ca lỗi)",
        "context_required_ja": "障害調査ノート（障害ケース番号指定）",
        "context_required_zh": "故障调查台账（需指定案例号）",
        "intent": "bao_cao_dieu_tra",
    },
    {
        "command": "/canhbao",
        "aliases": ["/canh-bao", "/アラート", "/警告", "/预警"],
        "category": "Cảnh báo & Giám sát",
        "category_ja": "アラート・監視",
        "category_zh": "预警与监控",
        "description": "Xem trạng thái hoặc thiết lập ngưỡng cảnh báo xu hướng và điểm bất thường JIG-LSU",
        "description_ja": "JIG-LSUのトレンド異常およびしきい値アラートの状態確認・設定",
        "description_zh": "查看状态或设置 JIG-LSU 趋势预警及异常阈值",
        "natural_query": "cảnh báo ngưỡng",
        "natural_query_ja": "しきい値アラート",
        "natural_query_zh": "阈值预警",
        "context_required": "Bất kỳ sổ nào",
        "context_required_ja": "すべてのノート",
        "context_required_zh": "任意台账",
        "intent": "canh_bao_nguong",
    },
    {
        "command": "/taovu",
        "aliases": ["/tao-vu", "/新規調査", "/新規ケース", "/新建调查", "/创建案例"],
        "category": "Điều tra sự cố",
        "category_ja": "障害調査業務",
        "category_zh": "故障调查业务",
        "description": "Tạo vụ điều tra sự cố mới, trích xuất thông tin lỗi và đối soát lịch sử tương tự",
        "description_ja": "新規障害調査ケースを作成し、障害情報を抽出して類似履歴と照合",
        "description_zh": "创建新的故障调查案例，提取故障要素并比对相似历史",
        "natural_query": "tạo vụ điều tra",
        "natural_query_ja": "新規障害調査作成",
        "natural_query_zh": "创建调查案例",
        "context_required": "Sổ Điều tra lỗi hoặc bất kỳ sổ nào",
        "context_required_ja": "障害調査ノートまたは任意のノート",
        "context_required_zh": "故障调查台账或任意台账",
        "intent": "tao_vu_dieu_tra",
    },
    {
        "command": "/dieutra-phanhoi",
        "aliases": ["/dieutra-duyet", "/dieutra", "/調査確認", "/调查确认"],
        "category": "Điều tra sự cố",
        "category_ja": "障害調査業務",
        "category_zh": "故障调查业务",
        "description": "Xem tổng hợp đánh giá và góp ý cây điều tra sự cố 4M Bước 3",
        "description_ja": "ステップ3の4M障害調査ツリーに対する評価・フィードバックサマリーを表示",
        "description_zh": "查看第3步 4M 故障调查分析树的评价与反馈统计汇总",
        "natural_query": "xem phản hồi điều tra",
        "natural_query_ja": "調査フィードバック確認",
        "natural_query_zh": "查看调查反馈",
        "context_required": "Bất kỳ sổ nào (đọc từ local_cases)",
        "context_required_ja": "すべてのノート（local_casesから読込）",
        "context_required_zh": "任意台账（从 local_cases 读取）",
        "intent": "xem_phan_hoi",
    },
    {
        "command": "/danhgiadieutra",
        "aliases": ["/調査評価", "/调查评价"],
        "category": "Điều tra sự cố",
        "category_ja": "障害調査業務",
        "category_zh": "故障调查业务",
        "description": "Đánh giá nhanh gợi ý cây điều tra 4M (đúng hướng, thiếu nhánh, không hữu ích)",
        "description_ja": "4M調査ツリーの提案を迅速に評価（方向性良好、枝不足、有用でない）",
        "description_zh": "快速评价 4M 调查树建议（方向正确、缺少分支、不实用）",
        "natural_query": "cây điều tra đúng hướng",
        "natural_query_ja": "調査ツリー方向性良好",
        "natural_query_zh": "调查树方向正确",
        "context_required": "Sổ Điều tra lỗi (ngữ cảnh ca điều tra đang mở)",
        "context_required_ja": "障害調査ノート（進行中の調査ケース文脈）",
        "context_required_zh": "故障调查台账（正在进行的调查案例上下文）",
        "intent": "danh_gia_dieu_tra",
    },
    {
        "command": "/dongvu",
        "aliases": ["/dong-vu", "/ケース終了", "/关闭案例"],
        "category": "Đóng vụ điều tra",
        "category_ja": "ケース終了",
        "category_zh": "关闭案例",
        "description": "Đóng vụ điều tra sự cố kèm bắt buộc ghi nhận nguyên nhân thật và biện pháp khắc phục",
        "description_ja": "根本原因と対策の必須記録ゲートを経て障害調査ケースをクローズ（ステップ2）",
        "description_zh": "关闭故障调查案例，执行根本原因与纠正措施的强制录入门禁（第2步）",
        "natural_query": "đóng vụ điều tra",
        "natural_query_ja": "障害ケース終了",
        "natural_query_zh": "关闭调查案例",
        "context_required": "Sổ Điều tra lỗi (yêu cầu mã vụ, nguyên nhân và đối sách)",
        "context_required_ja": "障害調査ノート（ケースID、原因、対策が必要）",
        "context_required_zh": "故障调查台账（需提供案例号、原因及对策）",
        "intent": "dong_vu",
    },
    {
        "command": "/dudoan",
        "aliases": ["/du-doan", "/再発予測", "/リスク予測", "/预测", "/复发预测"],
        "category": "Dự đoán & Phân tích",
        "category_ja": "予測・分析",
        "category_zh": "预测与分析",
        "description": "Chạy mô hình dự đoán rủi ro bóng (shadow risk) và nguy cơ tái phát lỗi trên dữ liệu LSU Iris",
        "description_ja": "LSU Irisデータに基づくシャドウリスクおよび障害再発危険度の予測",
        "description_zh": "基于 LSU Iris 数据运行影子风险及故障复发概率预测",
        "natural_query": "dự đoán rủi ro",
        "natural_query_ja": "リスク予測",
        "natural_query_zh": "风险预测",
        "context_required": "Sổ Điều tra lỗi hoặc kho LSU",
        "context_required_ja": "障害調査ノートまたはLSUデータ",
        "context_required_zh": "故障调查台账或LSU数据",
        "intent": "du_doan_rui_ro",
    },
    {
        "command": "/bando",
        "aliases": ["/ban-do", "/ナレッジマップ", "/知識マップ", "/知识地图", "/关系图"],
        "category": "Bản đồ & Trực quan",
        "category_ja": "マップ・可視化",
        "category_zh": "地图与可视化",
        "description": "Hiển thị bản đồ cấu trúc tri thức, mối liên kết hồ sơ và mạng lưới thực thể dạng đồ thị",
        "description_ja": "知識構造マップ、ケース関連図、エンティティ関係ネットワークを表示",
        "description_zh": "展示知识结构地图、案例关联图及实体关系网络",
        "natural_query": "bản đồ tri thức",
        "natural_query_ja": "ナレッジマップ表示",
        "natural_query_zh": "显示知识地图",
        "context_required": "Bất kỳ sổ nào",
        "context_required_ja": "すべてのノート",
        "context_required_zh": "任意台账",
        "intent": "ban_do_tri_thuc",
    },
    {
        "command": "/naptailieu",
        "aliases": ["/nap-tai-lieu", "/naptri-thuc", "/資料取込", "/知識取込", "/导入资料", "/知识录入"],
        "category": "Tri thức & Tài liệu",
        "category_ja": "知識・ドキュメント",
        "category_zh": "知识与文档",
        "description": "Mở phiên thu nạp tri thức chuyên gia hoặc kiểm tra các mục tri thức chờ nạp vào kho",
        "description_ja": "専門家知識の取込セッションを開始、または格納待ち項目を確認",
        "description_zh": "开启专家知识录入会话，或查看待入库知识清单",
        "natural_query": "thu tri thức",
        "natural_query_ja": "専門家知識取込",
        "natural_query_zh": "录入专家知识",
        "context_required": "Bất kỳ sổ nào",
        "context_required_ja": "すべてのノート",
        "context_required_zh": "任意台账",
        "intent": "nap_tai_lieu",
    },
    {
        "command": "/duyet",
        "aliases": ["/duyet-ban-nhap", "/承認", "/下書き承認", "/审批", "/草稿审核"],
        "category": "Duyệt tri thức",
        "category_ja": "知識承認",
        "category_zh": "知识审批",
        "description": "Xem danh sách hàng đợi các bản thảo tri thức chưa duyệt cần chuyên gia thẩm định",
        "description_ja": "専門家によるレビュー待ちの未承認知識下書きキューを表示",
        "description_zh": "查看待专家审核的未审批知识草稿队列",
        "natural_query": "liệt kê bản thảo chưa duyệt",
        "natural_query_ja": "未承認下書き一覧",
        "natural_query_zh": "列出未审批草稿",
        "context_required": "Bất kỳ sổ nào",
        "context_required_ja": "すべてのノート",
        "context_required_zh": "任意台账",
        "intent": "duyet_ban_nhap",
    },
    {
        "command": "/phanloai",
        "aliases": ["/phanloai-phanhoi", "/phanloai-duyet", "/分類確認", "/分类确认"],
        "category": "Phân loại Bước 5",
        "category_ja": "ステップ5自動分類",
        "category_zh": "第5步自动分类",
        "description": "Xem tổng hợp thống kê và đánh giá nhãn phân loại tự động sự cố Bước 5",
        "description_ja": "ステップ5の障害自動分類ラベルの統計および評価サマリーを表示",
        "description_zh": "查看第5步故障自动分类标签的统计数据与评价汇总",
        "natural_query": "xem phản hồi phân loại",
        "natural_query_ja": "分類フィードバック確認",
        "natural_query_zh": "查看分类反馈",
        "context_required": "Bất kỳ sổ nào (đọc từ local_cases)",
        "context_required_ja": "すべてのノート（local_casesから読込）",
        "context_required_zh": "任意台账（从 local_cases 读取）",
        "intent": "xem_phan_hoi",
    },
    {
        "command": "/danhgianhan",
        "aliases": ["/ラベル評価", "/标签评价"],
        "category": "Phân loại Bước 5",
        "category_ja": "ステップ5自動分類",
        "category_zh": "第5步自动分类",
        "description": "Đánh giá độ chính xác của nhãn phân loại tự động Bước 5 (đúng nhãn, sai, một phần)",
        "description_ja": "ステップ5の自動分類ラベルの正確性を評価（正確、誤り、一部）",
        "description_zh": "评价第5步自动分类标签的准确性（正确、错误、部分符合）",
        "natural_query": "đánh giá đúng nhãn",
        "natural_query_ja": "ラベル正確性評価",
        "natural_query_zh": "评价正确标签",
        "context_required": "Sổ Điều tra lỗi (ngữ cảnh phân loại sự cố)",
        "context_required_ja": "障害調査ノート（分類中のケース文脈）",
        "context_required_zh": "故障调查台账（分类中的案例上下文）",
        "intent": "danh_gia_nhan",
    },
    {
        "command": "/phanhoi",
        "aliases": ["/xemphanhoi", "/フィードバック", "/系统反馈"],
        "category": "Phản hồi hệ thống",
        "category_ja": "システム評価",
        "category_zh": "系统反馈",
        "description": "Xem tổng hợp thống kê tỷ lệ hài lòng (đạt/chê) và lý do phản hồi đáp án AI",
        "description_ja": "ローカルAI回答に対する満足度（Good/Bad比率）および理由の統計サマリーを表示",
        "description_zh": "查看本地 AI 答复的满意度统计（点赞/点踩比例）及理由汇总",
        "natural_query": "xem phản hồi",
        "natural_query_ja": "回答フィードバック確認",
        "natural_query_zh": "查看回答反馈",
        "context_required": "Bất kỳ sổ nào (đọc từ local_cases)",
        "context_required_ja": "すべてのノート（local_casesから読込）",
        "context_required_zh": "任意台账（从 local_cases 读取）",
        "intent": "xem_phan_hoi",
    },
    {
        "command": "/kynang",
        "aliases": ["/ky-nang", "/スキル", "/技能"],
        "category": "Kỹ năng người dùng",
        "category_ja": "ユーザー・スキル",
        "category_zh": "用户技能",
        "description": "Xem danh sách và trạng thái các kỹ năng cá nhân đã lưu trong máy",
        "description_ja": "端末ローカルに保存済みの個人スキル一覧とステータスを表示",
        "description_zh": "查看保存在本地的个人技能列表与状态",
        "natural_query": "xem kỹ năng của tôi",
        "natural_query_ja": "私のスキル一覧",
        "natural_query_zh": "查看我的技能",
        "context_required": "Bất kỳ sổ nào (đọc từ local_cases/skills)",
        "context_required_ja": "すべてのノート（local_cases/skillsから読込）",
        "context_required_zh": "任意台账（从 local_cases/skills 读取）",
        "intent": "kynang_danh_sach",
    },
    {
        "command": "/kynang tao",
        "aliases": ["/kynang-tao", "/スキル作成", "/创建技能"],
        "category": "Kỹ năng người dùng",
        "category_ja": "ユーザー・スキル",
        "category_zh": "用户技能",
        "description": "Khởi động phỏng vấn ngắn để tạo kỹ năng mới chuẩn Hermes lưu tại máy",
        "description_ja": "対話インタビューにより端末ローカルにHermes標準の新規スキルを作成",
        "description_zh": "通过简短问答交互在本地创建符合Hermes标准的全新技能",
        "natural_query": "tạo kỹ năng mới",
        "natural_query_ja": "新規スキル作成",
        "natural_query_zh": "创建新技能",
        "context_required": "Bất kỳ sổ nào",
        "context_required_ja": "すべてのノート",
        "context_required_zh": "任意台账",
        "intent": "kynang_tao",
    },
    {
        "command": "/kynang xem",
        "aliases": ["/kynang-xem", "/スキル確認", "/查看技能"],
        "category": "Kỹ năng người dùng",
        "category_ja": "ユーザー・スキル",
        "category_zh": "用户技能",
        "description": "Xem chi tiết quy trình SKILL.md và tệp hỗ trợ của kỹ năng cá nhân",
        "description_ja": "個人スキルの手順書（SKILL.md）および付属ファイルの内容を確認",
        "description_zh": "查看个人技能的操作规程（SKILL.md）及附属文件内容",
        "natural_query": "xem chi tiết kỹ năng",
        "natural_query_ja": "スキル詳細確認",
        "natural_query_zh": "查看技能详情",
        "context_required": "Tên kỹ năng cần xem",
        "context_required_ja": "確認対象のスキル名",
        "context_required_zh": "需要查看的技能名称",
        "intent": "kynang_xem",
    },
    {
        "command": "/kynang luu-tru",
        "aliases": ["/kynang-luu-tru", "/kynang-luutru", "/スキルアーカイブ", "/归档技能"],
        "category": "Kỹ năng người dùng",
        "category_ja": "ユーザー・スキル",
        "category_zh": "用户技能",
        "description": "Đưa kỹ năng vào thư mục lưu trữ đóng băng (.archive/) an toàn",
        "description_ja": "スキルをアーカイブ保管庫（.archive/）へ安全に退避移動",
        "description_zh": "将指定技能安全移入冻结归档目录（.archive/）",
        "natural_query": "lưu trữ kỹ năng",
        "natural_query_ja": "スキルをアーカイブ",
        "natural_query_zh": "归档此技能",
        "context_required": "Tên kỹ năng cần lưu trữ",
        "context_required_ja": "アーカイブ対象のスキル名",
        "context_required_zh": "需要归档的技能名称",
                "intent": "kynang_luu_tru",
    },
    {
        "command": "/phongvan",
        "aliases": ["/phong-van", "/インタビュー", "/专家访谈", "/采访"],
        "category": "Phỏng vấn chuyên gia",
        "category_ja": "専門家インタビュー",
        "category_zh": "专家访谈",
        "description": "Mở phiên phỏng vấn chuyên gia để thu thập tri thức và làm rõ khoảng trống kỹ thuật",
        "description_ja": "専門家インタビューセッションを開始し、暗黙知を収集して技術ギャップを明確化",
        "description_zh": "启动专家访谈会话，采集隐性知识并梳理技术空白",
        "natural_query": "bắt đầu phỏng vấn chuyên gia",
        "natural_query_ja": "専門家インタビュー",
        "natural_query_zh": "专家访谈",
        "context_required": "Bất kỳ sổ nào",
        "context_required_ja": "すべてのノート",
        "context_required_zh": "任意台账",
        "intent": "phong_van_chuyen_gia",
    },
    {
        "command": "/thongke",
        "aliases": ["/thong-ke", "/統計", "/统计", "/kpi"],
        "category": "Thống kê & KPI",
        "category_ja": "統計・KPI",
        "category_zh": "统计与KPI",
        "description": "Tổng hợp số liệu thống kê vận hành hệ thống, tỷ lệ phản hồi và chỉ số KPI xưởng",
        "description_ja": "システム運用統計、回答フィードバック率、工場KPI指標を集計表示",
        "description_zh": "汇总系统运行统计数据、回答反馈率及车间KPI指标",
        "natural_query": "thống kê vận hành",
        "natural_query_ja": "運用統計",
        "natural_query_zh": "运营统计",
        "context_required": "Bất kỳ sổ nào",
        "context_required_ja": "すべてのノート",
        "context_required_zh": "任意台账",
        "intent": "thong_ke_he_thong",
    },
    {
        "command": "/trangthai",
        "aliases": ["/trang-thai", "/ステータス", "/状态", "/系统状态"],
        "category": "Quản trị & Hệ thống",
        "category_ja": "管理・システム",
        "category_zh": "管理与系统",
        "description": "Kiểm tra trạng thái kết nối, cơ sở dữ liệu và sức khỏe toàn diện các dịch vụ AIOS",
        "description_ja": "接続状態、データベース、およびAIOS全サービスの健全性を確認",
        "description_zh": "检查连接状态、数据库及 AIOS 全部服务的运行健康度",
        "natural_query": "kiểm tra trạng thái hệ thống",
        "natural_query_ja": "システム状態確認",
        "natural_query_zh": "检查系统状态",
        "context_required": "Bất kỳ sổ nào",
        "context_required_ja": "すべてのノート",
        "context_required_zh": "任意台账",
        "intent": "trang_thai_he_thong",
    },
)


def get_command_catalog() -> List[Dict[str, Any]]:
    """Trả về toàn bộ danh mục lệnh slash hệ thống."""
    return [dict(item) for item in _SLASH_COMMANDS_CATALOG]


def get_all_alive_slash_commands() -> Set[str]:
    """Trả về tập hợp toàn bộ các chuỗi lệnh slash đang sống (bao gồm cả lệnh chính và biến thể)."""
    cmds: Set[str] = set()
    for item in _SLASH_COMMANDS_CATALOG:
        cmds.add(item["command"])
        for alias in item.get("aliases", []):
            cmds.add(alias)
    return cmds


def generate_manual_commands_markdown(lang: str = "vi") -> str:
    """Sinh nội dung bảng markdown cẩm nang danh mục lệnh theo ngôn ngữ chuẩn."""
    norm_lang = (lang or "vi").strip().lower()

    if norm_lang == "ja":
        lines = [
            "## 9. システムコマンド一覧（スラッシュコマンド）",
            "",
            "チャット入力欄で `/` を入力すると、システムコマンドの候補パレットがポップアップ表示されます。",
            "また、同等の自然言語文を通常どおり入力しても、AIOS は自動的に意図を認識して該当機能を実行します。",
            "",
            "| 主要コマンド & エイリアス | 同等の自然言語文 | 機能・用途 | 必要なコンテキスト | 機能グループ |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        for item in _SLASH_COMMANDS_CATALOG:
            aliases_str = ", ".join(f"`{a}`" for a in item["aliases"]) if item["aliases"] else "（なし）"
            cmd_display = f"**`{item['command']}`**<br>別名: {aliases_str}"
            nat_display = f"`{item['natural_query_ja']}`<br>*(越: `{item['natural_query']}`)*"
            desc = item["description_ja"]
            ctx = item["context_required_ja"]
            cat = item["category_ja"]
            lines.append(f"| {cmd_display} | {nat_display} | {desc} | {ctx} | **{cat}** |")
        lines.append("")
        lines.append("*ヒント: チャット枠で `/` を入力して ↑↓ キーで選択し、Enter を押すとコマンドが入力欄に挿入されます。送信ボタンを押すと実行されます。*")
        return "\n".join(lines)

    elif norm_lang == "zh":
        lines = [
            "## 9. 系统命令目录（斜杠命令 Slash Commands）",
            "",
            "在聊天输入框中输入 `/` 时，系统将弹出浮动命令建议面板。",
            "用户亦可直接输入等效的自然语言语句，AIOS 将自动识别意图并运行对应功能。",
            "",
            "| 主要命令与变体 | 等效自然语言语句 | 功能用途 | 适用上下文 | 功能分组 |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        for item in _SLASH_COMMANDS_CATALOG:
            aliases_str = ", ".join(f"`{a}`" for a in item["aliases"]) if item["aliases"] else "（无）"
            cmd_display = f"**`{item['command']}`**<br>变体: {aliases_str}"
            nat_display = f"`{item['natural_query_zh']}`<br>*(越: `{item['natural_query']}`)*"
            desc = item["description_zh"]
            ctx = item["context_required_zh"]
            cat = item["category_zh"]
            lines.append(f"| {cmd_display} | {nat_display} | {desc} | {ctx} | **{cat}** |")
        lines.append("")
        lines.append("*提示: 在聊天框中输入 `/` 并使用 ↑↓ 键选择，按 Enter 即可将命令插入输入框，点击发送按钮即可执行。*")
        return "\n".join(lines)

    else:
        lines = [
            "## 9. DANH MỤC LỆNH HỆ THỐNG (SLASH COMMANDS)",
            "",
            "Khi gõ `/` ở đầu ô soạn câu hỏi, hệ thống sẽ tự động hiển thị bảng gợi ý lệnh kèm mô tả và câu tự nhiên tương đương.",
            "Người dùng cũng có thể gõ câu nói tự nhiên thông thường, AIOS sẽ tự động nhận diện ý định và kích hoạt tính năng tương ứng.",
            "",
            "| Lệnh chính & Biến thể | Câu tự nhiên tương đương | Công dụng chức năng | Ngữ cảnh cần thiết | Nhóm tính năng |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        for item in _SLASH_COMMANDS_CATALOG:
            aliases_str = ", ".join(f"`{a}`" for a in item["aliases"]) if item["aliases"] else "*(không)*"
            cmd_display = f"**`{item['command']}`**<br>Biến thể: {aliases_str}"
            nat_display = f"`{item['natural_query']}`"
            desc = item["description"]
            ctx = item["context_required"]
            cat = item["category"]
            lines.append(f"| {cmd_display} | {nat_display} | {desc} | {ctx} | **{cat}** |")
        lines.append("")
        lines.append("*Mẹo: Gõ `/` trong ô chat, dùng phím ↑/↓ để di chuyển, Enter để chèn lệnh vào ô soạn thảo, sau đó bấm Gửi để thực thi.*")
        return "\n".join(lines)


def record_palette_event(
    action: str,  # "open" | "select"
    command: str = "",
    query: str = "",
    conversation_id: str = "",
) -> None:
    """Ghi nhận sự kiện bảng gợi ý lệnh vào local_cases (Vòng lặp cải thiện liên tục)."""
    try:
        lc_dir = _get_local_cases_dir()
        events_file = lc_dir / "palette_events.jsonl"
        metrics_file = lc_dir / "palette_metrics.json"

        now_iso = datetime.datetime.now().astimezone().isoformat()
        evt = {
            "timestamp": now_iso,
            "action": str(action or "unknown").strip().lower(),
            "command": str(command or "").strip(),
            "query": str(query or "").strip(),
            "conversation_id": str(conversation_id or "").strip(),
        }

        with open(events_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(evt, ensure_ascii=False) + "\n")

        # Cập nhật số liệu tích lũy
        metrics = {
            "total_palette_opens": 0,
            "total_command_selects": 0,
            "by_command": {},
            "by_action": {},
            "last_event_at": now_iso,
        }
        if metrics_file.is_file():
            try:
                metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        act = evt["action"]
        act_dict = metrics.setdefault("by_action", {})
        act_dict[act] = act_dict.get(act, 0) + 1

        if act == "open":
            metrics["total_palette_opens"] = metrics.get("total_palette_opens", 0) + 1
        elif act == "select":
            metrics["total_command_selects"] = metrics.get("total_command_selects", 0) + 1
            cmd = evt["command"]
            if cmd:
                cmd_dict = metrics.setdefault("by_command", {})
                cmd_dict[cmd] = cmd_dict.get(cmd, 0) + 1

        metrics["last_event_at"] = now_iso
        metrics_file.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def get_palette_metrics() -> Dict[str, Any]:
    """Đọc dữ liệu thống kê sự kiện bảng gợi ý từ local_cases."""
    metrics_file = _get_local_cases_dir() / "palette_metrics.json"
    if metrics_file.is_file():
        try:
            return json.loads(metrics_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "total_palette_opens": 0,
        "total_command_selects": 0,
        "by_command": {},
        "by_action": {},
    }

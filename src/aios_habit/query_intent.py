import re
from dataclasses import dataclass, field
from typing import List, Optional

from aios_habit.domain_playbooks import text_has_manufacturing_terms

@dataclass
class QueryIntent:
    intent_name: str
    positive_terms: List[str]
    negative_terms: List[str]
    preferred_source_terms: List[str]
    preferred_sheet_terms: List[str]
    required_terms_any: List[str]
    evidence_focus_note: str

INTENT_RULES = [
    QueryIntent(
        intent_name="manual_shipping_existing_line",
        positive_terms=["manual shipping", "existing line", "manual supply line", "container", "oricon", "workflow", "staging", "xuất kho manual"],
        negative_terms=[],
        preferred_source_terms=[
            "補足資料", "ステージングテーブル", "システムインターフェイス", "manualshipping", "existingline", "AMS以外のラインからの出庫指示"
        ],
        preferred_sheet_terms=["ステージングテーブル", "manualshipping", "inbounddownload", "出庫指示"],
        required_terms_any=["manualshipping", "existingline", "manual", "supply", "workflow", "staging"],
        evidence_focus_note="Ưu tiên trả lời theo evidence có source_match/intent_match cao. Không chuyển trọng tâm sang workflow khác nếu câu hỏi chỉ hỏi manual shipping existing line."
    ),
    QueryIntent(
        intent_name="design_change_running_change",
        positive_terms=["design change", "running change", "thay đổi thiết kế", "đổi sang linh kiện"],
        negative_terms=[],
        preferred_source_terms=[
            "AMS_設計変更", "設計変更", "ECO", "ECN", "RC", "Running Change"
        ],
        preferred_sheet_terms=["設計変更", "ECO"],
        required_terms_any=["design", "change", "running", "rc", "eco", "ecn", "revup"],
        evidence_focus_note="Ưu tiên bằng chứng mô tả quy trình ECO/ECN, thay đổi BOM/BOP và xác nhận hết tồn kho."
    ),
    QueryIntent(
        intent_name="wms_mom_agv_integration",
        positive_terms=["wms", "mom", "agv", "matecon", "tanaban", "oricon", "chỉ thị xuất/nhập kho"],
        negative_terms=[],
        preferred_source_terms=[
            "AGV通信仕様", "TANABAN_Master", "MOMおよびWMSデータ完全クリア方法", "tb_agv_issue_data", "e_orikon_data"
        ],
        preferred_sheet_terms=["TANABAN", "AGV", "通信仕様", "マテコン"],
        required_terms_any=["wms", "mom", "agv", "matecon", "tanaban", "oricon"],
        evidence_focus_note="Tập trung vào liên kết Master, Oricon ID, Address number và tín hiệu giao tiếp AGV."
    )
]

def extract_query_intent(query: str) -> Optional[QueryIntent]:
    query_lower = query.lower()
    if not text_has_manufacturing_terms(query_lower):
        return None

    best_intent = None
    max_matches = 0
    
    for intent in INTENT_RULES:
        matches = sum(1 for term in intent.positive_terms if term.lower() in query_lower)
        if matches > max_matches:
            max_matches = matches
            best_intent = intent
            
    if max_matches > 0:
        return best_intent
        
    return None

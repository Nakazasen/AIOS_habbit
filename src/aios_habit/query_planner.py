import json
import logging
from typing import Any, Mapping

LOGGER = logging.getLogger(__name__)


def generate_query_expansion(
    question: str,
    chat_history: tuple[dict[str, str], ...] = (),
    privacy_mode: str = "local_only",
    cloud_consent_confirmed: bool = False,
) -> Mapping[str, Any] | None:
    """Uses BrainGateway to analyze the question and generate sub-queries ONLY when cloud is explicitly allowed."""
    if privacy_mode != "cloud_allowed" or not cloud_consent_confirmed:
        return None

    history_text = ""
    if chat_history:
        history_text = "--- PREVIOUS CHAT HISTORY ---\n"
        for msg in chat_history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            history_text += f"{role}: {msg.get('content')}\n"
        history_text += "\n"

    prompt = (
        "You are an expert query planner for a Retrieval-Augmented Generation (RAG) system.\n"
        "Your task is to analyze the user's question and determine if it requires cross-source synthesis or complex retrieval.\n"
        "If it is a simple question (e.g., 'What is X?'), output intent 'general' and no variants.\n"
        "If it requires comparing, synthesizing from multiple sources, or exploring a broad architecture, output intent 'cross_source_synthesis'.\n"
        "If the question uses pronouns like 'it', 'that', 'he', 'they', resolve them using the CHAT HISTORY.\n"
        "For 'cross_source_synthesis', generate 2 to 3 distinct sub-queries that break down the complex question.\n\n"
        f"{history_text}"
        f"--- LATEST QUESTION ---\n{question}\n\n"
        "Output ONLY valid JSON in the following format, without markdown formatting or code blocks:\n"
        '{"intent_category": "<intent>", "variants": [{"text": "<sub-query 1>", "origin": "expansion", "target_equivalent": false}, ...]}'
    )

    try:
        from aios_habit.workspace_chat_ai_answer import RealWorkspaceAIProviderClient, WorkspaceAIAnswerRequest
        from aios_habit.workspace_chat_router_adapter import generate_answer_via_router

        req = WorkspaceAIAnswerRequest(
            conversation_id="planner",
            question=prompt,
            context_sources=(),
            privacy_mode="cloud_allowed",
            cloud_consent_confirmed=True,
            consent_source_keys=(),
            retrieval_applied=False,
            retrieved_context_sources=(),
            real_router_enabled=True,
        )

        res = generate_answer_via_router(req, RealWorkspaceAIProviderClient())

        if not res.ok or not res.answer_text:
            return None

        # Parse JSON safely
        text = res.answer_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        expansion = json.loads(text.strip())

        if expansion.get("intent_category") == "cross_source_synthesis" and expansion.get("variants"):
            LOGGER.info("Generated query expansion successfully")
            return expansion

        return None

    except Exception:
        LOGGER.warning("Failed to generate query expansion")
        return None


def generate_memory_compression(
    chat_history: tuple[dict[str, str], ...],
    privacy_mode: str = "local_only",
    cloud_consent_confirmed: bool = False,
) -> str:
    """Summarizes a long chat history to carry over context to a new session only when cloud is allowed."""
    if not chat_history or privacy_mode != "cloud_allowed" or not cloud_consent_confirmed:
        return ""

    history_text = ""
    for msg in chat_history:
        role = "Người dùng" if msg.get("role") == "user" else "Hệ thống/AI"
        history_text += f"{role}: {msg.get('content')}\n"

    prompt = (
        "Bạn là một chuyên gia hệ thống. Hãy tóm tắt ngắn gọn các thực thể, kiến trúc và nội dung kỹ thuật cốt lõi "
        "trong phiên chat RAG dưới đây để làm ngữ cảnh cho phiên làm việc sau.\n"
        "Tập trung vào các định nghĩa, quyết định kiến trúc và thông tin chuyên sâu. Trả về dưới dạng một đoạn văn bản tóm tắt súc tích, không lan man.\n\n"
        f"--- LỊCH SỬ HỘI THOẠI ---\n{history_text}"
    )

    from aios_habit.workspace_chat_ai_answer import RealWorkspaceAIProviderClient, WorkspaceAIAnswerRequest
    from aios_habit.workspace_chat_router_adapter import generate_answer_via_router

    req = WorkspaceAIAnswerRequest(
        conversation_id="memory_compress",
        question=prompt,
        context_sources=(),
        privacy_mode="cloud_allowed",
        cloud_consent_confirmed=True,
        consent_source_keys=(),
        retrieval_applied=False,
        retrieved_context_sources=(),
        real_router_enabled=True,
    )

    try:
        res = generate_answer_via_router(req, RealWorkspaceAIProviderClient())
        if res.ok and res.answer_text:
            return res.answer_text.strip()
    except Exception:
        LOGGER.warning("Error compressing memory")
    return ""


def plan_excel_query_via_llm(
    question: str,
    schemas_text: str,
    privacy_mode: str = "local_only",
    cloud_consent_confirmed: bool = False,
) -> dict | None:
    """Sử dụng LLM để sinh truy vấn cấu trúc từ câu hỏi phức tạp khi có sự đồng ý."""
    if privacy_mode != "cloud_allowed" or not cloud_consent_confirmed:
        return None

    prompt = (
        "You are an expert data analyst and SQL planner for manufacturing, warehouse, and enterprise spreadsheets. "
        "Your task is to translate a user's question about an Excel file into a bounded, structured JSON query plan.\n\n"
        f"--- EXCEL SCHEMAS ---\n{schemas_text}\n\n"
        f"--- USER QUESTION ---\n{question}\n\n"
        "Generate a JSON object matching this structure. Omit empty arrays or strings:\n"
        "{\n"
        '  "sheet": "Name of the target sheet",\n'
        '  "select_columns": ["col1", "col2"],\n'
        '  "filters": [{"column": "col1", "operator": "=", "value": "some_value"}],\n'
        '  "group_by": ["col1"],\n'
        '  "aggregates": [{"function": "sum", "column": "col2", "alias": "total_col2"}],\n'
        '  "order_by": [{"column": "total_col2", "direction": "desc"}],\n'
        '  "limit": 20\n'
        "}\n"
        "Rules:\n"
        "- Supported operators: =, !=, >, >=, <, <=, contains.\n"
        "- Supported aggregates: count, sum, avg, min, max.\n"
        "- When grouping, select_columns MUST contain the group_by columns.\n"
        "- For 'Top N ...' queries, set order_by on the metric and limit to N.\n"
        "- Output ONLY valid JSON, with no explanation or markdown code blocks."
    )

    try:
        import re
        from aios_habit.workspace_chat_ai_answer import RealWorkspaceAIProviderClient, WorkspaceAIAnswerRequest, generate_workspace_ai_answer

        req = WorkspaceAIAnswerRequest(
            conversation_id="excel_planner",
            question=prompt,
            context_sources=(),
            privacy_mode="cloud_allowed",
            cloud_consent_confirmed=True,
            consent_source_keys=(),
            retrieval_applied=False,
            retrieved_context_sources=(),
            real_router_enabled=True,
        )
        provider = RealWorkspaceAIProviderClient()
        res = generate_workspace_ai_answer(req, provider)
        if res.ok and res.answer_text:
            json_match = re.search(r'\{.*\}', res.answer_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
    except Exception:
        LOGGER.warning("Error in LLM Excel Planner")
    return None

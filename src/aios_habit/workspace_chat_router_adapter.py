import logging
from typing import Tuple
from nakazasen_ai_router import AIRequest, create_router_from_env

LOGGER = logging.getLogger(__name__)

def generate_answer_via_router(
    question: str,
    system_prompt: str,
    user_prompt: str
) -> Tuple[bool, str]:
    """
    Call nakazasen-ai-router with the prompt and system prompt.
    Returns (ok, text_or_error_message).
    """
    try:
        # Create router from environment variables.
        # enable_network=True is required for live network communication.
        router = create_router_from_env(enable_network=True)
    except Exception as e:
        LOGGER.error("Failed to create router from env: %s", e)
        return False, "Dịch vụ AI chưa phản hồi. Vui lòng kiểm tra cấu hình API key."

    # Construct messages to preserve system and user prompt structures
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # AIRequest with clean metadata (no raw api keys or secrets)
    req = AIRequest(
        prompt=user_prompt,
        metadata={"messages": messages}
    )

    try:
        outcome = router.route_outcome(req)
        if outcome.status == "success" and outcome.result:
            return True, outcome.result.text
        else:
            err_type = outcome.error_type or "all_providers_exhausted"
            if err_type == "budget_exceeded":
                return False, "Yêu cầu đã bị chặn vì vượt quá giới hạn ngân sách (budget exceeded)."
            return False, "Dịch vụ AI chưa phản hồi. Vui lòng kiểm tra lại kết nối mạng hoặc cấu hình API key."
    except Exception as e:
        LOGGER.error("Router route_outcome failed: %s", e)
        return False, "Dịch vụ AI chưa phản hồi. Vui lòng thử lại sau."


class WorkspaceChatRouterAdapter:
    def generate_answer(
        self,
        question: str,
        system_prompt: str,
        user_prompt: str
    ) -> Tuple[bool, str]:
        return generate_answer_via_router(question, system_prompt, user_prompt)

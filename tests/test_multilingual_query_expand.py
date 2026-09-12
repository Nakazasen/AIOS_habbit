from aios_habit.rag_v2.multilingual_query_expand import parse_expansion_payload
from aios_habit.rag_v2.query_planning import build_query_plan


def test_parse_expansion_keeps_cjk_search_queries():
    raw = """
    ```json
    {"variants":[
      {"text":"生産完了 登録 手順","language_hint":"ja"},
      {"text":"完工登録 ステップ","language_hint":"ja"},
      {"text":"What are the steps to register production completion?","language_hint":"en"}
    ]}
    ```
    """
    payload = parse_expansion_payload(
        raw,
        original_query="What are the steps to register production completion?",
        require_script="cjk",
    )
    assert payload is not None
    texts = [item["text"] for item in payload["variants"]]
    assert texts == ["生産完了 登録 手順", "完工登録 ステップ"]


def test_parse_expansion_rejects_english_only_when_cjk_required():
    raw = '{"variants":[{"text":"register completion steps","language_hint":"en"}]}'
    assert (
        parse_expansion_payload(
            raw,
            original_query="What are the steps?",
            require_script="cjk",
        )
        is None
    )


def test_build_query_plan_accepts_cjk_expansion():
    expansion = parse_expansion_payload(
        '{"variants":[{"text":"生産完了 登録 手順","language_hint":"ja"}]}',
        original_query="What are the steps to register production completion?",
        require_script="cjk",
    )
    plan = build_query_plan(
        "What are the steps to register production completion?",
        expansion,
    )
    assert plan.expansion_status == "expanded"
    assert any("生産完了" in variant.text for variant in plan.variants)

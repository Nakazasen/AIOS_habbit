from aios_habit.rag_v2.script_family import (
    majority_script,
    query_corpus_script_mismatch,
    script_family,
    uses_script_mismatch_ranking,
)


def test_script_family_latin_vietnamese_and_cjk():
    assert script_family("Chế độ hoạt động như thế nào?") == "latin"
    assert script_family("What are the steps to register completion?") == "latin"
    assert script_family("製造履歴の登録手順") == "cjk"


def test_majority_requires_strict_majority():
    assert majority_script(["abc", "def"]) == "latin"
    assert majority_script(["製造", "abc"]) is None
    assert majority_script(["製造", "手順", "完工", "hello"]) == "cjk"


def test_query_mismatch_latin_against_cjk_corpus():
    corpus = ["製造手順書", "完工登録", "設備メンテナンス", "品質管理", "安全規則", "作業手順"]
    assert query_corpus_script_mismatch("What are the steps to register completion?", corpus) is True
    assert uses_script_mismatch_ranking("What are the steps to register completion?", corpus) is True


def test_same_script_is_not_mismatch():
    corpus = ["quality process", "completion steps", "error handling"]
    assert query_corpus_script_mismatch("What are the steps to register completion?", corpus) is False


def test_should_retry_thin_results():
    from aios_habit.rag_v2.script_family import should_retry_thin_results
    from aios_habit.rag_v2.index import HybridRankingConfig
    from aios_habit.rag_v2.script_family import MISMATCH_CHANNEL_WEIGHTS

    assert should_retry_thin_results(
        unique_document_count=1, indexed_document_count=9, already_retried=False
    )
    assert not should_retry_thin_results(
        unique_document_count=1, indexed_document_count=9, already_retried=True
    )
    assert not should_retry_thin_results(
        unique_document_count=4, indexed_document_count=9, already_retried=False
    )
    lexical_w, dense_w, sparse_w = MISMATCH_CHANNEL_WEIGHTS
    ranking = HybridRankingConfig(
        lexical_weight=lexical_w, dense_weight=dense_w, sparse_weight=sparse_w
    )
    assert ranking.dense_weight > ranking.lexical_weight > 0

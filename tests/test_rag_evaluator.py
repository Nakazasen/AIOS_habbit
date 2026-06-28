from aios_habit.rag_answer_composer import compose_local_answer, PastedStrongModelAnswer
from aios_habit.rag_evidence import build_evidence_pack
from aios_habit.rag_search import RAGSearchResult
from aios_habit.rag_evaluator import evaluate_grounded_answer


def _result(text, metadata=None, score=20):
    return RAGSearchResult('C1','D1',text,score,1,'src','src','src','.txt','local_only',[],[],[],['text'],metadata or {},'intent=manual_shipping')


def test_local_draft_not_final_for_evaluator():
    pack = build_evidence_pack('q', [_result('ManualShipping Workflow evidence')])
    draft = compose_local_answer(pack)
    res = evaluate_grounded_answer(draft, pack, 'manual_shipping')
    assert res.final_answer_eligible is False
    assert res.heuristic_only is True


def test_metadata_only_answer_fails_groundedness():
    pack = build_evidence_pack('q', [_result('Metadata-only source record: file. Content was not extracted.')])
    draft = compose_local_answer(pack)
    res = evaluate_grounded_answer(draft, pack)
    assert res.metadata_only_rate == 1.0
    assert res.answer_groundedness == 0.0


def test_pasted_answer_with_evidence_can_be_final_candidate():
    pack = build_evidence_pack('q', [_result('ManualShipping Workflow Resource ExistingLine')])
    ans = PastedStrongModelAnswer('A1', pack.pack_id, 'q', 'ManualShipping Workflow uses ExistingLine Resource evidence', ['[1]'], [pack.items[0].evidence_id], 'local_only', False, False, 'high')
    res = evaluate_grounded_answer(ans, pack, 'manual_shipping')
    assert res.final_answer_eligible is True
    assert res.answer_groundedness > 0
    assert res.source_intent_match == 1.0

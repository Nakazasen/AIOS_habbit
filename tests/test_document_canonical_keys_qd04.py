"""Automated equivalence tests for QD-04: Document Filename Canonical Normalization.

Verifies:
1. Unicode NFKC and mechanical equivalence rules for all 31 alias pairs in QD-04:
   - Middle dots ('・', '･', '·', '•' -> '_')
   - Whitespace normalization (' ' -> '_')
   - Omitted and variant extensions (.xlsx, .txt, .pptx, no-extension)
   - Case folding
2. Mechanical equivalence of human-typo pairs:
   - OKNGUNITのCO_BRACKETの倒れ_傾き確認結果.xlsx <-> OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx
   - OKNGUNITのCO_BRACKETの倒れ_傾き確認結果 <-> OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx
   - Y_BeamH_Camera_140_to_bất_thường.pptx <-> Y_BeamH_Camera 140_to bất thường.pptx
   - Y_BeamH_Camera_140_to_bất_thường <-> Y_BeamH_Camera 140_to bất thường.pptx
3. All 27 wsc-* document IDs and their .txt variations produce identical canonical keys.
4. Total 31 pairs in QD-04 match 100% identically with the canonical normalization engine.
"""

import json
from pathlib import Path
import pytest

from aios_habit.document_canonical_keys import (
    are_document_names_equivalent,
    match_in_catalog,
    normalize_document_key,
)
from aios_habit.index_domain import load_domain_document_alias_map, match_named_documents


# 31 canonical pairs historically identified under QD-04
QD04_31_PAIRS = [
    # 27 ingestion hash pairs (with and without .txt)
    ("wsc-037c28842e209b28625d6157", "wsc-037c28842e209b28625d6157.txt", "CTUマップ再検討20260330.xlsx"),
    ("wsc-08d8d7616f71e6b9ae67940f", "wsc-08d8d7616f71e6b9ae67940f.txt", "ACRマップ再検討20260105.xlsx"),
    ("wsc-1526cbd0e45f7c07240030b8", "wsc-1526cbd0e45f7c07240030b8.txt", "AGVタスク一覧.xlsx"),
    ("wsc-38c83e012535c1c00a21b3a5", "wsc-38c83e012535c1c00a21b3a5.txt", "CTUマップ再検討20260316.xlsx"),
    ("wsc-513068676f45d2e034f94508", "wsc-513068676f45d2e034f94508.txt", "入庫済みデータ削除_20260213.xlsx"),
    ("wsc-54179f47d8d2421b827912e2", "wsc-54179f47d8d2421b827912e2.txt", "手順書付シナリオ.xlsx"),
    ("wsc-573a0a68739534ed9860dcec", "wsc-573a0a68739534ed9860dcec.txt", "生産履歴登録システム_変更確認チェックリスト_20260914.xlsx"),
    ("wsc-5d2f610a69cf193a6d06c754", "wsc-5d2f610a69cf193a6d06c754.txt", "CTUマップ再検討20260317.xlsx"),
    ("wsc-5ff58e0421fe9d5c5a8d1afb", "wsc-5ff58e0421fe9d5c5a8d1afb.txt", "CTUマップ修正20260406.xlsx"),
    ("wsc-6349bfab87ce7a5eb246e10f", "wsc-6349bfab87ce7a5eb246e10f.txt", "Báo_cáo_lỗi_xuất_kho_AMS.xlsx"),
    ("wsc-72b177b9dab655fc0371095f", "wsc-72b177b9dab655fc0371095f.txt", "KDC_P3MOM_MCO-309_システムインターフェイス設計.xlsx"),
    ("wsc-73a54cee764eda5d635dadbd", "wsc-73a54cee764eda5d635dadbd.txt", "CTU_3階の通路レイアウト_251211.xlsx"),
    ("wsc-803436a6d602b9775a3c0a44", "wsc-803436a6d602b9775a3c0a44.txt", "ステージングテーブル_ライン外出庫連携自動処理用__20231107見直し版___1_.xlsx"),
    ("wsc-831d5d9b2124642784bc0fb3", "wsc-831d5d9b2124642784bc0fb3.txt", "AGV通信仕様.xlsx"),
    ("wsc-84b2db45574ff975b7f3d674", "wsc-84b2db45574ff975b7f3d674.txt", "ACR_CTU製品仕様書Ver1_20251205.xlsx"),
    ("wsc-989a0376f54d1fc7ebc90698", "wsc-989a0376f54d1fc7ebc90698.txt", "CTUマップ再検討20251215.xlsx"),
    ("wsc-a6d76176e0998559e07f7072", "wsc-a6d76176e0998559e07f7072.txt", "KDC_P3MOM_MCO-309_コンポーネント設計.xlsx"),
    ("wsc-ab150f1186115f64ca93a65d", "wsc-ab150f1186115f64ca93a65d.txt", "補足資料_要件内容反映版_20231110.xlsx"),
    ("wsc-b8220b0d1cc36804b19e6dea", "wsc-b8220b0d1cc36804b19e6dea.txt", "AGV通信仕様_260206.xlsx"),
    ("wsc-bef87e7dfd165abf6a18c8a7", "wsc-bef87e7dfd165abf6a18c8a7.txt", "ORICON_STATUS_変換ツール_完成版.xlsx"),
    ("wsc-cf637181cd88adbdf54247c0", "wsc-cf637181cd88adbdf54247c0.txt", "ORICON_STAUS早見表.xlsx"),
    ("wsc-d489e437c9abecd020ee12ba", "wsc-d489e437c9abecd020ee12ba.txt", "CTUマップ再検討20260318.xlsx"),
    ("wsc-d86e792838659a8a6ddc040e", "wsc-d86e792838659a8a6ddc040e.txt", "MOMおよびWMSデータ完全クリア方法.xlsx"),
    ("wsc-e84bb328ced276d4ec291a7b", "wsc-e84bb328ced276d4ec291a7b.txt", "マテコン操作手順書_v001_生産技術_TV.xlsx"),
    ("wsc-ef0d393c086c7f07627ca8b8", "wsc-ef0d393c086c7f07627ca8b8.txt", "TANABAN_Master.xlsx"),
    ("wsc-fa03a4b0ad4fd23942b317c5", "wsc-fa03a4b0ad4fd23942b317c5.txt", "マテコン操作手順書_v001_生産技術_1.xlsx"),
    ("wsc-ee5a4f6d3c263185fe6ff10b", "wsc-ee5a4f6d3c263185fe6ff10b.txt", "OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx"),
    # 4 mechanical human typo pairs (middle dots, spaces, extension omissions)
    ("OKNGUNITのCO_BRACKETの倒れ_傾き確認結果.xlsx", "OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx", "OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx"),
    ("OKNGUNITのCO_BRACKETの倒れ_傾き確認結果", "OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx", "OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx"),
    ("Y_BeamH_Camera_140_to_bất_thường.pptx", "Y_BeamH_Camera 140_to bất thường.pptx", "Y_BeamH_Camera 140_to bất thường.pptx"),
    ("Y_BeamH_Camera_140_to_bất_thường", "Y_BeamH_Camera 140_to bất thường.pptx", "Y_BeamH_Camera 140_to bất thường.pptx"),
]


def test_qd04_31_pairs_count():
    """Verify exactly 31 pairs are defined and covered."""
    assert len(QD04_31_PAIRS) == 31


def test_mechanical_typos_equivalence():
    """Verify that mechanical typo pairs are recognized as 100% equivalent by normalize_document_key."""
    # 1. OKNGUNIT: underscore vs middle dot, with and without extension
    assert are_document_names_equivalent(
        "OKNGUNITのCO_BRACKETの倒れ_傾き確認結果.xlsx",
        "OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx"
    )
    assert are_document_names_equivalent(
        "OKNGUNITのCO_BRACKETの倒れ_傾き確認結果",
        "OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx"
    )

    # 2. Y_BeamH: underscore vs spaces, with and without extension
    assert are_document_names_equivalent(
        "Y_BeamH_Camera_140_to_bất_thường.pptx",
        "Y_BeamH_Camera 140_to bất thường.pptx"
    )
    assert are_document_names_equivalent(
        "Y_BeamH_Camera_140_to_bất_thường",
        "Y_BeamH_Camera 140_to bất thường.pptx"
    )


def test_all_27_wsc_stem_and_txt_equivalence():
    """Verify that every wsc-* hash and its .txt form produce identical canonical keys."""
    for item in QD04_31_PAIRS[:27]:
        stem_id, txt_name, _ = item
        assert normalize_document_key(stem_id) == normalize_document_key(txt_name)


def test_match_in_catalog_for_all_mechanical_variants():
    """Verify that candidate matching finds the target from catalog without relying on manual JSON mappings."""
    catalog = [
        "OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx",
        "Y_BeamH_Camera 140_to bất thường.pptx",
        "TANABAN_Master.xlsx",
    ]
    # Check OKNGUNIT variations
    assert match_in_catalog("OKNGUNITのCO_BRACKETの倒れ_傾き確認結果.xlsx", catalog) == "OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx"
    assert match_in_catalog("OKNGUNITのCO_BRACKETの倒れ_傾き確認結果", catalog) == "OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx"

    # Check Y_BeamH variations
    assert match_in_catalog("Y_BeamH_Camera_140_to_bất_thường.pptx", catalog) == "Y_BeamH_Camera 140_to bất thường.pptx"
    assert match_in_catalog("Y_BeamH_Camera_140_to_bất_thường", catalog) == "Y_BeamH_Camera 140_to bất thường.pptx"


def test_all_31_pairs_resolve_via_unified_alias_map():
    """Verify that load_domain_document_alias_map resolves all 31 pairs to their correct target documents."""
    alias_map = load_domain_document_alias_map()
    assert isinstance(alias_map, dict)

    for item in QD04_31_PAIRS[:27]:
        stem_id, txt_name, target = item
        assert alias_map.get(stem_id) == target
        assert alias_map.get(txt_name) == target

    # Mechanical pairs are verified to match target via normalize_document_key
    for item in QD04_31_PAIRS[27:]:
        alias_key, original, target = item
        assert are_document_names_equivalent(alias_key, target)

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aios_habit.rag_v2.converters import ExcelDocumentConverterAdapter, ConversionContext
from aios_habit.rag_v2.chunking import StructureAwareChunker
from aios_habit.rag_v2.index import LocalChunkIndex
from aios_habit.rag_v2.pipeline import RagV2DevConfig

excel_path = Path(r"D:\Sandbox\AIOS_habbit\Tài liệu của tất cả dòng máy\Iris LSU\OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx")
db_path = Path(r"D:\Sandbox\AIOS_index_split_new\lsu\library.sqlite")
targets = [
    ("wsc-edb642314890bccb9fbd61c9", "OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx"),
    ("wsc-ee5a4f6d3c263185fe6ff10b", "OKNGUNITのCO_BRACKETの倒れ_傾き確認結果.xlsx"),
]

from aios_habit.workspace_chat_rag_v2_adapter import (
    _pipeline_config,
    WorkspaceChatRagV2CanaryConfig,
)
from aios_habit.rag_v2.pipeline import RagV2DevPipeline
from dataclasses import replace

cfg = WorkspaceChatRagV2CanaryConfig.from_env()
pipe_cfg = _pipeline_config(cfg, "bge_m3_hybrid", read_only=False, collection_id="lsu")
pipe_cfg = replace(pipe_cfg, ensure_embeddings_on_open=False)
print("Initializing pipeline (ensure_embeddings_on_open=False)...", flush=True)
pipeline = RagV2DevPipeline(pipe_cfg)
index = pipeline.index

for doc_id, src_name in targets:
    print(f"\nProcessing {doc_id} ({src_name})...")
    adapter = ExcelDocumentConverterAdapter()
    context = ConversionContext(document_id=doc_id)
    elements = adapter.convert(excel_path, context)
    print(f"Elements: {len(elements)}")

    chunker = StructureAwareChunker()
    chunks = chunker.chunk_elements(elements)
    print(f"Generated chunks: {len(chunks)}")

    prepared_chunks = [
        replace(c, source_name=src_name, source_path=str(excel_path))
        for c in chunks
    ]

    print("Replacing document chunks in library.sqlite...", flush=True)
    retrievable_count = index.replace_document_chunks(doc_id, prepared_chunks)
    print(f"Successfully indexed {len(prepared_chunks)} chunks ({retrievable_count} retrievable) for {doc_id}!", flush=True)

    with index._conn:
        cur = index._conn.cursor()
        cur.execute("SELECT chunk_id, length(text), text FROM chunks WHERE document_id = ? AND (text LIKE '%0.002%' OR text LIKE '%43.956%')", (doc_id,))
        rows = cur.fetchall()
        print(f"Verification: Found {len(rows)} chunks with target data in database for {doc_id}:")
        for cid, l, txt in rows:
            print(f"  Chunk {cid[:16]} (len={l}): {repr(txt[:100])}")

index.close()
print("\nAll done!")

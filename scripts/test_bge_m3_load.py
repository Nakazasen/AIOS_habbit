import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aios_habit.rag_v2.retrieval_backends import BgeM3Backend, sha256_model_tree

MODEL_DIR = PROJECT_ROOT / "local_runs" / "retrieval_models" / "bge-m3-5617a9f"
actual_checksum = sha256_model_tree(MODEL_DIR)
print(f"Model directory: {MODEL_DIR}")
print(f"Tree checksum: {actual_checksum}")

print("Initializing BgeM3Backend on CPU...")
t0 = time.perf_counter()
backend = BgeM3Backend(
    model_path=MODEL_DIR,
    revision="5617a9f61b028005a4858fdac845db406aefb181",
    artifact_checksum=actual_checksum,
    device="cpu",
)
t1 = time.perf_counter()
print(f"BgeM3Backend initialized in {t1 - t0:.2f}s!")

texts = [
    "Minh phụ trách ticket ORCHID-731 và cần kiểm tra vào thứ Hai.",
    "Tài liệu hướng dẫn hệ thống AIOS Habit dành cho người dùng cá nhân.",
]
print("Encoding documents...")
dense = backend.embed_documents(texts)
sparse = backend.sparse_documents(texts)
print(f"Dense embeddings shape: {len(dense)} x {len(dense[0])}")
print(f"Sparse embeddings sample: {list(sparse[0].items())[:3]}")

query = "Ai phụ trách ORCHID-731?"
print("Encoding query...")
q_dense = backend.embed_query(query)
q_sparse = backend.sparse_query(query)
print(f"Query dense dim: {len(q_dense)}, Query sparse len: {len(q_sparse)}")

print("All embedding operations succeeded!")

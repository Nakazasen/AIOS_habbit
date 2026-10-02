"""Probe hoi dap tren so tay tri thuc (ve KNOWLEDGE-DIGEST-HOME).

Nap so tay Markdown vao context LLM -> hoi -> ghi dap an + thoi gian + token.
Dung de so sanh lane "so tay" voi lane RAG hien tai tren cung bo cau hoi
tong quan / co ban / rong.

Tuong thich Python 3.11.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

QA_PROMPT_TEMPLATE = """Bạn đang đọc một cuốn SỔ TAY TRI THỨC (bản thảo do LLM soạn từ kho tri thức
nội bộ, chưa qua chuyên gia duyệt). Hãy trả lời câu hỏi dưới đây CHỈ dựa vào
nội dung sổ tay. Nếu sổ tay không đủ dữ kiện, hãy nói rõ "chưa đủ dữ kiện"
thay vì suy đoán.

--- SỔ TAY ---
{handbook}
--- HẾT SỔ TAY ---

Câu hỏi: {question}

Yêu cầu: trả lời bằng tiếng Việt, ngắn gọn nhưng bao quát các ý chính liên quan,
liệt kê ý chính bằng gạch đầu dòng khi phù hợp."""


# Bo benchmark mac dinh: cau hoi tong quan / co ban / rong ve kho tri thuc
# dieu tra loi (OMP co the dieu chinh theo corpus thuc te o may nha).
DEFAULT_BENCHMARK_QUESTIONS: List[str] = [
    "LSU là gì và gồm những bộ phận quang học chính nào?",
    "Quy trình điều tra một ca lỗi gồm những bước nào?",
    "4M trong phân tích nguyên nhân lỗi là gì? Cho ví dụ mỗi nhánh.",
    "Các nhóm nguyên nhân gây lỗi F CALL thường gặp là gì?",
    "Khi gặp lỗi lặp lại nhiều lần trên cùng một line thì nên điều tra theo hướng nào?",
    "Đối sách tạm thời và đối sách lâu dài khác nhau thế nào? Khi nào dùng mỗi loại?",
    "Những thông số/ngưỡng nào thường phải kiểm tra đầu tiên khi máy báo lỗi?",
    "Các ngoại lệ hay gặp khiến một ca lỗi không đi theo kịch bản chuẩn là gì?",
    "Làm sao phân biệt lỗi do con người với lỗi do thiết bị?",
    "Bài học kinh nghiệm chung rút ra từ các ca lỗi đã xử lý là gì?",
    "Khi nào nên dừng máy ngay và khi nào có thể chạy tiếp khi có cảnh báo?",
    "Dữ liệu nào cần thu thập trước khi bắt đầu phân tích nguyên nhân một ca lỗi?",
]


@dataclass
class QAProbeResult:
    question: str
    answer: str
    elapsed_s: float
    handbook_chars: int
    prompt_chars: int


@dataclass
class QABenchmarkReport:
    results: List[QAProbeResult] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "questions": len(self.results),
            "results": [
                {
                    "question": r.question,
                    "answer": r.answer,
                    "elapsed_s": round(r.elapsed_s, 2),
                    "handbook_chars": r.handbook_chars,
                    "prompt_chars": r.prompt_chars,
                }
                for r in self.results
            ],
            "total_s": round(sum(r.elapsed_s for r in self.results), 2),
            "avg_s": (
                round(sum(r.elapsed_s for r in self.results) / len(self.results), 2)
                if self.results
                else 0.0
            ),
        }


def ask_handbook(
    handbook_text: str,
    question: str,
    llm_call: Callable[[str], str],
) -> QAProbeResult:
    """Hoi mot cau tren so tay; ghi thoi gian thuc te."""
    prompt = QA_PROMPT_TEMPLATE.format(handbook=handbook_text, question=question)
    started = time.monotonic()
    answer = llm_call(prompt) or ""
    elapsed = time.monotonic() - started
    return QAProbeResult(
        question=question,
        answer=answer,
        elapsed_s=elapsed,
        handbook_chars=len(handbook_text),
        prompt_chars=len(prompt),
    )


def run_benchmark(
    handbook_path: str | Path,
    llm_call: Callable[[str], str],
    questions: Optional[List[str]] = None,
    on_question: Optional[Callable[[int, int, str], None]] = None,
) -> QABenchmarkReport:
    """Chay toan bo benchmark tren file so tay."""
    handbook_text = Path(handbook_path).read_text(encoding="utf-8")
    questions = list(questions) if questions else list(DEFAULT_BENCHMARK_QUESTIONS)
    report = QABenchmarkReport()
    for index, question in enumerate(questions, start=1):
        if on_question is not None:
            on_question(index, len(questions), question)
        report.results.append(ask_handbook(handbook_text, question, llm_call))
    return report


# Rubric cham do bao quat (OMP dung khi so sanh lane so tay vs lane RAG).
COVERAGE_RUBRIC = """Chấm độ bao quát của câu trả lời (so sánh 2 lane trên cùng câu hỏi):
- 2 điểm (đủ ý chính): trả lời bao quát các ý chính liên quan, có số liệu/điều kiện then chốt khi câu hỏi cần.
- 1 điểm (thiếu ý): trả lời đúng hướng nhưng thiếu ý chính quan trọng.
- 0 điểm (sai/lạc): trả lời sai, bịa, hoặc nói chung chung không ăn nhập câu hỏi.
Ghi điểm từng câu cho từng lane, cộng tổng để so sánh."""

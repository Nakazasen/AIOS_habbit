# AIOS WorkLens North Star & Product Doctrine

## 1. What AIOS WorkLens Is
AIOS WorkLens is a **Personal Senior Work Intelligence System** (Hệ thống trí tuệ công việc cá nhân).
It is designed to help users learn, work, investigate cases, accumulate experience, and grow like a senior expert. Rather than just storing notes or managing checklists, it transforms documents, Excel/CSV files, screenshots, logs, chat messages, emails, and AI outputs into evidence-backed case files and reusable work memories.

---

## 2. What AIOS WorkLens Is NOT (What We Avoid)
- **NOT a NotebookLM clone:** NotebookLM is for source-grounded document reading. WorkLens connects knowledge directly with live work incidents, actions, and handovers.
- **NOT a Cursor / VS Code clone:** Cursor is for coding. WorkLens is for case investigations, reasoning, and operational decisions.
- **NOT a generic Second Brain:** A second brain collects abstract knowledge. WorkLens drives action, evidence, and structured lessons from daily work events.
- **NOT just a Streamlit case form:** Streamlit is merely our MVP presentation layer. The core is the underlying work intelligence model and experience vault.
- **NOT just a simple RAG/OCR/ingest tool:** WorkLens does not just dump files into a vector store. It organizes information into cases, evidence nodes, reasoning maps, and verified learning cards.
- **NO Fabricated Causes:** The system never guesses or concludes the "true cause" without evidence. Hypotheses remain hypotheses until verified.
- **NO Uncontrolled Self-Learning:** The system accumulates learning patterns, but the user must verify and transition cards to `confirmed` before they are trusted.
- **NO Data Leaks:** `local_only` raw data is strictly prevented from being exported to cloud services by default.

---

## 3. Product Loop (Vòng Lặp Sản Phẩm)
```
Knowledge → Case → Evidence → Reasoning Map → Action / Communication → Outcome → Learning Memory → Better Work
```

### Diễn giải tiếng Việt:
```
Tài liệu nền (Knowledge)
→ Sự việc hằng ngày (Case)
→ Phân tích có bằng chứng (Evidence)
→ Bản đồ tư duy / suy luận (Reasoning Map)
→ Hành động / giao tiếp (Action / Communication)
→ Kết quả thật (Outcome)
→ Bài học rút ra (Learning Memory)
→ Trí nhớ công việc / Lần sau làm tốt hơn (Better Work)
```

---

## 4. Five Core Product Layers + Two Advanced Layers

### Layer 1: Workspace
- Dedicated workspaces partitioned by domain/industry.
- Examples: Manufacturing MOM, IT Support, Accounting, QA/Testing, Project Management, Translation.
- Keeps cases and configurations isolated to avoid cross-contamination.

### Layer 2: Knowledge Notebook
- Sổ tri thức to ingest background documentation, guidelines, and manuals.
- Supports source notebook isolation so domains or clients do not mix.
- Focuses on mapping existing knowledge to resolve active cases, not just generic Q&A.

### Layer 3: Case Cockpit
- Daily work incident cockpit.
- Aggregates logs, screenshots, Excel sheets, chat, email, and manual notes.
- Generates case maps, rule-based next actions, prompt packs, and secure handovers.

### Layer 4: Learning Memory
- Lesson capture from daily work.
- Creates a structured **Senior Learning Card** ("Thẻ học nghề") detailing symptoms, related systems, initial/rejected hypotheses, verified causes, actions, reusable lessons, applicability rules, keywords, and useful bilingual (VI/JA) replies.
- Requires explicit user validation and review before status becomes `confirmed`.

### Layer 5: Senior Coach / Work Intelligence
- Guides the user like a patient senior colleague.
- Advises what to check first, who to ask, how to reply to chat/emails, identifies gaps in evidence, and references similar past cases.
- Progressively integrates with the knowledge notebook, case history, communication style, and pattern memories.

---

### Layer 6: Visual Knowledge Graph (Advanced Layer)
- Visualizes ingested knowledge, systems, databases, procedures, personnel, cases, and historical outcomes.
- Implemented only after a solid local data foundation exists. No premature graph construction.

### Layer 7: Field Intelligence / Alert (Advanced Layer)
- Spotlights live operational errors from telemetry, logs, and process chain context.
- Implemented only when schemas, historical cases, and validation rules are fully mature. No early predictive failures.

---

## 5. Principles & Core Values
- **Local-first Security:** Sensitive case and evidence details remain offline by default.
- **Evidence-first Discipline:** No hypothesis becomes a confirmed cause without verification evidence.
- **Bilingual Focus:** High-fidelity Japanese and Vietnamese support for industrial and operational teams.

import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

import streamlit as st

# We must import from local package
from aios_habit.audit import audit_repo
from aios_habit.discovery import discover_projects
from aios_habit.export_pack import redacted, validate_export_text
from aios_habit.handover import build_handover
from aios_habit.models import EvidenceRecord, MemoryUnit, nid, sha_text
from aios_habit.phase_gate import phase_validate
from aios_habit.profiles import build_profile_text
from aios_habit.storage import append_jsonl, read_jsonl, write_json

REPO = Path.cwd()
EVIDENCE_PATH = REPO / "03_evidence_registry" / "records" / "evidence.jsonl"
MEMORY_PATH = REPO / "05_memory_vault" / "memory_units.jsonl"
WORKFLOW_PATH = REPO / "06_workflow_library" / "workflows" / "workflow_cards.jsonl"
DECISION_PATH = REPO / "06_workflow_library" / "decision_patterns.jsonl"
EXPORT_DIR = REPO / "07_ai_export_packs"

st.set_page_config(page_title="AIOS Habit Studio", page_icon="🧠", layout="wide")

def load_evidence():
    return read_jsonl(EVIDENCE_PATH)

def load_memory():
    return read_jsonl(MEMORY_PATH)

def page_dashboard():
    st.title("📊 Dashboard")
    st.write(f"**Project Name:** AIOS Habit")
    st.write(f"**Repo Path:** `{REPO}`")
    
    evidence = load_evidence()
    memory = load_memory()
    
    verified_memory = [m for m in memory if m.get("status") == "verified"]
    needs_evidence = [m for m in memory if m.get("status") == "needs_evidence"]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Evidence Records", len(evidence))
    col2.metric("Total Memory Units", len(memory))
    col3.metric("Verified Memory", len(verified_memory))
    col4.metric("Needs Evidence", len(needs_evidence))
    
    st.divider()
    st.subheader("Quick Actions")
    
    col_a, col_b, col_c = st.columns(3)
    if col_a.button("Run Full Audit"):
        st.session_state.page = "Audit"
        st.rerun()
        
    if col_b.button("Build Handover"):
        st.session_state.page = "Handover"
        st.rerun()

    if col_c.button("Open Export Folder"):
        os.startfile(EXPORT_DIR) if os.name == 'nt' else None

def page_projects():
    st.title("📂 Project Discovery")
    
    root_path = st.text_input("Root Path to Scan", value=r"D:\Sandbox")
    max_depth = st.number_input("Max Depth", min_value=1, max_value=5, value=2)
    dry_run = st.checkbox("Dry Run (Don't save to inventory)", value=True)
    
    if st.button("Scan Projects"):
        with st.spinner("Scanning..."):
            cards = discover_projects(Path(root_path), max_depth)
            st.success(f"Found {len(cards)} projects.")
            
            data = [asdict(card) for card in cards]
            st.dataframe(data)
            
            if not dry_run:
                write_json(REPO / "02_sources" / "project_inventory.json", data)
                inventory = "# Source Discovery Inventory\n\nMetadata-only; no raw content ingested.\n\n"
                for card in cards:
                    inventory += f"## {card.name}\n"
                    inventory += f"- Path: `{card.path}`\n"
                    inventory += f"- Signals: {', '.join(card.detected_signals)}\n\n"
                (REPO / "02_sources" / "source_inventory.md").write_text(inventory, encoding="utf-8")
                st.info("Inventory saved.")

def page_evidence():
    st.title("📝 Evidence Registry")
    
    with st.expander("➕ Add New Evidence"):
        with st.form("evidence_form"):
            title = st.text_input("Title")
            source_type = st.selectbox("Source Type", ["markdown", "code", "chat", "url", "other"])
            source_path = st.text_input("Source Path/URL")
            source_pointer = st.text_input("Source Pointer (Line numbers, section)")
            classification = st.selectbox("Classification", ["metadata_only", "public", "internal", "confidential"])
            summary = st.text_area("Summary")
            risk_level = st.selectbox("Risk Level", ["low", "medium", "high", "local_only"])
            local_only = st.checkbox("Local Only (Prevent Export)")
            notes = st.text_area("Notes")
            
            if st.form_submit_button("Add Evidence"):
                record = EvidenceRecord(
                    evidence_id=nid("EVD"),
                    title=title,
                    source_type=source_type,
                    source_path=source_path,
                    source_pointer=source_pointer,
                    classification=classification,
                    summary=summary,
                    hash=sha_text((source_path or "") + (summary or "")),
                    risk_level=risk_level,
                    allowed_for_export=not local_only,
                    notes=notes,
                )
                errors = record.validate()
                if errors:
                    st.error("Validation failed:\n" + "\n".join(errors))
                else:
                    append_jsonl(EVIDENCE_PATH, asdict(record))
                    st.success(f"Added evidence {record.evidence_id}")
    
    st.divider()
    st.subheader("Existing Evidence")
    evidence = load_evidence()
    if evidence:
        st.dataframe(evidence)
    else:
        st.write("No evidence found.")

def page_memory():
    st.title("🧠 Memory Vault")
    
    with st.expander("➕ Add/Validate Memory"):
        with st.form("memory_form"):
            category = st.selectbox("Category", ["identity", "behavior", "language", "workflow", "project_knowledge", "lessons_learned", "decision_patterns"])
            title = st.text_input("Title")
            statement = st.text_area("Statement")
            evidence_ids = st.text_input("Evidence IDs (comma separated)")
            confidence = st.selectbox("Confidence", ["low", "medium", "high"])
            status = st.selectbox("Status", ["draft", "needs_evidence", "verified", "deprecated", "rejected"])
            export_allowed = st.checkbox("Export Allowed")
            tags = st.text_input("Tags (comma separated)")
            review_notes = st.text_area("Review Notes")
            
            col1, col2 = st.columns(2)
            btn_add = col1.form_submit_button("Add Memory")
            btn_validate = col2.form_submit_button("Validate Form Only")
            
            if btn_add or btn_validate:
                ev_list = [x.strip() for x in evidence_ids.split(",") if x.strip()]
                tag_list = [x.strip() for x in tags.split(",") if x.strip()]
                
                memory = MemoryUnit(
                    memory_id=nid("MEM"),
                    category=category,
                    title=title,
                    statement=statement,
                    evidence_ids=ev_list,
                    confidence=confidence,
                    status=status,
                    export_allowed=export_allowed,
                    tags=tag_list,
                    review_notes=review_notes,
                )
                
                errors = memory.validate()
                
                # Check actual evidence exists for verified
                if status == "verified":
                    existing_evs = {e.get("evidence_id") for e in load_evidence()}
                    missing = [e for e in ev_list if e not in existing_evs]
                    if missing:
                        errors.append(f"Missing evidence records: {missing}")

                if errors:
                    st.error("Validation failed:\n" + "\n".join(errors))
                else:
                    if btn_add:
                        append_jsonl(MEMORY_PATH, asdict(memory))
                        st.success(f"Added memory {memory.memory_id}")
                    else:
                        st.success("Memory is valid!")

    st.divider()
    st.subheader("Existing Memory")
    memory = load_memory()
    if memory:
        st.dataframe(memory)
    else:
        st.write("No memory found.")

def page_review_queue():
    st.title("📋 Review Queue")
    st.write("Candidates extracted from documents waiting for review.")
    
    candidate_dir = REPO / "04_extraction_workspace" / "candidate_memory"
    if not candidate_dir.exists():
        st.info("No candidates directory found.")
        return
        
    candidates = list(candidate_dir.glob("*.json"))
    if not candidates:
        st.info("No candidates in queue.")
        return
        
    for c_file in candidates:
        try:
            data = json.loads(c_file.read_text(encoding="utf-8"))
            st.write(f"### {data.get('memory_id')} - {data.get('title')}")
            st.json(data)
            
            col1, col2, col3 = st.columns(3)
            if col1.button("Approve as Verified", key=f"app_{c_file.name}"):
                if not data.get("evidence_ids"):
                    st.error("Cannot approve: Missing evidence_ids")
                else:
                    data["status"] = "verified"
                    data["export_allowed"] = True
                    append_jsonl(MEMORY_PATH, data)
                    c_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                    st.success("Approved and added to Memory Vault.")
                    
            if col2.button("Mark Needs Evidence", key=f"need_{c_file.name}"):
                data["status"] = "needs_evidence"
                c_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                st.info("Marked as Needs Evidence.")
                
            if col3.button("Reject", key=f"rej_{c_file.name}"):
                data["status"] = "rejected"
                c_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                st.warning("Rejected.")
                
            st.divider()
        except Exception as e:
            st.error(f"Error reading {c_file.name}: {e}")

def page_profiles():
    st.title("🎭 Master Profiles")
    st.info("Profiles are generated only from 'verified' and 'export_allowed' memories. Unsupported claims become UNKNOWN.")
    
    if st.button("Build Master Profiles"):
        memories = [m for m in load_memory() if m.get("status") == "verified" and m.get("export_allowed")]
        targets = [
            ("identity", "MASTER_IDENTITY.md"),
            ("behavior", "MASTER_BEHAVIOR_PROFILE.md"),
            ("language", "MASTER_LANGUAGE_PROFILE.md"),
            ("workflow", "MASTER_WORKFLOW_PROFILE.md"),
        ]
        for category, filename in targets:
            items = [m for m in memories if m.get("category") == category]
            content = build_profile_text(filename, items)
            (REPO / filename).write_text(content, encoding="utf-8")
            st.success(f"Built {filename}")
            with st.expander(f"Preview {filename}"):
                st.markdown(content)

def page_export():
    st.title("📦 Export Packs")
    
    target = st.selectbox("Target AI", ["generic", "gpt", "gemini", "claude", "grok"])
    
    col1, col2 = st.columns(2)
    if col1.button("Build Export Pack"):
        folder = {"generic": "future_ai"}.get(target, target)
        output_path = EXPORT_DIR / folder / f"{target}_export_pack.md"
        
        memories = [m for m in load_memory() if m.get("status") == "verified" and m.get("export_allowed")]
        
        body = f"# AIOS Habit Export Pack - {target}\n\n"
        body += "Source conversation archives are excluded by default.\n\n"
        body += "## Evidence Summary\n"
        for evidence in load_evidence():
            if evidence.get("allowed_for_export"):
                body += f"- {evidence.get('evidence_id')}: {evidence.get('title')}\n"
        body += "\n## Verified Memory\n"
        for memory in memories:
            evidence_str = ", ".join(memory.get("evidence_ids", []))
            body += f"- [{memory.get('category')}] {memory.get('statement')} Evidence: {evidence_str}\n"

        body = redacted(body)
        errors = validate_export_text(body)
        if errors:
            st.error("Validation failed:\n" + "\n".join(errors))
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(body, encoding="utf-8")
            st.success(f"Export pack created at `{output_path}`")
            
    if col2.button("Run Audit Before Export"):
        errors, warnings = audit_repo(REPO)
        if errors:
            st.error("Audit failed. Fix before export.")
            st.json(errors)
        else:
            st.success("Audit passed. Safe to export.")

def page_audit():
    st.title("🛡️ System Audit")
    
    if st.button("Run Full Audit"):
        with st.spinner("Auditing..."):
            errors, warnings = audit_repo(REPO)
            if errors:
                st.error("Full Audit Failed ❌")
                for e in errors:
                    st.write(f"- {e}")
            else:
                st.success("Full Audit Passed ✅")
                
            report_path = REPO / "08_audit" / "final_audit_report.md"
            report_path.parent.mkdir(exist_ok=True)
            status_str = "PASS" if not errors else "FAIL"
            report = f"# Audit\n\nStatus: `{status_str}`\n\n" + "\n".join(f"- {e}" for e in errors)
            report_path.write_text(report, encoding="utf-8")

    st.subheader("Phase Validation")
    phases = [str(i) for i in range(10)]
    selected_phase = st.selectbox("Select Phase", phases)
    if st.button(f"Validate Phase {selected_phase}"):
        errors = phase_validate(REPO, selected_phase)
        if errors:
            st.error(f"Phase {selected_phase} Failed ❌")
            for e in errors:
                st.write(f"- {e}")
        else:
            st.success(f"Phase {selected_phase} Passed ✅")

def page_handover():
    st.title("🤝 Handover Builder")
    
    if st.button("Build Handover"):
        evidence_count = len(load_evidence())
        memory_count = len(load_memory())
        body = build_handover(evidence_count, memory_count)
        
        (REPO / "09_handover").mkdir(exist_ok=True)
        (REPO / "09_handover" / "final_handover.md").write_text(body, encoding="utf-8")
        (REPO / "PROJECT_HANDOVER.md").write_text(body, encoding="utf-8")
        st.success("Handover built successfully.")
        st.markdown(body)

def page_settings():
    st.title("⚙️ Settings")
    st.write("Read-only settings for your current AIOS Habit instance.")
    
    st.text_input("Repository Path", value=str(REPO), disabled=True)
    st.text_input("Evidence Path", value=str(EVIDENCE_PATH), disabled=True)
    st.text_input("Memory Path", value=str(MEMORY_PATH), disabled=True)
    st.text_input("Export Directory", value=str(EXPORT_DIR), disabled=True)
    
    st.write("These paths are isolated to prevent accidental public git commits of your private data.")

def main():
    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"

    st.sidebar.title("AIOS Habit Studio")
    pages = {
        "Dashboard": page_dashboard,
        "Projects": page_projects,
        "Evidence": page_evidence,
        "Memory": page_memory,
        "Review Queue": page_review_queue,
        "Profiles": page_profiles,
        "Export": page_export,
        "Audit": page_audit,
        "Handover": page_handover,
        "Settings": page_settings,
    }
    
    selected = st.sidebar.radio("Navigation", list(pages.keys()), index=list(pages.keys()).index(st.session_state.page))
    st.session_state.page = selected
    
    pages[selected]()

def launch():
    import subprocess
    subprocess.run([sys.executable, "-m", "streamlit", "run", __file__])

if __name__ == "__main__":
    if "streamlit" not in sys.modules:
        launch()
    else:
        main()

import streamlit as st
import json
import os
import sys
from pathlib import Path
from datetime import datetime

from .case_models import Case, EvidenceItem
from .case_store import load_cases, load_evidence, save_case, save_evidence, init_store
from .case_ingest import ingest_excel, ingest_csv, save_uploaded_file
from .case_graph import generate_case_mermaid
from .case_actions import generate_next_actions

st.set_page_config(page_title="AIOS Case Cockpit v0.1", layout="wide")

def page_today_brief():
    st.title("☀️ Today Brief")
    cases = load_cases()
    open_cases = [c for c in cases if c.status == "open"]
    high_priority = [c for c in cases if c.priority == "high" and c.status != "resolved" and c.status != "archived"]
    recently_updated = sorted(cases, key=lambda c: c.updated_at, reverse=True)[:5]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Cases", len(cases))
    col2.metric("Open Cases", len(open_cases))
    col3.metric("High Priority (Active)", len(high_priority))
    
    st.subheader("Top Cases to Focus")
    for c in high_priority[:3] if high_priority else open_cases[:3]:
        st.write(f"- **{c.title}** ({c.status}) - Last updated: {c.updated_at[:10]}")
        
    if st.button("Refresh Brief"):
        st.rerun()
    if st.button("Run Audit"):
        st.session_state.page = "Audit"
        st.rerun()

    st.divider()
    st.subheader("Pilot & Governance")
    st.markdown("- [Open Monday Pilot Checklist](MONDAY_PILOT_CHECKLIST.md)")
    st.markdown("- [Open Product North Star](PRODUCT_NORTH_STAR.md)")

def page_cases():
    st.title("🗂️ Cases")
    cases = load_cases()
    
    with st.expander("➕ Create New Case"):
        with st.form("new_case"):
            title = st.text_input("Title")
            priority = st.selectbox("Priority", ["low", "normal", "high", "critical"], index=1)
            privacy = st.selectbox("Privacy Level", ["local_only", "redacted_export", "cloud_allowed"])
            if st.form_submit_button("Create"):
                import uuid
                c = Case(case_id=f"CASE-{str(uuid.uuid4())[:8].upper()}", title=title, priority=priority, privacy_level=privacy)
                save_case(c)
                st.success("Case created!")
                st.rerun()
                
    st.subheader("Select Case")
    case_opts = {c.case_id: f"{c.case_id} - {c.title} ({c.status})" for c in cases}
    selected_id = st.selectbox("Active Case", options=list(case_opts.keys()), format_func=lambda x: case_opts[x])
    
    if selected_id:
        st.session_state.active_case_id = selected_id
        active_case = next(c for c in cases if c.case_id == selected_id)
        st.write("---")
        st.subheader("Case Details")
        
        with st.form("edit_case"):
            sit = st.text_area("Current Situation", value=active_case.current_situation, height=150)
            stat = st.selectbox("Status", ["open", "investigating", "waiting", "resolved", "archived"], index=["open", "investigating", "waiting", "resolved", "archived"].index(active_case.status))
            pri = st.selectbox("Priority", ["low", "normal", "high", "critical"], index=["low", "normal", "high", "critical"].index(active_case.priority))
            
            if st.form_submit_button("Save Case"):
                active_case.current_situation = sit
                active_case.status = stat
                active_case.priority = pri
                active_case.updated_at = datetime.now().isoformat()
                save_case(active_case)
                st.success("Case updated!")

def get_active_case():
    if "active_case_id" not in st.session_state:
        return None
    cases = load_cases()
    for c in cases:
        if c.case_id == st.session_state.active_case_id:
            return c
    return None

def page_add_evidence():
    st.title("📎 Add Evidence")
    active_case = get_active_case()
    if not active_case:
        st.warning("Please select a case in the 'Cases' tab first.")
        return
        
    st.write(f"**Active Case:** {active_case.title}")
    st.warning("Evidence marked `local_only` stays on this machine and must not be copied into cloud prompts or public git.")
    
    import uuid
    new_ev_id = f"EVD-{str(uuid.uuid4())[:8].upper()}"
    
    tab1, tab2, tab3, tab4 = st.tabs(["Upload Excel/CSV", "Upload Image", "Paste Chat/Log", "Manual Note"])
    
    with tab1:
        uploaded_file = st.file_uploader("Choose an Excel/CSV file", type=["xlsx", "xls", "csv"])
        if uploaded_file and st.button("Process Spreadsheet"):
            path = save_uploaded_file(uploaded_file, active_case.case_id)
            if uploaded_file.name.endswith(".csv"):
                ev = ingest_csv(path, active_case.case_id, new_ev_id, uploaded_file.name)
            else:
                ev = ingest_excel(path, active_case.case_id, new_ev_id, uploaded_file.name)
            save_evidence(ev)
            st.success("Spreadsheet ingested.")
            st.text(ev.structured_summary)
            
    with tab2:
        uploaded_img = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg"])
        desc = st.text_input("What does this image show?")
        if uploaded_img and st.button("Save Image Evidence"):
            path = save_uploaded_file(uploaded_img, active_case.case_id)
            ev = EvidenceItem(evidence_id=new_ev_id, case_id=active_case.case_id, source_type="screenshot", source_path=path, title=f"Image: {uploaded_img.name}", extracted_text=desc)
            save_evidence(ev)
            st.success("Image saved.")
            
    with tab3:
        paste_text = st.text_area("Paste Chat or Log text here", height=200)
        title = st.text_input("Log Title")
        if st.button("Save Log Evidence"):
            ev = EvidenceItem(evidence_id=new_ev_id, case_id=active_case.case_id, source_type="chat_paste", source_path="clipboard", title=title, extracted_text=paste_text)
            save_evidence(ev)
            # Create a timeline event
            active_case.timeline_events.append({"date": datetime.now().isoformat(), "event": f"Log added: {title}"})
            save_case(active_case)
            st.success("Log saved and timeline updated.")
            
    with tab4:
        note_text = st.text_area("Manual Note", height=150)
        if st.button("Save Note"):
            ev = EvidenceItem(evidence_id=new_ev_id, case_id=active_case.case_id, source_type="note", source_path="manual", title="Manual Note", extracted_text=note_text)
            save_evidence(ev)
            st.success("Note saved.")

def page_case_map():
    st.title("🗺️ Case Map")
    active_case = get_active_case()
    if not active_case:
        st.warning("Please select a case in the 'Cases' tab first.")
        return
        
    st.write(f"**Active Case:** {active_case.title}")
    evs = [e for e in load_evidence() if e.case_id == active_case.case_id]
    
    mermaid_str = generate_case_mermaid(active_case, evs)
    st.markdown("### Visual Map (Mermaid)")
    st.code(mermaid_str, language="mermaid")
    
    st.markdown("### Fallback Table")
    st.write("**Case Nodes:**")
    st.write(f"- {active_case.title}")
    st.write("**Evidence:**")
    type_icons = {"excel": "📊", "csv": "📊", "screenshot": "🖼️", "image": "🖼️", "chat_paste": "💬", "log_paste": "📜", "note": "📝"}
    for e in evs:
        st.write(f"- {type_icons.get(e.source_type, '📌')} {e.source_type}: {e.title} — privacy: `{e.privacy_level}`")
    st.write("**Hypotheses:**")
    for h in active_case.hypotheses:
        st.write(f"- {h}")

def page_next_actions():
    st.title("🚀 Next Actions")
    active_case = get_active_case()
    if not active_case:
        st.warning("Please select a case in the 'Cases' tab first.")
        return
        
    st.write(f"**Active Case:** {active_case.title}")
    evs = [e for e in load_evidence() if e.case_id == active_case.case_id]
    
    if st.button("Generate Rule-based Next Actions"):
        actions = generate_next_actions(active_case, evs)
        active_case.next_actions.extend([a for a in actions if a not in active_case.next_actions])
        save_case(active_case)
        st.success("Generated next actions.")
        
    st.write("---")
    new_action = st.text_input("Add manual next action:")
    if st.button("Add Action"):
        active_case.next_actions.append(new_action)
        save_case(active_case)
        st.rerun()
        
    for i, a in enumerate(active_case.next_actions):
        st.write(f"{i+1}. {a}")

def page_prompt_pack():
    st.title("🤖 Prompt Pack")
    active_case = get_active_case()
    if not active_case:
        st.warning("Please select a case in the 'Cases' tab first.")
        return
        
    evs = [e for e in load_evidence() if e.case_id == active_case.case_id]
    
    target = st.selectbox("Target", ["Gemini", "GPT", "Copilot", "NotebookLM-safe summary"])
    
    prompt = f"Case Title: {active_case.title}\n"
    prompt += f"Current Situation: {active_case.current_situation}\n\n"
    prompt += "Evidence Summary:\n"
    
    for e in evs:
        if "NotebookLM" in target and e.privacy_level == "local_only":
            continue
        prompt += f"- [{e.source_type}] {e.title}: {e.extracted_text[:200]}...\n"
        
    prompt += "\nHypotheses:\n"
    for h in active_case.hypotheses:
        prompt += f"- {h}\n"
        
    prompt += "\nRequested Output: Please analyze the current situation and evidence. Do not invent facts. Ask for next diagnostic steps."
    
    st.text_area("Generated Prompt", value=prompt, height=300)

def page_handover():
    st.title("🤝 Handover")
    active_case = get_active_case()
    if not active_case:
        st.warning("Please select a case in the 'Cases' tab first.")
        return
        
    evs = [e for e in load_evidence() if e.case_id == active_case.case_id]
    
    md = f"# Case Handover: {active_case.title}\n"
    md += f"**Status:** {active_case.status} | **Priority:** {active_case.priority}\n\n"
    md += f"## What Happened (Situation)\n{active_case.current_situation}\n\n"
    md += "## Evidence\n"
    for e in evs:
        md += f"- {e.title} ({e.source_type})\n"
    md += "\n## Timeline\n"
    for t in active_case.timeline_events:
        md += f"- {t['date']}: {t['event']}\n"
    md += "\n## Next Actions\n"
    for a in active_case.next_actions:
        md += f"- {a}\n"
        
    md += "\n> ⚠️ Privacy Warning: This document contains local case data."
    
    st.markdown("### Preview")
    st.markdown(md)
    st.info("Copy the Markdown below for handover. Keep it local unless all evidence is safe to share.")
    st.download_button("Download Case Handover Markdown", md, file_name=f"{active_case.case_id}_handover.md", mime="text/markdown")
    st.text_area("Raw Markdown", value=md, height=200)

def page_audit():
    st.title("🛡️ Audit")
    
    if st.button("Run Local Audit"):
        cases = load_cases()
        evs = load_evidence()
        active = get_active_case()
        
        checks = []
        
        # Check 1: case file exists
        checks.append({"Check": "Cases file exists", "Status": "PASS" if cases else "WARN"})
        
        # Check 2: evidence has case_id
        ev_no_case = [e for e in evs if not e.case_id]
        checks.append({"Check": "All evidence has case_id", "Status": "FAIL" if ev_no_case else "PASS"})
        
        # Check 3: no missing selected case
        checks.append({"Check": "Active case selected", "Status": "PASS" if active else "FAIL"})
        
        # Check 4: no empty current situation for active case
        if active:
            checks.append({"Check": "Active case has situation", "Status": "FAIL" if not active.current_situation.strip() else "PASS"})
        else:
            checks.append({"Check": "Active case has situation", "Status": "SKIP"})
            
        import pandas as pd
        st.table(pd.DataFrame(checks))

def main():
    init_store()
    if "page" not in st.session_state:
        st.session_state.page = "Today Brief"

    st.sidebar.title("AIOS Case Cockpit")
    pages = {
        "Today Brief": page_today_brief,
        "Cases": page_cases,
        "Add Evidence": page_add_evidence,
        "Case Map": page_case_map,
        "Next Actions": page_next_actions,
        "Prompt Pack": page_prompt_pack,
        "Handover": page_handover,
        "Audit": page_audit,
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

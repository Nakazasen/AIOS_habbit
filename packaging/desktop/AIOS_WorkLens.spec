# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller Specification for AIOS WorkLens Desktop Application.

Builds a self-contained, offline-ready desktop bundle with all vendored
wheels and local assets included.
"""
from pathlib import Path
import sys
from PyInstaller.utils.hooks import copy_metadata, collect_data_files, collect_submodules

block_cipher = None
REPO_ROOT = Path(SPECPATH).resolve().parent.parent

added_files = [
    (str(REPO_ROOT / "src" / "aios_habit"), "aios_habit"),
    (str(REPO_ROOT / "vendor" / "wheels"), "vendor/wheels"),
    (str(REPO_ROOT / "packaging" / "models"), "packaging/models"),
]

all_datas = list(added_files)
for pkg in [
    "streamlit",
    "altair",
    "pyarrow",
    "tornado",
    "click",
    "pandas",
    "openpyxl",
    "excaliflow",
    "graphifyy",
    "nakazasen-ai-router",
    "aios-habit",
    "fastembed",
    "FlagEmbedding",
    "transformers",
    "sentence-transformers",
    "torch",
    "onnxruntime",
    "tokenizers",
    "huggingface-hub",
    "safetensors",
]:
    try:
        all_datas += copy_metadata(pkg)
    except Exception:
        pass

all_datas += collect_data_files("streamlit")
all_datas += collect_data_files("altair")
all_datas += collect_data_files("excaliflow")

hidden_imports = [
    "streamlit",
    "streamlit.web.bootstrap",
    "streamlit.web.cli",
    "streamlit.runtime",
    "streamlit.runtime.scriptrunner",
    "streamlit.runtime.state",
    "streamlit.components.v1",
    "graphify",
    "graphify.build",
    "graphify.extract",
    "graphify.cluster",
    "graphify.analyze",
    "graphify.export",
    "excaliflow",
    "excaliflow.atlas",
    "excaliflow.evidence_atlas",
    "excaliflow.knowledge",
    "excaliflow.explorer",
    "nakazasen_ai_router",
    "fastembed",
    "FlagEmbedding",
    "transformers",
    "sentence_transformers",
    "torch",
    "onnxruntime",
    "safetensors",
    "tokenizers",
    "huggingface_hub",
    "scipy",
    "sklearn",
    "aios_habit.cli",
    "aios_habit.workspace_chat_app",
    "aios_habit.workspace_chat_ui",
    "aios_habit.graphify_adapter",
    "aios_habit.excaliflow_adapter",
    "aios_habit.evidence_graph_viewer",
    "aios_habit.i18n",
    "aios_habit.evidence_trace",
    "aios_habit.evidence_trace_schema",
    "aios_habit.workspace_chat_store",
    "aios_habit.workspace_chat_ai_answer",
    "aios_habit.workspace_chat_rag_v2_adapter",
    "aios_habit.rag_v2",
    "aios_habit.rag_v2.retrieval_backends",
    "aios_habit.rag_v2.bge_subprocess_client",
    "aios_habit.rag_v2.pipeline",
    "aios_habit.ide_handoff_bridge",
    "aios_habit.antigravity_bridge",
    "aios_habit.model_pack",
    "aios_habit.storage",
    "aios_habit.models",
    "aios_habit.audit",
    "aios_habit.discovery",
]
hidden_imports += collect_submodules("streamlit")
hidden_imports += collect_submodules("altair")
hidden_imports += collect_submodules("tornado")

a = Analysis(
    [str(REPO_ROOT / "packaging" / "desktop" / "desktop_entry.py")],
    pathex=[str(REPO_ROOT / "src"), str(REPO_ROOT)],
    binaries=[],
    datas=all_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "tensorflow",
        "pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AIOS_WorkLens",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AIOS_WorkLens",
)

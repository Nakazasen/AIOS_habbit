@echo off
setlocal
cd /d "D:\Sandbox\AIOS_habbit"

set "PYTHONPATH=D:\Sandbox\AIOS_habbit\src;%PYTHONPATH%"
set "AIOS_RAG_V2_NUMPY_DENSE=1"
set "AIOS_BGE_QUERY_TIMEOUT=1200"
set "AIOS_BGE_INIT_TIMEOUT=420"
set "AIOS_RAGV2_WORKER_PERSIST=1"
set "AIOS_FEATURE_CHAT_ACTION=1"
set "AIOS_DOMAIN_ROUTING_ENABLED=1"
set "STREAMLIT_BROWSER_GATHER_USAGE_STATS=false"
set "STREAMLIT_SERVER_FILE_WATCHER_TYPE=none"
set "STREAMLIT_SERVER_RUN_ON_SAVE=false"

D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe -u -m streamlit run src\aios_habit\workspace_chat_app.py --server.port=8501 --server.headless=true --server.fileWatcherType=none --browser.gatherUsageStats=false

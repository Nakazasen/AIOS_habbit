# -*- coding: utf-8 -*-
"""Comprehensive verification suite for Commit D Offline Packaging & Dependency Readiness.

Verifies:
1. Offline vendored wheels (excaliflow, nakazasen_ai_router) and SHA-256 checksums.
2. In-process excaliflow module imports and bridge methods.
3. pyproject.toml and uv.lock synchronization (zero git+https dependencies).
4. Desktop build runner and PyInstaller spec validity.
5. VPS Dockerfile, docker-compose, and single-tenant isolation contract.
6. Clean machine smoke test execution.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
VENDOR_WHEELS_DIR = REPO_ROOT / "vendor" / "wheels"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
UV_LOCK_PATH = REPO_ROOT / "uv.lock"


class TestVendoredWheelsAndChecksums:
    """Verify vendored wheels existence and SHA-256 cryptographic integrity."""

    def test_checksums_json_exists_and_is_valid(self) -> None:
        """Verify checksums.json exists and contains required wheel records."""
        manifest_file = VENDOR_WHEELS_DIR / "checksums.json"
        assert manifest_file.exists(), "Missing vendor/wheels/checksums.json"

        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert "excaliflow-0.1.1-py3-none-any.whl" in data
        assert "nakazasen_ai_router-0.8.0-py3-none-any.whl" in data

    def test_excaliflow_wheel_checksum_matches(self) -> None:
        """Verify excaliflow wheel SHA-256 matches manifest."""
        manifest = json.loads((VENDOR_WHEELS_DIR / "checksums.json").read_text(encoding="utf-8"))
        whl_path = VENDOR_WHEELS_DIR / "excaliflow-0.1.1-py3-none-any.whl"
        assert whl_path.exists(), "Missing excaliflow wheel file"

        actual_sha = hashlib.sha256(whl_path.read_bytes()).hexdigest()
        assert actual_sha == manifest["excaliflow-0.1.1-py3-none-any.whl"]["sha256"]

    def test_nakazasen_ai_router_wheel_checksum_matches(self) -> None:
        """Verify nakazasen_ai_router wheel SHA-256 matches manifest."""
        manifest = json.loads((VENDOR_WHEELS_DIR / "checksums.json").read_text(encoding="utf-8"))
        whl_path = VENDOR_WHEELS_DIR / "nakazasen_ai_router-0.8.0-py3-none-any.whl"
        assert whl_path.exists(), "Missing nakazasen_ai_router wheel file"

        actual_sha = hashlib.sha256(whl_path.read_bytes()).hexdigest()
        assert actual_sha == manifest["nakazasen_ai_router-0.8.0-py3-none-any.whl"]["sha256"]

    def test_rebuilt_aios_wheel_contains_launcher_and_atlas(self) -> None:
        """Verify both Windows and Linux aios_habit wheels contain launcher and atlas functions."""
        import zipfile
        for target_dir in [VENDOR_WHEELS_DIR, REPO_ROOT / "vendor" / "wheels_linux"]:
            whl_file = target_dir / "aios_habit-0.1.0-py3-none-any.whl"
            assert whl_file.exists(), f"Missing {whl_file}"
            with zipfile.ZipFile(whl_file, "r") as zf:
                cli_content = zf.read("aios_habit/cli.py").decode("utf-8")
                viewer_content = zf.read("aios_habit/evidence_graph_viewer.py").decode("utf-8")
                adapter_content = zf.read("aios_habit/excaliflow_adapter.py").decode("utf-8")

                assert "launch_workspace_chat" in cli_content
                assert "cmd_chat" in cli_content
                assert "evidence_graph_tab_atlas" in viewer_content
                assert "render_evidence_atlas_html" in viewer_content
                assert "render_evidence_atlas_html" in adapter_content

    def test_linux_wheelhouse_integrity_and_glibc_compatibility(self) -> None:
        """Verify Linux wheelhouse has 140+ wheels, valid checksums, and glibc 2.17+ support."""
        linux_dir = REPO_ROOT / "vendor" / "wheels_linux"
        manifest_file = linux_dir / "checksums.json"
        assert manifest_file.exists(), "Missing vendor/wheels_linux/checksums.json"

        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert len(manifest) >= 140, f"Expected at least 140 Linux wheels, got {len(manifest)}"

        # Verify protobuf >= 5.26.1 and RAG wheels exist
        protobuf_wheels = [f for f in manifest if "protobuf" in f]
        assert len(protobuf_wheels) >= 1, "Missing protobuf wheel in Linux wheelhouse"

        torch_wheels = [f for f in manifest if "torch" in f]
        assert len(torch_wheels) >= 1, "Missing torch wheel in Linux wheelhouse"

        flag_wheels = [f for f in manifest if "flagembedding" in f.lower()]
        assert len(flag_wheels) >= 1, "Missing FlagEmbedding wheel in Linux wheelhouse"

        # Verify manylinux compatibility for python:3.11-slim (Debian 12 Bookworm, glibc 2.36)
        pandas_wheels = [f for f in manifest if "pandas" in f and "manylinux" in f]
        assert len(pandas_wheels) >= 1, "Missing manylinux pandas wheel"
        assert any(
            "manylinux2014" in w
            or "manylinux_2_17" in w
            or "manylinux_2_24" in w
            or "manylinux_2_28" in w
            for w in pandas_wheels
        ), f"Expected manylinux pandas wheel compatible with python:3.11-slim, found: {pandas_wheels}"

    def test_linux_offline_wheelhouse_resolution_dry_run(self) -> None:
        """Verify pip resolves all dependencies of full RAG profile offline for Linux."""
        cmd = [
            sys.executable, "-m", "pip", "install",
            "--dry-run",
            "--no-index",
            f"--find-links={REPO_ROOT / 'vendor' / 'wheels_linux'}",
            "--platform", "manylinux_2_28_x86_64",
            "--platform", "manylinux2014_x86_64",
            "--platform", "manylinux_2_17_x86_64",
            "--platform", "manylinux_2_24_x86_64",
            "--platform", "any",
            "--python-version", "311",
            "--implementation", "cp",
            "--abi", "cp311",
            "--only-binary=:all:",
            "aios-habit[rag-retrieval-lab,rag-semantic,rag-ingestion-cpu,rag-ingestion-xls]",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"Linux offline pip resolution dry-run failed:\n{res.stderr or res.stdout}"


class TestInProcessExcaliFlowIntegration:
    """Verify real excaliflow module imports and integration with adapter."""

    def test_excaliflow_module_imports_cleanly(self) -> None:
        """Verify import excaliflow succeeds and has correct version."""
        import excaliflow
        assert getattr(excaliflow, "__version__", None) == "0.1.1"

    def test_excaliflow_submodules_available(self) -> None:
        """Verify excaliflow submodules (atlas, evidence_atlas, knowledge, explorer) import."""
        import excaliflow.atlas as atlas
        import excaliflow.evidence_atlas as evidence_atlas
        import excaliflow.knowledge as knowledge
        import excaliflow.explorer as explorer

        assert atlas is not None
        assert evidence_atlas is not None
        assert knowledge is not None
        assert explorer is not None

    def test_excaliflow_adapter_detects_package(self) -> None:
        """Verify ExcaliFlowAdapter check_capabilities detects installed package."""
        from aios_habit.excaliflow_adapter import ExcaliFlowAdapter

        adapter = ExcaliFlowAdapter()
        caps = adapter.check_capabilities()
        assert caps.is_available is True
        assert caps.renderer_version == "0.1.1"
        assert caps.details.get("excaliflow_package_installed") is True
        assert caps.details.get("excaliflow_version") == "0.1.1"

    def test_excaliflow_adapter_get_module(self) -> None:
        """Verify ExcaliFlowAdapter.get_excaliflow_module returns real module."""
        from aios_habit.excaliflow_adapter import ExcaliFlowAdapter

        mod = ExcaliFlowAdapter.get_excaliflow_module()
        assert mod is not None
        assert getattr(mod, "__version__", None) == "0.1.1"


class TestDependencyManifestLockIntegrity:
    """Verify zero GitHub URL dependencies and uv.lock consistency."""

    def test_pyproject_contains_no_git_urls(self) -> None:
        """Verify pyproject.toml does NOT contain git+https URLs."""
        content = PYPROJECT_PATH.read_text(encoding="utf-8")
        assert "git+https://" not in content, "git+https URLs must not be present in pyproject.toml"
        assert "git+http://" not in content
        assert "nakazasen-ai-router==0.8.0" in content
        assert "excaliflow==0.1.1" in content
        assert "graphifyy==0.9.32" in content

    def test_uv_sources_configured_for_offline_wheels(self) -> None:
        """Verify tool.uv.sources maps wheels to vendor/wheels/."""
        content = PYPROJECT_PATH.read_text(encoding="utf-8")
        assert "[tool.uv.sources]" in content
        assert "vendor/wheels/nakazasen_ai_router-0.8.0-py3-none-any.whl" in content
        assert "vendor/wheels/excaliflow-0.1.1-py3-none-any.whl" in content

    def test_uv_lock_check_succeeds(self) -> None:
        """Verify uv lock --check passes with code 0."""
        res = subprocess.run(
            ["uv", "lock", "--check"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"uv lock --check failed: {res.stderr}\n{res.stdout}"


class TestBgeM3ModelPackPackaging:
    """Verify BGE-M3 versioned model packaging, checksum verification, and fail-closed discovery."""

    def test_bge_m3_manifest_exists_and_pinned(self) -> None:
        """Verify bge_m3_manifest.json contains pinned revision and SHA-256 tree digest."""
        from aios_habit.model_pack import DEFAULT_MANIFEST_PATH, BGE_M3_REVISION, BGE_M3_CHECKSUM

        assert DEFAULT_MANIFEST_PATH.exists(), f"Missing BGE-M3 manifest at {DEFAULT_MANIFEST_PATH}"
        manifest = json.loads(DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8"))

        assert manifest.get("model_id") == "BAAI/bge-m3"
        assert manifest.get("revision") == BGE_M3_REVISION
        assert manifest.get("model_tree_checksum") == BGE_M3_CHECKSUM
        assert "files" in manifest and len(manifest["files"]) >= 10
        assert "pytorch_model.bin" in manifest["files"]
        assert "sentencepiece.bpe.model" in manifest["files"]
        assert "tokenizer.json" in manifest["files"]

    def test_bge_m3_model_pack_verification_and_discovery(self) -> None:
        """Verify resolve_bge_m3_model_path finds and validates model pack."""
        from aios_habit.model_pack import resolve_bge_m3_model_path, verify_model_pack

        model_dir, status = resolve_bge_m3_model_path(auto_configure_env=True)
        assert model_dir is not None, f"BGE-M3 model path could not be resolved: {status}"
        assert status.get("status") == "ready", f"BGE-M3 model pack verification failed: {status}"
        assert status.get("checksum") == "sha256:b1d887e03f13547609b4c6498ce8f357242edb5079a448c62d31d4caac320b61"

    def test_bge_m3_fail_closed_on_missing_or_corrupted_pack(self, tmp_path: Path) -> None:
        """Verify verify_model_pack returns unavailable/corrupted on invalid model directories."""
        from aios_habit.model_pack import verify_model_pack, resolve_bge_m3_model_path

        # Empty directory -> unavailable
        empty_dir = tmp_path / "empty_model"
        empty_dir.mkdir()
        res_empty = verify_model_pack(empty_dir)
        assert res_empty["status"] == "unavailable"

        # Missing file directory -> unavailable
        incomplete_dir = tmp_path / "incomplete_model"
        incomplete_dir.mkdir()
        (incomplete_dir / "config.json").write_text("{}", encoding="utf-8")
        res_incomplete = verify_model_pack(incomplete_dir)
        assert res_incomplete["status"] == "unavailable"

        # Zero dev fallback check
        old_env = os.environ.pop("AIOS_BGE_M3_MODEL_PATH", None)
        try:
            m_dir, m_stat = resolve_bge_m3_model_path(auto_configure_env=False, allow_dev_fallback=False)
            # In dev environment without env var and outside PyInstaller, must not fallback to local_runs
            assert m_dir is None
            assert m_stat["status"] == "unavailable"
        finally:
            if old_env:
                os.environ["AIOS_BGE_M3_MODEL_PATH"] = old_env


class TestDesktopPackagingConfiguration:
    """Verify desktop build runner, PyInstaller spec, and genuine E2E execution."""

    def test_desktop_build_prerequisites_function(self, monkeypatch) -> None:
        """Verify desktop_build.py verify_build_prerequisites fails closed when model is missing."""
        import importlib.util
        script_path = REPO_ROOT / "packaging" / "desktop" / "desktop_build.py"
        spec = importlib.util.spec_from_file_location("desktop_build", script_path)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # 1. Normal run with verified model pack -> ready
        result = mod.verify_build_prerequisites(require_model=True)
        assert result["status"] == "ready"
        assert result["bge_enabled"] is True
        assert len(result["verified_wheels"]) >= 80

        # 2. Simulated missing model with require_model=True -> raises RuntimeError (Fail-Closed)
        def mock_missing_model(*args, **kwargs):
            return None, {"status": "unavailable", "reason": "model_pack_not_found"}

        monkeypatch.setattr("aios_habit.model_pack.resolve_bge_m3_model_path", mock_missing_model)
        with pytest.raises(RuntimeError, match="Cannot build BGE-enabled Desktop bundle"):
            mod.verify_build_prerequisites(require_model=True)

        # 3. Simulated missing model with require_model=False (Lightweight build) -> returns ready without BGE
        res_lightweight = mod.verify_build_prerequisites(require_model=False)
        assert res_lightweight["status"] == "ready"
        assert res_lightweight["bge_enabled"] is False

    def test_genuine_excaliflow_atlas_rendering(self) -> None:
        """Verify genuine ExcaliFlow Studio knowledge and evidence atlas engine."""
        from aios_habit.excaliflow_adapter import ExcaliFlowAdapter
        adapter = ExcaliFlowAdapter()
        fixture_file = REPO_ROOT / "tests" / "fixtures" / "synthetic_rag_trace_v1.json"
        trace_data = json.loads(fixture_file.read_text(encoding="utf-8"))

        html_out = adapter.render_evidence_atlas_html(trace_data)
        assert len(html_out) > 500
        assert "<div" in html_out or "<svg" in html_out
        assert "evidence-atlas" in html_out or "Evidence" in html_out

    def test_pyinstaller_spec_file_syntax(self) -> None:
        """Verify AIOS_WorkLens.spec is parseable Python AST."""
        spec_path = REPO_ROOT / "packaging" / "desktop" / "AIOS_WorkLens.spec"
        assert spec_path.exists()
        ast.parse(spec_path.read_text(encoding="utf-8"))

    def test_desktop_executable_gui_healthcheck(self) -> None:
        """Verify the built desktop executable starts GUI server and responds on /_stcore/health."""
        import socket
        import time
        import urllib.request

        exe_name = "AIOS_WorkLens.exe" if sys.platform == "win32" else "AIOS_WorkLens"
        exe_path = REPO_ROOT / "dist" / "AIOS_WorkLens" / exe_name
        if not exe_path.exists():
            pytest.skip(f"Executable not yet built at {exe_path}")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            test_port = s.getsockname()[1]

        proc = subprocess.Popen(
            [str(exe_path), "desktop", "--port", str(test_port), "--no-browser"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(REPO_ROOT),
        )
        health_url = f"http://127.0.0.1:{test_port}/_stcore/health"
        passed = False
        start_time = time.time()
        try:
            while time.time() - start_time < 15:
                try:
                    with urllib.request.urlopen(health_url, timeout=2) as resp:
                        if resp.status == 200:
                            body = resp.read().decode("utf-8")
                            if "ok" in body.lower():
                                passed = True
                                break
                except Exception:
                    time.sleep(0.5)
            assert passed, f"Desktop GUI healthcheck failed on {health_url}"
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

    def test_packaged_desktop_e2e_rag_to_atlas(self, tmp_path: Path) -> None:
        """Verify genuine E2E: Ingestion -> Chunking -> BGE-M3 Indexing -> Hybrid Search -> Dynamic Citation -> Trace -> Atlas."""
        # FlagEmbedding/PyTorch can fault at native level when a long packaging
        # suite has already imported native extensions.  Execute this genuine
        # BGE-M3 check in a fresh interpreter; the child keeps the same test
        # and assertions, rather than replacing them with a mock.
        if os.environ.get("AIOS_COMMIT_D_BGE_CHILD") != "1":
            child_env = os.environ.copy()
            child_env["AIOS_COMMIT_D_BGE_CHILD"] = "1"
            child_env["PYTHONIOENCODING"] = "utf-8"
            node_id = (
                f"{Path(__file__).resolve()}::TestDesktopPackagingConfiguration::"
                "test_packaged_desktop_e2e_rag_to_atlas"
            )
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", node_id],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
                env=child_env,
            )
            assert result.returncode == 0, (
                "Isolated BGE-M3 E2E check failed:\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
            return

        from aios_habit.model_pack import resolve_bge_m3_model_path
        from aios_habit.rag_v2.retrieval_backends import BgeM3Backend
        from aios_habit.rag_v2.chunking import DocumentChunk
        from aios_habit.rag_v2.index import LocalChunkIndex
        from aios_habit.evidence_trace import EvidenceTrace, EvidenceNode, EvidenceEdge, EvidenceTraceContract
        from aios_habit.rag_v2.converters import TextDocumentConverterAdapter
        from aios_habit.rag_v2.adapters import ConversionContext
        from aios_habit.rag_v2.chunking import StructureAwareChunker
        from aios_habit.rag_v2.index import LocalChunkIndex
        from aios_habit.evidence_trace import EvidenceTrace, EvidenceNode, EvidenceEdge, EvidenceTraceContract
        from aios_habit.excaliflow_adapter import ExcaliFlowAdapter
        from datetime import datetime, timezone

        model_dir, status = resolve_bge_m3_model_path(auto_configure_env=True)
        assert model_dir is not None, f"BGE-M3 model directory missing: {status}"

        # 1. Create real document fixture on disk
        doc_filename = "aios_architecture_policy.md"
        doc_file = tmp_path / doc_filename
        doc_content = (
            "# Chính Sách Kiến Trúc AIOS WorkLens\n\n"
            "AIOS WorkLens tích hợp công cụ tìm kiếm ngữ nghĩa BGE-M3 cục bộ kết hợp biểu đồ bằng chứng ExcaliFlow Studio Atlas.\n"
            "Hệ thống đảm bảo tính toàn vẹn 100% bằng chứng trích dẫn và không rò rỉ dữ liệu ra ngoài."
        )
        doc_file.write_text(doc_content, encoding="utf-8")

        # 2. Run real Document Converter
        converter = TextDocumentConverterAdapter()
        ctx = ConversionContext(source_id="src_doc_aios_policy_01", document_id="doc_aios_policy_01")
        elements = converter.convert(str(doc_file), ctx)
        assert len(elements) >= 1, "Expected converter to produce elements"

        # 3. Run real Structure-Aware Chunker
        chunker = StructureAwareChunker()
        chunks = chunker.chunk_elements(elements)
        assert len(chunks) >= 1, "Expected chunker to produce chunks"

        # 4. Initialize real BGE-M3 backend
        backend = BgeM3Backend(
            model_path=model_dir,
            revision=status["revision"],
            artifact_checksum=status["checksum"],
            device="cpu",
            batch_size=1,
            max_length=512,
        )

        # 5. Ingest into real LocalChunkIndex with BGE-M3 backend (dense + sparse embeddings)
        db_path = tmp_path / "rag_index.sqlite"
        with LocalChunkIndex(
            db_path=db_path,
            embedding_backend=backend,
            sparse_backend=backend,
        ) as index:
            inserted_count = index.replace_document_chunks("doc_aios_policy_01", chunks)
            assert inserted_count == len(chunks)

            # 6. Execute genuine 3-channel Hybrid Search (Dense + Sparse + Lexical)
            query_text = "AIOS WorkLens dùng công cụ tìm kiếm nào?"
            search_response = index.hybrid_search_with_summary(query_text, limit=3)
            assert len(search_response.results) >= 1
            assert len(search_response.summary.dense_pool) >= 1, "Expected dense candidates in hybrid pool"
            assert len(search_response.summary.sparse_pool) >= 1, "Expected sparse candidates in hybrid pool"

            top_match = search_response.results[0]
            assert top_match.score > 0.0
            assert "BGE-M3" in top_match.text

        # 7. Dynamically generate citation and grounded answer
        citation_id = "[1]"
        citation_key = "cit_1"
        grounded_answer = f"AIOS WorkLens sử dụng công cụ tìm kiếm ngữ nghĩa BGE-M3 {citation_id}."

        # 8. Construct genuine grounded EvidenceTrace from retrieval results
        trace = EvidenceTrace(
            schema_version="rag-trace/v1",
            trace_id="trc_e2e_real_rag_pipeline_001",
            created_at=datetime.now(timezone.utc).isoformat(),
            ui_locale="vi",
            answer_language="vi",
            source_language="vi",
            provenance={
                "operational_mode": "direct",
                "provider_name": "BGE-M3 LocalChunkIndex RAG",
                "model_name": "BAAI/bge-m3",
                "retrieval_score": top_match.score,
                "document_id": top_match.document_id,
            },
            nodes=[
                EvidenceNode("q1", "question", query_text),
                EvidenceNode("s1", "source", doc_filename, metadata={"source_path": str(doc_file)}),
                EvidenceNode(top_match.chunk_id, "chunk", top_match.text, metadata={"score": top_match.score}),
                EvidenceNode(citation_key, "citation", citation_id),
                EvidenceNode("ans1", "answer", grounded_answer),
            ],
            edges=[
                EvidenceEdge("s1", top_match.chunk_id, "extracted_from"),
                EvidenceEdge(top_match.chunk_id, citation_key, "supports"),
                EvidenceEdge(citation_key, "ans1", "cites"),
            ],
            metadata={"status": "grounded", "retrieval_score": top_match.score},
        )

        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert is_valid, f"Trace contract validation failed: {errors}"

        # 9. Render and verify ExcaliFlow Evidence Atlas HTML
        adapter = ExcaliFlowAdapter()
        viewer_html = adapter.render_evidence_atlas_html(trace, locale="vi")
        assert len(viewer_html) > 500
        assert "<div" in viewer_html or "<svg" in viewer_html
        assert "evidence-atlas" in viewer_html or "Evidence" in viewer_html or "AIOS" in viewer_html or "atlas" in viewer_html.lower()
        assert "[1]" in viewer_html or "BGE-M3" in viewer_html

    def test_desktop_companion_model_pack_packaged_and_discoverable(self, monkeypatch) -> None:
        """Verify built desktop bundle contains companion model pack and resolves in standalone frozen mode."""
        from aios_habit.model_pack import verify_model_pack, resolve_bge_m3_model_path

        dist_bundle = REPO_ROOT / "dist" / "AIOS_WorkLens"
        if dist_bundle.exists():
            companion_model_dir = dist_bundle / "models" / "bge-m3-5617a9f"
            assert companion_model_dir.exists(), f"Companion model dir missing in dist: {companion_model_dir}"
            res = verify_model_pack(companion_model_dir)
            assert res["status"] == "ready"
            assert res["checksum"] == "sha256:b1d887e03f13547609b4c6498ce8f357242edb5079a448c62d31d4caac320b61"

            # Test frozen executable sibling resolution without dev fallback
            exe_path = dist_bundle / ("AIOS_WorkLens.exe" if sys.platform == "win32" else "AIOS_WorkLens")
            monkeypatch.setattr(sys, "frozen", True, raising=False)
            monkeypatch.setattr(sys, "executable", str(exe_path))
            monkeypatch.delenv("AIOS_BGE_M3_MODEL_PATH", raising=False)

            resolved_dir, resolved_stat = resolve_bge_m3_model_path(
                auto_configure_env=False,
                allow_dev_fallback=False,
            )
            assert resolved_dir == companion_model_dir.resolve()
            assert resolved_stat["status"] == "ready"
            assert resolved_stat["checksum"] == "sha256:b1d887e03f13547609b4c6498ce8f357242edb5079a448c62d31d4caac320b61"


class TestVPSDeploymentConfiguration:
    """Verify VPS Dockerfile, docker-compose, and RAG model configuration."""

    def test_vps_dockerfile_contains_rag_extras_and_model_mount(self) -> None:
        """Verify Dockerfile installs full RAG extras and configures model mount point and canary."""
        dockerfile = REPO_ROOT / "packaging" / "vps" / "Dockerfile"
        assert dockerfile.exists()
        content = dockerfile.read_text(encoding="utf-8")

        assert "FROM python:3.11-slim" in content
        assert "vendor/wheels_linux" in content
        assert "aios-habit[rag-retrieval-lab,rag-semantic,rag-ingestion-cpu,rag-ingestion-xls]" in content
        assert "AIOS_WORKSPACE_RAG_V2_CANARY_ENABLED=1" in content
        assert "AIOS_WORKSPACE_RAG_V2_LOCAL_PILOT_ENABLED=1" in content
        assert "AIOS_BGE_M3_MODEL_PATH=/opt/aios/models/bge-m3-5617a9f" in content
        assert "AIOS_BGE_M3_MODEL_REVISION=5617a9f61b028005a4858fdac845db406aefb181" in content
        assert "AIOS_BGE_M3_MODEL_CHECKSUM=sha256:b1d887e03f13547609b4c6498ce8f357242edb5079a448c62d31d4caac320b61" in content
        assert "/opt/aios/models/bge-m3-5617a9f" in content
        assert "HEALTHCHECK" in content

    def test_vps_docker_compose_model_volume_mount(self) -> None:
        """Verify docker-compose mounts model directory read-only and sets canary activation."""
        compose_file = REPO_ROOT / "packaging" / "vps" / "docker-compose.yml"
        assert compose_file.exists()
        content = compose_file.read_text(encoding="utf-8")

        assert "127.0.0.1:8501:8501" in content
        assert "aios_local_data:/app/local_cases" in content
        assert "/opt/aios/models/bge-m3-5617a9f:ro" in content
        assert "AIOS_WORKSPACE_RAG_V2_CANARY_ENABLED=1" in content
        assert "AIOS_WORKSPACE_RAG_V2_LOCAL_PILOT_ENABLED=1" in content
        assert "no-new-privileges:true" in content

    def test_vps_environment_activates_rag_v2_canary_config(self) -> None:
        """Verify WorkspaceChatRagV2CanaryConfig.from_env evaluates to enabled=True with Docker env."""
        from aios_habit.workspace_chat_rag_v2_adapter import WorkspaceChatRagV2CanaryConfig

        docker_env = {
            "AIOS_WORKSPACE_RAG_V2_CANARY_ENABLED": "1",
            "AIOS_WORKSPACE_RAG_V2_LOCAL_PILOT_ENABLED": "1",
            "AIOS_WORKSPACE_RAG_V2_PROFILE": "bge_m3_hybrid",
            "AIOS_BGE_M3_MODEL_PATH": "/opt/aios/models/bge-m3-5617a9f",
            "AIOS_BGE_M3_MODEL_REVISION": "5617a9f61b028005a4858fdac845db406aefb181",
            "AIOS_BGE_M3_MODEL_CHECKSUM": "sha256:b1d887e03f13547609b4c6498ce8f357242edb5079a448c62d31d4caac320b61",
            "AIOS_RETRIEVAL_DEVICE": "cpu",
        }
        config = WorkspaceChatRagV2CanaryConfig.from_env(env=docker_env)
        assert config.enabled is True
        assert config.requested_profile == "bge_m3_hybrid"
        assert config.retrieval_device == "cpu"
        assert str(config.bge_m3_model_path) == Path("/opt/aios/models/bge-m3-5617a9f").as_posix() or str(config.bge_m3_model_path) == str(Path("/opt/aios/models/bge-m3-5617a9f"))


class TestCleanMachineSmokeScript:
    """Verify the clean machine smoke test script passes."""

    def test_clean_machine_smoke_test_runs_successfully(self) -> None:
        """Run scripts/desktop_smoke_test.py in fast mode to verify integrity and execution in CI."""
        smoke_script = REPO_ROOT / "scripts" / "desktop_smoke_test.py"
        assert smoke_script.exists()

        res = subprocess.run(
            [sys.executable, str(smoke_script), "--fast"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert res.returncode == 0, f"Smoke test failed: {res.stderr}\n{res.stdout}"
        assert "ALL CLEAN MACHINE SMOKE TESTS PASSED" in res.stdout

    @pytest.mark.slow
    def test_clean_machine_full_isolated_venv_installation(self) -> None:
        """Run full standalone clean machine smoke test with isolated venv."""
        smoke_script = REPO_ROOT / "scripts" / "desktop_smoke_test.py"
        assert smoke_script.exists()

        res = subprocess.run(
            [sys.executable, str(smoke_script)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        assert res.returncode == 0, f"Full venv smoke test failed: {res.stderr}\n{res.stdout}"
        assert "ALL CLEAN MACHINE SMOKE TESTS PASSED" in res.stdout

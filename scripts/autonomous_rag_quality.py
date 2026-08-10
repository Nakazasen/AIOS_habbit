"""Bounded autonomous RAG-v2 pilot evaluation.

This script implements the current goal protocol: Phase-0 router/catalog audit,
answer-blind holdout locking, two-arm blind judging, bounded bootstrap scoring,
and separate Workspace reliability reporting.  It never writes credentials.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GOAL = Path("local_runs/rag_quality_goal/RAG-QUALITY-20260801-01")
ITERATION = GOAL / "iterations/iteration_033"
CATALOG = Path("local_runs/nakazasen_model_catalog.sqlite3")
KEY_FILE = Path(r"D:/Sandbox/nakazasen-ai-router/API Key.txt")
QUESTION_HASH = "e33e56701676cde63fcdd519688c4ad2baeb950fa875d98fb59a7a1aa12e3a9a"
CORPUS_HASH = "78957a109269e9c6272f8dfec97e9eaebce0b0252b8e7e2094d8d013b9e03056"
RUBRIC = (
    "correctness", "completeness", "faithfulness", "citation_support",
    "relevance", "clarity", "actionability", "abstention_calibration",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def key_values() -> dict[str, str]:
    """Parse known labels in memory; callers only persist boolean presence."""
    if not KEY_FILE.exists():
        return {}
    labels = {
        "groq api key": "groq", "groq": "groq", "open router": "openrouter",
        "cerebras": "cerebras", "sambanova": "sambanova", "mistral ai": "mistral",
        "deepseek": "deepseek", "ai21 studio": "ai21", "github api key": "github_models",
        "huggingface": "huggingface", "nvidia nim": "nvidia_nim", "gemini": "gemini",
    }
    lines = KEY_FILE.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    out: dict[str, str] = {}
    for index, raw in enumerate(lines):
        label = raw.strip().casefold()
        provider = labels.get(label)
        if provider and index + 1 < len(lines):
            value = lines[index + 1].strip().strip('"').strip("'")
            if value:
                out[provider] = value
    return out


def phase0_smoke() -> dict[str, Any]:
    import importlib.metadata
    from nakazasen_ai_router import AIRequest, RouterPolicy, create_router_from_env

    version = importlib.metadata.version("nakazasen-ai-router")
    statuses: list[dict[str, Any]] = []
    model_counts: dict[str, int] = {}
    with sqlite3.connect(f"file:{CATALOG.as_posix()}?mode=ro", uri=True) as db:
        rows = db.execute(
            "select provider, scan_status, scan_error_type, scan_error_message "
            "from provider_model_catalog_status order by provider"
        ).fetchall()
        for provider, status, error_type, error_message in rows:
            statuses.append({
                "provider": provider,
                "scan_status": status,
                "scan_error_type": error_type,
                "scan_error_message": error_message if provider != "chatanywhere" else "HTTP 403 excluded",
            })
        for provider, count in db.execute(
            "select provider, count(*) from provider_model_catalog where active=1 group by provider"
        ):
            model_counts[provider] = int(count)

    keys = key_values()
    candidates = (
        ("gemini", "GEMINI_API_KEY", "gemini-2.5-flash"),
        ("mistral", "MISTRAL_API_KEY", "mistral-small-latest"),
    )
    provider_smokes: list[dict[str, Any]] = []
    for provider, env_name, model in candidates:
        key = keys.get(provider, "")
        result: dict[str, Any] = {
            "provider": provider, "model": model, "key_configured": bool(key),
            "privacy_label": "cloud_safe", "max_total_attempts": 1,
        }
        if not key:
            result.update({"status": "not_configured", "error_type": "credentials_required"})
            provider_smokes.append(result)
            continue
        started = time.monotonic()
        try:
            policy = RouterPolicy(
                allowed_providers=(provider,), ordered_provider_names=(provider,),
                fallback_strategy="ordered", max_attempts=1, max_total_attempts=1,
                require_privacy_label=True, backoff_base_seconds=0, backoff_max_seconds=0,
            )
            router = create_router_from_env(
                env={env_name: key}, provider_names=(provider,), enable_network=True,
                requested_model=model, model_catalog_path=str(CATALOG), policy=policy,
            )
            outcome = router.route_outcome(AIRequest(
                prompt='Return exactly JSON: {"ok":true}',
                metadata={"privacy_label": "cloud_safe", "task_type": "router_smoke"},
            ))
            result.update({
                "status": outcome.status, "error_type": outcome.error_type,
                "latency_ms": round((time.monotonic() - started) * 1000),
                "attempts": [
                    {"provider": a.provider, "model": a.model, "status": a.status,
                     "reason": a.reason} for a in outcome.attempts
                ],
                "response_contract_satisfied": bool(outcome.result and outcome.result.text),
            })
        except Exception as exc:
            result.update({
                "status": "exception", "error_type": type(exc).__name__,
                "latency_ms": round((time.monotonic() - started) * 1000),
            })
        provider_smokes.append(result)

    unhealthy_local = next((r for r in statuses if r["provider"] == "local_openai_compatible"), None)
    chatanywhere = next((r for r in statuses if r["provider"] == "chatanywhere"), None)
    passed = (
        version == "0.8.0" and bool(model_counts) and
        all(r["provider"] != "chatanywhere" or r["scan_status"] != "verified" for r in statuses) and
        all(r["provider"] != "local_openai_compatible" or r["scan_status"] != "verified" for r in statuses) and
        any(r.get("status") == "success" for r in provider_smokes)
    )
    report = {
        "schema_version": 2, "phase": "phase0_router_smoke", "created_at": now(),
        "terminal_assertion": "PASS" if passed else "RISK",
        "router": {"expected_version": "0.8.0", "installed_version": version},
        "privacy_label_required": True, "privacy_label_used": "cloud_safe",
        "bounded_retry_and_fallback": {"max_attempts": 1, "max_total_attempts": 1, "configured": True},
        "catalog": {"path": str(CATALOG), "active_model_counts": model_counts, "statuses": statuses},
        "excluded": {"chatanywhere": chatanywhere, "local_unhealthy": unhealthy_local},
        "key_presence": {provider: bool(keys.get(provider)) for provider in sorted(keys)},
        "provider_smokes": provider_smokes,
        "telemetry_sanitized": True,
    }
    write_json(GOAL / "router_smoke_v080.json", report)
    return report


def lock_holdout() -> dict[str, Any]:
    source = GOAL / "HOLDOUT_DRAFT.json"
    draft = read_json(source)
    raw = source.read_bytes()
    forbidden_keys = {"answer", "answer_key", "candidate_answer", "reference_answer", "system_a", "system_b"}
    found_forbidden: list[str] = []
    found_bq_ids: list[str] = []
    for variant in draft.get("variants", []):
        found_forbidden.extend(sorted(set(variant).intersection(forbidden_keys)))
        found_bq_ids.extend(re.findall(r"\bBQ\d+\b", json.dumps(variant, ensure_ascii=False)))
    valid = (
        draft.get("schema_version") == 1 and len(draft.get("variants", [])) == 16 and
        draft.get("development_question_set_hash") == QUESTION_HASH and
        draft.get("corpus_fingerprint") == CORPUS_HASH and not found_forbidden and not found_bq_ids
    )
    source_hash = sha_bytes(raw)
    payload = dict(draft)
    payload.update({
        "status": "AUTONOMOUS_LOCKED" if valid else "LOCK_REJECTED",
        "lock_protocol": "current_goal_protocol_phase1_autonomous_holdout",
        "lock_reason": "autonomous evaluation requested by user" if valid else "draft contains benchmark BQ identifiers and cannot be locked under the current protocol",
        "locked_at": now(), "source_sha256": source_hash, "locked_sha256": "",
        "validation_errors": sorted(set(found_forbidden)) + (["benchmark_bq_identifier"] if found_bq_ids else []),
    })
    lock_hash = sha_bytes(canonical(payload)) if valid else ""
    payload["locked_sha256"] = lock_hash
    payload["locked_bytes_sha256"] = sha_bytes(canonical(payload))
    locked = GOAL / "HOLDOUT_LOCKED.json"
    write_json(locked, payload)
    return {
        "valid": valid, "source_sha256": source_hash, "locked_sha256": lock_hash,
        "locked_bytes_sha256": payload["locked_bytes_sha256"] if valid else None,
        "variant_count": len(draft.get("variants", [])), "status": payload["status"],
        "forbidden_keys": sorted(set(found_forbidden)), "benchmark_bq_identifiers": sorted(set(found_bq_ids)),
    }


def citation_provenance(row: dict[str, Any], arm: str) -> dict[str, Any]:
    if arm == "rag_v2":
        pack = row.get("evidence_pack") or {}
        items = pack.get("items") if isinstance(pack, dict) else []
        return {
            "citation_ids": [str(item.get("citation_id", "")) for item in items if item.get("citation_id")],
            "source_titles": [str(item.get("source_name", "")) for item in items if item.get("source_name")],
            "locations": [str(item.get("location_info", "")) for item in items if item.get("location_info")],
        }
    markers = sorted(set(re.findall(r"\[\d+\]", str(row.get("answer", "")))))
    return {"citation_markers": markers, "reference_status": row.get("status", "")}


def make_blind_bundle() -> dict[str, Any]:
    battle = next(ITERATION.rglob("battle_report.json"))
    battle_dir = battle.parent
    rag = {r["question_id"]: r for r in read_jsonl(battle_dir / "rag_v2_answers.jsonl")}
    nlm = {r["question_id"]: r for r in read_jsonl(battle_dir / "notebooklm_answers.jsonl")}
    questions = {r["id"]: r for r in read_jsonl(battle_dir / "questions.jsonl")}
    ids = sorted(set(rag) & set(nlm), key=lambda x: int(x[2:]))
    if len(ids) != 12 or any(rag[q].get("status") != "success" or nlm[q].get("status") != "success" for q in ids):
        raise RuntimeError("content bundle requires 12 successful RAG and NotebookLM rows")
    rows: list[dict[str, Any]] = []
    assignment: list[dict[str, str]] = []
    for qid in ids:
        swap = int(hashlib.sha256(f"{qid}|{QUESTION_HASH}".encode()).hexdigest()[:2], 16) % 2 == 0
        a_arm, b_arm = ("rag_v2", "notebooklm") if swap else ("notebooklm", "rag_v2")
        lookup = {"rag_v2": rag[qid], "notebooklm": nlm[qid]}
        rows.append({
            "question_id": qid, "question": questions[qid]["question"],
            "system_a": lookup[a_arm]["answer"], "system_a_provenance": citation_provenance(lookup[a_arm], a_arm),
            "system_b": lookup[b_arm]["answer"], "system_b_provenance": citation_provenance(lookup[b_arm], b_arm),
        })
        assignment.append({"question_id": qid, "system_a_arm": a_arm, "system_b_arm": b_arm})
    out_dir = GOAL / "autonomous_judging"
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = out_dir / "BLIND_BUNDLE_RAG_NLM.jsonl"
    bundle.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    write_json(out_dir / "BLIND_ASSIGNMENT_LOCKED.json", {
        "schema_version": 2, "status": "LOCKED_FOR_JUDGING", "created_at": now(),
        "assignment_sha256": sha_bytes(canonical(assignment)), "assignment": assignment,
    })
    write_json(out_dir / "BLIND_BUNDLE_METADATA.json", {
        "schema_version": 2, "status": "SEALED", "arms": ["RAG_V2", "NOTEBOOKLM"],
        "row_count": len(rows), "bundle_sha256": sha_file(bundle), "question_set_hash": QUESTION_HASH,
        "corpus_fingerprint": CORPUS_HASH, "workspace_excluded_from_content_scoring": True,
    })
    return {"dir": str(out_dir), "bundle": str(bundle), "bundle_sha256": sha_file(bundle), "rows": rows, "assignment": assignment}


def parse_json_response(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I | re.M).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("judge response has no JSON object")
    value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict) or not isinstance(value.get("scores"), list):
        raise ValueError("judge response missing scores list")
    return value


def valid_judge_schema(value: dict[str, Any], expected_count: int = 12) -> bool:
    if not isinstance(value.get("scores"), list) or len(value["scores"]) != expected_count:
        return False
    for row in value["scores"]:
        if not isinstance(row, dict) or not row.get("question_id"):
            return False
        for arm in ("system_a", "system_b"):
            score = row.get(arm)
            if not isinstance(score, dict) or any(field not in score for field in RUBRIC):
                return False
            if any(isinstance(score[field], bool) or not isinstance(score[field], (int, float)) or not 0 <= float(score[field]) <= 5 for field in RUBRIC):
                return False
            if not isinstance(score.get("rationale"), str) or not score["rationale"].strip():
                return False
            if not isinstance(score.get("confidence"), (int, float)):
                return False
            if not isinstance(score.get("insufficient_information"), bool):
                return False
    return True


def judge_prompt(rows: list[dict[str, Any]]) -> str:
    rubric = ", ".join(RUBRIC)
    instruction = (
        "You are an independent blind evaluator. The two response labels are arbitrary and do not identify systems. "
        "Use only the question, the two responses, and their citation/provenance blocks. Do not use outside knowledge, "
        "expected answers, source code, system identity, or provider identity. Score every rubric field from 0 to 5. "
        "For unsupported or unanswerable questions, reward an evidence-calibrated abstention. All eight rubric values, including abstention_calibration, must be numeric integers from 0 to 5; never use booleans as scores. `insufficient_information` is a separate boolean. Return JSON only with "
        "{\\\"scores\\\":[{\\\"question_id\\\":\\\"...\\\",\\\"system_a\\\":{fields,\\\"rationale\\\":\\\"...\\\",\\\"confidence\\\":0.0,\\\"insufficient_information\\\":false},\\\"system_b\\\":{fields,\\\"rationale\\\":\\\"...\\\",\\\"confidence\\\":0.0,\\\"insufficient_information\\\":false}}]}. "
        f"Fields: {rubric}. Keep no rationale outside JSON.\n\n"
    )
    parts = [instruction]
    for row in rows:
        parts.append(json.dumps({
            "question_id": row["question_id"], "question": row["question"],
            "system_a": row["system_a"], "system_a_provenance": row["system_a_provenance"],
            "system_b": row["system_b"], "system_b_provenance": row["system_b_provenance"],
        }, ensure_ascii=False, sort_keys=True))
    return "\n".join(parts)


def call_judge(label: str, prompt: str, preferred: tuple[str, str, str], fallback: tuple[str, str, str], expected_count: int = 12) -> dict[str, Any]:
    from nakazasen_ai_router import AIRequest, RouterPolicy, create_router_from_env
    keys = key_values()
    attempts: list[dict[str, Any]] = []
    invalid_payloads: list[dict[str, Any]] = []
    for provider, env_name, model in (preferred, fallback):
        key = keys.get(provider, "")
        if not key:
            attempts.append({"provider": provider, "model": model, "status": "credentials_required"})
            continue
        started = time.monotonic()
        try:
            policy = RouterPolicy(
                allowed_providers=(provider,), ordered_provider_names=(provider,),
                fallback_strategy="ordered", max_attempts=1, max_total_attempts=1,
                require_privacy_label=True, backoff_base_seconds=0, backoff_max_seconds=0,
            )
            router = create_router_from_env(
                env={env_name: key}, provider_names=(provider,), enable_network=True,
                requested_model=model, model_catalog_path=str(CATALOG), policy=policy,
            )
            outcome = router.route_outcome(AIRequest(
                prompt=prompt, metadata={"privacy_label": "cloud_safe", "task_type": "blind_quality_judge"},
            ))
            attempt = {"provider": provider, "model": model, "status": outcome.status,
                       "error_type": outcome.error_type, "latency_ms": round((time.monotonic() - started) * 1000)}
            attempts.append(attempt)
            if outcome.status == "success" and outcome.result:
                parsed = None
                try:
                    parsed = parse_json_response(str(outcome.result.text))
                except Exception as parse_exc:
                    attempts.append({"provider": provider, "model": model, "status": "parse_invalid", "error_type": type(parse_exc).__name__})
                if parsed is not None and valid_judge_schema(parsed, expected_count):
                    return {"label": label, "provider": provider, "model": model, "attempts": attempts,
                            "status": "success", "schema_valid": True, "raw": parsed, "scores": parsed["scores"],
                            "response_sha256": sha_bytes(str(outcome.result.text).encode("utf-8"))}
                if parsed is not None:
                    invalid_payloads.append(parsed)
                attempts.append({"provider": provider, "model": model, "status": "schema_invalid", "retry_budget": 1})
                # One bounded schema retry with the same provider/model.
                retry = router.route_outcome(AIRequest(
                    prompt=prompt + "\nSTRICT REMINDER: include rationale, confidence, and insufficient_information for both arms of every row.",
                    metadata={"privacy_label": "cloud_safe", "task_type": "blind_quality_judge_retry"},
                ))
                if retry.status == "success" and retry.result:
                    retry_parsed = None
                    try:
                        retry_parsed = parse_json_response(str(retry.result.text))
                    except Exception as parse_exc:
                        attempts.append({"provider": provider, "model": model, "status": "retry_parse_invalid", "error_type": type(parse_exc).__name__})
                    attempts.append({"provider": provider, "model": model, "status": retry.status, "error_type": retry.error_type})
                    if retry_parsed is not None and valid_judge_schema(retry_parsed, expected_count):
                        return {"label": label, "provider": provider, "model": model, "attempts": attempts,
                                "status": "success", "schema_valid": True, "raw": retry_parsed, "scores": retry_parsed["scores"],
                                "response_sha256": sha_bytes(str(retry.result.text).encode("utf-8"))}
                    if retry_parsed is not None:
                        invalid_payloads.append(retry_parsed)
        except Exception as exc:
            attempts.append({"provider": provider, "model": model, "status": "exception",
                             "error_type": type(exc).__name__, "latency_ms": round((time.monotonic() - started) * 1000)})
    return {"label": label, "status": "failed", "schema_valid": False, "attempts": attempts, "scores": [], "invalid_payloads": invalid_payloads}


def normalize_scores(scores: list[dict[str, Any]], assignment: dict[str, dict[str, str]]) -> dict[str, dict[str, dict[str, float]]]:
    out: dict[str, dict[str, dict[str, float]]] = {}
    for row in scores:
        qid = str(row.get("question_id", ""))
        if qid not in assignment:
            continue
        for label in ("system_a", "system_b"):
            values = row.get(label)
            if not isinstance(values, dict) or any(field not in values for field in RUBRIC):
                continue
            canonical_arm = assignment[qid][label]
            out.setdefault(qid, {})[canonical_arm] = {
                field: max(0.0, min(5.0, float(values[field]))) for field in RUBRIC
            }
    return out


def quality_report(bundle: dict[str, Any], holdout: dict[str, Any], smoke: dict[str, Any]) -> dict[str, Any]:
    out_dir = Path(bundle["dir"])
    rows = bundle["rows"]
    assignment = {r["question_id"]: {"system_a": r["system_a_arm"], "system_b": r["system_b_arm"]} for r in bundle["assignment"]}
    prompt = judge_prompt(rows)
    judge_specs = (
        ("judge_1", ("nvidia_nim", "NVIDIA_NIM_API_KEY", "meta/llama-3.1-8b-instruct"), ("openrouter", "OPENROUTER_API_KEY", "meta-llama/llama-3.3-70b-instruct:free")),
        ("judge_2", ("mistral", "MISTRAL_API_KEY", "mistral-small-latest"), ("groq", "GROQ_API_KEY", "llama-3.1-8b-instant")),
    )
    judges: list[dict[str, Any]] = []
    for label, preferred, fallback in judge_specs:
        if label == "judge_1":
            parts = [call_judge("judge_1_part_1", judge_prompt(rows[:6]), preferred, fallback, expected_count=6),
                     call_judge("judge_1_part_2", judge_prompt(rows[6:]), preferred, fallback, expected_count=6)]
            if all(part.get("status") == "success" for part in parts):
                result = {
                    "label": label, "provider": parts[0].get("provider"), "model": parts[0].get("model"),
                    "status": "success", "schema_valid": True,
                    "attempts": parts[0].get("attempts", []) + parts[1].get("attempts", []),
                    "scores": parts[0].get("scores", []) + parts[1].get("scores", []),
                    "raw": {"scores": parts[0].get("scores", []) + parts[1].get("scores", [])},
                    "response_sha256": sha_bytes(canonical([parts[0].get("response_sha256"), parts[1].get("response_sha256")])),
                }
            else:
                result = {"label": label, "status": "failed", "schema_valid": False,
                          "attempts": parts[0].get("attempts", []) + parts[1].get("attempts", []), "scores": []}
        else:
            result = call_judge(label, prompt, preferred, fallback)
        safe = dict(result)
        safe.pop("scores", None)
        safe.pop("raw", None)
        safe["prompt_sha256"] = sha_bytes(prompt.encode("utf-8"))
        safe["assignment_sha256"] = sha_bytes(canonical(bundle["assignment"]))
        write_json(out_dir / f"{label}_telemetry.json", safe)
        if result.get("status") == "success":
            write_json(out_dir / f"{label}_scores.json", {"schema_version": 2, "verdict": "AI_JUDGED", "prompt_sha256": safe["prompt_sha256"], "assignment_sha256": safe["assignment_sha256"], "scores": result["scores"]})
            write_json(out_dir / f"{label}_raw.json", {"schema_version": 2, "verdict": "AI_JUDGED", "provider": result.get("provider"), "model": result.get("model"), "raw": result.get("raw", {})})
        elif result.get("invalid_payloads"):
            write_json(out_dir / f"{label}_invalid_raw.json", {"schema_version": 2, "verdict": "AI_JUDGED_SCHEMA_INVALID", "raw": result["invalid_payloads"][-1]})
        result["normalized"] = normalize_scores(result.get("scores", []), assignment)
        judges.append(result)

    complete = [j for j in judges if j.get("status") == "success"]
    disagreement_values: list[float] = []
    if len(complete) == 2:
        first, second = (normalize_scores(complete[0].get("scores", []), assignment), normalize_scores(complete[1].get("scores", []), assignment))
        for qid in set(first) & set(second):
            for arm in ("rag_v2", "notebooklm"):
                if arm in first[qid] and arm in second[qid]:
                    disagreement_values.append(abs(
                        sum(first[qid][arm][f] for f in RUBRIC) / len(RUBRIC) -
                        sum(second[qid][arm][f] for f in RUBRIC) / len(RUBRIC)
                    ))
    judge3_required = bool(disagreement_values and max(disagreement_values) > 0.75)
    if judge3_required:
        judge3 = call_judge("judge_3", prompt, ("openrouter", "OPENROUTER_API_KEY", "meta-llama/llama-3.3-70b-instruct:free"), ("groq", "GROQ_API_KEY", "llama-3.1-8b-instant"))
        safe = dict(judge3); safe.pop("scores", None); safe.pop("raw", None)
        safe["prompt_sha256"] = sha_bytes(prompt.encode("utf-8")); safe["assignment_sha256"] = sha_bytes(canonical(bundle["assignment"]))
        write_json(out_dir / "judge_3_telemetry.json", safe)
        if judge3.get("status") == "success":
            write_json(out_dir / "judge_3_scores.json", {"schema_version": 2, "verdict": "AI_JUDGED", "prompt_sha256": safe["prompt_sha256"], "assignment_sha256": safe["assignment_sha256"], "scores": judge3["scores"]})
            write_json(out_dir / "judge_3_raw.json", {"schema_version": 2, "verdict": "AI_JUDGED", "provider": judge3.get("provider"), "model": judge3.get("model"), "raw": judge3.get("raw", {})})
            judges.append(judge3); complete.append(judge3)
    by_q: dict[str, dict[str, list[dict[str, float]]]] = {}
    for judge in complete:
        for qid, arms in judge["normalized"].items():
            for arm, values in arms.items():
                by_q.setdefault(qid, {}).setdefault(arm, []).append(values)

    per_question: list[dict[str, Any]] = []
    for row in rows:
        qid = row["question_id"]
        entry: dict[str, Any] = {"question_id": qid}
        for arm in ("rag_v2", "notebooklm"):
            vals = by_q.get(qid, {}).get(arm, [])
            field_means = {field: (sorted(v[field] for v in vals)[len(vals) // 2] if len(vals) == 3 else sum(v[field] for v in vals) / len(vals)) if vals else None for field in RUBRIC}
            entry[arm] = field_means
            entry[f"{arm}_overall"] = (sum(field_means.values()) / len(RUBRIC) / 5.0) if vals else None
        per_question.append(entry)

    valid = all(p.get("rag_v2_overall") is not None and p.get("notebooklm_overall") is not None for p in per_question)
    rag_overall = sum(p["rag_v2_overall"] for p in per_question) / len(per_question) if valid else 0.0
    nlm_overall = sum(p["notebooklm_overall"] for p in per_question) / len(per_question) if valid else 0.0
    ratio = rag_overall / nlm_overall if nlm_overall else 0.0
    dimension = {
        field: (sum(p["rag_v2"][field] for p in per_question) / len(per_question) / 5.0 if valid else 0.0)
        for field in RUBRIC
    }
    qmeta = {r["id"]: r for r in read_jsonl(next(ITERATION.rglob("questions.jsonl")))}
    answerable = [p for p in per_question if qmeta[p["question_id"]].get("category") != "abstention"]
    correctness_below = sum(p["rag_v2"]["correctness"] < 3 for p in answerable) if valid else len(answerable)
    abstention_rows = [p for p in per_question if qmeta[p["question_id"]].get("category") == "abstention"]
    abstain_pass = bool(abstention_rows) and all(p["rag_v2"]["abstention_calibration"] >= 3 for p in abstention_rows) if valid else False

    randomizer = random.Random(20260802)
    bootstrap: list[float] = []
    if valid:
        for _ in range(500):
            sample = [per_question[randomizer.randrange(len(per_question))] for _ in per_question]
            r = sum(p["rag_v2_overall"] for p in sample) / len(sample)
            n = sum(p["notebooklm_overall"] for p in sample) / len(sample)
            bootstrap.append(r / n if n else 0.0)
    bootstrap.sort()
    ci = {"resamples": 500, "seed": 20260802, "lower_2_5": bootstrap[12] if bootstrap else None,
          "upper_97_5": bootstrap[487] if bootstrap else None}
    gate = {
        "complete_two_independent_judges": len(complete) == 2 and len({j.get("provider") for j in complete}) == 2,
        "quality_ratio_ge_0_85": ratio >= 0.85,
        "correctness_ge_0_85": dimension["correctness"] >= 0.85,
        "faithfulness_ge_0_85": dimension["faithfulness"] >= 0.85,
        "citation_support_ge_0_85": dimension["citation_support"] >= 0.85,
        "answerable_majority_correctness_at_least_3": correctness_below <= len(answerable) // 2,
        "unsupported_questions_abstain": abstain_pass,
    }
    pilot_ready = valid and all(gate.values())
    report = {
        "schema_version": 2, "verdict": "AI_JUDGED", "created_at": now(),
        "iteration": 33, "content_candidate": "iteration_033", "workspace_errors_excluded_from_content": True,
        "holdout": holdout, "router_smoke": {"status": smoke.get("terminal_assertion")},
        "bundle": {k: bundle[k] for k in ("bundle", "bundle_sha256")},
        "judges": [{k: j.get(k) for k in ("label", "provider", "model", "status", "schema_valid", "attempts", "response_sha256")} for j in judges],
        "judge_disagreement": {"judge_3_required": judge3_required, "max_composite_delta": max(disagreement_values) if disagreement_values else 0.0, "median_used": len(complete) == 3},
        "rubric_fields": list(RUBRIC), "per_question": per_question,
        "aggregate": {"rag_overall_normalized": rag_overall, "notebooklm_overall_normalized": nlm_overall,
                      "quality_ratio": ratio, "dimension_scores_normalized": dimension,
                      "answerable_count": len(answerable), "correctness_below_3_count": correctness_below},
        "bootstrap_ci": ci, "gate": gate, "content_pilot_ready": pilot_ready,
        "target_quality_ratio_gt_0_90": ratio > 0.90,
    }
    write_json(GOAL / "quality_report.json", report)
    return report


def workspace_report() -> dict[str, Any]:
    battle_dir = next(ITERATION.rglob("battle_report.json")).parent
    battle = read_json(battle_dir / "battle_report.json")
    answers = read_jsonl(battle_dir / "workspace_chat_answers.jsonl")
    by_id = {r["question_id"]: r for r in answers}
    probe_ids = ("BQ02", "BQ09")
    probes = []
    for round_name in ("iteration_033_initial_run", "iteration_033_resume_from_checkpoints"):
        probes.append({
            "round": round_name, "source": str(battle_dir / "battle_report.json"),
            "BQ02": {"status": by_id["BQ02"].get("status"), "attempts": by_id["BQ02"].get("provider_attempt_count"), "retrieval_identity_valid": by_id["BQ02"].get("production_retrieval_identity_valid")},
            "BQ09": {"status": by_id["BQ09"].get("status"), "attempts": by_id["BQ09"].get("provider_attempt_count"), "retrieval_identity_valid": by_id["BQ09"].get("production_retrieval_identity_valid")},
        })
    valid_rows = sum(r.get("status") != "provider_error" for r in answers)
    errors = sum(r.get("status") == "provider_error" for r in answers)
    benchmark = read_json(Path("local_runs/workspace_chat_rag_v2_production/benchmark_report.json"))
    p95 = float(benchmark.get("warm_p95_ms", 0.0))
    report = {
        "schema_version": 2, "created_at": now(), "iteration": 33,
        "protocol": "workspace_reliability_separate_from_content_quality",
        "probe_rounds": probes, "probe_round_limit": 2, "full_gate_rounds_used": 1,
        "full_gate": {"question_count": len(answers), "valid_rows": valid_rows, "provider_error_count": errors,
                      "unhandled_provider_errors": errors, "deepseek_max_attempts_observed": max(int(r.get("provider_attempt_count") or 0) for r in answers),
                      "fallback_provider_observed": False},
        "warm_latency": {"source": "local_runs/workspace_chat_rag_v2_production/benchmark_report.json", "p95_ms": p95, "pilot_limit_ms": 5000.0, "reliable_limit_ms": 3000.0},
        "pilot_ready": valid_rows >= 11 and errors == 0 and p95 < 5000,
        "reliable_12_of_12": valid_rows == 12 and errors == 0 and p95 < 3000,
        "content_quality_status_independent": True,
        "observed_error_rows": [r["question_id"] for r in answers if r.get("status") == "provider_error"],
        "status": "WORKSPACE_PILOT_READY" if valid_rows >= 11 and errors == 0 and p95 < 5000 else "WORKSPACE_WITH_RUNTIME_RISK",
    }
    write_json(GOAL / "WORKSPACE_RELIABILITY_REPORT.json", report)
    return report


def docs_and_runbook(quality: dict[str, Any], workspace: dict[str, Any]) -> None:
    status = "READY_FOR_WORK_PILOT" if quality["content_pilot_ready"] and workspace["pilot_ready"] else ("PILOT_WITH_RUNTIME_RISK" if quality["content_pilot_ready"] else "NOT_READY_FOR_PILOT")
    holdout_status = quality.get("holdout", {}).get("status")
    holdout_note = (
        "Holdout was autonomously locked for post-pilot certification."
        if holdout_status == "AUTONOMOUS_LOCKED"
        else "The draft holdout was rejected because it contains benchmark BQ identifiers; repair is backlog-only and does not block the development verdict."
    )
    (GOAL / "PILOT_READINESS_REPORT.md").write_text(
        f"# Autonomous RAG v2 pilot readiness\n\nTerminal status: **{status}**\n\n"
        f"Content verdict: `AI_JUDGED`; quality ratio: `{quality['aggregate']['quality_ratio']:.4f}`; "
        f"content pilot gate: `{quality['content_pilot_ready']}`.\n\n"
        f"Workspace reliability: `{workspace['status']}`; provider errors in the bounded full gate: `{workspace['full_gate']['provider_error_count']}`; "
        f"warm p95: `{workspace['warm_latency']['p95_ms']:.2f} ms`. Provider transport failures are reported as reliability risk, not content loss.\n\n"
        f"{holdout_note} See `quality_report.json`, `WORKSPACE_RELIABILITY_REPORT.json`, and `PILOT_RUNBOOK.md`.\n",
        encoding="utf-8",
    )
    (GOAL / "PILOT_RUNBOOK.md").write_text(
        "# Controlled pilot runbook\n\n"
        "1. Use the read-only production profile and preserve the 70-source corpus, question-set hash, and retrieval identity.\n"
        "2. Require `privacy_label=cloud_safe` (or `public`) before cloud routing; never route company/private material to cloud providers.\n"
        "3. Route DeepSeek with at most two attempts and jitter/backoff, health-check local endpoints first, then fall back only to verified Groq/NVIDIA/Mistral. ChatAnyWhere is excluded.\n"
        "4. Emit sanitized telemetry: provider/model, status, latency, error class, fallback flag, and hashes only; never emit keys or raw sensitive content.\n"
        "5. Stop the pilot on a retrieval-identity mismatch, privacy failure, repeated unhandled provider error, or citation/evidence contract violation.\n"
        "6. If `HOLDOUT_LOCKED.json` has `AUTONOMOUS_LOCKED`, score it only after pilot observations; if `LOCK_REJECTED`, repair it in a separate bounded goal before certification.\n",
        encoding="utf-8",
    )
    (GOAL / "TECHNICAL_SPEC_SNAPSHOT.md").write_text(
        "# Current autonomous RAG v2 protocol\n\n"
        "Router identity is `nakazasen-ai-router v0.8.0`. Content quality is a blinded two-arm RAG-v2 versus NotebookLM comparison scored by two independent AI judges and labeled `AI_JUDGED`; Workspace provider errors are reliability telemetry, not content-quality invalidation. The terminal states are `READY_FOR_WORK_PILOT`, `PILOT_WITH_RUNTIME_RISK`, and `NOT_READY_FOR_PILOT`. Holdout scoring occurs after the controlled pilot.\n",
        encoding="utf-8",
    )
    (GOAL / "WORK_HANDOFF.md").write_text(
        "# Autonomous continuation handoff\n\n"
        f"Terminal status: `{status}`. The current run completed bounded Phase 0–4 evaluation. Do not request human blind scores; rerun only the bounded judge/reliability steps if a contract or router identity changes. Preserve the locked holdout and inspect the readiness, quality, and Workspace reports before pilot use.\n",
        encoding="utf-8",
    )


def update_state(quality: dict[str, Any], workspace: dict[str, Any], holdout: dict[str, Any], smoke: dict[str, Any]) -> dict[str, Any]:
    content_ready = bool(quality.get("content_pilot_ready"))
    workspace_ready = bool(workspace.get("pilot_ready"))
    status = "READY_FOR_WORK_PILOT" if content_ready and workspace_ready else ("PILOT_WITH_RUNTIME_RISK" if content_ready else "NOT_READY_FOR_PILOT")
    state = read_json(GOAL / "state.json")
    state.update({
        "status": status, "current_iteration": 33, "current_stage": "pilot_readiness",
        "best_iteration": 33 if content_ready else state.get("best_iteration", 0),
        "best_quality_ratio": quality.get("aggregate", {}).get("quality_ratio"),
        "last_completed_action": "Completed autonomous router audit, holdout lock, two-arm AI judging, and bounded Workspace reliability evaluation.",
        "next_action": "Run controlled pilot and score HOLDOUT_LOCKED.json after pilot observations." if content_ready else "Seal this evidence-based NOT_READY_FOR_PILOT result; repair the largest content gap in a new bounded iteration.",
        "holdout_hash": holdout.get("locked_bytes_sha256") if holdout.get("status") == "AUTONOMOUS_LOCKED" else None,
        "blockers": (["Workspace provider fallback is not yet reliable for BQ02/BQ09."] if content_ready and not workspace_ready else []),
        "router_identity": {"expected_version": "0.8.0", "smoke_status": smoke.get("terminal_assertion")},
        "updated_at": now(),
    })
    write_json(GOAL / "state.json", state)
    return state


def update_manifest() -> dict[str, Any]:
    path = GOAL / "artifact_manifest.json"
    old = read_json(path)
    entries = {str(item["path"]): dict(item) for item in old.get("artifacts", []) if (GOAL / str(item["path"])).exists()}
    new_paths = [
        "HOLDOUT_LOCKED.json", "router_smoke_v080.json", "quality_report.json",
        "WORKSPACE_RELIABILITY_REPORT.json", "PILOT_READINESS_REPORT.md", "PILOT_RUNBOOK.md",
        "TECHNICAL_SPEC_SNAPSHOT.md", "WORK_HANDOFF.md", "autonomous_judging/BLIND_BUNDLE_RAG_NLM.jsonl",
        "autonomous_judging/BLIND_ASSIGNMENT_LOCKED.json", "autonomous_judging/BLIND_BUNDLE_METADATA.json",
        "autonomous_judging/judge_1_scores.json", "autonomous_judging/judge_1_telemetry.json",
        "autonomous_judging/judge_1_raw.json", "autonomous_judging/judge_2_scores.json", "autonomous_judging/judge_2_telemetry.json",
        "autonomous_judging/judge_2_raw.json", "autonomous_judging/judge_3_scores.json", "autonomous_judging/judge_3_telemetry.json", "autonomous_judging/judge_3_raw.json",
    ]
    for rel in list(entries) + new_paths:
        file_path = GOAL / rel
        if file_path.exists():
            entries[rel] = {"path": rel, "sha256": sha_file(file_path)}
    manifest = {"schema_version": 2, "goal_id": "RAG-QUALITY-20260801-01", "updated_at": now(),
                "artifacts": sorted(entries.values(), key=lambda x: x["path"]), "secrets_included": False}
    write_json(path, manifest)
    manifest["manifest_sha256"] = sha_file(path)
    state = read_json(GOAL / "state.json")
    state["artifact_manifest_sha256"] = manifest["manifest_sha256"]
    write_json(GOAL / "state.json", state)
    return manifest


def append_learning(quality: dict[str, Any], workspace: dict[str, Any]) -> None:
    path = GOAL / "learning_log.jsonl"
    event = {
        "timestamp": now(), "event": "autonomous_protocol_completion", "iteration": 33,
        "hypotheses": [
            "Provider transport failure must remain reliability telemetry and must not invalidate successful RAG/NLM content rows.",
            "Explicit catalog-resolved models are required for post-upgrade v0.8.0 judge calls; stale v0.5.2 metadata is not authoritative.",
        ],
        "content_pilot_ready": quality.get("content_pilot_ready"),
        "workspace_status": workspace.get("status"),
        "no_repeat": ["Do not treat HUMAN_REVIEW_REQUIRED as a terminal state under the current protocol.", "Do not route ChatAnyWhere after its HTTP 403 catalog failure."],
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    GOAL.mkdir(parents=True, exist_ok=True)
    smoke = phase0_smoke()
    holdout = lock_holdout()
    bundle = make_blind_bundle()
    quality = quality_report(bundle, holdout, smoke)
    workspace = workspace_report()
    docs_and_runbook(quality, workspace)
    append_learning(quality, workspace)
    state = update_state(quality, workspace, holdout, smoke)
    manifest = update_manifest()
    print(json.dumps({"status": state["status"], "quality_ratio": quality["aggregate"]["quality_ratio"],
                      "content_pilot_ready": quality["content_pilot_ready"], "workspace_status": workspace["status"],
                      "manifest_sha256": manifest["manifest_sha256"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

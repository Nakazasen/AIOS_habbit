from __future__ import annotations
import sqlite3
from pathlib import Path
import pytest
from aios_habit.rag_v2.ingestion_jobs import IngestionJobError, IngestionJobIdentity, IngestionJobStore

class Clock:
    def __init__(self): self.now=1000.0
    def __call__(self): return self.now

def identity():
    return IngestionJobIdentity("corpus-a","bge-m3@1","chunk-v2","rag-v2","cloud_safe")
def manifest():
    return [{"unit_id":"doc-1","sha256":"a"},{"unit_id":"doc-2","sha256":"b"}]

def test_submit_is_idempotent_and_rejects_manifest_drift(tmp_path: Path):
    store=IngestionJobStore(tmp_path/"jobs.sqlite")
    first,created=store.submit(identity(),manifest()); second,created_again=store.submit(identity(),manifest())
    assert created is True and created_again is False and first.job_id==second.job_id
    with pytest.raises(IngestionJobError,match="drifted"):
        store.submit(identity(),[{"unit_id":"other"}])

def test_expired_lease_resumes_without_repeating_checkpoint(tmp_path: Path):
    clock=Clock(); store=IngestionJobStore(tmp_path/"jobs.sqlite",clock=clock); job,_=store.submit(identity(),manifest())
    claimed=store.claim("worker-a",lease_seconds=10); assert claimed is not None
    _,token=claimed; store.checkpoint(job.job_id,token,unit_id="doc-1",ordinal=0,payload={"chunks":3})
    assert store.claim("worker-b") is None
    clock.now+=11
    reclaimed=store.claim("worker-b",lease_seconds=10); assert reclaimed is not None
    resumed,new_token=reclaimed
    assert resumed.attempt_count==2 and resumed.completed_unit_count==1
    assert store.completed_unit_ids(job.job_id)=={"doc-1"}
    with pytest.raises(IngestionJobError,match="Lease"):
        store.checkpoint(job.job_id,token,unit_id="doc-2",ordinal=1,payload={"chunks":1})
    store.checkpoint(job.job_id,new_token,unit_id="doc-2",ordinal=1,payload={"chunks":1})

def test_retry_waits_then_reclaims_and_state_machine_reaches_ready(tmp_path: Path):
    clock=Clock(); store=IngestionJobStore(tmp_path/"jobs.sqlite",clock=clock); job,_=store.submit(identity(),manifest())
    _,token=store.claim("cpu",lease_seconds=20)
    waiting=store.retry(job.job_id,token,error_code="cuda_unavailable",delay_seconds=30,capacity_wait=True)
    assert waiting.status=="WAITING_FOR_CAPACITY" and store.claim("gpu") is None
    clock.now+=31; _,token=store.claim("gpu",lease_seconds=60)
    assert store.transition(job.job_id,token,"EMBEDDING").status=="EMBEDDING"
    assert store.transition(job.job_id,token,"VERIFYING").status=="VERIFYING"
    assert store.transition(job.job_id,token,"DEPLOYING").status=="DEPLOYING"
    ready=store.transition(job.job_id,token,"READY")
    assert ready.status=="READY" and ready.lease_owner=="" and store.claim("other") is None

def test_checkpoint_tampering_is_detected(tmp_path: Path):
    store=IngestionJobStore(tmp_path/"jobs.sqlite"); job,_=store.submit(identity(),manifest()); _,token=store.claim("worker")
    store.checkpoint(job.job_id,token,unit_id="doc-1",ordinal=0,payload={"chunks":3})
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE ingestion_checkpoints SET payload_json='{}'")
    with pytest.raises(IngestionJobError,match="hash mismatch"):
        store.completed_unit_ids(job.job_id)

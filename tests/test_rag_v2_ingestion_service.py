from pathlib import Path
from aios_habit.rag_v2.ingestion_jobs import IngestionJobIdentity,IngestionJobStore
from aios_habit.rag_v2.ingestion_service import DirectoryJobWatcher,IngestionService
def identity(fp): return IngestionJobIdentity(fp,"model","chunk","schema","cloud_safe")
def test_watcher_debounces_and_submission_is_idempotent(tmp_path:Path):
    source=tmp_path/"sources"; source.mkdir(); (source/"a.txt").write_text("one"); store=IngestionJobStore(tmp_path/"jobs.sqlite"); watcher=DirectoryJobWatcher(source,store,identity,debounce_seconds=2)
    assert watcher.scan(now=1) is None; job=watcher.scan(now=3); assert job is not None; assert watcher.scan(now=4).job_id==job.job_id
    (source/"a.txt").write_text("two"); assert watcher.scan(now=5) is None; assert watcher.scan(now=7).job_id!=job.job_id
def test_service_claims_and_finishes_job(tmp_path:Path):
    store=IngestionJobStore(tmp_path/"jobs.sqlite"); job,_=store.submit(identity("fp"),[{"unit_id":"a"}])
    def handler(claimed,token):
        store.transition(claimed.job_id,token,"EMBEDDING"); store.checkpoint(claimed.job_id,token,unit_id="a",ordinal=0,payload={"ok":True}); store.transition(claimed.job_id,token,"VERIFYING"); store.transition(claimed.job_id,token,"DEPLOYING"); store.transition(claimed.job_id,token,"READY")
    service=IngestionService(store,handler); assert service.run_once() is True; assert store.get(job.job_id).status=="READY"; assert service.run_once() is False

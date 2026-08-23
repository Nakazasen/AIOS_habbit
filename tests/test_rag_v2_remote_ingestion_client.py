from __future__ import annotations
import hashlib, threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from aios_habit.rag_v2.remote_ingestion_client import RemoteIngestionClient
class Handler(BaseHTTPRequestHandler):
    uploaded=bytearray(); download=b"portable-bundle"
    def log_message(self,*args): pass
    def do_POST(self):
        self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Connection","close"); self.end_headers(); self.wfile.write(b'{"job_id":"job-1","status":"QUEUED"}')
    def do_GET(self):
        if self.path.endswith("/bundle"):
            start=int(self.headers.get("Range","bytes=0-").split("=")[1].split("-")[0]); body=self.download[start:]; self.send_response(206); self.send_header("Connection","close"); self.end_headers(); self.wfile.write(body)
        else:
            self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Connection","close"); self.end_headers(); self.wfile.write(b'{"job_id":"job-1","status":"READY"}')
    def do_PATCH(self):
        size=int(self.headers["Content-Length"]); block=self.rfile.read(size); assert hashlib.sha256(block).hexdigest()==self.headers["Chunk-SHA256"]
        offset=int(self.headers["Upload-Offset"]); assert offset==len(self.uploaded); self.uploaded.extend(block)
        self.send_response(204); self.send_header("Upload-Offset",str(len(self.uploaded))); self.send_header("Connection","close"); self.end_headers()
def test_remote_client_resumes_upload_and_download(tmp_path:Path):
    Handler.uploaded=bytearray(); server=ThreadingHTTPServer(("127.0.0.1",0),Handler); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    try:
        client=RemoteIngestionClient(f"http://127.0.0.1:{server.server_port}",lambda:"secret",chunk_size=4)
        source=tmp_path/"source.bin"; source.write_bytes(b"abcdefghij")
        Handler.uploaded.extend(b"abcd"); assert client.upload_file("job-1",source,start_offset=4)==10; assert bytes(Handler.uploaded)==source.read_bytes()
        destination=tmp_path/"bundle.bin"; destination.write_bytes(Handler.download[:5]); digest=hashlib.sha256(Handler.download).hexdigest(); assert client.download_bundle("job-1",destination,expected_sha256=digest).read_bytes()==Handler.download
        assert client.submit(idempotency_key="k",identity={"schema":"v2"},total_size=10,sha256="x")["job_id"]=="job-1"; assert client.status("job-1")["status"]=="READY"
    finally: server.shutdown(); server.server_close()

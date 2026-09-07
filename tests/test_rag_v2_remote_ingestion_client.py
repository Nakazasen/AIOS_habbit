from __future__ import annotations
import hashlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Mapping

from aios_habit.rag_v2.remote_ingestion_client import RemoteIngestionClient


class Handler(BaseHTTPRequestHandler):
    uploaded = bytearray()
    download = b"portable-bundle"

    def log_message(self, format: str, *args: object) -> None:
        return None

    def _read_request_body(self) -> bytes:
        content_length = int(self.headers.get("Content-Length", "0"))
        return self.rfile.read(content_length)

    def _send_response(
        self,
        status: int,
        body: bytes = b"",
        *,
        content_type: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        if content_type is not None:
            self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if body:
            self.wfile.write(body)
            self.wfile.flush()

    def do_POST(self) -> None:
        self._read_request_body()
        self._send_response(
            200,
            b'{"job_id":"job-1","status":"QUEUED"}',
            content_type="application/json",
        )

    def do_GET(self) -> None:
        if self.path.endswith("/bundle"):
            start = int(self.headers.get("Range", "bytes=0-").split("=")[1].split("-")[0])
            self._send_response(206, self.download[start:])
            return
        self._send_response(
            200,
            b'{"job_id":"job-1","status":"READY"}',
            content_type="application/json",
        )

    def do_PATCH(self) -> None:
        block = self._read_request_body()
        assert hashlib.sha256(block).hexdigest() == self.headers["Chunk-SHA256"]
        offset = int(self.headers["Upload-Offset"])
        assert offset == len(self.uploaded)
        self.uploaded.extend(block)
        self._send_response(204, headers={"Upload-Offset": str(len(self.uploaded))})


def test_remote_client_resumes_upload_and_download(tmp_path: Path) -> None:
    Handler.uploaded = bytearray()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = RemoteIngestionClient(
            f"http://127.0.0.1:{server.server_port}",
            lambda: "secret",
            chunk_size=4,
        )
        source = tmp_path / "source.bin"
        source.write_bytes(b"abcdefghij")
        Handler.uploaded.extend(b"abcd")
        assert client.upload_file("job-1", source, start_offset=4) == 10
        assert bytes(Handler.uploaded) == source.read_bytes()

        destination = tmp_path / "bundle.bin"
        destination.write_bytes(Handler.download[:5])
        digest = hashlib.sha256(Handler.download).hexdigest()
        downloaded = client.download_bundle(
            "job-1",
            destination,
            expected_sha256=digest,
        )
        assert downloaded.read_bytes() == Handler.download

        submitted = client.submit(
            idempotency_key="k",
            identity={"schema": "v2"},
            total_size=10,
            sha256="x",
        )
        assert submitted["job_id"] == "job-1"
        assert client.status("job-1")["status"] == "READY"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

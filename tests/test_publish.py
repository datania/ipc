"""Exercise make publish with the locked CLI and a local Hub API stand-in."""

import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOKEN = "hf_test_only_$literal_'quotes'"
FILES = {
    "README.md": b"---\nlicense: cc-by-4.0\n---\n# Test dataset\n",
    "datapackage.yaml": b"name: ipc\n",
    "ipc.csv": b"period;value\n2026M01;100\n",
}


class HubHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        self.server.requests.append((self.path, self.headers.get("Authorization"), body))
        status = 200
        if self.path == "/api/repos/create":
            response = {"url": f"{self.server.endpoint}/datasets/datania/ipc"}
        elif self.path == "/api/validate-yaml":
            response = {"errors": [], "warnings": []}
        elif self.path == "/api/datasets/datania/ipc/preupload/main":
            response = {"files": [
                {"path": file["path"], "uploadMode": "regular", "shouldIgnore": False}
                for file in json.loads(body)["files"]
            ]}
        elif self.path == "/api/datasets/datania/ipc/commit/main":
            if self.server.reject_commit:
                status, response = 403, {"error": "Test upload forbidden"}
            else:
                response = {
                    "commitUrl": f"{self.server.endpoint}/datasets/datania/ipc/commit/" + "a" * 40,
                    "commitOid": "a" * 40,
                }
        else:
            status, response = 404, {"error": "Unexpected test request"}
        encoded = json.dumps(response).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class PublishTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.workdir = Path(self.directory.name)
        for filename in ("Makefile", "pyproject.toml", "uv.lock", ".python-version"):
            shutil.copy(ROOT / filename, self.workdir / filename)
        (self.workdir / "dataset").mkdir()
        for filename, data in FILES.items():
            (self.workdir / "dataset" / filename).write_bytes(data)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), HubHandler)
        self.server.endpoint = f"http://127.0.0.1:{self.server.server_port}"
        self.server.requests = []
        self.server.reject_commit = False
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.env = os.environ.copy()
        self.env.pop("VIRTUAL_ENV", None)
        self.env.update({
            "HUGGINGFACE_TOKEN": TOKEN,
            "HF_TOKEN": "unused-other-token",
            "HF_ENDPOINT": self.server.endpoint,
            "HF_HOME": str(self.workdir / "hf-home"),
            "HF_HUB_DISABLE_UPDATE_CHECK": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "UV_OFFLINE": "1",
            "NO_PROXY": "127.0.0.1",
        })

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def make(self, *args):
        result = subprocess.run(
            ["make", *args], cwd=self.workdir, env=self.env,
            capture_output=True, text=True, timeout=30,
        )
        self.assertNotIn(TOKEN, result.stdout + result.stderr)
        return result

    def test_upload_preserves_destination_and_contents(self):
        result = self.make("publish")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.server.requests)
        for _, authorization, _ in self.server.requests:
            self.assertEqual(authorization, f"Bearer {TOKEN}")
        commits = [body for path, _, body in self.server.requests if "/commit/" in path]
        self.assertEqual(len(commits), 1)
        files = {}
        for line in commits[0].splitlines():
            item = json.loads(line)
            if item["key"] == "file":
                files[item["value"]["path"]] = base64.b64decode(item["value"]["content"])
        self.assertEqual(files, FILES)
        dry_run = self.make("-n", "publish")
        self.assertEqual(dry_run.returncode, 0)
        self.assertNotIn("--token", dry_run.stdout)

    def test_upload_errors_fail_make(self):
        self.server.reject_commit = True
        result = self.make("publish")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("403", result.stderr)
        self.assertTrue(any("/commit/" in path for path, _, _ in self.server.requests))

    def test_missing_token_stops_before_upload(self):
        self.env.pop("HUGGINGFACE_TOKEN")
        result = self.make("publish")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HUGGINGFACE_TOKEN is required", result.stderr)
        self.assertEqual(self.server.requests, [])

    def test_cli_check_needs_no_credentials_or_upload(self):
        self.env.pop("HUGGINGFACE_TOKEN")
        result = self.make("publish-check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.server.requests, [])


if __name__ == "__main__":
    unittest.main()

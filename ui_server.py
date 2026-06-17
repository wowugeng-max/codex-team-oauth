#!/usr/bin/env python3
"""Local web UI for configuring and running codex_team_oauth.py."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from run_config import get_run_count


PROJECT_DIR = Path(__file__).resolve().parent
STATIC_DIR = PROJECT_DIR / "ui_static"

CONFIG_FIELDS = [
    "MAIL_PROVIDER",
    "RUN_COUNT",
    "CLOUDMAIL_API_BASE",
    "CLOUDMAIL_ADMIN_EMAIL",
    "CLOUDMAIL_ADMIN_PASSWORD",
    "CLOUDMAIL_DOMAIN_SUFFIX",
    "CLOUDMAIL_ROLE_NAME",
    "CLOUDMAIL_PROXY",
    "TEST_EMAIL",
    "TEST_PASSWORD",
    "TEST_INBOX_API",
]

DEFAULT_CONFIG = {
    "MAIL_PROVIDER": "cloudmail",
    "RUN_COUNT": "1",
    "CLOUDMAIL_API_BASE": "",
    "CLOUDMAIL_ADMIN_EMAIL": "",
    "CLOUDMAIL_ADMIN_PASSWORD": "",
    "CLOUDMAIL_DOMAIN_SUFFIX": "",
    "CLOUDMAIL_ROLE_NAME": "",
    "CLOUDMAIL_PROXY": "",
    "TEST_EMAIL": "",
    "TEST_PASSWORD": "",
    "TEST_INBOX_API": "",
}


def _parse_env_text(text: str) -> dict[str, str]:
    values = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return _parse_env_text(path.read_text(encoding="utf-8"))


def _clean_env_value(value) -> str:
    return str(value or "").replace("\n", " ").replace("\r", " ").strip()


class EnvConfigStore:
    def __init__(self, project_dir: Path = PROJECT_DIR):
        self.project_dir = Path(project_dir)
        self.env_path = self.project_dir / ".env"
        self.example_path = self.project_dir / ".env.example"

    def load_config(self) -> dict[str, str]:
        config = dict(DEFAULT_CONFIG)
        for source in (_read_env(self.example_path), _read_env(self.env_path)):
            for key, value in source.items():
                if key in CONFIG_FIELDS:
                    config[key] = value
        return config

    def save_config(self, config: dict[str, str]) -> None:
        merged = self.load_config()
        for key in CONFIG_FIELDS:
            if key in config:
                merged[key] = _clean_env_value(config[key])

        lines = [
            "MAIL_PROVIDER=" + merged["MAIL_PROVIDER"],
            "RUN_COUNT=" + merged["RUN_COUNT"],
            "CLOUDMAIL_API_BASE=" + merged["CLOUDMAIL_API_BASE"],
            "CLOUDMAIL_ADMIN_EMAIL=" + merged["CLOUDMAIL_ADMIN_EMAIL"],
            "CLOUDMAIL_ADMIN_PASSWORD=" + merged["CLOUDMAIL_ADMIN_PASSWORD"],
            "CLOUDMAIL_DOMAIN_SUFFIX=" + merged["CLOUDMAIL_DOMAIN_SUFFIX"],
            "CLOUDMAIL_ROLE_NAME=" + merged["CLOUDMAIL_ROLE_NAME"],
            "CLOUDMAIL_PROXY=" + merged["CLOUDMAIL_PROXY"],
            "",
            "# Legacy inbuck provider. Used only when MAIL_PROVIDER=inbuck.",
            "TEST_EMAIL=" + merged["TEST_EMAIL"],
            "TEST_PASSWORD=" + merged["TEST_PASSWORD"],
            "TEST_INBOX_API=" + merged["TEST_INBOX_API"],
            "",
        ]
        self.env_path.write_text("\n".join(lines), encoding="utf-8")


class RunController:
    def __init__(self, project_dir: Path = PROJECT_DIR, popen_factory=None):
        self.project_dir = Path(project_dir)
        self.popen_factory = popen_factory or subprocess.Popen
        self.lock = threading.RLock()
        self.process = None
        self.log_lines: list[str] = []
        self.started_at = None
        self.stopped_at = None
        self.exit_code = None

    def append_log(self, text: str) -> None:
        with self.lock:
            self.log_lines.append(str(text))
            if len(self.log_lines) > 5000:
                self.log_lines = self.log_lines[-5000:]

    def reset_log(self) -> None:
        with self.lock:
            self.log_lines = []

    def _is_running_locked(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def _refresh_exit_locked(self) -> None:
        if self.process is None:
            return
        code = self.process.poll()
        if code is None:
            return
        if self.exit_code is None:
            self.exit_code = code
            self.stopped_at = time.time()

    def status(self) -> dict[str, object]:
        with self.lock:
            self._refresh_exit_locked()
            running = self._is_running_locked()
            return {
                "running": running,
                "exit_code": None if running else self.exit_code,
                "started_at": self.started_at,
                "stopped_at": self.stopped_at,
                "log": "".join(self.log_lines),
            }

    def start(self, config: dict[str, str]) -> None:
        run_count = get_run_count(config)
        with self.lock:
            self._refresh_exit_locked()
            if self._is_running_locked():
                raise RuntimeError("process is already running")

            env = os.environ.copy()
            for key in CONFIG_FIELDS:
                if key in config:
                    env[key] = _clean_env_value(config[key])
            env["PYTHONUNBUFFERED"] = "1"

            command = [sys.executable, "-u", "codex_team_oauth.py"]
            kwargs = {
                "cwd": str(self.project_dir),
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "text": True,
                "bufsize": 1,
                "env": env,
            }
            if os.name != "nt":
                kwargs["start_new_session"] = True

            self.process = self.popen_factory(command, **kwargs)
            self.started_at = time.time()
            self.stopped_at = None
            self.exit_code = None
            self.append_log("Starting codex_team_oauth.py with RUN_COUNT=" + str(run_count) + "\n")

            reader = threading.Thread(target=self._read_process_output, args=(self.process,), daemon=True)
            reader.start()

    def _read_process_output(self, process) -> None:
        stdout = getattr(process, "stdout", None)
        if stdout is None:
            return
        for line in stdout:
            self.append_log(line)

    def stop(self) -> bool:
        with self.lock:
            if not self._is_running_locked():
                return False
            process = self.process

        try:
            if os.name != "nt" and getattr(process, "pid", None):
                os.killpg(process.pid, signal.SIGTERM)
            else:
                process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            if os.name != "nt" and getattr(process, "pid", None):
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait(timeout=5)

        with self.lock:
            self.exit_code = process.poll()
            self.stopped_at = time.time()
            self.append_log("Process stopped by UI.\n")
        return True


class UIRequestHandler(SimpleHTTPRequestHandler):
    config_store: EnvConfigStore = EnvConfigStore()
    run_controller: RunController = RunController()

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, format, *args):  # noqa: A002
        return

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/config":
            self._send_json({"config": self.config_store.load_config()})
            return
        if parsed.path == "/api/status":
            self._send_json(self.run_controller.status())
            return
        if parsed.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/config":
                payload = self._read_json()
                config = payload.get("config", payload)
                self.config_store.save_config(config)
                self._send_json({"ok": True, "config": self.config_store.load_config()})
                return
            if parsed.path == "/api/run":
                payload = self._read_json()
                config = self.config_store.load_config()
                config.update(payload.get("config", {}))
                if "run_count" in payload:
                    config["RUN_COUNT"] = str(payload["run_count"])
                self.config_store.save_config(config)
                self.run_controller.start(self.config_store.load_config())
                self._send_json({"ok": True, "status": self.run_controller.status()})
                return
            if parsed.path == "/api/stop":
                stopped = self.run_controller.stop()
                self._send_json({"ok": True, "stopped": stopped, "status": self.run_controller.status()})
                return
            if parsed.path == "/api/log/reset":
                self.run_controller.reset_log()
                self._send_json({"ok": True, "status": self.run_controller.status()})
                return
        except ValueError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=400)
            return
        except RuntimeError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=409)
            return
        self.send_error(404)

    def translate_path(self, path):
        parsed_path = unquote(urlparse(path).path)
        if parsed_path == "/":
            parsed_path = "/index.html"
        return str(STATIC_DIR / parsed_path.lstrip("/"))

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        if not raw:
            return {}
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    def _send_json(self, payload: dict, status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def create_server(host: str, port: int, project_dir: Path = PROJECT_DIR) -> ThreadingHTTPServer:
    UIRequestHandler.config_store = EnvConfigStore(project_dir)
    UIRequestHandler.run_controller = RunController(project_dir)
    return ThreadingHTTPServer((host, port), UIRequestHandler)


def main() -> int:
    parser = argparse.ArgumentParser(description="Start the local Codex Team OAuth UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = create_server(args.host, args.port)
    url = "http://" + args.host + ":" + str(args.port)
    print("UI running at " + url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping UI server")
    finally:
        UIRequestHandler.run_controller.stop()
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

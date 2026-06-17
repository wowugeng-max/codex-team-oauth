import io
import sys
import tempfile
import time
import unittest
from pathlib import Path

import ui_server


class FakeProcess:
    def __init__(self, output="ready\n"):
        self.stdout = io.StringIO(output)
        self.returncode = None
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        if self.returncode is None:
            self.returncode = 0
        return self.returncode


class UIConfigStoreTest(unittest.TestCase):
    def test_load_config_merges_example_defaults_and_env_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / ".env.example").write_text(
                "MAIL_PROVIDER=cloudmail\n"
                "RUN_COUNT=1\n"
                "CLOUDMAIL_API_BASE=https://example.invalid\n"
                "CLOUDMAIL_ADMIN_EMAIL=admin@example.com\n",
                encoding="utf-8",
            )
            (project_dir / ".env").write_text(
                "RUN_COUNT=4\n"
                "CLOUDMAIL_ADMIN_EMAIL=real-admin@example.com\n",
                encoding="utf-8",
            )

            store = ui_server.EnvConfigStore(project_dir)
            config = store.load_config()

        self.assertEqual(config["MAIL_PROVIDER"], "cloudmail")
        self.assertEqual(config["RUN_COUNT"], "4")
        self.assertEqual(config["CLOUDMAIL_API_BASE"], "https://example.invalid")
        self.assertEqual(config["CLOUDMAIL_ADMIN_EMAIL"], "real-admin@example.com")

    def test_save_config_writes_known_fields_without_unknown_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            store = ui_server.EnvConfigStore(project_dir)

            store.save_config(
                {
                    "MAIL_PROVIDER": "cloudmail",
                    "RUN_COUNT": "2",
                    "CLOUDMAIL_DOMAIN_SUFFIX": "mx.example.com",
                    "UNKNOWN_SECRET": "do-not-save",
                }
            )

            saved = (project_dir / ".env").read_text(encoding="utf-8")

        self.assertIn("MAIL_PROVIDER=cloudmail\n", saved)
        self.assertIn("RUN_COUNT=2\n", saved)
        self.assertIn("CLOUDMAIL_DOMAIN_SUFFIX=mx.example.com\n", saved)
        self.assertNotIn("UNKNOWN_SECRET", saved)


class UIRunControllerTest(unittest.TestCase):
    def test_start_launches_python_script_with_configured_run_count(self):
        calls = []

        def fake_popen(args, **kwargs):
            calls.append((args, kwargs))
            return FakeProcess("line one\n")

        with tempfile.TemporaryDirectory() as tmpdir:
            controller = ui_server.RunController(Path(tmpdir), popen_factory=fake_popen)
            controller.start({"MAIL_PROVIDER": "cloudmail", "RUN_COUNT": "3"})

            time.sleep(0.01)
            status = controller.status()

        self.assertEqual(calls[0][0], [sys.executable, "-u", "codex_team_oauth.py"])
        self.assertEqual(calls[0][1]["cwd"], str(Path(tmpdir)))
        self.assertEqual(calls[0][1]["env"]["RUN_COUNT"], "3")
        self.assertEqual(calls[0][1]["env"]["MAIL_PROVIDER"], "cloudmail")
        self.assertTrue(status["running"])
        self.assertIn("line one", status["log"])

    def test_start_rejects_when_process_is_already_running(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = ui_server.RunController(
                Path(tmpdir),
                popen_factory=lambda args, **kwargs: FakeProcess(),
            )

            controller.start({"RUN_COUNT": "1"})

            with self.assertRaisesRegex(RuntimeError, "already running"):
                controller.start({"RUN_COUNT": "2"})

    def test_start_rejects_invalid_run_count_before_launching_process(self):
        calls = []

        with tempfile.TemporaryDirectory() as tmpdir:
            controller = ui_server.RunController(
                Path(tmpdir),
                popen_factory=lambda args, **kwargs: calls.append((args, kwargs)) or FakeProcess(),
            )

            with self.assertRaisesRegex(ValueError, "RUN_COUNT"):
                controller.start({"RUN_COUNT": "0"})

        self.assertEqual(calls, [])

    def test_stop_terminates_running_process(self):
        process = FakeProcess()

        with tempfile.TemporaryDirectory() as tmpdir:
            controller = ui_server.RunController(
                Path(tmpdir),
                popen_factory=lambda args, **kwargs: process,
            )
            controller.start({"RUN_COUNT": "1"})

            stopped = controller.stop()
            status = controller.status()

        self.assertTrue(stopped)
        self.assertTrue(process.terminated)
        self.assertFalse(status["running"])

    def test_reset_log_clears_current_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = ui_server.RunController(Path(tmpdir))
            controller.append_log("hello")

            controller.reset_log()

            self.assertEqual(controller.status()["log"], "")


if __name__ == "__main__":
    unittest.main()

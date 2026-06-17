import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import call, patch

import codex_team_oauth


class CodexTeamOAuthMainTest(unittest.TestCase):
    def test_main_runs_once_per_configured_count(self):
        with patch.dict("os.environ", {"RUN_COUNT": "3"}, clear=True):
            with patch.object(codex_team_oauth, "load_dotenv"):
                with patch.object(codex_team_oauth, "run_once") as run_once:
                    with redirect_stdout(io.StringIO()):
                        result = codex_team_oauth.main()

        self.assertEqual(result, 0)
        self.assertEqual(
            run_once.call_args_list,
            [
                call(run_index=1, run_count=3),
                call(run_index=2, run_count=3),
                call(run_index=3, run_count=3),
            ],
        )

    def test_main_rejects_invalid_run_count_before_running(self):
        with patch.dict("os.environ", {"RUN_COUNT": "0"}, clear=True):
            with patch.object(codex_team_oauth, "load_dotenv"):
                with patch.object(codex_team_oauth, "run_once") as run_once:
                    with redirect_stdout(io.StringIO()):
                        result = codex_team_oauth.main()

        self.assertEqual(result, 1)
        run_once.assert_not_called()

    def test_main_continues_after_single_run_system_exit_failure(self):
        def fail_first_run(run_index, run_count):
            if run_index == 1:
                raise SystemExit(1)

        with patch.dict("os.environ", {"RUN_COUNT": "3"}, clear=True):
            with patch.object(codex_team_oauth, "load_dotenv"):
                with patch.object(codex_team_oauth, "run_once", side_effect=fail_first_run) as run_once:
                    with redirect_stdout(io.StringIO()):
                        result = codex_team_oauth.main()

        self.assertEqual(result, 1)
        self.assertEqual(
            run_once.call_args_list,
            [
                call(run_index=1, run_count=3),
                call(run_index=2, run_count=3),
                call(run_index=3, run_count=3),
            ],
        )

    def test_main_continues_after_single_run_exception_failure(self):
        def fail_second_run(run_index, run_count):
            if run_index == 2:
                raise RuntimeError("network failed")

        with patch.dict("os.environ", {"RUN_COUNT": "3"}, clear=True):
            with patch.object(codex_team_oauth, "load_dotenv"):
                with patch.object(codex_team_oauth, "run_once", side_effect=fail_second_run) as run_once:
                    output = io.StringIO()
                    with redirect_stdout(output):
                        result = codex_team_oauth.main()

        self.assertEqual(result, 1)
        self.assertIn("Run 2/3 failed: network failed", output.getvalue())
        self.assertEqual(
            run_once.call_args_list,
            [
                call(run_index=1, run_count=3),
                call(run_index=2, run_count=3),
                call(run_index=3, run_count=3),
            ],
        )


if __name__ == "__main__":
    unittest.main()

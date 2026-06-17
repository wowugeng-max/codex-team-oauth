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


if __name__ == "__main__":
    unittest.main()

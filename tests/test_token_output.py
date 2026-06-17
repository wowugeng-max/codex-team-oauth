import base64
import json
import tempfile
import unittest
from pathlib import Path

import token_output


def fake_jwt(payload):
    header = {"alg": "none", "typ": "JWT"}

    def enc(value):
        raw = json.dumps(value, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    return enc(header) + "." + enc(payload) + ".sig"


class TokenOutputTest(unittest.TestCase):
    def test_formats_token_payload_like_example_with_los_angeles_times(self):
        access_token = fake_jwt(
            {
                "iat": 1781711724,
                "exp": 1782575724,
                "https://api.openai.com/auth": {
                    "chatgpt_account_id": "acct-123",
                },
                "https://api.openai.com/profile": {
                    "email": "user@example.com",
                },
            }
        )
        id_token = fake_jwt({"email": "fallback@example.com"})

        payload = token_output.format_codex_token_payload(
            "explicit@example.com",
            {
                "access_token": access_token,
                "refresh_token": "rt-test",
                "id_token": id_token,
            },
        )

        self.assertEqual(
            list(payload.keys()),
            [
                "access_token",
                "account_id",
                "disabled",
                "email",
                "expired",
                "id_token",
                "last_refresh",
                "refresh_token",
                "type",
            ],
        )
        self.assertEqual(payload["account_id"], "acct-123")
        self.assertFalse(payload["disabled"])
        self.assertEqual(payload["email"], "explicit@example.com")
        self.assertEqual(payload["expired"], "2026-06-27T08:55:24-07:00")
        self.assertEqual(payload["last_refresh"], "2026-06-17T08:55:24-07:00")
        self.assertEqual(payload["refresh_token"], "rt-test")
        self.assertEqual(payload["type"], "codex")

    def test_saves_compact_json_to_project_result_json_directory_with_email_filename(self):
        access_token = fake_jwt(
            {
                "iat": 1781711724,
                "exp": 1782575724,
                "https://api.openai.com/auth": {
                    "chatgpt_account_id": "acct-123",
                },
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = token_output.save_codex_token_json(
                "user@example.com",
                {
                    "access_token": access_token,
                    "refresh_token": "rt-test",
                    "id_token": "id-token",
                },
                project_dir=tmpdir,
            )

            self.assertEqual(output_path, Path(tmpdir) / "result" / "json" / "user@example.com.json")
            text = output_path.read_text(encoding="utf-8")
            self.assertNotIn("\n", text)
            saved = json.loads(text)
            self.assertEqual(saved["email"], "user@example.com")
            self.assertEqual(saved["account_id"], "acct-123")

    def test_formats_saved_path_for_log_as_project_relative_path(self):
        project_dir = Path("/Users/ruiyaosong/codex-team-oauth")
        saved_path = project_dir / "result" / "json" / "user@example.com.json"

        self.assertEqual(
            token_output.format_saved_path_for_log(saved_path, project_dir=project_dir),
            "result/json/user@example.com.json",
        )


if __name__ == "__main__":
    unittest.main()

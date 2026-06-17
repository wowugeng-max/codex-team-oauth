import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import mail_providers


class FakeResponse:
    def __init__(self, status_code=200, data=None, text=""):
        self.status_code = status_code
        self._data = data
        self.text = text

    def json(self):
        return self._data


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, timeout=0):
        self.calls.append(("GET", url, None, None))
        return self.responses.pop(0)

    def post(self, url, json=None, headers=None, timeout=0, verify=True):
        self.calls.append(("POST", url, json, headers or {}))
        return self.responses.pop(0)


class MailProviderTest(unittest.TestCase):
    def test_provider_defaults_to_inbuck(self):
        self.assertEqual(mail_providers.get_mail_provider({}), "inbuck")

    def test_empty_env_does_not_fall_back_to_process_environment(self):
        with patch.dict("os.environ", {"MAIL_PROVIDER": "cloudmail"}):
            self.assertEqual(mail_providers.get_mail_provider({}), "inbuck")

    def test_unknown_provider_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "MAIL_PROVIDER"):
            mail_providers.get_mail_provider({"MAIL_PROVIDER": "unknown"})

    def test_resolves_inbuck_email_without_cloudmail_suffix(self):
        email = mail_providers.resolve_mail_email(
            {
                "MAIL_PROVIDER": "inbuck",
                "TEST_EMAIL": "alice@inbuck.example",
                "CLOUDMAIL_DOMAIN_SUFFIX": "mx.example.com",
            }
        )

        self.assertEqual(email, "alice@inbuck.example")

    def test_create_cloudmail_email_rejects_invalid_domain_suffix(self):
        with self.assertRaisesRegex(ValueError, "CLOUDMAIL_DOMAIN_SUFFIX"):
            mail_providers.create_cloudmail_email(
                FakeSession([]),
                {
                    "MAIL_PROVIDER": "cloudmail",
                    "CLOUDMAIL_API_BASE": "https://cloudmail.test",
                    "CLOUDMAIL_ADMIN_EMAIL": "admin@example.com",
                    "CLOUDMAIL_ADMIN_PASSWORD": "secret",
                    "CLOUDMAIL_DOMAIN_SUFFIX": "invalid-domain",
                }
            )

    def test_extracts_codes_from_html_and_text(self):
        self.assertEqual(
            mail_providers.extract_verification_code("<p>Your code is <b>123456</b></p>"),
            "123456",
        )
        self.assertEqual(
            mail_providers.extract_verification_code("OpenAI verification code: AB1-2CD"),
            "AB1-2CD",
        )

    def test_inbuck_provider_reads_existing_mailbox_shape(self):
        session = FakeSession(
            [
                FakeResponse(200, [{"id": "msg-1"}]),
                FakeResponse(200, {"body": {"text": "Use 654321 to verify your email."}}),
            ]
        )

        with redirect_stdout(io.StringIO()):
            otp = mail_providers.wait_for_otp(
                "alice@example.com",
                session,
                env={"MAIL_PROVIDER": "inbuck", "TEST_INBOX_API": "https://inbox.test/api"},
                attempts=1,
                sleep_seconds=0,
            )

        self.assertEqual(otp, "654321")
        self.assertEqual(
            [call[1] for call in session.calls],
            [
                "https://inbox.test/api/mailbox/alice",
                "https://inbox.test/api/mailbox/alice/msg-1",
            ],
        )

    def test_cloudmail_provider_generates_token_and_queries_full_email(self):
        session = FakeSession(
            [
                FakeResponse(200, {"code": 200, "data": {"token": "token-123"}}),
                FakeResponse(
                    200,
                    {
                        "code": 200,
                        "data": [
                            {
                                "subject": "OpenAI verification",
                                "text": "Your verification code is 112233.",
                                "content": "",
                            }
                        ],
                    },
                ),
            ]
        )

        with redirect_stdout(io.StringIO()):
            otp = mail_providers.wait_for_otp(
                "bob@example.com",
                session,
                env={
                    "MAIL_PROVIDER": "cloudmail",
                    "CLOUDMAIL_API_BASE": "https://cloudmail.test",
                    "CLOUDMAIL_ADMIN_EMAIL": "admin@example.com",
                    "CLOUDMAIL_ADMIN_PASSWORD": "secret",
                },
                attempts=1,
                sleep_seconds=0,
            )

        self.assertEqual(otp, "112233")
        self.assertEqual(session.calls[0][1], "https://cloudmail.test/api/public/genToken")
        self.assertEqual(session.calls[0][2], {"email": "admin@example.com", "password": "secret"})
        self.assertEqual(session.calls[1][1], "https://cloudmail.test/api/public/emailList")
        self.assertEqual(session.calls[1][2]["toEmail"], "bob@example.com")
        self.assertEqual(session.calls[1][3]["Authorization"], "token-123")


if __name__ == "__main__":
    unittest.main()

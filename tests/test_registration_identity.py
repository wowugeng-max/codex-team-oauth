import unittest
from unittest.mock import patch

import registration_identity

from tests.test_mail_providers import FakeResponse, FakeSession


class RegistrationIdentityTest(unittest.TestCase):
    def test_cloudmail_identity_creates_mailbox_without_test_email_or_password(self):
        session = FakeSession(
            [
                FakeResponse(200, {"code": 200, "data": {"token": "token-123"}}),
                FakeResponse(200, {"code": 200, "data": {}}),
            ]
        )

        with patch("mail_providers._generate_cloudmail_local_part", return_value="alex.smith"):
            with patch("mail_providers._generate_cloudmail_password", return_value="Aa1!generated"):
                with patch(
                    "registration_identity.generate_registration_profile",
                    return_value={"name": "James Smith", "age": 30, "birthday": "1996-01-02"},
                ):
                    identity = registration_identity.prepare_registration_identity(
                        session,
                        {
                            "MAIL_PROVIDER": "cloudmail",
                            "CLOUDMAIL_API_BASE": "https://cloudmail.test",
                            "CLOUDMAIL_ADMIN_EMAIL": "admin@example.com",
                            "CLOUDMAIL_ADMIN_PASSWORD": "secret",
                            "CLOUDMAIL_DOMAIN_SUFFIX": "mx.example.com",
                        },
                    )

        self.assertEqual(identity.email, "alex.smith@mx.example.com")
        self.assertEqual(identity.password, "Aa1!generated")
        self.assertEqual(identity.name, "James Smith")
        self.assertEqual(identity.birthdate, "1996-01-02")
        self.assertEqual(session.calls[0][1], "https://cloudmail.test/api/public/genToken")
        self.assertEqual(session.calls[1][1], "https://cloudmail.test/api/public/addUser")
        self.assertEqual(
            session.calls[1][2],
            {"list": [{"email": "alex.smith@mx.example.com", "password": "Aa1!generated"}]},
        )
        self.assertEqual(session.calls[1][3]["Authorization"], "token-123")

    def test_inbuck_identity_keeps_legacy_test_email_and_password(self):
        identity = registration_identity.prepare_registration_identity(
            None,
            {
                "MAIL_PROVIDER": "inbuck",
                "TEST_EMAIL": "alice@inbuck.example",
                "TEST_PASSWORD": "legacy-password",
            },
        )

        self.assertEqual(identity.email, "alice@inbuck.example")
        self.assertEqual(identity.password, "legacy-password")
        self.assertTrue(identity.name)
        self.assertRegex(identity.birthdate, r"^\d{4}-\d{2}-\d{2}$")

    def test_generated_profile_matches_registration_shape(self):
        profile = registration_identity.generate_registration_profile()

        self.assertIn("name", profile)
        self.assertIn("age", profile)
        self.assertIn("birthday", profile)
        self.assertGreaterEqual(profile["age"], 18)
        self.assertLessEqual(profile["age"], 55)
        self.assertRegex(profile["birthday"], r"^\d{4}-\d{2}-\d{2}$")


if __name__ == "__main__":
    unittest.main()

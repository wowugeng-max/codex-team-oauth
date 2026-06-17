import unittest

import oauth_steps


class OAuthStepsTest(unittest.TestCase):
    def test_new_account_about_you_requires_create_account(self):
        self.assertTrue(
            oauth_steps.should_create_account_after_otp(
                True,
                "https://auth.openai.com/about-you",
            )
        )

    def test_existing_account_consent_skips_create_account(self):
        self.assertFalse(
            oauth_steps.should_create_account_after_otp(
                False,
                "https://auth.openai.com/sign-in-with-chatgpt/codex/consent",
            )
        )

    def test_new_account_non_about_you_skips_create_account(self):
        self.assertFalse(
            oauth_steps.should_create_account_after_otp(
                True,
                "https://auth.openai.com/sign-in-with-chatgpt/codex/consent",
            )
        )

    def test_relative_continue_url_is_normalized_to_auth_host(self):
        self.assertEqual(
            oauth_steps.normalize_continue_url("/about-you"),
            "https://auth.openai.com/about-you",
        )

    def test_absolute_continue_url_is_preserved(self):
        self.assertEqual(
            oauth_steps.normalize_continue_url("https://chatgpt.com/somewhere"),
            "https://chatgpt.com/somewhere",
        )


if __name__ == "__main__":
    unittest.main()

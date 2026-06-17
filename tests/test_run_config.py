import unittest

import run_config


class RunConfigTest(unittest.TestCase):
    def test_run_count_defaults_to_one_when_missing_or_blank(self):
        self.assertEqual(run_config.get_run_count({}), 1)
        self.assertEqual(run_config.get_run_count({"RUN_COUNT": ""}), 1)
        self.assertEqual(run_config.get_run_count({"RUN_COUNT": "   "}), 1)

    def test_run_count_accepts_positive_integer(self):
        self.assertEqual(run_config.get_run_count({"RUN_COUNT": "3"}), 3)

    def test_run_count_rejects_zero_negative_and_non_integer_values(self):
        for value in ("0", "-1", "abc", "1.5"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "RUN_COUNT"):
                    run_config.get_run_count({"RUN_COUNT": value})


if __name__ == "__main__":
    unittest.main()

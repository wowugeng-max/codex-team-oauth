import os
import stat
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_DIR / "start_ui_mac.command"


class MacCommandScriptTest(unittest.TestCase):
    def test_mac_command_script_is_executable_and_starts_ui(self):
        self.assertTrue(SCRIPT_PATH.exists())

        mode = SCRIPT_PATH.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR)

        text = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn('SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"', text)
        self.assertIn('cd "$SCRIPT_DIR"', text)
        self.assertIn('open "$UI_URL"', text)
        self.assertIn("python3 ui_server.py --host 127.0.0.1 --port 8765", text)


if __name__ == "__main__":
    unittest.main()

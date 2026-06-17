import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
CSS_TEXT = (PROJECT_DIR / "ui_static" / "styles.css").read_text(encoding="utf-8")


class UIStaticStyleTest(unittest.TestCase):
    def test_log_panel_uses_fixed_height_scroll_region(self):
        self.assertIn("height: calc(100vh - 128px);", CSS_TEXT)
        self.assertIn("grid-template-rows: auto auto minmax(0, 1fr);", CSS_TEXT)
        self.assertIn("min-height: 0;", CSS_TEXT)
        self.assertIn("overflow: auto;", CSS_TEXT)


if __name__ == "__main__":
    unittest.main()

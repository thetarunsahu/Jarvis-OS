import unittest
from pathlib import Path


class OperatingShellSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shell_source = (Path(__file__).resolve().parents[1] / "interface" / "shell.py").read_text(
            encoding="utf-8"
        )
        cls.main_source = (Path(__file__).resolve().parents[1] / "main.py").read_text(
            encoding="utf-8"
        )

    def test_shell_defines_real_stacked_pages(self):
        source = self.shell_source
        self.assertIn("QStackedWidget", source)
        self.assertIn("PAGE_HOME = 0", source)
        self.assertIn("PAGE_WORKSPACE = 1", source)
        self.assertIn("PAGE_FILES = 2", source)
        self.assertIn("PAGE_TASKS = 3", source)
        self.assertIn("self.pages.addWidget(self._build_workspace_page())", source)
        self.assertIn("self.pages.addWidget(self._build_files_page())", source)
        self.assertIn("self.pages.addWidget(self._build_tasks_page())", source)

    def test_files_have_dedicated_search_results_surface(self):
        source = self.shell_source
        self.assertIn("file_search_requested = Signal(str)", source)
        self.assertIn("self.file_results = QListWidget()", source)
        self.assertIn("def set_file_results", source)

    def test_main_boots_new_operating_app(self):
        self.assertIn("from interface.operating_app import run_app", self.main_source)
        self.assertNotIn("from interface.jarvis_app import run_app", self.main_source)


if __name__ == "__main__":
    unittest.main()

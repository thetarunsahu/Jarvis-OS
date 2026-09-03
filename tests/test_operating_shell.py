import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from interface.shell import JarvisShell


class OperatingShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.shell = JarvisShell()

    def tearDown(self):
        self.shell.close()

    def test_dock_pages_are_real_stacked_views(self):
        self.assertEqual(self.shell.pages.count(), 4)
        self.assertEqual(self.shell.pages.currentIndex(), JarvisShell.PAGE_HOME)

        self.shell.show_page(JarvisShell.PAGE_WORKSPACE)
        self.assertEqual(self.shell.pages.currentIndex(), JarvisShell.PAGE_WORKSPACE)

        self.shell.show_page(JarvisShell.PAGE_FILES)
        self.assertEqual(self.shell.pages.currentIndex(), JarvisShell.PAGE_FILES)

        self.shell.show_page(JarvisShell.PAGE_TASKS)
        self.assertEqual(self.shell.pages.currentIndex(), JarvisShell.PAGE_TASKS)

    def test_workspace_state_is_reflected_on_workspace_page(self):
        self.shell.set_workspace(
            "JARVIS OS",
            ["Project  ·  Python", "Branch  ·  feat/core-architecture-v1"],
            resumable=True,
            next_action="Build workspace navigation",
        )

        self.assertEqual(self.shell.workspace_page_title.text(), "JARVIS OS")
        self.assertIn("Python", self.shell.workspace_page_details.text())
        self.assertIn("Build workspace navigation", self.shell.workspace_page_next.text())
        self.assertTrue(self.shell.workspace_page_resume.isEnabled())

    def test_file_results_render_in_files_view(self):
        self.shell.set_file_results(
            "architecture",
            [
                {
                    "name": "ARCHITECTURE.md",
                    "path": "C:/Projects/Jarvis/docs/ARCHITECTURE.md",
                    "extension": ".md",
                }
            ],
        )

        self.assertEqual(self.shell.file_results.count(), 1)
        self.assertIn("ARCHITECTURE.md", self.shell.file_results.item(0).text())
        self.assertIn("1 result", self.shell.file_result_title.text())


if __name__ == "__main__":
    unittest.main()

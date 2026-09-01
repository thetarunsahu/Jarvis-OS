import tempfile
import unittest
from pathlib import Path

from files.file_index import FileIndex


class FileIntelligenceTests(unittest.TestCase):
    def test_indexes_text_content_and_binary_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            root.mkdir()

            notes = root / "mentor_notes.md"
            notes.write_text(
                "Final agriculture weed removal robot design shown to mentor.",
                encoding="utf-8",
            )
            image = root / "final_robot_design.png"
            image.write_bytes(b"not-a-real-png")

            db_path = Path(temp_dir) / "jarvis-test.db"
            index = FileIndex(db_path=db_path, roots=[root])

            result = index.scan()
            self.assertEqual(result["indexed"], 2)

            content_matches = index.search("agriculture robot", limit=5)
            self.assertTrue(
                any(match["name"] == "mentor_notes.md" for match in content_matches)
            )

            filename_matches = index.search("final_robot_design", limit=5)
            self.assertTrue(
                any(match["name"] == "final_robot_design.png" for match in filename_matches)
            )

    def test_scan_prunes_deleted_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            root.mkdir()
            document = root / "temporary.txt"
            document.write_text("temporary indexed content", encoding="utf-8")

            index = FileIndex(
                db_path=Path(temp_dir) / "jarvis-test.db",
                roots=[root],
            )
            index.scan()
            self.assertEqual(index.stats()["files"], 1)

            document.unlink()
            index.scan()
            self.assertEqual(index.stats()["files"], 0)


if __name__ == "__main__":
    unittest.main()

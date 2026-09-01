import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.file_tools import FileTools


class FileToolsTests(unittest.TestCase):
    def test_reads_file_inside_explicit_allowed_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            document = root / "notes.txt"
            document.write_text("Jarvis sandbox test", encoding="utf-8")

            with patch.dict(os.environ, {"JARVIS_ALLOWED_PATHS": str(root)}):
                result = FileTools.read_text_file(str(document))

            self.assertEqual(result, "Jarvis sandbox test")

    def test_denies_file_outside_allowed_roots(self):
        with tempfile.TemporaryDirectory() as allowed_dir, tempfile.TemporaryDirectory() as other_dir:
            other = Path(other_dir) / "secret.txt"
            other.write_text("outside", encoding="utf-8")

            with patch.dict(
                os.environ,
                {
                    "JARVIS_ALLOWED_PATHS": str(Path(allowed_dir)),
                    "JARVIS_INDEX_PATHS": "",
                },
                clear=False,
            ):
                result = FileTools.read_text_file(str(other))

            self.assertIn("File access denied", result)

    def test_denies_env_and_private_key_even_inside_allowed_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            env_file = root / ".env"
            env_file.write_text("API_KEY=super-secret", encoding="utf-8")
            key_file = root / "private.pem"
            key_file.write_text("private key material", encoding="utf-8")

            with patch.dict(os.environ, {"JARVIS_ALLOWED_PATHS": str(root)}):
                env_result = FileTools.read_text_file(str(env_file))
                key_result = FileTools.read_text_file(str(key_file))

            self.assertIn("protected", env_result)
            self.assertIn("protected", key_result)
            self.assertNotIn("super-secret", env_result)

    def test_allows_env_example_for_configuration_help(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            example = root / ".env.example"
            example.write_text("API_KEY=example", encoding="utf-8")

            with patch.dict(os.environ, {"JARVIS_ALLOWED_PATHS": str(root)}):
                result = FileTools.read_text_file(str(example))

            self.assertEqual(result, "API_KEY=example")

    def test_read_is_truncated_to_requested_limit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            document = root / "long.txt"
            document.write_text("abcdefghij", encoding="utf-8")

            with patch.dict(os.environ, {"JARVIS_ALLOWED_PATHS": str(root)}):
                result = FileTools.read_text_file(str(document), max_chars=4)

            self.assertTrue(result.startswith("abcd"))
            self.assertIn("TRUNCATED", result)


if __name__ == "__main__":
    unittest.main()

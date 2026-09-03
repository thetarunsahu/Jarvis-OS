import unittest

from core.router import CommandRouter


class CommandRouterNormalizationTests(unittest.TestCase):
    def test_hello_jarvis_stays_on_direct_command_path(self):
        self.assertEqual(
            CommandRouter._normalize_direct_command("hello Jarvis"),
            "hello",
        )

    def test_jarvis_prefix_and_punctuation_are_removed(self):
        self.assertEqual(
            CommandRouter._normalize_direct_command("Jarvis, what time is it?"),
            "what time is it",
        )

    def test_voice_style_greeting_normalizes(self):
        self.assertEqual(
            CommandRouter._normalize_direct_command("Hey, JARVIS!"),
            "hey",
        )


if __name__ == "__main__":
    unittest.main()

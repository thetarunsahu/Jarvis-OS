import unittest
from unittest.mock import patch

from voice.voice_manager import VoiceManager


class VoiceManagerTests(unittest.TestCase):
    def test_clean_text_makes_screen_content_speakable(self):
        text = "## Result\nUse **JARVIS** and `main.py`. https://example.com"
        cleaned = VoiceManager.clean_text(text)

        self.assertEqual(cleaned, "Result Use JARVIS and main.py.")

    def test_long_response_is_clipped_for_voice_only(self):
        voice = VoiceManager()
        voice.max_speech_chars = 24

        result = voice.speech_text("This is a deliberately long response for the screen.")

        self.assertLess(len(result), 100)
        self.assertIn("rest of the response on screen", result)

    @patch("voice.voice_manager.subprocess.run")
    def test_windows_tts_passes_text_through_environment(self, run):
        run.return_value.returncode = 0
        unsafe_text = "hello'; Remove-Item C:\\important; '"

        result = VoiceManager._speak_windows(unsafe_text)

        self.assertTrue(result)
        args, kwargs = run.call_args
        command = args[0]
        self.assertEqual(command[0], "powershell.exe")
        self.assertFalse(kwargs["shell"])
        self.assertNotIn(unsafe_text, " ".join(command))
        self.assertEqual(kwargs["env"]["JARVIS_TTS_TEXT"], unsafe_text)


if __name__ == "__main__":
    unittest.main()

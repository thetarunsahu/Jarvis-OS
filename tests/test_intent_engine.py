import unittest

from core.intent_engine import IntentEngine


class IntentEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = IntentEngine()

    def test_conversation_default(self):
        task = self.engine.analyze("hello jarvis")
        self.assertEqual(task.intent, "conversation")
        self.assertFalse(task.background)
        self.assertFalse(task.requires_tools)

    def test_file_request(self):
        task = self.engine.analyze("find my project image")
        self.assertEqual(task.intent, "file")
        self.assertTrue(task.requires_tools)

    def test_productivity_request_requires_tools(self):
        task = self.engine.analyze("remind me to solve DSA tomorrow")
        self.assertEqual(task.intent, "productivity")
        self.assertTrue(task.requires_tools)
        self.assertFalse(task.background)

    def test_research_request_is_background_and_tool_dependent(self):
        task = self.engine.analyze("deep research current agent frameworks")
        self.assertEqual(task.intent, "research")
        self.assertTrue(task.background)
        self.assertTrue(task.requires_tools)

    def test_ui_request(self):
        task = self.engine.analyze("redesign the ui of this project")
        self.assertEqual(task.intent, "ui_design")
        self.assertTrue(task.background)
        self.assertTrue(task.requires_tools)


if __name__ == "__main__":
    unittest.main()

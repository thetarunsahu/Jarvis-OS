import unittest
from unittest.mock import patch

from security.permissions import PermissionLevel
from tools.browser_tools import BrowserTools
from tools.system_control_tools import SystemControlTools
from tools.tool_registry import ToolRegistry


class BrowserToolsTests(unittest.TestCase):
    def test_normalises_host_to_https(self):
        self.assertEqual(
            BrowserTools._normalise_url("example.com"),
            "https://example.com",
        )

    def test_rejects_non_http_scheme(self):
        with self.assertRaises(ValueError):
            BrowserTools._normalise_url("file:///C:/Windows/system.ini")

    @patch("tools.browser_tools.webbrowser.open", return_value=True)
    def test_web_search_encodes_query(self, open_mock):
        result = BrowserTools.search_web("jarvis local ai")
        self.assertIn("jarvis+local+ai", result["url"])
        open_mock.assert_called_once_with(result["url"], new=2)

    @patch("tools.browser_tools.webbrowser.open", return_value=True)
    def test_youtube_search_encodes_query(self, open_mock):
        result = BrowserTools.search_youtube("interstellar soundtrack")
        self.assertIn("interstellar+soundtrack", result["url"])
        open_mock.assert_called_once_with(result["url"], new=2)


class SystemControlToolsTests(unittest.TestCase):
    @patch("tools.system_control_tools.platform.system", return_value="Windows")
    @patch.object(SystemControlTools, "_press_media_key")
    def test_set_volume_reports_unverified_estimate(self, press_mock, _platform):
        result = SystemControlTools.set_volume(40)
        self.assertEqual(result["requested_percent"], 40)
        self.assertEqual(result["estimated_percent"], 40)
        self.assertFalse(result["verified"])
        self.assertEqual(press_mock.call_count, 2)

    def test_volume_steps_are_bounded(self):
        with self.assertRaises(ValueError):
            SystemControlTools._normalise_steps(0)
        with self.assertRaises(ValueError):
            SystemControlTools._normalise_steps(21)

    def test_power_delay_is_bounded(self):
        with self.assertRaises(ValueError):
            SystemControlTools._normalise_delay(-1)
        with self.assertRaises(ValueError):
            SystemControlTools._normalise_delay(3601)


class ToolRegistryActionMetadataTests(unittest.TestCase):
    def test_new_action_tools_are_registered_with_expected_risk(self):
        metadata = {
            item["name"]: item["permission"]
            for item in ToolRegistry().get_tool_metadata()
        }

        self.assertEqual(metadata["search_web"], PermissionLevel.CONFIRM.value)
        self.assertEqual(metadata["open_url"], PermissionLevel.CONFIRM.value)
        self.assertEqual(metadata["set_volume"], PermissionLevel.CONFIRM.value)
        self.assertEqual(
            metadata["shutdown_computer"],
            PermissionLevel.DESTRUCTIVE.value,
        )
        self.assertEqual(
            metadata["restart_computer"],
            PermissionLevel.DESTRUCTIVE.value,
        )
        self.assertEqual(metadata["cancel_power_action"], PermissionLevel.SAFE.value)


if __name__ == "__main__":
    unittest.main()

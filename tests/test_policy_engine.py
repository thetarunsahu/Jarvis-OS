import unittest

from core.policy_engine import PermissionLevel, PolicyEngine


class PolicyEngineTests(unittest.TestCase):
    def test_read_action_is_automatic(self):
        policy = PolicyEngine()
        decision = policy.evaluate("read_file", PermissionLevel.READ)

        self.assertTrue(decision.allowed)
        self.assertFalse(decision.requires_confirmation)

    def test_modify_action_requires_confirmation(self):
        policy = PolicyEngine()
        decision = policy.evaluate("edit_file", PermissionLevel.MODIFY)

        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_confirmation)

    def test_explicit_approval_allows_sensitive_action(self):
        policy = PolicyEngine()
        decision = policy.evaluate(
            "delete_file",
            PermissionLevel.SENSITIVE,
            approved=True,
        )

        self.assertTrue(decision.allowed)
        self.assertFalse(decision.requires_confirmation)


if __name__ == "__main__":
    unittest.main()

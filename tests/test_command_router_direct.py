import unittest

from core.router import CommandRouter


class CommandRouterDirectTests(unittest.TestCase):
    def _router_without_runtime(self):
        router = CommandRouter.__new__(CommandRouter)
        router.current_time = lambda: "TIME_OK"
        router.greeting = lambda: "HELLO_OK"
        return router

    def test_hello_jarvis_is_direct(self):
        router = self._router_without_runtime()
        self.assertEqual(router.route("hey Jarvis"), "HELLO_OK")
        self.assertEqual(router.route("Jarvis, hello"), "HELLO_OK")

    def test_natural_time_phrases_are_direct(self):
        router = self._router_without_runtime()
        for phrase in [
            "what is time",
            "what is the time",
            "what's the time?",
            "Jarvis, tell me the time",
            "time now",
        ]:
            with self.subTest(phrase=phrase):
                self.assertEqual(router.route(phrase), "TIME_OK")


if __name__ == "__main__":
    unittest.main()

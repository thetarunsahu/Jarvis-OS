from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    reason: str = ""


class BasicVerifier:
    """Minimum verification boundary before a task can be marked complete.

    Specialist agents can replace this with domain-specific verification
    such as tests, browser checks, file existence checks, or second-model review.
    """

    provider_failure_markers = (
        "jarvis could not reach an ai provider",
        "provider is not configured",
        "tool execution failed",
    )

    def verify(self, task, result):
        if result is None:
            return VerificationResult(False, "Task returned no result.")

        text = str(result).strip()
        if not text:
            return VerificationResult(False, "Task returned an empty result.")

        lowered = text.lower()
        if any(marker in lowered for marker in self.provider_failure_markers):
            return VerificationResult(False, text)

        return VerificationResult(True, "Basic verification passed.")

import os
from dataclasses import dataclass, field

from openai import OpenAI


@dataclass
class ResearchResult:
    text: str
    sources: list = field(default_factory=list)

    def render(self):
        if not self.sources:
            return self.text

        lines = [self.text.rstrip(), "", "Sources:"]
        for source in self.sources[:20]:
            title = source.get("title") or source.get("url") or "Source"
            url = source.get("url") or ""
            lines.append(f"- {title}: {url}" if url else f"- {title}")
        return "\n".join(lines)


class OpenAIWebResearchRuntime:
    """Optional specialist runtime using OpenAI's hosted web search tool.

    It is disabled by default because hosted web search can incur API cost.
    Set OPENAI_WEB_RESEARCH_ENABLED=true to opt in.
    """

    def __init__(self, client=None):
        self.enabled = (
            os.getenv("OPENAI_WEB_RESEARCH_ENABLED", "false").lower() == "true"
        )
        self.model = os.getenv(
            "OPENAI_RESEARCH_MODEL",
            os.getenv("OPENAI_MODEL", "gpt-5.6"),
        )

        if client is not None:
            self.client = client
            self.enabled = True
            return

        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if self.enabled and api_key else None

    @property
    def is_available(self):
        return bool(self.enabled and self.client is not None)

    @staticmethod
    def _collect_sources(response):
        seen = set()
        sources = []

        def add_source(url=None, title=None):
            if not url or url in seen:
                return
            seen.add(url)
            sources.append({"url": str(url), "title": str(title or url)})

        for item in getattr(response, "output", None) or []:
            # URL citations attached to output text.
            if getattr(item, "type", None) == "message":
                for content in getattr(item, "content", None) or []:
                    for annotation in getattr(content, "annotations", None) or []:
                        if getattr(annotation, "type", None) == "url_citation":
                            add_source(
                                getattr(annotation, "url", None),
                                getattr(annotation, "title", None),
                            )

            # Best-effort extraction when web_search_call sources are included.
            if getattr(item, "type", None) == "web_search_call":
                action = getattr(item, "action", None)
                for source in getattr(action, "sources", None) or []:
                    if isinstance(source, dict):
                        add_source(source.get("url"), source.get("title"))
                    else:
                        add_source(
                            getattr(source, "url", None),
                            getattr(source, "title", None),
                        )

        return sources

    def research(self, query, context=None):
        if not self.is_available:
            raise RuntimeError("OpenAI web research runtime is not enabled.")

        prompt = (
            "Research the user's request using current web sources. Prefer "
            "primary and authoritative sources, distinguish evidence from "
            "inference, call out uncertainty, and produce a concise synthesis."
        )
        if context:
            prompt += f"\n\nRelevant JARVIS context:\n{context}"
        prompt += f"\n\nResearch request:\n{query}"

        response = self.client.responses.create(
            model=self.model,
            tools=[{"type": "web_search_preview"}],
            include=["web_search_call.action.sources"],
            input=prompt,
        )

        result = ResearchResult(
            text=getattr(response, "output_text", "") or "",
            sources=self._collect_sources(response),
        )
        return result.render()

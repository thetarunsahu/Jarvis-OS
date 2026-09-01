import os

import ollama


class EmbeddingError(RuntimeError):
    pass


class OllamaEmbeddingProvider:
    """Optional local embedding provider for semantic file retrieval.

    Semantic indexing is opt-in so JARVIS does not unexpectedly download or
    run an embedding model. Set JARVIS_SEMANTIC_SEARCH_ENABLED=true after
    pulling OLLAMA_EMBEDDING_MODEL locally.
    """

    def __init__(self):
        self.enabled = (
            os.getenv("JARVIS_SEMANTIC_SEARCH_ENABLED", "false").lower()
            == "true"
        )
        self.model = os.getenv("OLLAMA_EMBEDDING_MODEL", "embeddinggemma")

    @property
    def is_available(self):
        return self.enabled

    def embed(self, inputs):
        if not self.enabled:
            raise EmbeddingError("Semantic search is not enabled.")

        if isinstance(inputs, str):
            values = [inputs]
        else:
            values = list(inputs)

        if not values:
            return []

        try:
            response = ollama.embed(
                model=self.model,
                input=values,
            )
            vectors = response["embeddings"]
        except Exception as error:
            raise EmbeddingError(
                f"Ollama embedding request failed: {error}"
            ) from error

        return [list(map(float, vector)) for vector in vectors]

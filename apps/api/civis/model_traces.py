"""Langfuse receives only technical metadata and usage, never inputs or outputs."""

import os
from contextlib import suppress

from langfuse import Langfuse
from langfuse._client.span import LangfuseGeneration


class ModelTracing:
    def __init__(self) -> None:
        self.client: Langfuse | None = None
        if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
            self.client = Langfuse(
                public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
                secret_key=os.environ["LANGFUSE_SECRET_KEY"],
                host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
                debug=False,
                timeout=2,
                mask=lambda **kwargs: None,
            )

    def start(self, mode: str, model: str | None) -> LangfuseGeneration | None:
        if self.client is None:
            return None
        with suppress(Exception):
            return self.client.start_generation(
                name="chat", model=model, metadata={"mode": mode}, version=mode + "-v1"
            )
        return None

    @staticmethod
    def finish(
        generation: LangfuseGeneration | None, input_tokens: int, output_tokens: int, complete: bool
    ) -> None:
        if generation is not None:
            with suppress(Exception):
                generation.update(
                    usage_details={"input": input_tokens, "output": output_tokens},
                    metadata={"complete": complete},
                )
                generation.end()

    def shutdown(self) -> None:
        if self.client is not None:
            self.client.shutdown()

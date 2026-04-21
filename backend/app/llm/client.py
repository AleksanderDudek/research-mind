from app.config import settings


_langfuse_enabled = bool(
    settings.langfuse_public_key and settings.langfuse_secret_key
)


def _make_client():
    if _langfuse_enabled:
        from langfuse.openai import AsyncOpenAI
    else:
        from openai import AsyncOpenAI

    return AsyncOpenAI(
        base_url=f"{settings.litellm_base_url}/v1",
        api_key=settings.litellm_api_key,
    )


class LLMClient:
    _client = None

    @classmethod
    def get(cls):
        if cls._client is None:
            cls._client = _make_client()
        return cls._client

    @classmethod
    async def complete(
        cls,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.1,
        name: str | None = None,
    ) -> str:
        client = cls.get()
        extra = {"name": name} if (name and _langfuse_enabled) else {}
        response = await client.chat.completions.create(
            model=model or settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            **extra,
        )
        return response.choices[0].message.content or ""

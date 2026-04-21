from app.config import settings


def _make_client():
    if settings.langfuse_public_key and settings.langfuse_secret_key:
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
        kwargs = {}
        if name:
            kwargs["name"] = name
        response = await client.chat.completions.create(
            model=model or settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            **kwargs,
        )
        return response.choices[0].message.content or ""

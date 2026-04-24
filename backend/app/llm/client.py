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

    _VISION_PROMPTS = {
        "quick": "Describe this image in 1-2 sentences.",
        "standard": (
            "Describe this image in detail, including all visible objects, people, "
            "scene, colors and any text."
        ),
        "detailed": (
            "Provide a comprehensive analysis of this image: every visible object, "
            "people and their attributes, spatial relationships, any text or numbers, "
            "colors, mood, context and any notable details."
        ),
    }

    @classmethod
    async def complete_vision(
        cls,
        image_b64: str,
        mime_type: str,
        detail_level: str = "standard",
        model: str | None = None,
    ) -> str:
        client = cls.get()
        prompt = cls._VISION_PROMPTS.get(detail_level, cls._VISION_PROMPTS["standard"])
        response = await client.chat.completions.create(
            model=model or settings.vision_model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
            temperature=0.1,
        )
        return response.choices[0].message.content or ""

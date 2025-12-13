from __future__ import annotations

from typing import Any, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from src.core.config import settings

TModel = TypeVar("TModel", bound=BaseModel)


def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Return a JSON schema patched for strict `response_format: json_schema` use."""
    schema: dict[str, Any] = model.model_json_schema()
    _make_schema_strict(schema)
    return schema


def _make_schema_strict(node: object) -> None:
    """Recursively:
    - set `additionalProperties: false` for all object schemas with explicit properties
    - ensure `required` lists all properties (Azure `json_schema` strictness)
    """

    if isinstance(node, dict):
        if node.get("type") == "object" and isinstance(node.get("properties"), dict):
            node["additionalProperties"] = False

            props_in_order = list(node["properties"].keys())
            required = list(node.get("required", []))
            required_set = set(required)
            missing = [p for p in props_in_order if p not in required_set]
            if missing:
                node["required"] = required + missing

        for value in node.values():
            _make_schema_strict(value)
        return

    if isinstance(node, list):
        for item in node:
            _make_schema_strict(item)
        return


class OpenRouterLLM:
    """Minimal OpenRouter (OpenAI-compatible) chat client helpers."""

    def __init__(self, *, client: AsyncOpenAI) -> None:
        self._client = client

    @classmethod
    def from_settings(cls) -> "OpenRouterLLM":
        api_key = settings.OPENROUTER_API_KEY.strip()
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set.")

        default_headers: dict[str, str] = {}
        if settings.OPENROUTER_HTTP_REFERER.strip():
            default_headers["HTTP-Referer"] = settings.OPENROUTER_HTTP_REFERER
        if settings.OPENROUTER_APP_TITLE.strip():
            default_headers["X-Title"] = settings.OPENROUTER_APP_TITLE

        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers=default_headers or None,
            timeout=settings.OPENROUTER_TIMEOUT_SECONDS,
        )
        return cls(client=client)

    async def chat_json_schema(
        self,
        *,
        messages: list[dict[str, Any]],
        response_model: type[TModel],
        schema_name: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> TModel:
        """Call OpenRouter and parse a strict JSON-schema response into a Pydantic model."""

        schema = strict_json_schema(response_model)
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name or response_model.__name__,
                "schema": schema,
            },
        }

        resp = await self._client.chat.completions.create(
            model=model or settings.OPENROUTER_MODEL,
            messages=messages,
            temperature=temperature,
            response_format=response_format,
        )

        content = (resp.choices[0].message.content or "").strip()
        if not content:
            raise RuntimeError("OpenRouter returned an empty completion.")

        try:
            return response_model.model_validate_json(content)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "OpenRouter returned a response that did not match the expected schema."
            ) from exc

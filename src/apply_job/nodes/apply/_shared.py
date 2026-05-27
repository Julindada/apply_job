import re
import socket
from contextlib import asynccontextmanager
from typing import Any, TypeVar
from urllib.parse import urlparse, urlunparse

from pydantic import BaseModel

from apply_job.config import settings

T = TypeVar("T", bound=BaseModel)


def resolve_cdp_url(cdp_url: str) -> str:
    """Replace hostname with its IP so Chrome accepts the Host header."""
    parsed = urlparse(cdp_url)
    host = parsed.hostname or ""
    if host and host not in ("localhost", "127.0.0.1"):
        try:
            ip = socket.gethostbyname(host)
            netloc = f"{ip}:{parsed.port}" if parsed.port else ip
            return urlunparse(parsed._replace(netloc=netloc))
        except socket.gaierror:
            pass
    return cdp_url


def _strip_code_block(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers Claude sometimes adds."""
    m = re.match(r"```(?:json)?\s*\n?(.*?)\n?```$", text.strip(), re.DOTALL)
    return m.group(1).strip() if m else text.strip()


class _AI233ChatOpenAI:
    """Thin wrapper around browser_use ChatOpenAI.

    AI233's Claude proxy ignores response_format=json_schema and wraps JSON in
    markdown code blocks.  This class overrides ainvoke to:
      1. Use response_format=json_object (which AI233 does support).
      2. Strip markdown code blocks before Pydantic validation.
    All other attributes are delegated to the inner ChatOpenAI instance.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    async def ainvoke(
        self, messages: list, output_format: type[T] | None = None, **kwargs: Any
    ):
        from browser_use.llm.openai.chat import ChatOpenAI
        from browser_use.llm.exceptions import ModelProviderError
        from browser_use.llm.schema import SchemaOptimizer
        from browser_use.llm.openai.serializer import OpenAIMessageSerializer
        from browser_use.llm.views import ChatInvokeCompletion

        inner = self._inner
        openai_messages = OpenAIMessageSerializer.serialize_messages(messages)

        model_params: dict[str, Any] = {}
        if inner.temperature is not None:
            model_params["temperature"] = inner.temperature
        if inner.frequency_penalty is not None:
            model_params["frequency_penalty"] = inner.frequency_penalty
        if inner.max_completion_tokens is not None:
            model_params["max_completion_tokens"] = inner.max_completion_tokens

        if output_format is None:
            return await inner.ainvoke(messages, output_format=None, **kwargs)

        # Append JSON instruction to the last user message.
        # AI233 Claude ignores system-message JSON constraints; user-message
        # instructions are reliably followed.
        schema = SchemaOptimizer.create_optimized_json_schema(output_format)
        json_instruction = (
            f"\n\nIMPORTANT: Reply ONLY with raw JSON — no markdown, no code blocks, "
            f"no extra text. Your entire response must be a single valid JSON object "
            f"conforming to this schema:\n{schema}"
        )
        for i in range(len(openai_messages) - 1, -1, -1):
            if openai_messages[i]["role"] == "user":
                content = openai_messages[i]["content"]
                if isinstance(content, str):
                    openai_messages[i]["content"] = content + json_instruction
                elif isinstance(content, list):
                    openai_messages[i]["content"] = content + [
                        {"type": "text", "text": json_instruction}
                    ]
                break

        client = inner.get_client()
        try:
            response = await client.chat.completions.create(
                model=inner.model,
                messages=openai_messages,
                response_format={"type": "json_object"},
                **model_params,
            )
        except Exception as e:
            raise ModelProviderError(message=str(e), model=inner.name) from e

        choice = response.choices[0] if response.choices else None
        if choice is None:
            raise ModelProviderError(
                message="Empty choices in response", model=inner.name
            )

        content = choice.message.content or ""
        content = _strip_code_block(content)

        try:
            parsed = output_format.model_validate_json(content)
        except Exception as e:
            raise ModelProviderError(message=str(e), model=inner.name) from e

        return ChatInvokeCompletion(
            completion=parsed,
            usage=inner._get_usage(response),
            stop_reason=choice.finish_reason,
        )


def make_llm() -> _AI233ChatOpenAI:
    from browser_use.llm.openai.chat import ChatOpenAI

    inner = ChatOpenAI(
        model=settings.apply_model,
        api_key=settings.apply_api_key,
        base_url=settings.apply_base_url,
        temperature=0,
    )
    return _AI233ChatOpenAI(inner)


@asynccontextmanager
async def browser_session():
    """Yield a BrowserSession connected to the host Chrome via CDP.

    Resolves the CDP hostname to an IP so Chrome accepts the Host header.
    keep_alive=True prevents Agent.close() from killing Chrome between steps.
    """
    from browser_use import BrowserProfile, BrowserSession

    session = BrowserSession(
        cdp_url=resolve_cdp_url(settings.cdp_url),
        browser_profile=BrowserProfile(keep_alive=True),
    )
    yield session

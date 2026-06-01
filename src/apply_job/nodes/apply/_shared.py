import logging
import re
import socket
import time
from contextlib import asynccontextmanager
from typing import Any, TypeVar
from urllib.parse import urlparse, urlunparse

from pydantic import BaseModel

from apply_job.config import settings

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


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


def _output_format_name(output_format: type[BaseModel] | None) -> str:
    return output_format.__name__ if output_format else "text"


def _usage_total_tokens(result: Any) -> Any:
    usage = getattr(result, "usage", None)
    return getattr(usage, "total_tokens", None)


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
        start_time = time.monotonic()
        format_name = _output_format_name(output_format)
        logger.info(
            "LLM call started model=%s output_format=%s messages=%d timeout=%s",
            inner.model,
            format_name,
            len(messages),
            settings.apply_llm_timeout_seconds,
        )

        model_params: dict[str, Any] = {}
        if inner.temperature is not None:
            model_params["temperature"] = inner.temperature
        if inner.frequency_penalty is not None:
            model_params["frequency_penalty"] = inner.frequency_penalty
        if inner.max_completion_tokens is not None:
            model_params["max_completion_tokens"] = inner.max_completion_tokens

        if output_format is None:
            try:
                result = await inner.ainvoke(messages, output_format=None, **kwargs)
            except Exception as exc:
                logger.exception(
                    "LLM call failed model=%s output_format=%s duration=%.2fs error_type=%s error=%s",
                    inner.model,
                    format_name,
                    time.monotonic() - start_time,
                    type(exc).__name__,
                    exc,
                )
                raise
            logger.info(
                "LLM call completed model=%s output_format=%s duration=%.2fs total_tokens=%s stop_reason=%s",
                inner.model,
                format_name,
                time.monotonic() - start_time,
                _usage_total_tokens(result),
                getattr(result, "stop_reason", None),
            )
            return result

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
            logger.exception(
                "LLM call failed model=%s output_format=%s duration=%.2fs error_type=%s error=%s",
                inner.model,
                format_name,
                time.monotonic() - start_time,
                type(e).__name__,
                e,
            )
            raise ModelProviderError(message=str(e), model=inner.name) from e

        choice = response.choices[0] if response.choices else None
        if choice is None:
            logger.error(
                "LLM call failed model=%s output_format=%s duration=%.2fs error=empty_choices",
                inner.model,
                format_name,
                time.monotonic() - start_time,
            )
            raise ModelProviderError(
                message="Empty choices in response", model=inner.name
            )

        content = choice.message.content or ""
        content = _strip_code_block(content)

        try:
            parsed = output_format.model_validate_json(content)
        except Exception as e:
            logger.exception(
                "LLM response parse failed model=%s output_format=%s duration=%.2fs content_prefix=%r error_type=%s error=%s",
                inner.model,
                format_name,
                time.monotonic() - start_time,
                content[:500],
                type(e).__name__,
                e,
            )
            raise ModelProviderError(message=str(e), model=inner.name) from e

        result = ChatInvokeCompletion(
            completion=parsed,
            usage=inner._get_usage(response),
            stop_reason=choice.finish_reason,
        )
        logger.info(
            "LLM call completed model=%s output_format=%s duration=%.2fs total_tokens=%s stop_reason=%s",
            inner.model,
            format_name,
            time.monotonic() - start_time,
            _usage_total_tokens(result),
            result.stop_reason,
        )
        return result


def make_llm() -> _AI233ChatOpenAI:
    from browser_use.llm.openai.chat import ChatOpenAI

    inner = ChatOpenAI(
        model=settings.apply_model,
        api_key=settings.apply_api_key,
        base_url=settings.apply_base_url,
        temperature=0,
        timeout=settings.apply_llm_timeout_seconds,
        max_retries=settings.max_retries,
        default_headers={"User-Agent": "apply-job/llm-debug"},
    )
    return _AI233ChatOpenAI(inner)


@asynccontextmanager
async def browser_session():
    """Yield a BrowserSession connected to the host Chrome via CDP.

    Resolves the CDP hostname to an IP so Chrome accepts the Host header.
    keep_alive=True prevents Agent.close() from killing Chrome between steps.
    Explicitly stops the session on exit to cancel background tasks and avoid
    'Task was destroyed but it is pending!' warnings from asyncio GC.
    """
    import asyncio
    import logging
    from browser_use import BrowserProfile, BrowserSession

    session = BrowserSession(
        cdp_url=resolve_cdp_url(settings.cdp_url),
        browser_profile=BrowserProfile(keep_alive=True),
    )
    try:
        yield session
    finally:
        try:
            await session.stop()
        except Exception as exc:
            logging.debug("browser_session cleanup: %s", exc)

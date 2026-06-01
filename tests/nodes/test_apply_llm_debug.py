import asyncio
import logging

from browser_use.llm.messages import UserMessage
from pydantic import BaseModel

import apply_job.nodes.apply._shared as shared
from apply_job.nodes.apply._shared import _AI233ChatOpenAI


class _FakeInner:
    model = "test-model"
    name = "test-model"
    temperature = None
    frequency_penalty = None
    max_completion_tokens = None
    last_output_format = None

    async def ainvoke(self, messages, output_format=None, **kwargs):
        self.last_output_format = output_format
        return _FakeResult()


class _FakeUsage:
    total_tokens = 12


class _FakeResult:
    usage = _FakeUsage()
    stop_reason = "stop"


def test_ai233_llm_wrapper_logs_text_call_duration(caplog):
    llm = _AI233ChatOpenAI(_FakeInner())

    with caplog.at_level(logging.INFO):
        result = asyncio.run(llm.ainvoke([UserMessage(content="hello")]))

    assert result.stop_reason == "stop"
    assert "LLM call started model=test-model output_format=text" in caplog.text
    assert "LLM call completed model=test-model output_format=text" in caplog.text
    assert "total_tokens=12" in caplog.text


def test_ai233_llm_wrapper_delegates_browser_use_agent_output(caplog):
    class AgentOutput(BaseModel):
        action: list

    AgentOutput.__module__ = "browser_use.agent.views"
    inner = _FakeInner()
    llm = _AI233ChatOpenAI(inner)

    with caplog.at_level(logging.INFO):
        result = asyncio.run(
            llm.ainvoke([UserMessage(content="hello")], output_format=AgentOutput)
        )

    assert result.stop_reason == "stop"
    assert inner.last_output_format is AgentOutput
    assert "LLM call completed model=test-model output_format=AgentOutput" in caplog.text


def test_make_agent_kwargs_passes_configured_timeout(monkeypatch):
    fake_llm = object()
    monkeypatch.setattr(shared, "make_llm", lambda: fake_llm)
    monkeypatch.setattr(shared.settings, "apply_llm_timeout_seconds", 123.0)

    kwargs = shared.make_agent_kwargs()

    assert kwargs == {"llm": fake_llm, "llm_timeout": 123}

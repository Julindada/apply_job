import asyncio
import logging

from browser_use.llm.messages import UserMessage

from apply_job.nodes.apply._shared import _AI233ChatOpenAI


class _FakeInner:
    model = "test-model"
    name = "test-model"
    temperature = None
    frequency_penalty = None
    max_completion_tokens = None

    async def ainvoke(self, messages, output_format=None, **kwargs):
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

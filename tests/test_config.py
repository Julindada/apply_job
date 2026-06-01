import importlib

import apply_job.config as config


def test_apply_model_defaults_to_gpt_5_4_mini(monkeypatch):
    monkeypatch.delenv("APPLY_LLM_MODEL", raising=False)

    reloaded_config = importlib.reload(config)

    assert reloaded_config.settings.apply_model == "gpt-5.4-mini"


def test_apply_model_can_be_overridden_by_env(monkeypatch):
    monkeypatch.setenv("APPLY_LLM_MODEL", "custom-apply-model")

    reloaded_config = importlib.reload(config)

    assert reloaded_config.settings.apply_model == "custom-apply-model"


def test_scoring_llm_uses_ai233_env(monkeypatch):
    monkeypatch.setenv("AI233_KEY", "ai233-key")
    monkeypatch.setenv("AI233_BASE_URL", "https://ai233.example")

    reloaded_config = importlib.reload(config)

    assert reloaded_config.settings.api_key == "ai233-key"
    assert reloaded_config.settings.llm_base_url == "https://ai233.example/v1"


def test_apply_llm_timeout_can_be_overridden_by_env(monkeypatch):
    monkeypatch.setenv("APPLY_LLM_TIMEOUT_SECONDS", "45")

    reloaded_config = importlib.reload(config)

    assert reloaded_config.settings.apply_llm_timeout_seconds == 45

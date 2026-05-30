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

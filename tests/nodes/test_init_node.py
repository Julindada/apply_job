import pytest

import apply_job.nodes.init as init_module


def test_init_node_requires_ai233_key(monkeypatch, tmp_path):
    monkeypatch.setattr(init_module.settings, "data_dir", str(tmp_path))
    monkeypatch.delenv("AI233_KEY", raising=False)
    monkeypatch.setenv("APIFY_API_TOKEN", "apify-token")

    with pytest.raises(EnvironmentError) as exc_info:
        init_module.init_node({})

    assert "AI233_KEY" in str(exc_info.value)

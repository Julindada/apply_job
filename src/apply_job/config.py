import os
from dataclasses import dataclass


@dataclass
class Settings:
    model: str = os.getenv("LLM_MODEL", "qwen3.6-plus")
    apply_model: str = os.getenv("APPLY_LLM_MODEL", "gpt-5.4-mini")
    llm_base_url: str = os.getenv("AI233_BASE_URL", "")
    apply_base_url: str = os.getenv("AI233_BASE_URL", "")
    api_key: str = os.getenv("AI233_KEY", "")
    apply_api_key: str = os.getenv("AI233_KEY", "")
    apify_token: str = os.getenv("APIFY_API_TOKEN", "")
    cdp_url: str = os.getenv("CDP_URL", "http://host.docker.internal:9222")
    data_dir: str = os.getenv("DATA_DIR", "/app/data")
    default_resume_path: str = os.getenv("DEFAULT_RESUME_PATH", "/app/data/resume.pdf")
    apply_llm_timeout_seconds: float = float(
        os.getenv("APPLY_LLM_TIMEOUT_SECONDS", "120")
    )
    temperature: float = 0.0
    max_retries: int = 3

    def __post_init__(self) -> None:
        # OpenAI-compatible clients expect base_url to end with /v1
        self.llm_base_url = self._normalize_base_url(self.llm_base_url)
        self.apply_base_url = self._normalize_base_url(self.apply_base_url)

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        if not base_url:
            return base_url
        url = base_url.rstrip("/")
        if not url.endswith("/v1"):
            return url + "/v1"
        return url


settings = Settings()

import os
from dataclasses import dataclass


@dataclass
class Settings:
    model: str = os.getenv("LLM_MODEL", "qwen3.6-plus")
    apply_model: str = os.getenv("APPLY_LLM_MODEL", "claude-sonnet-4-6")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://dashscope-us.aliyuncs.com/compatible-mode/v1")
    api_key: str = os.getenv("DASHSCOPE_V2_API_KEY", "")
    apify_token: str = os.getenv("APIFY_API_TOKEN", "")
    cdp_url: str = os.getenv("CDP_URL", "http://host.docker.internal:9222")
    data_dir: str = os.getenv("DATA_DIR", "/app/data")
    default_resume_path: str = os.getenv("DEFAULT_RESUME_PATH", "/app/data/resume.pdf")
    temperature: float = 0.0
    max_retries: int = 3


settings = Settings()

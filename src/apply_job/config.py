import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    model: str = os.getenv("LLM_MODEL", "qwen3.6-plus")
    api_key: str = os.getenv("DASHSCOPE_V2_API_KEY", "")
    temperature: float = 0.0
    max_retries: int = 3


settings = Settings()

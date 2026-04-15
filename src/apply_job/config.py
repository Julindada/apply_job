import os
from dataclasses import dataclass


@dataclass
class Settings:
    model: str = os.getenv("LLM_MODEL", "qwen3.6-plus")
    api_key: str = os.getenv("DASHSCOPE_V2_API_KEY", "")
    data_dir: str = os.getenv("DATA_DIR", "data")
    temperature: float = 0.0
    max_retries: int = 3


settings = Settings()

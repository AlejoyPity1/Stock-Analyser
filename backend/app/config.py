from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit, urlunsplit
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]

def loopback_ai_url(value):
    if not isinstance(value, str) or any(c.isspace() for c in value):
        raise ValueError('Expected a loopback LM Studio URL')
    p = urlsplit(value)
    if (p.scheme not in ('http', 'https') or p.hostname not in ('127.0.0.1', '::1', 'localhost')
            or p.username is not None or p.password is not None or p.query or p.fragment
            or p.path.rstrip('/') != '/v1' or not p.port or not 1024 <= p.port <= 65535):
        raise ValueError('Expected a loopback LM Studio URL ending in /v1')
    host = '[::1]' if p.hostname == '::1' else '127.0.0.1'
    return urlunsplit((p.scheme, f'{host}:{p.port}', '/v1', '', ''))

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    database_url: str = f'sqlite:///{ROOT}/stock.db'
    sec_user_agent: str = ''
    finnhub_api_key: str = ''
    alphavantage_api_key: str = ''
    paid_ai_enabled: bool = False
    ai_provider: Literal['disabled', 'local', 'openai'] = 'disabled'
    local_ai_base_url: str = 'http://127.0.0.1:1234/v1'
    local_ai_model: str = 'qwen/qwen3.5-9b'
    local_ai_api_key: str = ''
    local_ai_context_tokens: int = 8192
    local_ai_max_output_tokens: int = 1200
    local_ai_timeout_seconds: int = 180
    local_ai_quick_batches: int = 6
    local_ai_deep_batches: int = 12
    research_api_key: str = ''
    research_model: str = 'gpt-6.1-sol'
    advanced_model: str = 'gpt-6-astra'
    app_token: str = ''
    app_environment: str = 'development'
    cache_seconds: int = 3600
    research_max_articles: int = 30
    research_max_output_tokens: int = 3000
    # Optional verified account pricing: never invent a price for an unknown model.
    ai_input_usd_per_million: float | None = None
    ai_output_usd_per_million: float | None = None
    research_max_usd: float = 0.25

    @field_validator('local_ai_base_url')
    @classmethod
    def local_url(cls, value):
        return loopback_ai_url(value)

    @field_validator('ai_input_usd_per_million', 'ai_output_usd_per_million', mode='before')
    @classmethod
    def blank_price(cls, value):
        return None if value == '' else value

settings = Settings()

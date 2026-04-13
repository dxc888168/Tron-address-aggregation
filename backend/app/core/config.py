from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=('.env', '../.env'),
        env_file_encoding='utf-8',
        extra='ignore',
    )

    app_name: str = 'Tron Collector'
    app_env: str = 'dev'
    app_host: str = '0.0.0.0'
    app_port: int = 8000

    database_url: str = 'sqlite:///./tron_collector.db'
    redis_url: str = 'redis://localhost:6379/0'
    job_execution_mode: str = 'inline'  # inline | redis
    auth_disabled: bool = True

    jwt_secret: str = 'replace_me'
    jwt_algorithm: str = 'HS256'
    jwt_expire_minutes: int = 120

    admin_username: str = 'admin'
    admin_password: str = 'admin123456'

    encryption_master_key: str = ''

    trongrid_api_key: str = ''
    tron_network: str = 'mainnet'
    usdt_contract: str = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'

    default_trx_reserve_sun: int = 500_000
    default_trx_min_sweep_sun: int = 1_000_000
    default_usdt_min_sweep_raw: int = 1_000_000
    default_usdt_fee_limit_sun: int = 20_000_000


@lru_cache
def get_settings() -> Settings:
    return Settings()

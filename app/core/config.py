from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
    # db_url
    database_url: str

    # api_url
    backend_api_url: str

    # redis_url
    redis_url: str

    # frontend_url
    frontend_url: str

    # kafka_bootstrap_server
    kafka_bootstrap_servers: str


settings = Settings()
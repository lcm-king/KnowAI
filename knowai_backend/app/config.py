from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "KnowAI Backend"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api"

    mysql_host: str = Field(default="localhost", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_user: str = Field(default="root", alias="MYSQL_USER")
    mysql_password: str = Field(default="123456", alias="MYSQL_PASSWORD")
    mysql_database: str = Field(default="knowai", alias="MYSQL_DATABASE")

    mongodb_url: str = Field(default="mongodb://localhost:27017", alias="MONGODB_URL")
    mongodb_db: str = Field(default="knowai", alias="MONGODB_DB")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    elasticsearch_host: str = Field(default="localhost", alias="ELASTICSEARCH_HOST")
    elasticsearch_port: int = Field(default=9200, alias="ELASTICSEARCH_PORT")

    jwt_secret_key: str = Field(default="your-secret-key-change-this", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60 * 24 * 7, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    order_expire_minutes: int = Field(default=30, alias="ORDER_EXPIRE_MINUTES")

    weixin_appid: str = Field(default="wx123", alias="WEIXIN_APPID")
    weixin_mchid: str = Field(default="123", alias="WEIXIN_MCHID")
    weixin_key: str = Field(default="yourkey", alias="WEIXIN_KEY")
    alipay_appid: str = Field(default="202100", alias="ALIPAY_APPID")
    alipay_private_key: str = Field(default="", alias="ALIPAY_PRIVATE_KEY")
    alipay_public_key: str = Field(default="", alias="ALIPAY_PUBLIC_KEY")
    alipay_sandbox: bool = Field(default=False, alias="ALIPAY_SANDBOX")
    notify_url: str = Field(default="https://yourdomain.com/api/pay/notify", alias="NOTIFY_URL")
    pay_mock: bool = Field(default=True, alias="PAY_MOCK")
    dify_api_url: str = Field(default="https://api.dify.ai/v1", alias="DIFY_API_URL")
    dify_api_key: str = Field(default="", alias="DIFY_API_KEY")

    # 容联云通讯 SMS
    cloopen_account_sid: str = Field(default="", alias="CLOOPEN_ACCOUNT_SID")
    cloopen_auth_token: str = Field(default="", alias="CLOOPEN_AUTH_TOKEN")
    cloopen_app_id: str = Field(default="", alias="CLOOPEN_APP_ID")
    cloopen_template_id: str = Field(default="", alias="CLOOPEN_TEMPLATE_ID")
    cloopen_rest_url: str = Field(default="https://app.cloopen.com:8883", alias="CLOOPEN_REST_URL")
    sms_mock: bool = Field(default=True, alias="SMS_MOCK")

    # ── AI / LangChain ──
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_api_key: str = Field(default="", alias="EMBEDDING_API_KEY")
    embedding_base_url: str | None = Field(default=None, alias="EMBEDDING_BASE_URL")
    vector_db_path: str = Field(default="./chroma_db", alias="VECTOR_DB_PATH")

    upload_dir: Path = Field(default=Path("/app/uploads"), alias="UPLOAD_DIR")

    allowed_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        alias="ALLOWED_ORIGINS",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", populate_by_name=True, extra="ignore")

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def mongo_url(self) -> str:
        return self.mongodb_url

    @property
    def mongo_db_name(self) -> str:
        return self.mongodb_db

    @property
    def access_token_expire_seconds(self) -> int:
        return self.access_token_expire_minutes * 60

    @property
    def elasticsearch_url(self) -> str:
        return f"http://{self.elasticsearch_host}:{self.elasticsearch_port}"

    @property
    def cors_origin_list(self) -> list[str]:
        return self.allowed_origins


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

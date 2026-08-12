from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/glimmer"

    # JWT
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_seconds: int = 604800  # 7 days

    # SMS
    alibaba_access_key_id: str = ""
    alibaba_access_key_secret: str = ""
    alibaba_sms_sign_name: str = ""
    alibaba_sms_template_code: str = ""

    # OSS
    oss_endpoint: str = ""
    oss_bucket: str = ""
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""

    # App
    app_env: str = "development"
    debug: bool = True

    # Phone hash salt
    phone_hash_salt: str = "dev-salt-change-in-production"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

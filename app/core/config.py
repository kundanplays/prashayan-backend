from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "Prashayan API"
    DATABASE_URL: str = "sqlite:///./prashayan.db"
    SECRET_KEY: str = "supersecretkey_change_me_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 1 week

    # Razorpay
    RAZORPAY_KEY_ID: str = "rzp_test_placeholder"
    RAZORPAY_KEY_SECRET: str = "rzp_secret_placeholder"
    RAZORPAY_WEBHOOK_SECRET: str = "webhook_secret"

    # Zoho Mail (mapped from .env)
    MAIL_USERNAME: str = Field("orders@prashayan.com", validation_alias="MAIL_USERNAME")
    MAIL_PASSWORD: str = Field("LWAdW5MjYtL5", validation_alias="APP_PASSWORD")
    MAIL_FROM: str = Field("orders@prashayan.com", validation_alias="MAIL_FROM")
    MAIL_PORT: int = Field(465, validation_alias="PORT")
    MAIL_SERVER: str = Field("smtppro.zoho.in", validation_alias="Outgoing_Server_Name")
    MAIL_TLS: bool = Field(False, validation_alias="MAIL_TLS")
    MAIL_SSL: bool = Field(True, validation_alias="MAIL_SSL")

    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET: str = "prashayan-s3-aws"

    @property
    def S3_BASE_URL(self) -> str:
        return f"https://{self.S3_BUCKET}.s3.{self.AWS_REGION}.amazonaws.com"

    class Config:
        env_file = ".env"
        extra = "ignore" 


settings = Settings()


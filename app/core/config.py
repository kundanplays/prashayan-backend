from pydantic_settings import BaseSettings

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

    # Zoho Mail
    MAIL_USERNAME: str = "orders@prashayan.com"
    MAIL_PASSWORD: str = "zoho_password_placeholder"
    MAIL_FROM: str = "orders@prashayan.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.zoho.com"
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore" # Allow extra fields in .env

settings = Settings()

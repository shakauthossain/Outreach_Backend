"""
Application configuration management using Pydantic Settings.
All sensitive credentials and configuration values are loaded from environment variables.
"""
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings with validation and type checking.
    Automatically loads from .env file and environment variables.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    APP_NAME: str = "NH Outreach Agent API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    RELOAD: bool = False
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["https://outreach.hellonotionhive.com"]
    ALLOW_CREDENTIALS: bool = True
    ALLOWED_METHODS: List[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    ALLOWED_HEADERS: List[str] = ["*"]
    
    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_PRE_PING: bool = True
    DB_ECHO: bool = False
    
    # Redis
    REDIS_URL: str
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_DECODE_RESPONSES: bool = True
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
    
    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    CELERY_TASK_TIME_LIMIT: int = 600
    CELERY_TASK_SOFT_TIME_LIMIT: int = 540
    CELERY_TASK_ACKS_LATE: bool = True
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1
    
    # Cache TTL (seconds)
    CACHE_TTL_LEADS: int = 120
    CACHE_TTL_STATISTICS: int = 300
    CACHE_TTL_INBOX: int = 180
    CACHE_TTL_PAGESPEED: int = 86400  # 24 hours
    CACHE_TTL_SCRAPING: int = 21600   # 6 hours
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_SPEEDTEST: str = "10/minute"
    RATE_LIMIT_MAIL_GENERATE: str = "20/hour"
    RATE_LIMIT_RECOMMENDATIONS: str = "10/minute"
    RATE_LIMIT_PUNCHLINES: str = "15/hour"
    RATE_LIMIT_UPLOAD: str = "5/minute"
    
    # External APIs
    PAGESPEED_API_KEY: str
    PAGESPEED_API_URL: str = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    PAGESPEED_TIMEOUT: int = 60
    
    GHL_API_KEY: str
    GHL_API_BASE_URL: str = "https://rest.gohighlevel.com/v1"
    GHL_LOCATION_ID: str
    GHL_TIMEOUT: int = 30
    
    SENDGRID_API_KEY: str
    SENDGRID_FROM_EMAIL: str
    SENDGRID_FROM_NAME: str = "NH Outreach"
    
    FIRECRAWL_API_KEY: str
    FIRECRAWL_API_URL: str = "https://api.firecrawl.dev/v0/scrape"
    FIRECRAWL_TIMEOUT: int = 45
    
    # LLM Providers
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_TIMEOUT: int = 60
    
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    GROQ_TIMEOUT: int = 60
    
    DEFAULT_LLM_PROVIDER: str = "gemini"  # gemini or groq
    
    # File Upload
    UPLOAD_DIR: str = "./uploaded_csvs"
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".csv"]
    
    # Screenshots
    SCREENSHOT_DIR: str = "./static"
    SCREENSHOT_TIMEOUT: int = 30000  # milliseconds
    SCREENSHOT_QUALITY: int = 80
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text
    LOG_FILE: Optional[str] = None
    
    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 500
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL (for Alembic)"""
        return self.DATABASE_URL.replace("+asyncpg", "").replace("+psycopg", "")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENVIRONMENT == "development"
    
    def model_post_init(self, __context) -> None:
        """Validate configuration after initialization"""
        # Ensure SECRET_KEY is set and strong
        if not self.SECRET_KEY or len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        
        # Ensure required API keys are set
        required_keys = [
            "PAGESPEED_API_KEY",
            "GHL_API_KEY",
            "SENDGRID_API_KEY",
            "FIRECRAWL_API_KEY",
            "GEMINI_API_KEY",
            "GROQ_API_KEY"
        ]
        
        for key in required_keys:
            if not getattr(self, key):
                if self.is_production:
                    raise ValueError(f"{key} is required in production environment")
                else:
                    print(f"⚠️  Warning: {key} is not set")


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Use this function to access settings throughout the application.
    """
    return Settings()


# Convenience alias
settings = get_settings()

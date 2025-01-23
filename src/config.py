from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Web Migration System"
    
    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    
    # Elasticsearch
    ELASTICSEARCH_HOST: str
    ELASTICSEARCH_PORT: int = 9200
    ELASTICSEARCH_USERNAME: Optional[str] = None
    ELASTICSEARCH_PASSWORD: Optional[str] = None
    
    # Contentful
    CONTENTFUL_SPACE_ID: str
    CONTENTFUL_ACCESS_TOKEN: str
    CONTENTFUL_ENVIRONMENT: str = "master"
    
    # Scraping
    MAX_CONCURRENT_SCRAPES: int = 5
    SCRAPING_DELAY: float = 1.0  # seconds
    TARGET_DOMAIN: str
    
    class Config:
        env_file = ".env"

settings = Settings() 
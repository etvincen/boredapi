from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    
    # Target Website
    TARGET_DOMAIN: str = "https://www.roc-eclerc.fr"
    MAX_CONCURRENT_SCRAPES: int = 5
    SCRAPING_DELAY: float = 1.0  # seconds
    
    # Elasticsearch Settings
    ELASTICSEARCH_HOST: str = "localhost"
    ELASTICSEARCH_PORT: int = 9200
    ELASTICSEARCH_USER: Optional[str] = None
    ELASTICSEARCH_PASSWORD: Optional[str] = None
    ELASTICSEARCH_USE_SSL: bool = False
    
    # Kibana Settings
    KIBANA_HOST: str = "localhost"
    KIBANA_PORT: int = 5601
    KIBANA_USER: str = "elastic"
    KIBANA_PASSWORD: str = "elastic"
    
    class Config:
        env_file = ".env"

settings = Settings() 
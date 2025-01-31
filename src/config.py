from pydantic_settings import BaseSettings
from pydantic import BaseModel, field_validator
from typing import Optional, List

# All of these are defaults, and can be overridden in the .env file

class APISettings(BaseModel):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

class CrawlerSettings(BaseModel):
    TARGET_DOMAIN: str = "https://roc-eclerc.com/"
    MAX_CONCURRENT_SCRAPES: int = 3
    SCRAPING_DELAY: float = 2.0
    URL_BLACKLIST_PATTERNS: List[str] = ["nos-agences", "avis-de-deces"]

    @field_validator('URL_BLACKLIST_PATTERNS', mode='before')
    @classmethod
    def parse_blacklist_patterns(cls, v):
        if isinstance(v, str):
            return [p.strip() for p in v.split(',') if p.strip()]
        return v

class ElasticsearchSettings(BaseModel):
    HOST: str = "localhost"
    PORT: int = 9200
    USERNAME: str = "elastic"
    PASSWORD: str = "elastic123"
    USE_SSL: bool = False

class KibanaSettings(BaseModel):
    HOST: str = "localhost"
    PORT: int = 5601
    USER: str = "kibana_system"
    PASSWORD: str = "kibana123"

class ContentfulSettings(BaseModel):
    SPACE_ID: str = "1234567890"
    ACCESS_TOKEN: str = "1234567890"
    ENVIRONMENT: str = "master"

class Settings(BaseSettings):
    api: APISettings = APISettings()
    crawler: CrawlerSettings = CrawlerSettings()
    elasticsearch: ElasticsearchSettings = ElasticsearchSettings()
    kibana: KibanaSettings = KibanaSettings()
    contentful: ContentfulSettings = ContentfulSettings()

    model_config = {
        "env_file": ".env",
        "env_nested_delimiter": "__",
        "env_prefix": "",
        "extra": "ignore"
    }

settings = Settings() 
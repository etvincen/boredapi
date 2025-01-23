import contentful_management
from typing import Dict, Any, List, Optional
import structlog
from src.config import settings

logger = structlog.get_logger()

class ContentfulClient:
    def __init__(self):
        self.client = contentful_management.Client(
            settings.CONTENTFUL_ACCESS_TOKEN
        )
        self.space = self.client.spaces().find(settings.CONTENTFUL_SPACE_ID)
        self.environment = self.space.environments().find(settings.CONTENTFUL_ENVIRONMENT)
        
    async def create_content_types(self):
        """Create required content types in Contentful"""
        content_types = {
            'article': {
                'name': 'Article',
                'fields': [
                    {'id': 'title', 'name': 'Title', 'type': 'Symbol', 'required': True},
                    {'id': 'content', 'name': 'Content', 'type': 'Text', 'required': True},
                    {'id': 'url', 'name': 'Original URL', 'type': 'Symbol'},
                    {'id': 'metadata', 'name': 'Metadata', 'type': 'Object'},
                ]
            },
            'faq': {
                'name': 'FAQ',
                'fields': [
                    {'id': 'question', 'name': 'Question', 'type': 'Symbol', 'required': True},
                    {'id': 'answer', 'name': 'Answer', 'type': 'Text', 'required': True},
                ]
            },
            'product': {
                'name': 'Product',
                'fields': [
                    {'id': 'name', 'name': 'Name', 'type': 'Symbol', 'required': True},
                    {'id': 'description', 'name': 'Description', 'type': 'Text', 'required': True},
                    {'id': 'features', 'name': 'Features', 'type': 'Array', 'items': {'type': 'Symbol'}},
                ]
            }
        }
        
        for content_type_id, content_type_data in content_types.items():
            try:
                content_type = self.environment.content_types().create(
                    content_type_id,
                    {
                        'name': content_type_data['name'],
                        'fields': content_type_data['fields']
                    }
                )
                content_type.publish()
                logger.info(f"Created content type: {content_type_id}")
            except Exception as e:
                logger.error(f"Error creating content type: {content_type_id}", error=str(e))
    
    async def create_entry(self, content_type: str, fields: Dict[str, Any]) -> str:
        """Create a new entry in Contentful"""
        try:
            entry = self.environment.entries().create(
                content_type,
                {
                    'fields': {
                        k: {'en-US': v} for k, v in fields.items()
                    }
                }
            )
            entry.publish()
            return entry.id
        except Exception as e:
            logger.error("Error creating Contentful entry", 
                        content_type=content_type,
                        error=str(e))
            raise 
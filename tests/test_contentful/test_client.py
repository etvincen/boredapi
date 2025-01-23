import pytest
from src.contentful.client import ContentfulClient

@pytest.mark.asyncio
async def test_create_content_types():
    client = ContentfulClient()
    await client.create_content_types()
    
    # Verify content types were created
    content_types = client.environment.content_types().all()
    content_type_ids = [ct.id for ct in content_types]
    
    assert "article" in content_type_ids
    assert "faq" in content_type_ids
    assert "product" in content_type_ids

@pytest.mark.asyncio
async def test_create_entry():
    client = ContentfulClient()
    
    test_article = {
        "title": "Test Article",
        "content": "Test content",
        "url": "https://test.com/article1",
        "metadata": {"word_count": 100}
    }
    
    entry_id = await client.create_entry("article", test_article)
    assert entry_id is not None
    
    # Verify entry was created
    entry = client.environment.entries().find(entry_id)
    assert entry.fields()["title"]["en-US"] == test_article["title"] 
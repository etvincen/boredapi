import pytest
from src.storage.elasticsearch import ElasticsearchClient

@pytest.mark.asyncio
async def test_store_and_retrieve_content():
    client = ElasticsearchClient()
    test_content = {
        "url": "https://test.com/article1",
        "title": "Test Article",
        "content": "Test content",
        "type": "article"
    }
    
    # Store content
    content_id = await client.store_content(test_content)
    assert content_id is not None
    
    # Retrieve content
    retrieved = await client.get_content_by_id(content_id)
    assert retrieved["title"] == test_content["title"]
    assert retrieved["content"] == test_content["content"]

@pytest.mark.asyncio
async def test_search_content():
    client = ElasticsearchClient()
    
    # Search with pagination
    results = await client.search_content(
        query="test",
        content_type="article",
        page=1,
        size=10
    )
    
    assert "total" in results
    assert "items" in results
    assert isinstance(results["items"], list) 
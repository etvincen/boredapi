import pytest
from src.scraper.crawler import WebCrawler
from playwright.async_api import async_playwright

@pytest.mark.asyncio
async def test_crawler_initialization():
    crawler = WebCrawler()
    assert crawler.visited_urls == set()
    assert crawler.results == []

@pytest.mark.asyncio
async def test_extract_content(mock_page):
    crawler = WebCrawler()
    content = await crawler.extract_content(mock_page)
    
    assert "url" in content
    assert "title" in content
    assert "content" in content
    assert "media" in content
    assert "metadata" in content

@pytest.mark.asyncio
async def test_extract_media(mock_page):
    crawler = WebCrawler()
    media = await crawler._extract_media(mock_page)
    
    assert isinstance(media, list)
    for item in media:
        assert "type" in item
        assert "url" in item 
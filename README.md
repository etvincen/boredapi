# Roc Eclerc Content Pipeline

A complete pipeline for crawling, processing, indexing, and searching content with semantic capabilities.

## Architecture Overview

```
Playwright Crawler → Content Processor → Elasticsearch + Embeddings → FastAPI Search Service
```

## Features

### 1. Content Crawling
- JavaScript-rendered content support via Playwright
- Structured content extraction (sections, subsections)
- Media and link tracking
- Rate limiting and robots.txt compliance

### 2. Content Processing
- Text extraction and cleaning
- Section hierarchy preservation
- Statistics generation:
  * Word and sentence counts
  * Internal/external link counts
  * Media asset tracking
  * Section structure analysis

### 3. Intelligent Indexing
- Hybrid storage with Elasticsearch
- Vector embeddings (SBERT all-MiniLM-L6-v2)
- Text chunking for optimal embedding
- Content statistics and metadata
- Automatic backup/restore capabilities

### 4. Semantic Search API
- Hybrid search combining:
  * BM25 text similarity
  * Vector similarity (cosine)
  * Smart result ranking
- Auto-suggestions
- Performance metrics
- OpenAPI documentation

## Prerequisites
- Python 3.12+
- Docker and Docker Compose
- ~1GB free memory
- Poetry for dependency management

## Quick Start Guide

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/etvincen/boredapi
cd boredapi

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### 2. Poetry Setup

```bash
# Configure Poetry
poetry config virtualenvs.path
poetry config virtualenvs.in-project true

# Install dependencies and generate lock file
poetry install

# Activate the virtual environment
source .venv/bin/activate

# Install Playwright browser
poetry run playwright install chromium
```

### 3. Running the Pipeline

```bash
# 1. Start the services
docker-compose -f docker/docker-compose.dev.yml up -d

# 2. Run the crawler
poetry run python -m src.cli.crawler_cli

# 3. Ingest data into Elasticsearch
poetry run python -m src.cli.ingest_data
```

### 4. Verify Installation

- Check Elasticsearch: http://localhost:9200
- Check Kibana: http://localhost:5601
- Check API docs: http://localhost:8000/docs

### 5. Search API
The API runs at http://localhost:8000 with these endpoints:

#### Search
```bash
curl "http://localhost:8000/search?q=Comment%20pr%C3%A9parer%20ses%20obs%C3%A8ques&size=3"
```
Parameters:
- `q`: Search query (required)
- `size`: Number of results (default: 10)
- `min_score`: Minimum score threshold
- `include_stats`: Include document statistics

#### Suggestions
```bash
curl "http://localhost:8000/suggest?q=obs&size=5"
```

#### Documentation
- OpenAPI docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Performance

### Resource Usage
- Elasticsearch: 400MB memory
- Search API: 384MB memory
- Kibana: 384MB memory

### Processing Speed
- Crawling: ~1-2 pages/second
- Indexing: ~5-10 documents/second
- Search latency: ~200-500ms

### Capacity
- Tested with:
  * ~40 pages
  * ~5000-8000 words per page
  * ~200KB average document size

## Development

### Testing
```bash
# Test embeddings
poetry run python src/nlp/test_embeddings.py

# Test search
poetry run python src/nlp/test_vector_search.py
```

### Monitoring
- Elasticsearch: http://localhost:9200
- Kibana: http://localhost:5601

## Limitations

Current known limitations:
1. Single-node Elasticsearch (development setup)
2. Limited to ~5 chunks per document for embeddings
3. Basic auto-suggestions (title-based only)
4. No authentication on the search API
5. Memory-optimized for small-medium content sets

## Future Improvements

Potential enhancements:
1. Multi-node Elasticsearch setup
2. Advanced query understanding
3. Search result highlighting
4. User feedback integration
5. Authentication and rate limiting
6. Content type facets and filters
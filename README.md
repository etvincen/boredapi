# Web Content Migration System

A robust web scraping and content migration system that automatically crawls websites and migrates content to Contentful CMS, with built-in storage limits and monitoring.

## Overview

This system provides:
- Automated web content scraping (with 1GB storage limit)
- Content migration to Contentful CMS
- Search capabilities via Elasticsearch
- Progress tracking in PostgreSQL
- Monitoring with Prometheus metrics

## Environment Setup

The system supports two environments:

### Development Environment (default)
- Python code runs locally through Poetry
- Databases (Elasticsearch, PostgreSQL) run in containers
- Hot-reloading enabled for faster development
- Access databases directly on localhost ports

```bash
# Start development databases
./scripts/manage.sh start

# Run crawler locally
./scripts/manage.sh crawler

# Ingest data to databases
./scripts/manage.sh ingest
```

### Production Environment
- All components run in containers
- Proper service orchestration
- Automatic health checks
- Internal container networking

```bash
# Start production environment
ENV=prod ./scripts/manage.sh start

# Run crawler in container
ENV=prod ./scripts/manage.sh crawler

# Ingest data in container
ENV=prod ./scripts/manage.sh ingest
```

## Quick Start

1. Clone the repository:
    git clone <repository-url>
    cd web-migration-system

2. Configure environment:
    cp .env.example .env
    # Edit .env with your values:
    # - TARGET_DOMAIN: Website to scrape
    # - CONTENTFUL credentials
    # - Database settings

3. Choose your environment:
   - For development (default): ./scripts/manage.sh start
   - For production: ENV=prod ./scripts/manage.sh start

## Key Features

- **Smart Scraping**:
  - Concurrent scraping with configurable workers
  - Automatic content type detection
  - Storage limit monitoring (1GB max)
  - Rate limiting and retry mechanisms

- **Content Processing**:
  - Structured content extraction
  - Media asset handling
  - Metadata collection
  - Content hierarchy preservation

- **Storage & Search**:
  - Elasticsearch for content storage and search
  - PostgreSQL for migration tracking
  - Automatic cleanup when approaching storage limits

- **Monitoring**:
  - Real-time progress tracking
  - Storage usage alerts
  - Service health monitoring
  - Prometheus metrics integration

## Development Workflow

1. Start development environment:
```bash
./scripts/manage.sh start  # Starts Elasticsearch and PostgreSQL containers
```

2. Run crawler locally:
```bash
./scripts/manage.sh crawler  # Uses local Python with Poetry
```

3. Ingest data:
```bash
./scripts/manage.sh ingest  # Processes latest results into databases
```

4. View logs:
```bash
./scripts/manage.sh logs
```

## Production Workflow

1. Start production environment:
```bash
ENV=prod ./scripts/manage.sh start  # Starts all containers
```

2. Run crawler in container:
```bash
ENV=prod ./scripts/manage.sh crawler
```

3. Ingest data:
```bash
ENV=prod ./scripts/manage.sh ingest
```

4. Monitor:
```bash
ENV=prod ./scripts/manage.sh logs
```

## Environment Differences

Development:
- Local Python execution (faster development)
- Direct database access (localhost:5432, localhost:9200)
- Development volume mounts
- Hot-reloading enabled

Production:
- Fully containerized
- Internal container networking
- Production volume mounts
- Health checks enforced

## API Endpoints

- GET /api/v1/content/search - Search content
- GET /api/v1/content/{id} - Get specific content
- POST /api/v1/migration/start - Start migration
- GET /api/v1/migration/status - Get migration status
- GET /api/v1/health - Service health check

## Configuration

Key environment variables:

# Scraping
TARGET_DOMAIN=https://example.com
MAX_CONCURRENT_SCRAPES=5
SCRAPING_DELAY=1.0

# Contentful
CONTENTFUL_SPACE_ID=your-space-id
CONTENTFUL_ACCESS_TOKEN=your-token
CONTENTFUL_ENVIRONMENT=master

# Storage
POSTGRES_SERVER=localhost  # (dev) or db (prod)
ELASTICSEARCH_HOST=localhost  # (dev) or elasticsearch (prod)

## Project Structure

web_migration_system/
├── docker/          # Docker configuration
│   ├── docker-compose.dev.yml   # Development setup
│   └── docker-compose.prod.yml  # Production setup
├── scripts/         # Management scripts
├── src/
│   ├── api/        # FastAPI application
│   ├── cli/        # Command-line tools
│   ├── scraper/    # Web scraping logic
│   ├── storage/    # Database clients
│   ├── contentful/ # CMS integration
│   └── monitoring/ # Metrics collection
└── tests/          # Test suites

## Monitoring & Alerts

The system monitors:
- Storage usage (warns at 80%, stops at 100% of 1GB)
- Service health
- Migration progress
- Error rates
- Processing times

## Dependencies

- Python 3.12
- PostgreSQL 15
- Elasticsearch 8.11
- Playwright (for web scraping)
- FastAPI (for API layer)
- Poetry (for dependency management)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: ./scripts/manage.sh test
5. Submit a pull request

## License

[Your License Here] 
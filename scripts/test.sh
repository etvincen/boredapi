#!/bin/bash

# Run tests with coverage
poetry run pytest tests/ --cov=src --cov-report=term-missing

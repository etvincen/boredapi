from typing import Dict, Any

def get_elasticsearch_mappings() -> Dict[str, Any]:
    """Get Elasticsearch mappings for web content"""
    return {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "refresh_interval": "1s",
            "analysis": {
                "analyzer": {
                    "french_exact": {  # For exact token matching
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase"
                        ]
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "url": {
                    "type": "keyword"
                },
                "title": {
                    "type": "text"
                },
                "raw_text": {
                    "type": "text"
                },
                "preprocessed_keywords": {
                    "type": "text",
                    "analyzer": "french_exact",
                    "similarity": "BM25"  # Explicitly set BM25 similarity
                },
                "topics": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "keyword"
                        },
                        "probability": {
                            "type": "float"
                        }
                    }
                },
                "statistics": {
                    "properties": {
                        "word_count": {
                            "type": "integer"
                        },
                        "sentence_count": {
                            "type": "integer"
                        },
                        "section_count": {
                            "type": "integer"
                        },
                        "external_link_count": {
                            "type": "integer"
                        },
                        "internal_link_count": {
                            "type": "integer"
                        },
                        "image_count": {
                            "type": "integer"
                        },
                        "avg_words_per_sentence": {
                            "type": "float"
                        }
                    }
                }
            }
        }
    }

def get_index_name() -> str:
    """Get the name of the Elasticsearch index"""
    return "roc_eclerc_content"

def get_index_settings() -> Dict[str, Any]:
    """Get index creation settings"""
    return get_elasticsearch_mappings() 
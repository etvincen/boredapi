from typing import Dict, Any

def get_elasticsearch_mappings() -> Dict[str, Any]:
    """Get Elasticsearch mappings for web content"""
    return {
        "settings": {
            "analysis": {
                "analyzer": {
                    "french_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",
                            "french_elision",
                            "french_stop",
                            "french_stemmer"
                        ]
                    }
                },
                "filter": {
                    "french_elision": {
                        "type": "elision",
                        "articles_case": True,
                        "articles": [
                            "l", "m", "t", "qu", "n", "s", "j", "d", "c", "jusqu", "quoiqu",
                            "lorsqu", "puisqu"
                        ]
                    },
                    "french_stop": {
                        "type": "stop",
                        "stopwords": "_french_"
                    },
                    "french_stemmer": {
                        "type": "stemmer",
                        "language": "light_french"
                    }
                }
            },
            "index": {
                "mapping": {
                    "total_fields": {
                        "limit": 2000
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                # Basic page information
                "url": {
                    "type": "keyword",
                    "index": True,
                    "doc_values": True
                },
                "timestamp": {
                    "type": "date",
                    "format": "strict_date_optional_time||epoch_millis",
                    "doc_values": True
                },
                "title": {
                    "type": "text",
                    "analyzer": "french_analyzer",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256,
                            "doc_values": True
                        }
                    }
                },
                
                # Meta tags
                "meta_tags": {
                    "properties": {
                        "description": {
                            "type": "text",
                            "analyzer": "french_analyzer"
                        },
                        "keywords": {
                            "type": "text",
                            "analyzer": "french_analyzer",
                            "fields": {
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            }
                        }
                    }
                },
                
                # Content
                "content": {
                    "properties": {
                        "text": {
                            "type": "text",
                            "analyzer": "french_analyzer",
                            "fielddata": True  # Enable for aggregations
                        },
                        "section_titles": {
                            "type": "text",
                            "analyzer": "french_analyzer",
                            "fields": {
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256,
                                    "doc_values": True
                                }
                            }
                        }
                    }
                },
                
                # Metadata
                "metadata": {
                    "properties": {
                        "language": {
                            "type": "keyword",
                            "doc_values": True
                        },
                        "last_updated": {
                            "type": "date",
                            "format": "strict_date_optional_time||epoch_millis",
                            "doc_values": True
                        },
                        "word_count": {
                            "type": "integer",
                            "doc_values": True
                        },
                        "section_count": {
                            "type": "integer",
                            "doc_values": True
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
    mappings = get_elasticsearch_mappings()
    return {
        "settings": mappings["settings"],
        "mappings": mappings["mappings"]
    } 
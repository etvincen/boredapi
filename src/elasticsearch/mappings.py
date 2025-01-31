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
                "max_result_window": 10000,
                "mapping": {
                    "nested_fields": {
                        "limit": 100
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                # Basic page information
                "url": {"type": "keyword"},
                "timestamp": {"type": "date"},
                "title": {
                    "type": "text",
                    "analyzer": "french_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                
                # Meta tags
                "meta_tags": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "text",
                            "analyzer": "french_analyzer"
                        },
                        "keywords": {
                            "type": "text",
                            "analyzer": "french_analyzer"
                        }
                    }
                },
                
                # Main content
                "main_content": {
                    "properties": {
                        "text": {
                            "type": "text",
                            "analyzer": "french_analyzer"
                        },
                        "sections": {
                            "type": "nested",
                            "include_in_root": False,
                            "properties": {
                                "title": {
                                    "type": "text",
                                    "analyzer": "french_analyzer",
                                    "fields": {
                                        "keyword": {"type": "keyword"}
                                    }
                                },
                                "text": {
                                    "type": "text",
                                    "analyzer": "french_analyzer"
                                },
                                "level": {"type": "integer"},
                                "images": {
                                    "type": "nested",
                                    "include_in_root": False,
                                    "properties": {
                                        "src": {"type": "keyword"},
                                        "alt": {"type": "text"},
                                        "title": {"type": "text"},
                                        "width": {"type": "keyword"},
                                        "height": {"type": "keyword"}
                                    }
                                },
                                "subsections": {
                                    "type": "nested",
                                    "include_in_root": False
                                }
                            }
                        }
                    }
                },
                
                # Content statistics
                "content_stats": {
                    "properties": {
                        "word_count": {"type": "integer"},
                        "text_length": {"type": "integer"},
                        "section_count": {"type": "integer"},
                        "sections_by_level": {
                            "properties": {
                                "1": {"type": "integer"},
                                "2": {"type": "integer"},
                                "3": {"type": "integer"}
                            }
                        },
                        "paragraph_count": {"type": "integer"},
                        "sections_with_images": {"type": "integer"},
                        "total_images": {"type": "integer"},
                        "average_section_length": {"type": "float"}
                    }
                },
                
                # Image statistics
                "image_stats": {
                    "properties": {
                        "total_count": {"type": "integer"},
                        "with_alt": {"type": "integer"},
                        "with_dimensions": {"type": "integer"},
                        "types": {
                            "properties": {
                                "content": {"type": "integer"},
                                "logos": {"type": "integer"}
                            }
                        }
                    }
                },
                
                # Section analytics
                "section_analytics": {
                    "properties": {
                        "level_distribution": {
                            "properties": {
                                "1": {"type": "integer"},
                                "2": {"type": "integer"},
                                "3": {"type": "integer"}
                            }
                        },
                        "sections_list": {
                            "type": "nested",
                            "include_in_root": False,
                            "properties": {
                                "title": {"type": "keyword"},
                                "text": {
                                    "type": "text",
                                    "analyzer": "french_analyzer"
                                },
                                "level": {"type": "integer"},
                                "path": {"type": "keyword"},
                                "word_count": {"type": "integer"},
                                "has_images": {"type": "boolean"},
                                "image_count": {"type": "integer"}
                            }
                        }
                    }
                },
                
                # Metadata
                "metadata": {
                    "properties": {
                        "language": {"type": "keyword"},
                        "last_updated": {"type": "date"},
                        "status_code": {"type": "integer"},
                        "content_type": {"type": "keyword"},
                        "response_time": {"type": "float"},
                        "viewport": {"type": "keyword"},
                        "description": {"type": "text", "analyzer": "french_analyzer"},
                        "robots": {"type": "keyword"}
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
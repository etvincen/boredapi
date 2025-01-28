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
                                "images": {
                                    "type": "nested",
                                    "properties": {
                                        "src": {"type": "keyword"},
                                        "alt": {"type": "text"},
                                        "title": {"type": "text"}
                                    }
                                }
                            }
                        }
                    }
                },
                
                # Links analysis
                "links": {
                    "properties": {
                        "internal": {"type": "keyword"},
                        "external": {"type": "keyword"},
                        "resources": {"type": "keyword"}
                    }
                },
                
                # Images
                "images": {
                    "type": "nested",
                    "properties": {
                        "src": {"type": "keyword"},
                        "alt": {"type": "text"},
                        "title": {"type": "text"},
                        "width": {"type": "keyword"},
                        "height": {"type": "keyword"},
                        "loading": {"type": "keyword"},
                        "srcset": {"type": "keyword"}
                    }
                },
                
                # Metadata
                "metadata": {
                    "properties": {
                        "status_code": {"type": "integer"},
                        "content_type": {"type": "keyword"},
                        "crawl_depth": {"type": "integer"},
                        "response_time": {"type": "float"},
                        "language": {"type": "keyword"}
                    }
                },
                
                # Analysis fields
                "content_stats": {
                    "properties": {
                        "text_length": {"type": "integer"},
                        "section_count": {"type": "integer"},
                        "image_count": {"type": "integer"},
                        "internal_link_count": {"type": "integer"},
                        "external_link_count": {"type": "integer"},
                        "resource_link_count": {"type": "integer"}
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
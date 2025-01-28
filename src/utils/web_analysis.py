from bs4 import BeautifulSoup
from PIL import Image
import requests
from io import BytesIO
import json
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import logging
import re
from datetime import datetime
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CrawlResultsAnalyzer:
    """Analyzer for the entire crawl results structure"""
    def __init__(self, crawl_data: Dict[str, Any]):
        self.stats = crawl_data.get('stats', {})
        self.storage = crawl_data.get('storage', {})
        self.config = crawl_data.get('config', {})
        self.results = crawl_data.get('results', [])
        self.web_analyzer = WebContentAnalyzer()
        
    def get_crawl_stats(self) -> Dict[str, Any]:
        """Get statistics about the crawl"""
        return {
            'total_pages': len(self.results),
            'crawl_config': self.config,
            'storage_info': self.storage,
            'crawl_stats': self.stats
        }
    
    def analyze_all_pages(self) -> List[Dict[str, Any]]:
        """Analyze all crawled pages"""
        analyzed_pages = []
        for page in self.results:
            try:
                analyzed_pages.append(self.web_analyzer.analyze_page(page))
            except Exception as e:
                logger.error(f"Error analyzing page {page.get('url', 'unknown')}: {str(e)}")
        return analyzed_pages

class WebContentAnalyzer:
    """Analyzer for individual web pages"""
    def __init__(self):
        self.soup = None
        self.current_url = None
        self.current_page = None
        
    def analyze_page(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single page from crawl results"""
        self.current_page = page_data
        self.current_url = page_data.get('url')
        
        # print(self.current_page.keys())

        # Load HTML content
        html_content = page_data.get('content', '')
        self.load_html(html_content)
        
        return {
            'url': self.current_url,
            'timestamp': page_data.get('timestamp', datetime.now().isoformat()),
            'title': self.extract_title(),
            'meta_tags': self.extract_meta_tags(),
            'main_content': self.extract_main_content(),
            'links': self.extract_links(),
            'images': self.extract_images(),
            'metadata': {
                'status_code': page_data.get('status_code'),
                'headers': page_data.get('headers'),
                'content_type': page_data.get('content_type'),
                'crawl_depth': page_data.get('depth', 0),
                'response_time': page_data.get('response_time'),
                'language': self.detect_language()
            }
        }
        
    def load_html(self, html_content: str) -> BeautifulSoup:
        """Load HTML content into BeautifulSoup object"""
        self.soup = BeautifulSoup(html_content, 'html.parser')
        return self.soup
    
    def extract_title(self) -> Optional[str]:
        """Extract page title with fallbacks"""
        if not self.soup:
            return None
            
        # Try different ways to get the title
        title = None
        # Check for MUI specific title components first
        mui_title = self.soup.find('h1', class_=lambda x: x and 'MuiTypography' in x)
        if mui_title:
            title = mui_title.get_text(strip=True)
        
        if not title and self.soup.title:
            title = self.soup.title.string
            # Remove " - Roc Eclerc" suffix if present
            if title and " - Roc Eclerc" in title:
                title = title.replace(" - Roc Eclerc", "").strip()
                
        if not title:
            og_title = self.soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content')
                
        return title.strip() if title else None
    
    def extract_meta_tags(self) -> Dict[str, str]:
        """Extract all meta tags"""
        if not self.soup:
            return {}
            
        meta_tags = {}
        for meta in self.soup.find_all('meta'):
            name = meta.get('name', meta.get('property', ''))
            content = meta.get('content', '')
            if name and content:
                meta_tags[name] = content
                
        return meta_tags
    
    def extract_main_content(self) -> Dict[str, Any]:
        """Extract main content specifically for ROC Eclerc pages"""
        if not self.soup:
            return {
                'text': '',
                'sections': []
            }
            
        content = {
            'text': '',
            'sections': []
        }
        
        # Find the main content area - ROC Eclerc uses MUI components
        main_content = None
        
        # Try different possible main content containers
        for selector in [
            'main',  # Standard main tag
            'div[class*="MuiContainer-root"]',  # MUI container
            'div[class*="MuiBox-root"]',  # MUI box component
            'div[role="main"]'  # Role-based selection
        ]:
            main_content = self.soup.select_one(selector)
            if main_content:
                logger.info(f"Found main content using selector: {selector}")
                break
                
        if not main_content:
            logger.info("No specific container found, falling back to body")
            main_content = self.soup.body
            
        if main_content:
            # Remove navigation, header, and footer elements
            for element in main_content.select('header, footer, nav, [role="navigation"], [class*="footer"], [class*="header"], [class*="navigation"]'):
                element.decompose()
            
            # Extract sections - ROC Eclerc uses MUI components for sections
            processed_sections = []  # Store BeautifulSoup objects of processed sections
            seen_text = set()  # Track unique text to avoid duplicates
            
            # Look for section-like containers
            potential_sections = main_content.select(
                'section, ' 
                'article, '
                'div[class*="section"], '
                'div[class*="content"], '
                'div[class*="MuiContainer-root"]:not([class*="footer"]):not([class*="header"]), '
                'div[class*="MuiBox-root"]:not([class*="footer"]):not([class*="header"])'
            )
            
            logger.info(f"Found {len(potential_sections)} potential sections")
            
            for section in potential_sections:
                # Skip if this section is nested within another section we've already processed
                is_nested = any(section in processed.descendants for processed in processed_sections)
                if is_nested:
                    continue
                    
                section_content = {
                    'title': '',
                    'text': '',
                    'images': []
                }
                
                # Extract section title - try multiple heading patterns
                for heading in section.select('h1, h2, h3, [class*="MuiTypography-h"]'):
                    title_text = heading.get_text(strip=True)
                    if title_text and not any(skip in title_text.lower() for skip in ['roc eclerc', 'menu', 'navigation', 'footer']):
                        section_content['title'] = title_text
                        logger.info(f"Found section title: {title_text}")
                        break
                
                # Extract text content from paragraphs and text elements
                text_elements = []
                for text_elem in section.select('p, [class*="MuiTypography-root"], [class*="MuiTypography-body"]'):
                    # Skip if element is part of navigation or contains only whitespace
                    text = text_elem.get_text(strip=True)
                    if text and not any(skip in text.lower() for skip in ['menu', 'navigation', 'footer']):
                        # Only add text if we haven't seen it before
                        if text not in seen_text:
                            text_elements.append(text)
                            seen_text.add(text)
                
                section_content['text'] = ' '.join(text_elements)
                
                # Extract images, excluding logos and icons
                for img in section.select('img'):
                    src = img.get('src', '')
                    if src and not any(skip in src.lower() for skip in [
                        'logo', 'icon', 'favicon', 'banner',
                        'Logo_RE', 'Logo_Roc_Assistance', 'Logo_Funecap'
                    ]):
                        section_content['images'].append({
                            'src': src,
                            'alt': img.get('alt', ''),
                            'title': img.get('title', '')
                        })
                
                # Only add section if it has meaningful content
                if (section_content['title'] or 
                    section_content['text'] or 
                    section_content['images']):
                    content['sections'].append(section_content)
                    processed_sections.append(section)  # Keep track of processed BeautifulSoup objects
                    logger.info(f"Added section with {len(section_content['text'])} chars of text and {len(section_content['images'])} images")
            
            # Combine all text for full-text search (using unique text only)
            content['text'] = ' '.join(section['text'] for section in content['sections'])
            logger.info(f"Total extracted text length: {len(content['text'])}")
            
        return content
    
    def detect_language(self) -> str:
        """Detect the language of the page"""
        # Check HTML lang attribute
        html_tag = self.soup.find('html')
        if html_tag and html_tag.get('lang'):
            return html_tag.get('lang')
            
        # Check meta tags
        meta_lang = self.soup.find('meta', {'http-equiv': 'content-language'})
        if meta_lang:
            return meta_lang.get('content')
            
        return 'fr'  # Default to French for ROC Eclerc
    
    def extract_text_content(self, selector: str = None) -> str:
        """Extract clean text content from HTML, optionally using a CSS selector"""
        if not self.soup:
            raise ValueError("No HTML content loaded. Call load_html first.")
        
        if selector:
            elements = self.soup.select(selector)
            text = ' '.join([elem.get_text(strip=True) for elem in elements])
        else:
            # Exclude script and style elements
            for script in self.soup(['script', 'style']):
                script.decompose()
            text = self.soup.get_text(strip=True)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def extract_links(self, internal_domain: str = None) -> Dict[str, List[str]]:
        """Extract all links, optionally filtering for internal/external"""
        if not self.soup:
            raise ValueError("No HTML content loaded. Call load_html first.")
            
        links = self.soup.find_all('a', href=True)
        result = {
            'internal': [],
            'external': [],
            'resources': []  # For media, documents, etc.
        }
        
        # Get base domain from current URL
        if self.current_url:
            parsed_url = urlparse(self.current_url)
            base_domain = parsed_url.netloc
        else:
            base_domain = internal_domain if internal_domain else 'roc-eclerc.com'
        
        for link in links:
            href = link['href']
            # Skip anchor links
            if href.startswith('#'):
                continue
                
            # Normalize URL
            if href.startswith('//'):
                href = f"https:{href}"
            elif href.startswith('/'):
                href = f"https://{base_domain}{href}"
                
            # Parse the URL
            try:
                parsed_href = urlparse(href)
                # Categorize link
                if any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip']):
                    if href not in result['resources']:
                        result['resources'].append(href)
                elif base_domain in parsed_href.netloc:
                    if href not in result['internal']:
                        result['internal'].append(href)
                else:
                    if href not in result['external']:
                        result['external'].append(href)
            except Exception:
                # If URL parsing fails, skip this link
                continue
                
        return result
    
    def extract_images(self) -> List[Dict[str, str]]:
        """Extract image information including src, alt text, and dimensions"""
        if not self.soup:
            raise ValueError("No HTML content loaded. Call load_html first.")
            
        images = self.soup.find_all('img')
        image_data = []
        
        for img in images:
            src = img.get('src', '')
            # Normalize image URL
            if src.startswith('//'):
                src = f"https:{src}"
            elif src.startswith('/'):
                src = f"https://{self.current_url.split('/')[2]}{src}" if self.current_url else src
                
            data = {
                'src': src,
                'alt': img.get('alt', ''),
                'title': img.get('title', ''),
                'width': img.get('width', ''),
                'height': img.get('height', ''),
                'loading': img.get('loading', ''),
                'srcset': img.get('srcset', '')
            }
            image_data.append(data)
            
        return image_data

class ImageAnalyzer:
    @staticmethod
    def analyze_image_from_url(url: str) -> Dict[str, Union[int, str]]:
        """Analyze an image from URL, returning size, format, and basic stats"""
        try:
            response = requests.get(url)
            img = Image.open(BytesIO(response.content))
            
            analysis = {
                'format': img.format,
                'mode': img.mode,
                'size': img.size,
                'width': img.width,
                'height': img.height,
                'aspect_ratio': round(img.width / img.height, 2)
            }
            
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing image from {url}: {str(e)}")
            return {}

def load_crawl_results(file_path: str) -> Dict[str, Any]:
    """Load and parse crawl results from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading crawl results: {str(e)}")
        return {}

def prepare_for_elk(crawl_data: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare crawled data for ELK ingestion"""
    analyzer = CrawlResultsAnalyzer(crawl_data)
    
    # Get crawl metadata
    crawl_stats = analyzer.get_crawl_stats()
    
    # Analyze all pages
    analyzed_pages = analyzer.analyze_all_pages()
    
    # Prepare the complete document
    elk_document = {
        'crawl_metadata': crawl_stats,
        'pages': analyzed_pages,
        'timestamp': datetime.now().isoformat()
    }
    
    return elk_document 
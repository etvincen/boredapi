from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import re
from pathlib import Path

logger = logging.getLogger(__name__)

class ContentParser:
    """Parser to transform raw HTML content into structured data"""
    def __init__(self):
        self.soup = None
        self.current_url = None
        
    def parse_page(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a page into structured content"""
        self.current_url = page_data.get('url')
        html_content = page_data.get('content', '')
        self.soup = BeautifulSoup(html_content, 'html.parser')
        
        # Clean the content first
        self._remove_unwanted_elements()
        
        return {
            'url': self.current_url,
            'title': self._extract_title(),
            'sections': self._extract_sections(),
            'metadata': self._extract_metadata(page_data),
            'content_stats': self._calculate_content_stats(),
            'image_stats': self._calculate_image_stats(),
            'timestamp': datetime.now().isoformat()
        }
    
    def _remove_unwanted_elements(self):
        """Remove scripts, styles, and navigation elements"""
        if not self.soup:
            return
            
        # Remove unwanted elements
        for element in self.soup.select('script, style, nav, header, footer, [role="navigation"]'):
            element.decompose()
            
        # Remove comments
        for comment in self.soup.find_all(string=lambda text: isinstance(text, str) and '<!--' in text):
            comment.extract()
    
    def _extract_title(self) -> Optional[str]:
        """Extract the main title of the page"""
        if not self.soup:
            return None
            
        # Try different title sources
        for title_source in [
            lambda: self.soup.find('h1', class_=lambda x: x and 'MuiTypography' in x),
            lambda: self.soup.title,
            lambda: self.soup.find('meta', property='og:title'),
            lambda: self.soup.find('h1')
        ]:
            element = title_source()
            if element:
                title = element.get('content', '') if isinstance(element, dict) else element.get_text(strip=True)
                if title:
                    return title
        
        return None
    
    def _extract_sections(self) -> List[Dict[str, Any]]:
        """Extract content sections with hierarchy"""
        if not self.soup:
            return []
            
        sections = []
        main_content = self.soup.find(['main', 'article']) or self.soup.body
        if not main_content:
            return []
            
        # Track seen content to avoid duplicates
        seen_text = set()
        current_section = None
        
        # Process all headings and their content
        for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'img', 'a']):
            if element.name.startswith('h'):
                # Start new section when heading is found
                if current_section and (current_section['text'] or current_section['images'] or current_section['links']):
                    sections.append(current_section)
                
                level = int(element.name[1])
                heading_text = element.get_text(strip=True)
                
                current_section = {
                    'title': heading_text,
                    'level': level,
                    'text': '',
                    'images': [],
                    'links': [],
                    'subsections': []
                }
            elif element.name == 'p' and current_section:
                # Add paragraph text to current section
                text = element.get_text(strip=True)
                if text and text not in seen_text:
                    # Add text with proper spacing - ensure single newline between paragraphs
                    if current_section['text']:
                        current_section['text'] = current_section['text'].rstrip() + '\n\n'
                    current_section['text'] += text
                    seen_text.add(text)
                
                # Process any links within the paragraph
                for link in element.find_all('a', href=True):
                    href = link['href']
                    is_internal = not href.startswith(('http', 'https')) or (self.current_url and href.startswith(self.current_url))
                    current_section['links'].append({
                        'url': href,
                        'text': link.get_text(strip=True),
                        'is_internal': is_internal
                    })
            elif element.name == 'img' and current_section:
                # Add image to current section
                src = element.get('src', '')
                if src and not any(skip in src.lower() for skip in ['logo', 'icon', 'favicon']):
                    current_section['images'].append({
                        'src': src,
                        'alt': element.get('alt', ''),
                        'title': element.get('title', ''),
                        'width': element.get('width', ''),
                        'height': element.get('height', '')
                    })
            elif element.name == 'a' and current_section:
                # Process standalone links
                href = element.get('href')
                if href:
                    is_internal = not href.startswith(('http', 'https')) or (self.current_url and href.startswith(self.current_url))
                    current_section['links'].append({
                        'url': href,
                        'text': element.get_text(strip=True),
                        'is_internal': is_internal
                    })
        
        # Add last section if it exists
        if current_section and (current_section['text'] or current_section['images'] or current_section['links']):
            sections.append(current_section)
        
        # Organize sections hierarchically
        return self._organize_sections_hierarchy(sections)
    
    def _organize_sections_hierarchy(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Organize flat sections list into a hierarchical structure"""
        if not sections:
            return []
            
        root_sections = []
        section_stack = []
        
        for section in sections:
            while section_stack and section_stack[-1]['level'] >= section['level']:
                section_stack.pop()
                
            if not section_stack:
                root_sections.append(section)
            else:
                section_stack[-1]['subsections'].append(section)
                
            section_stack.append(section)
        
        return root_sections
    
    def _extract_metadata(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and combine metadata"""
        metadata = {
            'language': self._detect_language(),
            'last_updated': page_data.get('timestamp'),
            'status_code': page_data.get('status_code'),
            'content_type': page_data.get('content_type'),
            'response_time': page_data.get('response_time')
        }
        
        # Add meta tags
        if self.soup:
            for meta in self.soup.find_all('meta'):
                name = meta.get('name', meta.get('property', ''))
                content = meta.get('content', '')
                if name and content:
                    metadata[name] = content
        
        return metadata
    
    def _calculate_content_stats(self) -> Dict[str, int]:
        """Calculate statistics about the content"""
        if not self.soup:
            return {}
            
        # Get clean text content
        text_content = self._get_clean_text()
        
        return {
            'word_count': len(text_content.split()),
            'text_length': len(text_content),
            'section_count': len(self.soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])),
            'paragraph_count': len(self.soup.find_all('p')),
            'external_link_count': len([a for a in self.soup.find_all('a', href=True) 
                                      if a['href'].startswith(('http', 'https')) and self.current_url 
                                      and not a['href'].startswith(self.current_url)]),
            'internal_link_count': len([a for a in self.soup.find_all('a', href=True) 
                                      if not a['href'].startswith(('http', 'https')) or 
                                      (self.current_url and a['href'].startswith(self.current_url))])
        }
    
    def _calculate_image_stats(self) -> Dict[str, Any]:
        """Calculate statistics about images"""
        if not self.soup:
            return {}
            
        images = self.soup.find_all('img')
        total_images = len(images)
        
        if not total_images:
            return {
                'total_count': 0,
                'with_alt': 0,
                'with_dimensions': 0
            }
        
        return {
            'total_count': total_images,
            'with_alt': len([img for img in images if img.get('alt')]),
            'with_dimensions': len([img for img in images if img.get('width') and img.get('height')]),
            'types': {
                'content': len([img for img in images 
                              if not any(skip in (img.get('src', '').lower()) 
                                       for skip in ['logo', 'icon', 'favicon'])]),
                'logos': len([img for img in images 
                            if 'logo' in (img.get('src', '').lower())])
            }
        }
    
    def _get_clean_text(self) -> str:
        """Get clean text content without scripts, styles, etc."""
        if not self.soup:
            return ""
            
        # Get text excluding scripts and styles
        text = self.soup.get_text(separator=' ', strip=True)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _detect_language(self) -> str:
        """Detect the language of the page"""
        if not self.soup:
            return 'fr'  # Default to French
            
        # Check HTML lang attribute
        html_tag = self.soup.find('html')
        if html_tag and html_tag.get('lang'):
            return html_tag.get('lang')
            
        # Check meta tags
        meta_lang = self.soup.find('meta', {'http-equiv': 'content-language'})
        if meta_lang:
            return meta_lang.get('content')
            
        return 'fr'  # Default to French

class ContentTransformer:
    """Transform crawl results into structured content"""
    def __init__(self, crawl_data: Dict[str, Any]):
        self.crawl_data = crawl_data
        self.parser = ContentParser()
    
    def transform(self) -> Dict[str, Any]:
        """Transform all pages in crawl data"""
        transformed_pages = []
        stats = {
            'total_pages': len(self.crawl_data.get('results', [])),
            'processed': 0,
            'failed': 0
        }
        
        for page in self.crawl_data.get('results', []):
            try:
                transformed = self.parser.parse_page(page)
                transformed_pages.append(transformed)
                stats['processed'] += 1
            except Exception as e:
                logger.error(f"Error transforming page {page.get('url', 'unknown')}: {str(e)}")
                stats['failed'] += 1
        
        return {
            'pages': transformed_pages,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }

def transform_content(crawl_data: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to transform crawl data"""
    transformer = ContentTransformer(crawl_data)
    return transformer.transform() 
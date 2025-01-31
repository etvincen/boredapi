import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SectionAnalyzer:
    def __init__(self, json_path: str):
        self.json_path = Path(json_path)
        self.total_sections = 0
        self.total_subsections = 0
        self.section_stats = defaultdict(int)  # Track sections by level
        self.pages_with_sections = 0
        self.empty_sections = 0
        
    def load_json(self) -> Dict[str, Any]:
        """Load the transformed JSON file"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading JSON file: {e}")
            raise
            
    def is_section_empty(self, section: Dict[str, Any]) -> bool:
        """Check if a section is empty"""
        return not any([
            section.get('title', '').strip(),
            section.get('text', '').strip(),
            section.get('images', []),
            section.get('subsections', [])
        ])
        
    def count_sections_recursive(self, section: Dict[str, Any], level: int = 1) -> Tuple[int, int]:
        """Count sections and subsections recursively"""
        if self.is_section_empty(section):
            self.empty_sections += 1
            return 0, 0
            
        sections = 1  # Count current section
        subsections = 0
        
        # Track section level
        self.section_stats[level] += 1
        
        # Process subsections
        for subsection in section.get('subsections', []):
            sub_sections, sub_subsections = self.count_sections_recursive(subsection, level + 1)
            sections += sub_sections
            subsections += sub_subsections + (1 if not self.is_section_empty(subsection) else 0)
            
        return sections, subsections
        
    def analyze(self) -> Dict[str, Any]:
        """Analyze the transformed JSON file"""
        data = self.load_json()
        pages = data.get('pages', [])
        
        logger.info(f"Analyzing {len(pages)} pages...")
        
        for page in pages:
            page_sections = 0
            page_subsections = 0
            
            for section in page.get('sections', []):
                sections, subsections = self.count_sections_recursive(section)
                page_sections += sections
                page_subsections += subsections
                
            if page_sections > 0:
                self.pages_with_sections += 1
                
            self.total_sections += page_sections
            self.total_subsections += page_subsections
            
        return {
            "total_pages": len(pages),
            "pages_with_sections": self.pages_with_sections,
            "total_sections": self.total_sections,
            "total_subsections": self.total_subsections,
            "empty_sections": self.empty_sections,
            "sections_by_level": dict(self.section_stats),
            "total_content_pieces": self.total_sections + self.total_subsections,
            "average_sections_per_page": self.total_sections / len(pages) if pages else 0
        }

def main():
    # Find latest transformed file
    transform_dir = Path('transformed_results')
    if not transform_dir.exists():
        logger.error("Transformed results directory not found")
        return
        
    result_files = list(transform_dir.glob('transformed_*.json'))
    if not result_files:
        logger.error("No transformed result files found")
        return
        
    latest_file = max(result_files, key=lambda p: p.stat().st_mtime)
    logger.info(f"Analyzing latest transformed file: {latest_file}")
    
    analyzer = SectionAnalyzer(latest_file)
    stats = analyzer.analyze()
    
    logger.info("\n=== Section Analysis Results ===")
    logger.info(f"Total pages: {stats['total_pages']}")
    logger.info(f"Pages with sections: {stats['pages_with_sections']}")
    logger.info(f"Total sections: {stats['total_sections']}")
    logger.info(f"Total subsections: {stats['total_subsections']}")
    logger.info(f"Empty sections: {stats['empty_sections']}")
    logger.info("\nSections by level:")
    for level, count in sorted(stats['sections_by_level'].items()):
        logger.info(f"  Level {level}: {count}")
    logger.info(f"\nTotal content pieces: {stats['total_content_pieces']}")
    logger.info(f"Average sections per page: {stats['average_sections_per_page']:.2f}")

if __name__ == "__main__":
    main() 
from src.utils.web_analysis import load_crawl_results, CrawlResultsAnalyzer
from pathlib import Path
import json
import logging
from collections import defaultdict
from typing import Dict, List, Any
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def display_section_content(section: dict, indent: str = "") -> None:
    """Helper function to display section content in a readable format"""
    if section.get('title'):
        logger.info(f"{indent}Title: {section['title']}")
    if section.get('text'):
        text_preview = section['text'][:150] + "..." if len(section['text']) > 150 else section['text']
        logger.info(f"{indent}Text: {text_preview}")
    if section.get('images'):
        logger.info(f"{indent}Images ({len(section['images'])}):")
        for img in section['images']:
            logger.info(f"{indent}  - {img['src']} (alt: {img['alt']}")

def analyze_page_stats(page: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a single page and return statistics"""
    stats = {
        'url': page['url'],
        'title_length': len(page['title']) if page.get('title') else 0,
        'has_meta_description': bool(page['meta_tags'].get('description')),
        'text_length': len(page['main_content']['text']),
        'num_sections': len(page['main_content']['sections']),
        'num_images': len(page['images']),
        'num_links': {
            'internal': len(page['links']['internal']),
            'external': len(page['links']['external']),
            'resources': len(page['links']['resources'])
        },
        'has_title': bool(page.get('title')),
        'has_content': bool(page['main_content']['text']),
        'language': page['metadata']['language']
    }
    return stats

def analyze_all_pages(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze statistics across all pages"""
    all_stats = []
    issues = defaultdict(list)
    
    for page in pages:
        stats = analyze_page_stats(page)
        all_stats.append(stats)
        
        # Check for potential issues
        if not stats['has_title']:
            issues['missing_title'].append(stats['url'])
        if not stats['has_meta_description']:
            issues['missing_meta_description'].append(stats['url'])
        if not stats['has_content']:
            issues['no_content'].append(stats['url'])
        if stats['text_length'] < 100:  # Arbitrary threshold
            issues['low_content'].append(stats['url'])
        if not stats['num_sections']:
            issues['no_sections'].append(stats['url'])
            
    # Calculate aggregate statistics
    aggregate_stats = {
        'total_pages': len(pages),
        'pages_with_issues': len(set().union(*issues.values())),
        'avg_text_length': sum(s['text_length'] for s in all_stats) / len(all_stats),
        'avg_sections': sum(s['num_sections'] for s in all_stats) / len(all_stats),
        'avg_images': sum(s['num_images'] for s in all_stats) / len(all_stats),
        'languages': list(set(s['language'] for s in all_stats)),
        'issues': {k: len(v) for k, v in issues.items()}
    }
    
    return {
        'aggregate_stats': aggregate_stats,
        'issues': issues,
        'page_stats': all_stats
    }

def main():
    # Load crawl results
    crawl_path = Path('crawl_results/crawl_results_20250127_221009.json')
    if not crawl_path.exists():
        logger.error(f"Crawl results file not found at {crawl_path}")
        return

    logger.info("Loading crawl results...")
    crawl_data = load_crawl_results(str(crawl_path))
    
    # Initialize analyzer
    analyzer = CrawlResultsAnalyzer(crawl_data)
    
    # Get crawl statistics
    stats = analyzer.get_crawl_stats()
    logger.info("\n=== Crawl Statistics ===")
    logger.info(f"Total pages: {stats['total_pages']}")
    logger.info(f"Configuration: {json.dumps(stats['crawl_config'], indent=2)}")
    
    # Process all pages
    logger.info("\n=== Processing All Pages ===")
    analyzed_pages = []
    for i, page in enumerate(analyzer.results):
        try:
            analyzed = analyzer.web_analyzer.analyze_page(page)
            analyzed_pages.append(analyzed)
            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i + 1} pages...")
        except Exception as e:
            logger.error(f"Error processing page {page.get('url')}: {str(e)}")
    
    # Analyze results
    analysis_results = analyze_all_pages(analyzed_pages)
    
    # Display aggregate statistics
    logger.info("\n=== Analysis Results ===")
    logger.info(f"Total pages processed: {analysis_results['aggregate_stats']['total_pages']}")
    logger.info(f"Pages with issues: {analysis_results['aggregate_stats']['pages_with_issues']}")
    logger.info(f"Average text length: {analysis_results['aggregate_stats']['avg_text_length']:.2f} characters")
    logger.info(f"Average sections per page: {analysis_results['aggregate_stats']['avg_sections']:.2f}")
    logger.info(f"Average images per page: {analysis_results['aggregate_stats']['avg_images']:.2f}")
    logger.info(f"Languages detected: {', '.join(analysis_results['aggregate_stats']['languages'])}")
    
    # Display issues
    logger.info("\n=== Content Issues ===")
    for issue_type, count in analysis_results['aggregate_stats']['issues'].items():
        if count > 0:
            logger.info(f"{issue_type}: {count} pages")
            # Show up to 5 example URLs for each issue
            for url in analysis_results['issues'][issue_type][:5]:
                logger.info(f"  - {url}")
    
    # Save detailed analysis
    output_path = Path('analysis_results')
    output_path.mkdir(exist_ok=True)
    
    # Save full analysis
    full_analysis_path = output_path / 'full_site_analysis.json'
    with full_analysis_path.open('w', encoding='utf-8') as f:
        json.dump(analysis_results, f, ensure_ascii=False, indent=2)
    logger.info(f"\nDetailed analysis saved to {full_analysis_path}")

if __name__ == "__main__":
    main() 
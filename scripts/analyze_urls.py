#!/usr/bin/env python3
import os
import json
from collections import defaultdict
from urllib.parse import urlparse, unquote
from pathlib import Path
from typing import Dict, List, Set, Tuple
import argparse
from pprint import pprint
import logging
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class URLAnalysis:
    exact_duplicates: Dict[str, List[str]]
    similar_paths: Dict[str, List[str]]
    base_duplicates: Dict[str, List[str]]
    stats: Dict[str, int]

class URLAnalyzer:
    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        self.url_map: Dict[str, str] = {}  # URL to file path mapping
        self.normalized_urls: Dict[str, Set[str]] = defaultdict(set)  # Normalized path to original URLs
        
    def load_transformed_results(self) -> None:
        """Load all transformed JSON files and extract URLs"""
        logger.info(f"Loading transformed results from {self.results_dir}")
        
        json_file = list(self.results_dir.glob("**/*.json"))[-1]

        try:
            logger.info(f"Processing {json_file}")
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data = data['pages']
                # Handle both single document and array of documents
                documents = data if isinstance(data, list) else [data]
                
                for doc in documents:
                    # Try different possible URL field locations
                    url = None
                    if isinstance(doc, dict):
                        # Check common URL field locations
                        if 'metadata' in doc and 'url' in doc['metadata']:
                            url = doc['metadata']['url']
                        elif 'url' in doc:
                            url = doc['url']
                        elif 'source' in doc and 'url' in doc['source']:
                            url = doc['source']['url']
                        elif 'content' in doc and 'url' in doc['content']:
                            url = doc['content']['url']
                    
                    if url:
                        logger.debug(f"Found URL: {url} in file: {json_file}")
                        self.url_map[url] = str(json_file)
                    else:
                        logger.warning(f"No URL found in document from file: {json_file}")
                        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in file {json_file}: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing {json_file}: {str(e)}")
                
        logger.info(f"Loaded {len(self.url_map)} URLs")
        
        # Log sample of found URLs for verification
        sample_size = min(5, len(self.url_map))
        if sample_size > 0:
            logger.info("Sample of found URLs:")
            for url in list(self.url_map.keys())[:sample_size]:
                logger.info(f"  - {url}")

    def normalize_url(self, url: str) -> str:
        """Normalize URL by removing trailing slashes and decoding"""
        parsed = urlparse(unquote(url))
        path = parsed.path.rstrip('/')
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    def get_base_path(self, url: str) -> str:
        """Extract the base path (last segment) of the URL"""
        parsed = urlparse(unquote(url))
        path = parsed.path.rstrip('/')
        return os.path.basename(path)

    def analyze_urls(self) -> URLAnalysis:
        """Analyze URLs for duplicates and similar paths"""
        # Initialize collections
        exact_duplicates: Dict[str, List[str]] = defaultdict(list)
        similar_paths: Dict[str, List[str]] = defaultdict(list)
        base_duplicates: Dict[str, List[str]] = defaultdict(list)
        
        # Analyze normalized URLs
        for url in self.url_map.keys():
            normalized = self.normalize_url(url)
            self.normalized_urls[normalized].add(url)
            
            # Group by base path
            base_path = self.get_base_path(url)
            if base_path:  # Skip empty base paths
                base_duplicates[base_path].append(url)

        # Find exact duplicates
        for normalized, urls in self.normalized_urls.items():
            if len(urls) > 1:
                exact_duplicates[normalized] = sorted(urls)

        # Find similar paths
        for url in self.url_map.keys():
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            
            # Skip very short paths
            if len(path_parts) <= 1:
                continue
                
            # Create path signature (excluding one level up)
            if len(path_parts) > 2:
                signature = '/'.join(path_parts[:-2] + [path_parts[-1]])
                similar_paths[signature].append(url)

        # Filter out non-duplicates
        exact_duplicates = {k: v for k, v in exact_duplicates.items() if len(v) > 1}
        similar_paths = {k: v for k, v in similar_paths.items() if len(v) > 1}
        base_duplicates = {k: v for k, v in base_duplicates.items() if len(v) > 1}

        # Calculate statistics
        stats = {
            "total_urls": len(self.url_map),
            "exact_duplicate_groups": len(exact_duplicates),
            "similar_path_groups": len(similar_paths),
            "base_duplicate_groups": len(base_duplicates),
            "total_exact_duplicates": sum(len(urls) for urls in exact_duplicates.values()),
            "total_similar_paths": sum(len(urls) for urls in similar_paths.values()),
            "total_base_duplicates": sum(len(urls) for urls in base_duplicates.values())
        }

        return URLAnalysis(
            exact_duplicates=exact_duplicates,
            similar_paths=similar_paths,
            base_duplicates=base_duplicates,
            stats=stats
        )

    def generate_report(self, analysis: URLAnalysis, output_dir: str) -> None:
        """Generate a detailed report of the URL analysis"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = output_dir / f"url_analysis_report_{timestamp}.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("URL Analysis Report\n")
            f.write("=================\n\n")
            
            # Write statistics
            f.write("Statistics\n")
            f.write("---------\n")
            for key, value in analysis.stats.items():
                f.write(f"{key.replace('_', ' ').title()}: {value}\n")
            f.write("\n")
            
            # Write exact duplicates
            if analysis.exact_duplicates:
                f.write("Exact Duplicates\n")
                f.write("---------------\n")
                for normalized, urls in analysis.exact_duplicates.items():
                    f.write(f"\nNormalized URL: {normalized}\n")
                    for url in urls:
                        f.write(f"  - {url}\n")
                        f.write(f"    File: {self.url_map[url]}\n")
                f.write("\n")
            
            # Write similar paths
            if analysis.similar_paths:
                f.write("Similar Paths\n")
                f.write("------------\n")
                for signature, urls in analysis.similar_paths.items():
                    f.write(f"\nPath Signature: {signature}\n")
                    for url in urls:
                        f.write(f"  - {url}\n")
                        f.write(f"    File: {self.url_map[url]}\n")
                f.write("\n")
            
            # Write base duplicates
            if analysis.base_duplicates:
                f.write("Base Path Duplicates\n")
                f.write("-------------------\n")
                for base_path, urls in analysis.base_duplicates.items():
                    f.write(f"\nBase Path: {base_path}\n")
                    for url in urls:
                        f.write(f"  - {url}\n")
                        f.write(f"    File: {self.url_map[url]}\n")
                f.write("\n")
        
        logger.info(f"Report generated: {report_file}")

def main():
    parser = argparse.ArgumentParser(description="Analyze URLs in transformed results for duplicates")
    parser.add_argument(
        "--results-dir",
        type=str,
        required=True,
        help="Directory containing transformed JSON results"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="url_analysis_results",
        help="Directory to save the analysis report"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--show-json-structure",
        action="store_true",
        help="Show the structure of the first JSON file found"
    )
    args = parser.parse_args()

    # Set logging level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    try:
        analyzer = URLAnalyzer(args.results_dir)
        
        # Show JSON structure if requested
        if args.show_json_structure:
            first_json = next(Path(args.results_dir).glob("**/*.json"))
            if first_json:
                with open(first_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info("Sample JSON structure:")
                    logger.info(json.dumps(data, indent=2)[:500] + "...")
        
        analyzer.load_transformed_results()
        
        # Log some diagnostics
        if args.verbose:
            logger.debug("Directory contents:")
            for item in Path(args.results_dir).glob("**/*"):
                logger.debug(f"  {item}")
        
        analysis = analyzer.analyze_urls()
        analyzer.generate_report(analysis, args.output_dir)
        
        # Print summary to console
        logger.info("\nAnalysis Summary:")
        for key, value in analysis.stats.items():
            logger.info(f"{key.replace('_', ' ').title()}: {value}")
            
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        raise

if __name__ == "__main__":
    main() 
import json
import os
import re
import time
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.shl.com/solutions/products/product-catalog/"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
JSONL_PATH = os.path.join(OUTPUT_DIR, 'catalog.jsonl')
PARQUET_PATH = os.path.join(OUTPUT_DIR, 'catalog.parquet')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def fetch(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, 'html.parser')


def is_individual_test_solution(card: BeautifulSoup) -> bool:
    # The catalog page groups categories; we will crawl all product detail pages then filter by inferred category text
    return True


def parse_sitemap(url: str) -> List[str]:
    """Parse a sitemap (or sitemap index) and return all URLs."""
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'xml')
    urls = []
    # If it's a sitemap index
    for loc in soup.select('sitemap > loc'):
        try:
            sub_url = loc.get_text(strip=True)
            urls.extend(parse_sitemap(sub_url))
        except Exception:
            continue
    # Regular urlset
    if not urls:
        for loc in soup.select('url > loc'):
            u = loc.get_text(strip=True)
            urls.append(u)
    return urls


def discover_product_urls() -> List[str]:
    candidates = set()
    # Try main sitemap
    sitemap_urls = [
        "https://www.shl.com/sitemap.xml",
        "https://www.shl.com/post-sitemap.xml",
        "https://www.shl.com/page-sitemap.xml",
        "https://www.shl.com/product-sitemap.xml",
    ]
    seen_maps = set()
    for sm in sitemap_urls:
        try:
            if sm in seen_maps:
                continue
            seen_maps.add(sm)
            urls = parse_sitemap(sm)
            for u in urls:
                if not u.startswith('http'):
                    continue
                # product detail patterns observed on SHL site
                if '/product/' in u or '/products/product-catalog/' in u:
                    candidates.add(u)
        except Exception:
            continue
    # Fallback: seed from local train/test CSVs
    try:
        import pandas as pd
        root = os.path.dirname(os.path.dirname(__file__))
        for fname in (os.path.join(root, 'data', 'train.csv'), os.path.join(root, 'data', 'test.csv')):
            if not os.path.exists(fname):
                continue
            df = pd.read_csv(fname)
            # look for Assessment_url column (case-insensitive)
            url_col = None
            for c in df.columns:
                if c.lower().strip() == 'assessment_url' or 'url' in c.lower():
                    url_col = c
                    break
            if url_col is None:
                continue
            for val in df[url_col].dropna().astype(str).tolist():
                val = val.strip()
                if val.startswith('http') and ('shl.com' in val):
                    candidates.add(val)
    except Exception:
        pass
    return sorted(candidates)


def extract_product_details(url: str) -> Dict:
    soup = fetch(url)
    name = soup.select_one('h1')
    name = name.get_text(strip=True) if name else ''
    desc_el = soup.select_one('meta[name="description"]')
    description = desc_el.get('content').strip() if desc_el and desc_el.get('content') else ''
    # Heuristics for test type from page tags/text
    page_text = soup.get_text(" ", strip=True)
    test_type = None
    # Simple keyword mapping
    mapping = {
        'Knowledge': 'K', 'Skills': 'K', 'Skill': 'K', 'Technical': 'K', 'Coding': 'K',
        'Personality': 'P', 'Behavior': 'P', 'Behaviour': 'P', 'Motivation': 'P', 'Values': 'P',
        'Cognitive': 'C', 'Aptitude': 'C', 'Reasoning': 'C', 'Numerical': 'C', 'Verbal': 'C',
        'Situational': 'S', 'Judgement': 'S', 'SJT': 'S',
    }
    for key, val in mapping.items():
        if re.search(rf"\b{re.escape(key)}\b", page_text, re.I):
            test_type = val
            break
    return {
        'name': name,
        'url': url,
        'test_type': test_type,
        'description': description,
        'category': 'Individual Test Solutions',
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    urls = discover_product_urls()
    results = []
    for i, url in enumerate(urls):
        try:
            details = extract_product_details(url)
            # We ignore pre-packaged job solutions; if page clearly indicates job packages, skip
            if re.search(r"Pre[- ]?packaged Job Solutions", details.get('description', ''), re.I):
                continue
            results.append(details)
            print(f"[{i+1}/{len(urls)}] {details['name']}" )
            time.sleep(0.3)
        except Exception as e:
            print(f"Error {url}: {e}")
            continue
    # write JSONL
    with open(JSONL_PATH, 'w', encoding='utf-8') as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # optional parquet
    try:
        import pandas as pd
        df = pd.DataFrame(results)
        df.to_parquet(PARQUET_PATH, index=False)
    except Exception:
        pass
    print(f"Wrote {len(results)} items to {JSONL_PATH}")


if __name__ == "__main__":
    main()

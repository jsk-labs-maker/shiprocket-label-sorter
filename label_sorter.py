#!/usr/bin/env python3
"""
Shiprocket Label Sorter
=======================
Sorts bulk shipping labels by Courier and SKU, outputs organized PDFs.

Output format: YYYY-MM-DD_Courier_SKU.pdf

Author: Kluzo 😎 for Dhruv Shetty / JSK Labs
"""

import re
import os
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Add venv packages
sys.path.insert(0, '/Users/klaus/.openclaw/workspace/.venv/lib/python3.13/site-packages')

from pypdf import PdfReader, PdfWriter


def normalize_courier(courier_raw: str) -> str:
    """Normalize courier names for consistent file naming."""
    courier_lower = courier_raw.lower()
    
    if 'ekart' in courier_lower:
        return 'Ekart'
    elif 'delhivery' in courier_lower:
        return 'Delhivery'
    elif 'xpressbees' in courier_lower:
        return 'Xpressbees'
    elif 'bluedart' in courier_lower:
        return 'BlueDart'
    elif 'dtdc' in courier_lower:
        return 'DTDC'
    elif 'shadowfax' in courier_lower:
        return 'Shadowfax'
    elif 'ecom' in courier_lower:
        return 'EcomExpress'
    else:
        # Clean up for filename
        return re.sub(r'[^\w\-]', '', courier_raw.replace(' ', '-'))[:30]


def normalize_sku(sku_raw: str) -> str:
    """Normalize SKU for filename safety."""
    # Remove special chars, keep alphanumeric and hyphens
    return re.sub(r'[^\w\-]', '', sku_raw.replace(' ', '-'))[:50]


def extract_label_info(page_text: str) -> dict:
    """Extract courier, SKU, and date from label text."""
    info = {
        'courier': 'Unknown',
        'sku': 'Unknown',
        'date': datetime.now().strftime('%Y-%m-%d')
    }
    
    # Courier patterns (order matters - more specific first)
    courier_patterns = [
        (r'Ekart[^\n]*', 'Ekart'),
        (r'Delhivery[^\n]*', 'Delhivery'),
        (r'Xpressbees[^\n]*', 'Xpressbees'),
        (r'BlueDart[^\n]*', 'BlueDart'),
        (r'DTDC[^\n]*', 'DTDC'),
        (r'Shadowfax[^\n]*', 'Shadowfax'),
        (r'Ecom\s*Express[^\n]*', 'EcomExpress'),
    ]
    
    for pattern, name in courier_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            info['courier'] = name
            break
    
    # SKU extraction
    sku_match = re.search(r'SKU:\s*([^\n]+)', page_text)
    if sku_match:
        info['sku'] = normalize_sku(sku_match.group(1).strip())
    
    # Date extraction (Invoice Date preferred)
    date_match = re.search(r'Invoice Date:\s*(\d{4}-\d{2}-\d{2})', page_text)
    if date_match:
        info['date'] = date_match.group(1)
    else:
        # Try other date formats
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', page_text)
        if date_match:
            info['date'] = date_match.group(1)
    
    return info


def sort_labels(input_pdf: str, output_dir: str = None) -> dict:
    """
    Sort labels from input PDF into separate PDFs by Courier + SKU.
    
    Args:
        input_pdf: Path to the input PDF with bulk labels
        output_dir: Directory for output PDFs (default: same as input)
    
    Returns:
        dict with summary of created files
    """
    input_path = Path(input_pdf)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")
    
    if output_dir is None:
        output_dir = input_path.parent / 'sorted_labels'
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📄 Reading: {input_path.name}")
    reader = PdfReader(str(input_path))
    total_pages = len(reader.pages)
    print(f"   Found {total_pages} labels")
    
    # Group pages by (date, courier, sku)
    groups = defaultdict(list)
    
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ''
        info = extract_label_info(text)
        
        key = (info['date'], info['courier'], info['sku'])
        groups[key].append(i)
        
        if (i + 1) % 50 == 0:
            print(f"   Processed {i + 1}/{total_pages} labels...")
    
    print(f"\n📦 Found {len(groups)} unique groups")
    
    # Create output PDFs
    results = []
    
    for (date, courier, sku), page_indices in sorted(groups.items()):
        # Output filename: YYYY-MM-DD_Courier_SKU.pdf
        filename = f"{date}_{courier}_{sku}.pdf"
        output_path = output_dir / filename
        
        writer = PdfWriter()
        for idx in page_indices:
            writer.add_page(reader.pages[idx])
        
        with open(output_path, 'wb') as f:
            writer.write(f)
        
        result = {
            'file': filename,
            'date': date,
            'courier': courier,
            'sku': sku,
            'labels': len(page_indices)
        }
        results.append(result)
        print(f"   ✅ {filename} ({len(page_indices)} labels)")
    
    print(f"\n🎉 Done! {len(results)} files created in: {output_dir}")
    
    return {
        'input': str(input_path),
        'output_dir': str(output_dir),
        'total_labels': total_pages,
        'files': results
    }


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Sort Shiprocket shipping labels by Courier and SKU'
    )
    parser.add_argument('input_pdf', help='Path to input PDF with bulk labels')
    parser.add_argument('-o', '--output', help='Output directory (default: ./sorted_labels)')
    
    args = parser.parse_args()
    
    try:
        result = sort_labels(args.input_pdf, args.output)
        
        print("\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        print(f"Total labels processed: {result['total_labels']}")
        print(f"Output files created: {len(result['files'])}")
        print(f"Output directory: {result['output_dir']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

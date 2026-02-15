# Shiprocket Label Sorter 📦

Automatically sorts bulk shipping labels by **Courier** and **SKU** for efficient warehouse operations.

## Problem Solved

When you download bulk labels from Shiprocket, they come as one big PDF. Your warehouse team needs them sorted by:
1. **SKU** - so pickers can grab items efficiently
2. **Courier** - for organized handoff to delivery partners

This tool does that automatically!

## Output Format

```
YYYY-MM-DD_Courier_SKU.pdf
```

Examples:
- `2026-01-17_Ekart_Derma-P2.pdf` (68 labels)
- `2026-01-17_Delhivery_Derma-P2.pdf` (17 labels)
- `2026-01-17_Xpressbees_Derma-P2.pdf` (4 labels)

## Usage

### Command Line

```bash
python3 label_sorter.py /path/to/bulk_labels.pdf
```

With custom output directory:
```bash
python3 label_sorter.py /path/to/bulk_labels.pdf -o /path/to/output/
```

### As a Module

```python
from label_sorter import sort_labels

result = sort_labels('bulk_labels.pdf', output_dir='./sorted')
print(f"Created {len(result['files'])} files")
```

## Supported Couriers

- ✅ Ekart
- ✅ Delhivery
- ✅ Xpressbees
- ✅ BlueDart
- ✅ DTDC
- ✅ Shadowfax
- ✅ Ecom Express

## Requirements

- Python 3.8+
- pypdf (`pip install pypdf`)

## How It Works

1. Reads the bulk PDF
2. Extracts text from each label page
3. Parses: Courier name, SKU, Invoice Date
4. Groups labels by Date + Courier + SKU
5. Creates separate PDFs for each group

## Label Format Expected

The tool expects Shiprocket's standard 4x6 thermal label format with:
- Courier name visible (e.g., "Ekart Special Surface 500gm")
- SKU field (e.g., "SKU: Derma P2")
- Invoice Date (e.g., "Invoice Date: 2026-01-17")

---

Built by **Kluzo** 😎 for **JSK Labs**

"""
Shiprocket Label Sorter - Web Interface
=======================================
Upload bulk labels → Get sorted PDFs by Courier + SKU

Built by Kluzo 😎 for JSK Labs
"""

import streamlit as st
import re
import io
import zipfile
from collections import defaultdict
from datetime import datetime
from pypdf import PdfReader, PdfWriter

st.set_page_config(
    page_title="Label Sorter | JSK Labs",
    page_icon="📦",
    layout="centered"
)

# --- Helper Functions ---

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
        return re.sub(r'[^\w\-]', '', courier_raw.replace(' ', '-'))[:30]


def normalize_sku(sku_raw: str) -> str:
    """Normalize SKU for filename safety."""
    return re.sub(r'[^\w\-]', '', sku_raw.replace(' ', '-'))[:50]


def extract_label_info(page_text: str) -> dict:
    """Extract courier, SKU, and date from label text."""
    info = {
        'courier': 'Unknown',
        'sku': 'Unknown',
        'date': datetime.now().strftime('%Y-%m-%d')
    }
    
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
    
    sku_match = re.search(r'SKU:\s*([^\n]+)', page_text)
    if sku_match:
        info['sku'] = normalize_sku(sku_match.group(1).strip())
    
    date_match = re.search(r'Invoice Date:\s*(\d{4}-\d{2}-\d{2})', page_text)
    if date_match:
        info['date'] = date_match.group(1)
    else:
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', page_text)
        if date_match:
            info['date'] = date_match.group(1)
    
    return info


def sort_labels(pdf_file) -> tuple:
    """Sort labels and return zip buffer with results."""
    reader = PdfReader(pdf_file)
    total_pages = len(reader.pages)
    
    # Group pages by (date, courier, sku)
    groups = defaultdict(list)
    
    progress_bar = st.progress(0, text="Analyzing labels...")
    
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ''
        info = extract_label_info(text)
        key = (info['date'], info['courier'], info['sku'])
        groups[key].append(i)
        progress_bar.progress((i + 1) / total_pages, text=f"Analyzing label {i+1}/{total_pages}")
    
    progress_bar.progress(1.0, text="Creating sorted PDFs...")
    
    # Create zip with all sorted PDFs
    zip_buffer = io.BytesIO()
    results = []
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for (date, courier, sku), page_indices in sorted(groups.items()):
            filename = f"{date}_{courier}_{sku}.pdf"
            
            writer = PdfWriter()
            for idx in page_indices:
                writer.add_page(reader.pages[idx])
            
            pdf_buffer = io.BytesIO()
            writer.write(pdf_buffer)
            pdf_buffer.seek(0)
            
            zf.writestr(filename, pdf_buffer.getvalue())
            
            results.append({
                'file': filename,
                'date': date,
                'courier': courier,
                'sku': sku,
                'labels': len(page_indices)
            })
    
    zip_buffer.seek(0)
    progress_bar.empty()
    
    return zip_buffer, results, total_pages


# --- UI ---

st.title("📦 Shiprocket Label Sorter")
st.markdown("**Sort bulk labels by Courier + SKU in seconds**")

st.divider()

uploaded_file = st.file_uploader(
    "Upload your bulk labels PDF",
    type=['pdf'],
    help="Download bulk labels from Shiprocket and upload here"
)

if uploaded_file:
    st.info(f"📄 **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
    
    if st.button("🚀 Sort Labels", type="primary", use_container_width=True):
        with st.spinner("Processing..."):
            try:
                zip_buffer, results, total_pages = sort_labels(uploaded_file)
                
                st.success(f"✅ Sorted **{total_pages} labels** into **{len(results)} files**")
                
                # Results table
                st.subheader("📊 Summary")
                
                for r in results:
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.markdown(f"**{r['courier']}** / {r['sku']}")
                    with col2:
                        st.markdown(f"📅 {r['date']}")
                    with col3:
                        st.markdown(f"🏷️ {r['labels']} labels")
                
                st.divider()
                
                # Download button
                st.download_button(
                    label="📥 Download All (ZIP)",
                    data=zip_buffer,
                    file_name=f"sorted_labels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    type="primary",
                    use_container_width=True
                )
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

st.divider()

with st.expander("ℹ️ How it works"):
    st.markdown("""
    1. **Upload** your bulk labels PDF from Shiprocket
    2. The tool scans each label and extracts:
       - Courier name (Ekart, Delhivery, Xpressbees, etc.)
       - SKU code
       - Invoice date
    3. Labels are grouped and saved as separate PDFs
    4. **Download** the ZIP with all sorted files
    
    **Output format:** `YYYY-MM-DD_Courier_SKU.pdf`
    """)

st.caption("Built with ❤️ by JSK Labs")

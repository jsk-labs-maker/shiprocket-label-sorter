"""
Shiprocket Label Sorter - Web Interface
=======================================
Upload bulk labels → Get sorted PDFs by Courier + SKU
Now with Shiprocket API integration! 🚀

Built by Kluzo 😎 for JSK Labs
"""

import streamlit as st
import re
import io
import zipfile
import requests
from collections import defaultdict
from datetime import datetime
from pypdf import PdfReader, PdfWriter

st.set_page_config(
    page_title="Label Sorter | JSK Labs",
    page_icon="📦",
    layout="wide"
)

# --- Initialize Session State ---
if 'api_token' not in st.session_state:
    st.session_state.api_token = None
if 'api_email' not in st.session_state:
    st.session_state.api_email = None


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


# --- Shiprocket API Functions ---

def api_authenticate(email: str, password: str) -> dict:
    """Authenticate with Shiprocket API."""
    url = "https://apiv2.shiprocket.in/v1/external/auth/login"
    response = requests.post(url, json={"email": email, "password": password})
    response.raise_for_status()
    return response.json()


def api_get_orders(token: str, status: str = "new", per_page: int = 50, days: int = 7) -> dict:
    """Fetch orders by status, filtered to last N days."""
    from datetime import datetime, timedelta
    
    url = "https://apiv2.shiprocket.in/v1/external/orders"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Calculate date range (last N days)
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    params = {
        "filter": status, 
        "per_page": per_page,
        "from": from_date,
        "to": to_date
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def api_ship_order(token: str, shipment_id: int) -> dict:
    """Assign AWB to shipment (ship order with auto courier)."""
    url = "https://apiv2.shiprocket.in/v1/external/courier/assign/awb"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json={"shipment_id": shipment_id})
    response.raise_for_status()
    return response.json()


def api_get_label_url(token: str, shipment_ids: list) -> str:
    """Get label PDF URL for shipments."""
    url = "https://apiv2.shiprocket.in/v1/external/courier/generate/label"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json={"shipment_id": shipment_ids})
    response.raise_for_status()
    data = response.json()
    return data.get("label_url", "")


def api_get_wallet_balance(token: str) -> dict:
    """Get wallet balance."""
    url = "https://apiv2.shiprocket.in/v1/external/account/details/wallet-balance"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


# --- UI ---

st.title("📦 Shiprocket Label Sorter")
st.markdown("**Sort bulk labels by Courier + SKU • Auto-ship orders via API**")

# Tabs for different modes
tab1, tab2 = st.tabs(["📤 Upload Labels", "🔌 Shiprocket API"])

# ===== TAB 1: Manual Upload =====
with tab1:
    st.markdown("### Upload & Sort Labels")
    
    uploaded_file = st.file_uploader(
        "Upload your bulk labels PDF",
        type=['pdf'],
        help="Download bulk labels from Shiprocket and upload here"
    )

    if uploaded_file:
        st.info(f"📄 **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
        
        if st.button("🚀 Sort Labels", type="primary", use_container_width=True, key="sort_btn"):
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


# ===== TAB 2: Shiprocket API =====
with tab2:
    st.markdown("### Connect to Shiprocket API")
    
    # Login Section
    if not st.session_state.api_token:
        with st.form("login_form"):
            st.markdown("**Enter your Shiprocket credentials**")
            email = st.text_input("Email", placeholder="your@email.com")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("🔐 Connect", use_container_width=True)
            
            if submit and email and password:
                try:
                    with st.spinner("Authenticating..."):
                        auth_data = api_authenticate(email, password)
                        st.session_state.api_token = auth_data.get("token")
                        st.session_state.api_email = email
                        st.success("✅ Connected successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Authentication failed: {str(e)}")
    
    else:
        # Connected - Show dashboard
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"✅ Connected as **{st.session_state.api_email}**")
        with col2:
            if st.button("🔓 Disconnect"):
                st.session_state.api_token = None
                st.session_state.api_email = None
                st.rerun()
        
        # Wallet Balance
        try:
            balance_data = api_get_wallet_balance(st.session_state.api_token)
            balance = balance_data.get("data", {}).get("balance_amount", 0)
            st.metric("💰 Wallet Balance", f"₹{balance:,.2f}")
        except:
            pass
        
        st.divider()
        
        # Orders Section
        st.markdown("### 📋 Orders")
        
        col1, col2 = st.columns(2)
        with col1:
            order_status = st.selectbox(
                "Filter by status",
                ["new", "ready_to_ship", "pickup_scheduled", "in_transit", "delivered"],
                format_func=lambda x: x.replace("_", " ").title()
            )
        with col2:
            days_filter = st.selectbox(
                "Date range",
                [7, 14, 30],
                format_func=lambda x: f"Last {x} days"
            )
        
        if st.button("🔄 Fetch Orders", use_container_width=True):
            try:
                with st.spinner(f"Fetching orders from last {days_filter} days..."):
                    orders_data = api_get_orders(st.session_state.api_token, status=order_status, days=days_filter)
                    orders = orders_data.get("data", [])
                    
                    if orders:
                        st.session_state.orders = orders
                        st.success(f"Found **{len(orders)}** orders")
                    else:
                        st.info("No orders found with this status")
                        st.session_state.orders = []
            except Exception as e:
                st.error(f"Error fetching orders: {str(e)}")
        
        # Display orders
        if 'orders' in st.session_state and st.session_state.orders:
            orders = st.session_state.orders
            
            # Show order table
            st.markdown(f"**{len(orders)} Orders**")
            
            for order in orders[:20]:  # Limit display
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                    
                    order_id = order.get("channel_order_id", order.get("id"))
                    customer = order.get("customer_name", "N/A")
                    total = order.get("total", 0)
                    status = order.get("status", "")
                    
                    # Get shipment info
                    shipments = order.get("shipments", {})
                    if isinstance(shipments, dict):
                        shipment_id = shipments.get("id")
                        courier = shipments.get("courier", "-")
                        awb = shipments.get("awb", "-")
                    elif isinstance(shipments, list) and shipments:
                        shipment_id = shipments[0].get("id")
                        courier = shipments[0].get("courier", "-")
                        awb = shipments[0].get("awb", "-")
                    else:
                        shipment_id = None
                        courier = "-"
                        awb = "-"
                    
                    with col1:
                        st.markdown(f"**#{order_id}**")
                        st.caption(customer)
                    with col2:
                        st.markdown(f"₹{total}")
                        st.caption(f"Courier: {courier or '-'}")
                    with col3:
                        st.caption(f"AWB: {awb or '-'}")
                    with col4:
                        if order_status == "new" and shipment_id:
                            if st.button("🚀 Ship", key=f"ship_{order_id}"):
                                try:
                                    result = api_ship_order(st.session_state.api_token, shipment_id)
                                    if result.get("awb_assign_status") == 1:
                                        awb_code = result.get("response", {}).get("data", {}).get("awb_code", "")
                                        courier_name = result.get("response", {}).get("data", {}).get("courier_name", "")
                                        st.success(f"✅ Shipped via {courier_name}\nAWB: {awb_code}")
                                    else:
                                        st.error("Failed to ship")
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                    
                    st.divider()
            
            # Bulk Ship Button
            if order_status == "new":
                st.markdown("### ⚡ Bulk Actions")
                
                if st.button("🚀 Ship All Orders (Auto Courier)", type="primary", use_container_width=True):
                    shipment_ids = []
                    for order in orders:
                        shipments = order.get("shipments", {})
                        if isinstance(shipments, dict):
                            shipment_ids.append(shipments.get("id"))
                        elif isinstance(shipments, list) and shipments:
                            shipment_ids.append(shipments[0].get("id"))
                    
                    shipment_ids = [sid for sid in shipment_ids if sid]
                    
                    if shipment_ids:
                        progress = st.progress(0, text="Shipping orders...")
                        success_count = 0
                        failed = []
                        
                        for i, sid in enumerate(shipment_ids):
                            try:
                                result = api_ship_order(st.session_state.api_token, sid)
                                if result.get("awb_assign_status") == 1:
                                    success_count += 1
                                else:
                                    failed.append(sid)
                            except Exception as e:
                                failed.append(sid)
                            
                            progress.progress((i + 1) / len(shipment_ids), 
                                            text=f"Processing {i+1}/{len(shipment_ids)}...")
                        
                        progress.empty()
                        st.success(f"✅ Shipped **{success_count}** orders successfully!")
                        if failed:
                            st.warning(f"⚠️ {len(failed)} orders failed")
                    else:
                        st.warning("No valid shipments found")
            
            # Download Labels
            if order_status == "ready_to_ship":
                st.markdown("### 📥 Download Labels")
                
                if st.button("📄 Generate & Download Labels", type="primary", use_container_width=True):
                    shipment_ids = []
                    for order in orders:
                        shipments = order.get("shipments", {})
                        if isinstance(shipments, dict):
                            shipment_ids.append(shipments.get("id"))
                        elif isinstance(shipments, list) and shipments:
                            shipment_ids.append(shipments[0].get("id"))
                    
                    shipment_ids = [sid for sid in shipment_ids if sid]
                    
                    if shipment_ids:
                        try:
                            with st.spinner("Generating labels..."):
                                label_url = api_get_label_url(st.session_state.api_token, shipment_ids)
                                
                                if label_url:
                                    # Download the PDF
                                    response = requests.get(label_url)
                                    if response.status_code == 200:
                                        # Option 1: Direct download
                                        st.download_button(
                                            "📥 Download Labels PDF",
                                            data=response.content,
                                            file_name=f"labels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                            mime="application/pdf",
                                            use_container_width=True
                                        )
                                        
                                        # Option 2: Sort labels
                                        st.info("💡 Want sorted labels? Download and re-upload in the 'Upload Labels' tab!")
                                    else:
                                        st.markdown(f"[📥 Download Labels PDF]({label_url})")
                                else:
                                    st.warning("Could not generate label URL")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")


# --- Footer ---
st.divider()

with st.expander("ℹ️ How it works"):
    st.markdown("""
    ### 📤 Upload Labels (Manual)
    1. Download bulk labels PDF from Shiprocket
    2. Upload here and get sorted PDFs by Courier + SKU
    3. Output format: `YYYY-MM-DD_Courier_SKU.pdf`
    
    ### 🔌 Shiprocket API (Automated)
    1. Connect with your Shiprocket credentials
    2. View and manage orders directly
    3. **Ship All** - One-click bulk shipping with auto courier assignment
    4. **Download Labels** - Generate and download labels for shipped orders
    
    **Supported Couriers:** Ekart, Delhivery, Xpressbees, BlueDart, DTDC, Shadowfax, Ecom Express
    """)

st.caption("Built with ❤️ by JSK Labs")

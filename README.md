# 📦 Shiprocket Label Sorter

Sort bulk shipping labels by Courier + SKU in seconds. Now with **Shiprocket API integration** for automated shipping!

**Live Demo:** [jsk-labs-maker-shiprocket-label-sorter-app-zzx9qs.streamlit.app](https://jsk-labs-maker-shiprocket-label-sorter-app-zzx9qs.streamlit.app/)

## ✨ Features

### 📤 Manual Upload Mode
- Upload bulk labels PDF from Shiprocket
- Auto-detects courier (Ekart, Delhivery, Xpressbees, BlueDart, DTDC, Shadowfax, Ecom Express)
- Extracts SKU and invoice date
- Outputs sorted PDFs: `YYYY-MM-DD_Courier_SKU.pdf`
- Download all as ZIP

### 🔌 Shiprocket API Mode (NEW!)
- Connect directly to your Shiprocket account
- View orders by status (New, Ready to Ship, In Transit, etc.)
- **One-click bulk shipping** with auto courier assignment (uses your priority settings!)
- Download labels directly from API
- View wallet balance

## 🚀 Quick Start

### Option 1: Use the Web App
Just visit the [live demo](https://jsk-labs-maker-shiprocket-label-sorter-app-zzx9qs.streamlit.app/) - no installation needed!

### Option 2: Run Locally

```bash
# Clone the repo
git clone https://github.com/jsk-labs-maker/shiprocket-label-sorter.git
cd shiprocket-label-sorter

# Install dependencies
pip install -r requirements.txt

# (Optional) Set up API credentials
cp .env.example .env
# Edit .env with your Shiprocket email/password

# Run the app
streamlit run app.py
```

## 📁 Project Structure

```
shiprocket-label-sorter/
├── app.py              # Streamlit web app
├── label_sorter.py     # CLI sorting tool
├── shiprocket_api.py   # Shiprocket API client
├── requirements.txt    # Python dependencies
├── .env.example        # Example credentials file
└── README.md
```

## 🔑 API Credentials

For API mode, you need Shiprocket credentials:

1. Create a `.env` file (copy from `.env.example`)
2. Add your credentials:
   ```
   SHIPROCKET_EMAIL=your_email@example.com
   SHIPROCKET_PASSWORD=your_password
   ```

Or enter them directly in the web UI (credentials are not stored).

## 📖 API Usage (Python)

```python
from shiprocket_api import ShiprocketAPI

# Initialize (uses .env or pass credentials)
api = ShiprocketAPI()

# Get new orders
orders = api.get_orders(status="NEW")

# Ship an order (auto courier based on your priority)
result = api.assign_awb(shipment_id=1234567)
print(f"AWB: {result['response']['data']['awb_code']}")
print(f"Courier: {result['response']['data']['courier_name']}")

# Bulk ship all new orders
from shiprocket_api import quick_ship_new_orders
summary = quick_ship_new_orders()
print(f"Shipped: {summary['shipped']} orders")

# Download labels
label_url = api.get_label_url([shipment_id_1, shipment_id_2])
```

## 🔧 Supported Couriers

| Courier | Detected As |
|---------|-------------|
| Ekart Logistics | Ekart |
| Delhivery (all variants) | Delhivery |
| Xpressbees (all variants) | Xpressbees |
| BlueDart | BlueDart |
| DTDC | DTDC |
| Shadowfax | Shadowfax |
| Ecom Express | EcomExpress |

## 🛠️ CLI Usage

For command-line processing:

```bash
python label_sorter.py input_labels.pdf --output ./sorted/
```

## 📝 Output Format

Sorted files follow this naming convention:
```
YYYY-MM-DD_Courier_SKU.pdf
```

Examples:
- `2026-02-16_Delhivery_SKU123.pdf`
- `2026-02-16_Ekart_PROD456.pdf`

## 🤝 Contributing

PRs welcome! This tool is built by JSK Labs.

## 📄 License

MIT License

---

Built with ❤️ by Kluzo 😎 for JSK Labs

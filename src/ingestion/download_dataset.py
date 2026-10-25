import os
import urllib.request
import pandas as pd

RAW_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "raw")
BASE_URL = "https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets/"

FILES_TO_DOWNLOAD = [
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv"
]

def download_raw_data():
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    for filename in FILES_TO_DOWNLOAD:
        target_path = os.path.join(RAW_DATA_DIR, filename)
        if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
            print(f"[ALREADY EXISTS] {filename} ({os.path.getsize(target_path):,} bytes)")
            continue
        url = BASE_URL + filename
        print(f"[DOWNLOADING] {filename} from {url}...")
        try:
            urllib.request.urlretrieve(url, target_path)
            size = os.path.getsize(target_path)
            print(f"[SUCCESS] Downloaded {filename}: {size:,} bytes")
        except Exception as e:
            print(f"[ERROR] Failed to download {filename}: {e}")

if __name__ == "__main__":
    download_raw_data()

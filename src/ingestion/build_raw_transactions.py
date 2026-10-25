import os
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")

def build_raw_transactional_view():
    print("[INFO] Loading raw datasets...")
    orders_path = os.path.join(RAW_DIR, "olist_orders_dataset.csv")
    items_path = os.path.join(RAW_DIR, "olist_order_items_dataset.csv")
    products_path = os.path.join(RAW_DIR, "olist_products_dataset.csv")
    trans_path = os.path.join(RAW_DIR, "product_category_name_translation.csv")
    sellers_path = os.path.join(RAW_DIR, "olist_sellers_dataset.csv")

    df_orders = pd.read_csv(orders_path)
    df_items = pd.read_csv(items_path)
    df_products = pd.read_csv(products_path)
    df_trans = pd.read_csv(trans_path)
    df_sellers = pd.read_csv(sellers_path)

    print(f"Loaded {len(df_orders):,} orders, {len(df_items):,} order items.")

    # Convert timestamps
    df_orders['order_purchase_timestamp'] = pd.to_datetime(df_orders['order_purchase_timestamp'], errors='coerce')
    df_orders['order_delivered_customer_date'] = pd.to_datetime(df_orders['order_delivered_customer_date'], errors='coerce')
    df_orders['order_estimated_delivery_date'] = pd.to_datetime(df_orders['order_estimated_delivery_date'], errors='coerce')

    # Compute actual lead time in days, fallback to estimated lead time
    actual_lead_time = (df_orders['order_delivered_customer_date'] - df_orders['order_purchase_timestamp']).dt.total_seconds() / 86400.0
    estimated_lead_time = (df_orders['order_estimated_delivery_date'] - df_orders['order_purchase_timestamp']).dt.total_seconds() / 86400.0

    df_orders['lead_time_days'] = actual_lead_time.fillna(estimated_lead_time)
    # Clip negative or unrealistically high lead times (e.g. 1 to 120 days)
    median_lead = df_orders['lead_time_days'].median()
    df_orders['lead_time_days'] = df_orders['lead_time_days'].apply(
        lambda x: round(float(x), 2) if (pd.notnull(x) and 0.5 <= x <= 180) else round(float(median_lead), 2)
    )

    # Product category translation
    df_products = df_products.merge(df_trans, on='product_category_name', how='left')
    df_products['product_category_name_english'] = df_products['product_category_name_english'].fillna('other')

    # Aggregate item quantities per order, product, seller (warehouse)
    item_agg = df_items.groupby(['order_id', 'product_id', 'seller_id']).agg(
        quantity=('order_item_id', 'count'),
        unit_price=('price', 'mean'),
        total_price=('price', 'sum'),
        total_freight=('freight_value', 'sum')
    ).reset_index()

    # Merge orders with aggregated items
    merged = item_agg.merge(
        df_orders[['order_id', 'customer_id', 'order_status', 'order_purchase_timestamp', 'lead_time_days']],
        on='order_id',
        how='inner'
    )

    # Merge products
    merged = merged.merge(
        df_products[['product_id', 'product_category_name_english', 'product_weight_g']],
        on='product_id',
        how='left'
    )

    # Rename and standardize required supply chain columns
    merged.rename(columns={
        'order_purchase_timestamp': 'order_date',
        'seller_id': 'warehouse_id',
        'product_category_name_english': 'product_category'
    }, inplace=True)

    merged['store_id'] = merged['warehouse_id']

    # Final column ordering matching requirements
    output_cols = [
        'order_id',
        'product_id',
        'order_date',
        'quantity',
        'unit_price',
        'store_id',
        'warehouse_id',
        'lead_time_days',
        'customer_id',
        'product_category',
        'order_status'
    ]
    df_final = merged[output_cols].sort_values('order_date').reset_index(drop=True)

    output_file = os.path.join(RAW_DIR, "raw_supply_chain_transactions.csv")
    df_final.to_csv(output_file, index=False)
    print(f"[SUCCESS] Generated standardized transactional dataset: {output_file}")
    print(f"Total Rows: {len(df_final):,}")
    print(f"Date Range: {df_final['order_date'].min()} to {df_final['order_date'].max()}")
    print(f"Unique Products: {df_final['product_id'].nunique():,}")
    print(f"Unique Warehouses/Sellers: {df_final['warehouse_id'].nunique():,}")
    print("\nSample Preview:")
    print(df_final.head(3).to_string())

if __name__ == "__main__":
    build_raw_transactional_view()

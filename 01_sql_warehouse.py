"""
================================================================================
Phase 2: Local SQL Analytics & Data Warehousing (DuckDB)
Project: Smart Supply Chain Analytics & Automated Demand Forecasting Engine
Script: 01_sql_warehouse.py
================================================================================
"""

import os
import duckdb
import pandas as pd

def main():
    db_path = 'supply_chain.duckdb'
    print(f"[INFO] Connecting to DuckDB database: {db_path}...")
    con = duckdb.connect(database=db_path)

    # Ensure processed directory exists
    os.makedirs(os.path.join('data', 'processed'), exist_ok=True)

    # --------------------------------------------------------------------------
    # 1. Ingestion: Raw Tables & Relational Schema Modeling
    # --------------------------------------------------------------------------
    print("\n[STEP 1] Ingesting raw CSVs and building relational schema...")

    # Primary raw orders ingestion
    orders_source = 'orders.csv' if os.path.exists('orders.csv') else 'data/raw/raw_supply_chain_transactions.csv'
    con.execute(f"""
        CREATE OR REPLACE TABLE raw_orders AS 
        SELECT * FROM read_csv_auto('{orders_source}');
    """)
    orders_count = con.execute("SELECT COUNT(*) FROM raw_orders").fetchone()[0]
    print(f" -> Table 'raw_orders' loaded: {orders_count:,} records.")

    # Products Dimension
    if os.path.exists('data/raw/olist_products_dataset.csv'):
        con.execute("""
            CREATE OR REPLACE TABLE dim_products AS
            SELECT 
                p.product_id,
                COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') AS category_name,
                p.product_weight_g,
                p.product_length_cm,
                p.product_height_cm,
                p.product_width_cm
            FROM read_csv_auto('data/raw/olist_products_dataset.csv') p
            LEFT JOIN read_csv_auto('data/raw/product_category_name_translation.csv') t
                ON p.product_category_name = t.product_category_name;
        """)
        prod_count = con.execute("SELECT COUNT(*) FROM dim_products").fetchone()[0]
        print(f" -> Dimension 'dim_products' created: {prod_count:,} SKUs.")

    # Warehouses / Sellers Dimension
    if os.path.exists('data/raw/olist_sellers_dataset.csv'):
        con.execute("""
            CREATE OR REPLACE TABLE dim_warehouses AS
            SELECT 
                seller_id AS warehouse_id,
                seller_zip_code_prefix AS zip_code,
                seller_city AS city,
                seller_state AS state
            FROM read_csv_auto('data/raw/olist_sellers_dataset.csv');
        """)
        wh_count = con.execute("SELECT COUNT(*) FROM dim_warehouses").fetchone()[0]
        print(f" -> Dimension 'dim_warehouses' created: {wh_count:,} warehouse locations.")

    # Fact Orders table with standardized data types
    con.execute("""
        CREATE OR REPLACE TABLE fact_orders AS
        SELECT 
            order_id,
            product_id,
            CAST(order_date AS TIMESTAMP) AS order_timestamp,
            CAST(order_date AS DATE) AS order_date,
            quantity,
            unit_price,
            ROUND(quantity * unit_price, 2) AS total_revenue,
            warehouse_id,
            ROUND(lead_time_days, 2) AS lead_time_days,
            customer_id,
            product_category,
            order_status
        FROM raw_orders
        WHERE order_status NOT IN ('canceled', 'unavailable');
    """)
    fact_count = con.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0]
    print(f" -> Fact Table 'fact_orders' generated: {fact_count:,} valid sales orders.")

    # --------------------------------------------------------------------------
    # 2. Benchmark Query: 7-Day & 30-Day Rolling Demand Averages (Window Functions)
    # --------------------------------------------------------------------------
    print("\n[STEP 2] Computing Rolling 7-Day and 30-Day Moving Demand Averages...")
    query_rolling_demand = """
        WITH DailyDemand AS (
            SELECT 
                product_id,
                product_category,
                CAST(order_date AS DATE) AS demand_date,
                SUM(quantity) AS total_units_sold,
                ROUND(SUM(total_revenue), 2) AS daily_revenue
            FROM fact_orders
            GROUP BY product_id, product_category, CAST(order_date AS DATE)
        )
        SELECT 
            product_id,
            product_category,
            demand_date,
            total_units_sold,
            daily_revenue,
            ROUND(AVG(total_units_sold) OVER (
                PARTITION BY product_id 
                ORDER BY demand_date 
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            ), 2) AS rolling_7day_avg_demand,
            ROUND(AVG(total_units_sold) OVER (
                PARTITION BY product_id 
                ORDER BY demand_date 
                ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ), 2) AS rolling_30day_avg_demand,
            SUM(total_units_sold) OVER (
                PARTITION BY product_id 
                ORDER BY demand_date 
                ROWS UNBOUNDED PRECEDING
            ) AS cumulative_units_sold
        FROM DailyDemand
        ORDER BY product_id, demand_date;
    """
    df_rolling = con.execute(query_rolling_demand).df()
    con.execute("CREATE OR REPLACE TABLE analytics_rolling_demand AS SELECT * FROM df_rolling;")
    print("Preview of Rolling Demand Averages:")
    print(df_rolling.head(10).to_string())

    # --------------------------------------------------------------------------
    # 3. Supply Chain Lead Times & Order Intervals (LAG / LEAD Window Functions)
    # --------------------------------------------------------------------------
    print("\n[STEP 3] Analyzing Order Intervals & Warehouse Lead Time Variance (LAG/LEAD)...")
    query_lead_times = """
        WITH OrderSequence AS (
            SELECT 
                product_id,
                order_id,
                warehouse_id,
                order_date,
                lead_time_days,
                LAG(order_date) OVER (
                    PARTITION BY product_id 
                    ORDER BY order_date
                ) AS prev_order_date,
                LEAD(order_date) OVER (
                    PARTITION BY product_id 
                    ORDER BY order_date
                ) AS next_order_date
            FROM fact_orders
        )
        SELECT 
            product_id,
            order_id,
            warehouse_id,
            order_date,
            lead_time_days,
            prev_order_date,
            DATEDIFF('day', prev_order_date, order_date) AS days_since_last_order,
            next_order_date,
            DATEDIFF('day', order_date, next_order_date) AS days_until_next_order
        FROM OrderSequence
        WHERE prev_order_date IS NOT NULL
        ORDER BY product_id, order_date;
    """
    df_order_intervals = con.execute(query_lead_times).df()
    con.execute("CREATE OR REPLACE TABLE analytics_order_intervals AS SELECT * FROM df_order_intervals;")
    print(f" -> Computed inter-order intervals: {len(df_order_intervals):,} sequences.")
    print(df_order_intervals.head(5).to_string())

    # --------------------------------------------------------------------------
    # 4. Warehouse & Supplier Performance Metrics
    # --------------------------------------------------------------------------
    print("\n[STEP 4] Supplier & Warehouse Fulfillment Benchmarking...")
    query_warehouse_perf = """
        SELECT 
            warehouse_id,
            COUNT(order_id) AS total_orders_fulfilled,
            SUM(quantity) AS total_units_shipped,
            ROUND(AVG(lead_time_days), 2) AS avg_lead_time_days,
            ROUND(STDDEV_SAMP(lead_time_days), 2) AS lead_time_stddev,
            ROUND(MIN(lead_time_days), 2) AS min_lead_time_days,
            ROUND(MAX(lead_time_days), 2) AS max_lead_time_days,
            ROUND(QUANTILE_CONT(lead_time_days, 0.95), 2) AS p95_lead_time_days
        FROM fact_orders
        GROUP BY warehouse_id
        HAVING COUNT(order_id) >= 10
        ORDER BY total_orders_fulfilled DESC;
    """
    df_wh_perf = con.execute(query_warehouse_perf).df()
    con.execute("CREATE OR REPLACE TABLE analytics_warehouse_performance AS SELECT * FROM df_wh_perf;")
    print(df_wh_perf.head(5).to_string())

    # --------------------------------------------------------------------------
    # 5. Inventory Turnover & Stockout Frequency Simulation (CTEs + Window Functions)
    # --------------------------------------------------------------------------
    print("\n[STEP 5] Computing Inventory Turnover Rates & Stockout Risk...")
    query_inventory_turnover = """
        WITH CategorySummary AS (
            SELECT 
                product_category,
                COUNT(DISTINCT product_id) AS total_skus,
                SUM(quantity) AS annual_demand_units,
                ROUND(SUM(total_revenue), 2) AS total_cogs_revenue,
                ROUND(AVG(lead_time_days), 2) AS avg_lead_time_days,
                ROUND(STDDEV_SAMP(quantity), 2) AS demand_stddev
            FROM fact_orders
            GROUP BY product_category
        ),
        InventoryEstimates AS (
            SELECT 
                product_category,
                total_skus,
                annual_demand_units,
                total_cogs_revenue,
                avg_lead_time_days,
                -- Average daily demand
                ROUND(annual_demand_units / 365.0, 2) AS daily_demand_rate,
                -- Baseline safety stock target: 1.65 (95% service level) * sigma * sqrt(L)
                ROUND(1.65 * COALESCE(demand_stddev, 1.0) * SQRT(avg_lead_time_days), 2) AS safety_stock_units,
                -- Estimated cycle inventory: Q / 2 = (14 days demand) / 2
                ROUND((annual_demand_units / 365.0 * 14.0) / 2.0, 2) AS cycle_stock_units
            FROM CategorySummary
        )
        SELECT 
            product_category,
            total_skus,
            annual_demand_units,
            total_cogs_revenue,
            avg_lead_time_days,
            safety_stock_units,
            ROUND(cycle_stock_units + safety_stock_units, 2) AS estimated_avg_inventory_units,
            -- Inventory Turnover = Annual Demand / Average Inventory
            ROUND(annual_demand_units / NULLIF(cycle_stock_units + safety_stock_units, 0), 2) AS inventory_turnover_ratio,
            -- Days of Supply = (Average Inventory / Annual Demand) * 365
            ROUND(((cycle_stock_units + safety_stock_units) / NULLIF(annual_demand_units, 0)) * 365.0, 1) AS days_of_supply,
            -- Reorder Point (ROP) = (Daily Demand * Lead Time) + Safety Stock
            ROUND((daily_demand_rate * avg_lead_time_days) + safety_stock_units, 2) AS reorder_point_units
        FROM InventoryEstimates
        WHERE annual_demand_units > 100
        ORDER BY annual_demand_units DESC;
    """
    df_inv = con.execute(query_inventory_turnover).df()
    con.execute("CREATE OR REPLACE TABLE analytics_inventory_turnover AS SELECT * FROM df_inv;")
    print(df_inv.head(10).to_string())

    # --------------------------------------------------------------------------
    # 6. Multi-Dimensional Aggregation (GROUP BY CUBE / ROLLUP)
    # --------------------------------------------------------------------------
    print("\n[STEP 6] Executing Multi-Dimensional Aggregation (GROUP BY ROLLUP / CUBE)...")
    query_cube = """
        SELECT 
            product_category,
            EXTRACT(YEAR FROM order_date) AS order_year,
            EXTRACT(QUARTER FROM order_date) AS order_quarter,
            SUM(quantity) AS total_units_sold,
            ROUND(SUM(total_revenue), 2) AS total_sales_usd,
            COUNT(DISTINCT order_id) AS total_orders
        FROM fact_orders
        WHERE product_category IN ('health_beauty', 'bed_bath_table', 'sports_leisure', 'computers_accessories', 'furniture_decor')
        GROUP BY ROLLUP(product_category, EXTRACT(YEAR FROM order_date), EXTRACT(QUARTER FROM order_date))
        ORDER BY product_category NULLS LAST, order_year NULLS LAST, order_quarter NULLS LAST;
    """
    df_cube = con.execute(query_cube).df()
    con.execute("CREATE OR REPLACE TABLE analytics_rollup_summary AS SELECT * FROM df_cube;")
    print(df_cube.head(15).to_string())

    # --------------------------------------------------------------------------
    # 7. Export Baseline Artifacts for Downstream ML & Power BI
    # --------------------------------------------------------------------------
    print("\n[STEP 7] Exporting processed analytics baselines...")
    rolling_export = os.path.join('data', 'processed', 'rolling_demand_baseline.parquet')
    con.execute(f"COPY analytics_rolling_demand TO '{rolling_export}' (FORMAT PARQUET);")
    
    inv_export = os.path.join('data', 'processed', 'inventory_turnover_kpis.csv')
    con.execute(f"COPY analytics_inventory_turnover TO '{inv_export}' (HEADER, DELIMITER ',');")
    
    wh_export = os.path.join('data', 'processed', 'warehouse_fulfillment_kpis.csv')
    con.execute(f"COPY analytics_warehouse_performance TO '{wh_export}' (HEADER, DELIMITER ',');")

    print(f" -> Exported Parquet: {rolling_export} ({os.path.getsize(rolling_export):,} bytes)")
    print(f" -> Exported CSV: {inv_export} ({os.path.getsize(inv_export):,} bytes)")
    print(f" -> Exported CSV: {wh_export} ({os.path.getsize(wh_export):,} bytes)")

    # Display database tables summary
    tables = con.execute("SHOW TABLES;").df()
    print("\n[SUMMARY] DuckDB Warehouse Tables:")
    print(tables.to_string())

    con.close()
    print("\n[SUCCESS] Phase 2: DuckDB Analytical Data Warehouse setup completed successfully!")

if __name__ == '__main__':
    main()

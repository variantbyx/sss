-- =============================================================================
-- SMART SUPPLY CHAIN ANALYTICS: ANALYTICAL SQL REPOSITORY
-- Database Engine: DuckDB / PostgreSQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Daily Demand Aggregation & Rolling 7-Day / 30-Day Moving Averages
-- -----------------------------------------------------------------------------
WITH DailyDemand AS (
    SELECT 
        product_id,
        product_category,
        CAST(order_date AS DATE) AS demand_date,
        SUM(quantity) AS total_units_sold,
        ROUND(SUM(quantity * unit_price), 2) AS daily_revenue
    FROM fact_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
    GROUP BY product_id, product_category, CAST(order_date AS DATE)
)
SELECT 
    product_id,
    product_category,
    demand_date,
    total_units_sold,
    daily_revenue,
    -- 7-Day Moving Demand Average
    ROUND(AVG(total_units_sold) OVER (
        PARTITION BY product_id 
        ORDER BY demand_date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_7day_avg_demand,
    -- 30-Day Moving Demand Average
    ROUND(AVG(total_units_sold) OVER (
        PARTITION BY product_id 
        ORDER BY demand_date 
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_30day_avg_demand,
    -- Cumulative Units Sold to Date
    SUM(total_units_sold) OVER (
        PARTITION BY product_id 
        ORDER BY demand_date 
        ROWS UNBOUNDED PRECEDING
    ) AS cumulative_units_sold
FROM DailyDemand
ORDER BY product_id, demand_date;

-- -----------------------------------------------------------------------------
-- 2. Inter-Order Velocity & Fulfillment Lead Time (LAG / LEAD Functions)
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- 3. Supplier / Warehouse Fulfillment & P95 Lead Time Benchmarks
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- 4. Dynamic Safety Stock, Reorder Point (ROP) & Inventory Turnover Ratio
-- -----------------------------------------------------------------------------
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
        ROUND(annual_demand_units / 365.0, 2) AS daily_demand_rate,
        -- Safety Stock = Z (1.65 for 95% service level) * sigma * sqrt(L)
        ROUND(1.65 * COALESCE(demand_stddev, 1.0) * SQRT(avg_lead_time_days), 2) AS safety_stock_units,
        -- Cycle Stock (Q/2 with 14-day reorder cycle)
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
    ROUND(annual_demand_units / NULLIF(cycle_stock_units + safety_stock_units, 0), 2) AS inventory_turnover_ratio,
    ROUND(((cycle_stock_units + safety_stock_units) / NULLIF(annual_demand_units, 0)) * 365.0, 1) AS days_of_supply,
    ROUND((daily_demand_rate * avg_lead_time_days) + safety_stock_units, 2) AS reorder_point_units
FROM InventoryEstimates
WHERE annual_demand_units > 100
ORDER BY annual_demand_units DESC;

-- -----------------------------------------------------------------------------
-- 5. Multi-Dimensional Demand Cube (GROUP BY ROLLUP / CUBE)
-- -----------------------------------------------------------------------------
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

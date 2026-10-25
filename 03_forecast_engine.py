"""
================================================================================
Phase 4: Time-Series Demand Forecasting & Inventory Optimization
Project: Smart Supply Chain Analytics & Automated Demand Forecasting Engine
Script: 03_forecast_engine.py
================================================================================
"""

import os
import duckdb
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from prophet import Prophet
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error

def prepare_daily_demand():
    """Ensure daily_demand.csv exists by querying DuckDB if needed."""
    if not os.path.exists('daily_demand.csv'):
        print("[INFO] Generating daily_demand.csv from supply_chain.duckdb...")
        con = duckdb.connect('supply_chain.duckdb')
        df_demand = con.execute("""
            SELECT 
                CAST(order_date AS DATE) AS ds,
                SUM(quantity) AS y
            FROM fact_orders
            WHERE order_date BETWEEN '2017-01-01' AND '2018-08-31'
            GROUP BY CAST(order_date AS DATE)
            ORDER BY ds;
        """).df()
        df_demand.to_csv('daily_demand.csv', index=False)
        con.close()
        print(f"[SUCCESS] Created daily_demand.csv with {len(df_demand)} records.")
    return pd.read_csv('daily_demand.csv')

def main():
    print("=" * 70)
    print(" Smart Supply Chain Automated Demand Forecasting Engine")
    print(" Model: Facebook Prophet (Bayesian Time-Series with Seasonality)")
    print("=" * 70)

    # --------------------------------------------------------------------------
    # 1. Load Daily Aggregated Demand Data
    # --------------------------------------------------------------------------
    df = prepare_daily_demand()
    df['ds'] = pd.to_datetime(df['ds'])
    print(f"\n[STEP 1] Loaded {len(df)} historical daily demand observations.")
    print(f"Date Range: {df['ds'].min().date()} to {df['ds'].max().date()}")
    print(f"Demand Summary: Mean={df['y'].mean():.2f}, Min={df['y'].min():.0f}, Max={df['y'].max():.0f}, Std={df['y'].std():.2f}")

    # --------------------------------------------------------------------------
    # 2. Train Time-Series Forecasting Model
    # --------------------------------------------------------------------------
    print("\n[STEP 2] Training Prophet Time-Series Model...")
    # Evaluate accuracy using holdout period (last 30 days)
    train_df = df.iloc[:-30]
    test_df = df.iloc[-30:]

    eval_model = Prophet(
        yearly_seasonality=True, 
        weekly_seasonality=True, 
        daily_seasonality=False,
        interval_width=0.95
    )
    eval_model.fit(train_df)

    eval_future = eval_model.make_future_dataframe(periods=30)
    eval_forecast = eval_model.predict(eval_future)

    # Compute validation metrics
    preds_test = eval_forecast.iloc[-30:]['yhat'].values
    actuals_test = test_df['y'].values
    rmse = np.sqrt(mean_squared_error(actuals_test, preds_test))
    mape = mean_absolute_percentage_error(actuals_test, preds_test) * 100

    print(f"\n--- Model Validation Metrics (30-Day Holdout) ---")
    print(f"Root Mean Squared Error (RMSE): {rmse:.2f} units")
    print(f"Mean Absolute Percentage Error (MAPE): {mape:.2f}%")
    print(f"Forecast Accuracy: {max(0, 100 - mape):.2f}%")

    # Fit final model on full historical dataset
    print("\nFitting final model on full dataset for 30-day forward forecast...")
    model = Prophet(
        yearly_seasonality=True, 
        weekly_seasonality=True, 
        daily_seasonality=False,
        interval_width=0.95
    )
    model.fit(df)

    # Forecast next 30 days
    future = model.make_future_dataframe(periods=30)
    forecast = model.predict(future)

    # --------------------------------------------------------------------------
    # 3. Supply Chain Logic: Safety Stock & Reorder Point (ROP) Calculation
    # --------------------------------------------------------------------------
    print("\n[STEP 3] Calculating Supply Chain Safety Stock & Reorder Point (ROP)...")
    service_level_z = 1.65  # 95% service level confidence (Z-score)
    lead_time_days = 7
    avg_daily_demand = forecast['yhat'].mean()
    std_daily_demand = df['y'].std()

    safety_stock = int(service_level_z * std_daily_demand * np.sqrt(lead_time_days))
    reorder_point = int((avg_daily_demand * lead_time_days) + safety_stock)

    print("-" * 55)
    print(f" Service Level Target (Z):       {service_level_z} (95% non-stockout probability)")
    print(f" Supplier Lead Time (L):         {lead_time_days} days")
    print(f" Average Daily Demand (d):       {avg_daily_demand:.2f} units/day")
    print(f" Demand Std Deviation (sigma_d): {std_daily_demand:.2f} units")
    print(f" >> Calculated Safety Stock:     {safety_stock} units")
    print(f" >> Calculated Reorder Point:    {reorder_point} units")
    print("-" * 55)

    # --------------------------------------------------------------------------
    # 4. Multi-Category Supply Chain KPI Optimization
    # --------------------------------------------------------------------------
    print("\n[STEP 4] Running Category-Level Forecasting & Inventory Optimization...")
    con = duckdb.connect('supply_chain.duckdb')
    top_categories = ['bed_bath_table', 'health_beauty', 'sports_leisure', 'computers_accessories', 'furniture_decor']
    cat_kpis = []

    for cat in top_categories:
        cat_df = con.execute(f"""
            SELECT 
                CAST(order_date AS DATE) AS ds,
                SUM(quantity) AS y
            FROM fact_orders
            WHERE product_category = '{cat}'
              AND order_date BETWEEN '2017-01-01' AND '2018-08-31'
            GROUP BY CAST(order_date AS DATE)
            ORDER BY ds;
        """).df()

        if len(cat_df) > 60:
            cat_df['ds'] = pd.to_datetime(cat_df['ds'])
            cat_model = Prophet(yearly_seasonality=False, weekly_seasonality=True)
            cat_model.fit(cat_df)
            cat_future = cat_model.make_future_dataframe(periods=30)
            cat_fc = cat_model.predict(cat_future)

            cat_avg_d = cat_fc['yhat'].mean()
            cat_std_d = cat_df['y'].std()
            cat_ss = int(1.65 * cat_std_d * np.sqrt(13.0)) # ~13 day avg lead time
            cat_rop = int((cat_avg_d * 13.0) + cat_ss)

            cat_kpis.append({
                'product_category': cat,
                'historical_days': len(cat_df),
                'total_units_sold': int(cat_df['y'].sum()),
                'avg_daily_demand': round(cat_avg_d, 2),
                'daily_std_dev': round(cat_std_d, 2),
                'safety_stock_units': cat_ss,
                'reorder_point_units': cat_rop
            })
    con.close()

    df_cat_kpis = pd.DataFrame(cat_kpis)
    print("\nTop Category Reorder Optimization Table:")
    print(df_cat_kpis.to_string(index=False))

    # --------------------------------------------------------------------------
    # 5. Export Datasets for Power BI & Executive Dashboards
    # --------------------------------------------------------------------------
    print("\n[STEP 5] Exporting Forecast & Inventory Data for Power BI...")
    os.makedirs(os.path.join('data', 'processed'), exist_ok=True)

    # 1. Standard user-requested output
    forecast_output = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
    forecast_output.to_csv('demand_forecast_output.csv', index=False)
    print(f" -> Exported user forecast: demand_forecast_output.csv ({len(forecast_output)} rows)")

    # 2. Detailed Power BI model: merge actuals with predictions
    df_merged = pd.merge(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper', 'trend', 'weekly', 'yearly']], 
                         df[['ds', 'y']], on='ds', how='left')
    df_merged['is_forecast'] = np.where(df_merged['y'].isna(), 1, 0)
    df_merged['safety_stock_threshold'] = safety_stock
    df_merged['reorder_point_threshold'] = reorder_point
    df_merged['model_rmse'] = round(rmse, 2)
    df_merged['model_mape_pct'] = round(mape, 2)

    detailed_path = os.path.join('data', 'processed', 'demand_forecast_detailed.csv')
    df_merged.to_csv(detailed_path, index=False)
    print(f" -> Exported Power BI detailed model: {detailed_path} ({len(df_merged)} rows)")

    # 3. Export Category KPIs
    cat_kpi_path = os.path.join('data', 'processed', 'category_reorder_kpis.csv')
    df_cat_kpis.to_csv(cat_kpi_path, index=False)
    print(f" -> Exported Category KPIs: {cat_kpi_path}")

    # --------------------------------------------------------------------------
    # 6. Generate Forecast Chart
    # --------------------------------------------------------------------------
    print("\n[STEP 6] Rendering forecast visualization plot...")
    plt.figure(figsize=(12, 6))
    plt.plot(df['ds'], df['y'], label='Historical Daily Demand', color='#2b5c8f', alpha=0.7, lw=1.2)
    plt.plot(forecast['ds'], forecast['yhat'], label='Prophet Predicted Demand', color='#e74c3c', lw=2)
    plt.fill_between(forecast['ds'], forecast['yhat_lower'], forecast['yhat_upper'], color='#e74c3c', alpha=0.15, label='95% Confidence Band')
    plt.axvline(x=df['ds'].max(), color='#27ae60', linestyle='--', label='Forecast Start Date (T+30 Days)')
    plt.axhline(y=reorder_point / lead_time_days, color='#e67e22', linestyle=':', label=f'Avg Daily ROP Equiv ({reorder_point//lead_time_days} u/d)')
    plt.title('Supply Chain Daily Demand Forecast & 30-Day Forward Projection', fontsize=14, fontweight='bold')
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Daily Units Demanded', fontsize=12)
    plt.legend(loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()

    chart_path = os.path.join('data', 'processed', 'forecast_projection_chart.png')
    plt.savefig(chart_path, dpi=200)
    plt.close()
    print(f" -> Saved chart: {chart_path}")

    print("\n[SUCCESS] Phase 4: Time-Series Demand Forecasting & Inventory Optimization completed successfully!")

if __name__ == '__main__':
    main()

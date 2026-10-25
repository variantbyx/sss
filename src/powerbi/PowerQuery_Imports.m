// =============================================================================
// POWER BI POWER QUERY (M) SCRIPT IMPORTS
// Project: Smart Supply Chain Analytics
// =============================================================================

// -----------------------------------------------------------------------------
// TABLE 1: DailyDemand
// -----------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents("c:\Users\BIT\Desktop\Garbage\smart supply chain\DailyDemand.csv"),[Delimiter=",", Columns=8, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"product_id", type text}, 
        {"product_category", type text}, 
        {"order_date", type date}, 
        {"actual_units", Int64.Type}, 
        {"daily_revenue", type number}, 
        {"avg_lead_time_days", type number}, 
        {"rolling_7d_avg_demand", type number}, 
        {"rolling_30d_avg_demand", type number}
    })
in
    #"Changed Type"


// -----------------------------------------------------------------------------
// TABLE 2: DemandForecast
// -----------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents("c:\Users\BIT\Desktop\Garbage\smart supply chain\DemandForecast.csv"),[Delimiter=",", Columns=8, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"ds", type date}, 
        {"yhat", type number}, 
        {"yhat_lower", type number}, 
        {"yhat_upper", type number}, 
        {"actual_units", Int64.Type}, 
        {"safety_stock_threshold", Int64.Type}, 
        {"reorder_point_threshold", Int64.Type}, 
        {"forecast_accuracy_pct", type number}
    })
in
    #"Changed Type"


// -----------------------------------------------------------------------------
// TABLE 3: SKUInventory
// -----------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents("c:\Users\BIT\Desktop\Garbage\smart supply chain\sku_inventory_status.csv"),[Delimiter=",", Columns=14, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"product_id", type text}, 
        {"product_category", type text}, 
        {"unit_price", type number}, 
        {"total_units_sold", Int64.Type}, 
        {"daily_demand_rate", type number}, 
        {"lead_time_days", type number}, 
        {"safety_stock_level", Int64.Type}, 
        {"reorder_point", Int64.Type}, 
        {"current_stock", Int64.Type}, 
        {"reorder_alert_status", type text}, 
        {"status_color", type text}, 
        {"stockout_risk_flag", Int64.Type}, 
        {"days_of_supply_remaining", type number}, 
        {"inventory_value_usd", type number}
    })
in
    #"Changed Type"

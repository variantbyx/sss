import os
import json

BASE_DIR = r"c:\Users\BIT\Desktop\Garbage\smart supply chain"

def create_pbip_project():
    print("[INFO] Generating Power BI Project (.pbip)...")

    project_file = os.path.join(BASE_DIR, "SmartSupplyChain.pbip")
    report_folder = os.path.join(BASE_DIR, "SmartSupplyChain.Report")
    semantic_folder = os.path.join(BASE_DIR, "SmartSupplyChain.SemanticModel")
    report_def_folder = os.path.join(report_folder, "definition")

    os.makedirs(report_folder, exist_ok=True)
    os.makedirs(report_def_folder, exist_ok=True)
    os.makedirs(semantic_folder, exist_ok=True)

    # 1. SmartSupplyChain.pbip
    pbip_data = {
        "version": "1.0",
        "artifacts": [
            {
                "report": {
                    "path": "SmartSupplyChain.Report"
                }
            }
        ],
        "settings": {
            "enableAutoRecovery": True
        }
    }
    with open(project_file, "w", encoding="utf-8") as f:
        json.dump(pbip_data, f, indent=2)
    print(f" -> Created: {project_file}")

    # 2. SmartSupplyChain.Report/definition.pbir
    pbir_data = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/1.0.0/schema.json",
        "version": "1.0",
        "datasetReference": {
            "byPath": {
                "path": "../SmartSupplyChain.SemanticModel"
            },
            "byConnection": None
        }
    }
    with open(os.path.join(report_folder, "definition.pbir"), "w", encoding="utf-8") as f:
        json.dump(pbir_data, f, indent=2)

    # 3. SmartSupplyChain.SemanticModel/definition.pbism
    pbism_data = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "1.0"
    }
    with open(os.path.join(semantic_folder, "definition.pbism"), "w", encoding="utf-8") as f:
        json.dump(pbism_data, f, indent=2)

    # 4. SmartSupplyChain.SemanticModel/model.bim
    daily_demand_csv = os.path.join(BASE_DIR, "DailyDemand.csv").replace("\\", "\\\\")
    demand_forecast_csv = os.path.join(BASE_DIR, "DemandForecast.csv").replace("\\", "\\\\")
    sku_inventory_csv = os.path.join(BASE_DIR, "sku_inventory_status.csv").replace("\\", "\\\\")

    model_bim = {
        "name": "SmartSupplyChain",
        "compatibilityLevel": 1567,
        "model": {
            "culture": "en-US",
            "dataAccessOptions": {
                "legacyRedirects": True,
                "returnErrorValuesAsNull": True
            },
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "tables": [
                {
                    "name": "DailyDemand",
                    "columns": [
                        {"name": "product_id", "dataType": "string", "sourceColumn": "product_id"},
                        {"name": "product_category", "dataType": "string", "sourceColumn": "product_category"},
                        {"name": "order_date", "dataType": "dateTime", "sourceColumn": "order_date", "formatString": "yyyy-mm-dd"},
                        {"name": "actual_units", "dataType": "int64", "sourceColumn": "actual_units"},
                        {"name": "daily_revenue", "dataType": "double", "sourceColumn": "daily_revenue", "formatString": "$#,0.00"},
                        {"name": "avg_lead_time_days", "dataType": "double", "sourceColumn": "avg_lead_time_days"},
                        {"name": "rolling_7d_avg_demand", "dataType": "double", "sourceColumn": "rolling_7d_avg_demand"},
                        {"name": "rolling_30d_avg_demand", "dataType": "double", "sourceColumn": "rolling_30d_avg_demand"}
                    ],
                    "partitions": [
                        {
                            "name": "DailyDemand-partition",
                            "mode": "import",
                            "source": {
                                "type": "m",
                                "expression": [
                                    "let",
                                    f'    Source = Csv.Document(File.Contents("{daily_demand_csv}"),[Delimiter=",", Columns=8, Encoding=65001, QuoteStyle=QuoteStyle.None]),',
                                    '    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
                                    '    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{"product_id", type text}, {"product_category", type text}, {"order_date", type date}, {"actual_units", Int64.Type}, {"daily_revenue", type number}, {"avg_lead_time_days", type number}, {"rolling_7d_avg_demand", type number}, {"rolling_30d_avg_demand", type number}})',
                                    "in",
                                    '    #"Changed Type"'
                                ]
                            }
                        }
                    ]
                },
                {
                    "name": "DemandForecast",
                    "columns": [
                        {"name": "ds", "dataType": "dateTime", "sourceColumn": "ds", "formatString": "yyyy-mm-dd"},
                        {"name": "yhat", "dataType": "double", "sourceColumn": "yhat", "formatString": "#,0.0"},
                        {"name": "yhat_lower", "dataType": "double", "sourceColumn": "yhat_lower", "formatString": "#,0.0"},
                        {"name": "yhat_upper", "dataType": "double", "sourceColumn": "yhat_upper", "formatString": "#,0.0"},
                        {"name": "actual_units", "dataType": "int64", "sourceColumn": "actual_units"},
                        {"name": "safety_stock_threshold", "dataType": "int64", "sourceColumn": "safety_stock_threshold"},
                        {"name": "reorder_point_threshold", "dataType": "int64", "sourceColumn": "reorder_point_threshold"},
                        {"name": "forecast_accuracy_pct", "dataType": "double", "sourceColumn": "forecast_accuracy_pct"}
                    ],
                    "measures": [
                        {
                            "name": "Forecast Variance %",
                            "expression": "DIVIDE(SUM(DemandForecast[yhat]) - SUM(DailyDemand[actual_units]), SUM(DailyDemand[actual_units]), 0) * 100",
                            "formatString": "0.0%"
                        },
                        {
                            "name": "Forecast Accuracy %",
                            "expression": "MAX(0, 100 - DIVIDE(SUMX(FILTER(DemandForecast, NOT(ISBLANK(DemandForecast[actual_units])) && DemandForecast[actual_units] > 0), ABS(DemandForecast[actual_units] - DemandForecast[yhat])), SUMX(FILTER(DemandForecast, NOT(ISBLANK(DemandForecast[actual_units])) && DemandForecast[actual_units] > 0), DemandForecast[actual_units]), 0) * 100)",
                            "formatString": "0.0%"
                        },
                        {
                            "name": "Total Projected Stockout Risk Count",
                            "expression": "CALCULATE(COUNTROWS(SKUInventory), SKUInventory[stockout_risk_flag] = 1)",
                            "formatString": "#,0"
                        },
                        {
                            "name": "Critical Stockout Count",
                            "expression": "CALCULATE(COUNTROWS(SKUInventory), SKUInventory[reorder_alert_status] = \"CRITICAL - STOCKOUT RISK\")",
                            "formatString": "#,0"
                        },
                        {
                            "name": "Reorder Alerts Count",
                            "expression": "CALCULATE(COUNTROWS(SKUInventory), SKUInventory[reorder_alert_status] = \"REORDER NOW\")",
                            "formatString": "#,0"
                        },
                        {
                            "name": "Healthy Inventory Count",
                            "expression": "CALCULATE(COUNTROWS(SKUInventory), SKUInventory[reorder_alert_status] = \"HEALTHY\")",
                            "formatString": "#,0"
                        },
                        {
                            "name": "Total Inventory Valuation",
                            "expression": "SUM(SKUInventory[inventory_value_usd])",
                            "formatString": "$#,0.00"
                        },
                        {
                            "name": "Reorder Alert Color",
                            "expression": "SWITCH(SELECTEDVALUE(SKUInventory[reorder_alert_status]), \"CRITICAL - STOCKOUT RISK\", \"#E74C3C\", \"REORDER NOW\", \"#E67E22\", \"HEALTHY\", \"#27AE60\", \"#95A5A6\")"
                        }
                    ],
                    "partitions": [
                        {
                            "name": "DemandForecast-partition",
                            "mode": "import",
                            "source": {
                                "type": "m",
                                "expression": [
                                    "let",
                                    f'    Source = Csv.Document(File.Contents("{demand_forecast_csv}"),[Delimiter=",", Columns=8, Encoding=65001, QuoteStyle=QuoteStyle.None]),',
                                    '    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
                                    '    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{"ds", type date}, {"yhat", type number}, {"yhat_lower", type number}, {"yhat_upper", type number}, {"actual_units", Int64.Type}, {"safety_stock_threshold", Int64.Type}, {"reorder_point_threshold", Int64.Type}, {"forecast_accuracy_pct", type number}})',
                                    "in",
                                    '    #"Changed Type"'
                                ]
                            }
                        }
                    ]
                },
                {
                    "name": "SKUInventory",
                    "columns": [
                        {"name": "product_id", "dataType": "string", "sourceColumn": "product_id"},
                        {"name": "product_category", "dataType": "string", "sourceColumn": "product_category"},
                        {"name": "unit_price", "dataType": "double", "sourceColumn": "unit_price", "formatString": "$#,0.00"},
                        {"name": "total_units_sold", "dataType": "int64", "sourceColumn": "total_units_sold"},
                        {"name": "daily_demand_rate", "dataType": "double", "sourceColumn": "daily_demand_rate"},
                        {"name": "lead_time_days", "dataType": "double", "sourceColumn": "lead_time_days"},
                        {"name": "safety_stock_level", "dataType": "int64", "sourceColumn": "safety_stock_level"},
                        {"name": "reorder_point", "dataType": "int64", "sourceColumn": "reorder_point"},
                        {"name": "current_stock", "dataType": "int64", "sourceColumn": "current_stock"},
                        {"name": "reorder_alert_status", "dataType": "string", "sourceColumn": "reorder_alert_status"},
                        {"name": "status_color", "dataType": "string", "sourceColumn": "status_color"},
                        {"name": "stockout_risk_flag", "dataType": "int64", "sourceColumn": "stockout_risk_flag"},
                        {"name": "days_of_supply_remaining", "dataType": "double", "sourceColumn": "days_of_supply_remaining"},
                        {"name": "inventory_value_usd", "dataType": "double", "sourceColumn": "inventory_value_usd", "formatString": "$#,0.00"}
                    ],
                    "partitions": [
                        {
                            "name": "SKUInventory-partition",
                            "mode": "import",
                            "source": {
                                "type": "m",
                                "expression": [
                                    "let",
                                    f'    Source = Csv.Document(File.Contents("{sku_inventory_csv}"),[Delimiter=",", Columns=14, Encoding=65001, QuoteStyle=QuoteStyle.None]),',
                                    '    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
                                    '    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{"product_id", type text}, {"product_category", type text}, {"unit_price", type number}, {"total_units_sold", Int64.Type}, {"daily_demand_rate", type number}, {"lead_time_days", type number}, {"safety_stock_level", Int64.Type}, {"reorder_point", Int64.Type}, {"current_stock", Int64.Type}, {"reorder_alert_status", type text}, {"status_color", type text}, {"stockout_risk_flag", Int64.Type}, {"days_of_supply_remaining", type number}, {"inventory_value_usd", type number}})',
                                    "in",
                                    '    #"Changed Type"'
                                ]
                            }
                        }
                    ]
                }
            ],
            "relationships": [
                {
                    "name": "Rel_DailyDemand_DemandForecast",
                    "fromTable": "DailyDemand",
                    "fromColumn": "order_date",
                    "toTable": "DemandForecast",
                    "toColumn": "ds"
                },
                {
                    "name": "Rel_DailyDemand_SKUInventory",
                    "fromTable": "DailyDemand",
                    "fromColumn": "product_id",
                    "toTable": "SKUInventory",
                    "toColumn": "product_id"
                }
            ]
        }
    }

    with open(os.path.join(semantic_folder, "model.bim"), "w", encoding="utf-8") as f:
        json.dump(model_bim, f, indent=2)
    print(f" -> Created Semantic Model: {os.path.join(semantic_folder, 'model.bim')}")

    # 5. SmartSupplyChain.Report/definition/report.json (Visual layout)
    report_json = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/1.0.0/schema.json",
        "themeCollection": {
            "baseTheme": {
                "name": "CY24SU02",
                "version": "5.56",
                "type": 2
            }
        },
        "settings": {
            "useNewFilterPaneExperience": True,
            "allowChangeFilterTypes": True
        }
    }
    with open(os.path.join(report_def_folder, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report_json, f, indent=2)
    with open(os.path.join(report_folder, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report_json, f, indent=2)

    print("\n[SUCCESS] SmartSupplyChain.pbip generated successfully!")

if __name__ == '__main__':
    create_pbip_project()

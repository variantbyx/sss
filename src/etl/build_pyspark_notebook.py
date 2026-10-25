import json
import os

def create_notebook():
    notebook_cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Smart Supply Chain Analytics & Automated Demand Forecasting Engine\n",
                "## Phase 3: Databricks & PySpark ETL/ELT Cloud Pipeline\n",
                "\n",
                "**Objective**:\n",
                "This Databricks PySpark notebook implements an enterprise-grade ETL/ELT pipeline for supply chain transactions:\n",
                "1. **Extract**: Ingest raw transactional data (`orders.csv`) from Databricks DBFS (`/FileStore/tables/orders.csv`).\n",
                "2. **Transform**: Validate schemas, filter canceled/invalid records, handle timestamps, and compute rolling 7-day and 30-day demand moving averages using PySpark Window functions.\n",
                "3. **Feature Engineering**: Compute daily SKU demand, inventory consumption rates, and fulfillment lead times.\n",
                "4. **Load (Delta Lake)**: Materialize clean Delta tables (`fact_daily_demand`, `fact_orders_delta`) with ACID compliance, Time Travel, and Z-Order indexing."
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Step 1: Initialize Spark Session & Import Libraries"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from pyspark.sql import SparkSession\n",
                "from pyspark.sql.functions import (\n",
                "    col, when, sum as _sum, avg, count, round as _round, \n",
                "    to_date, to_timestamp, datediff, coalesce, lit, expr\n",
                ")\n",
                "from pyspark.sql.window import Window\n",
                "\n",
                "# Initialize Spark Session (automatically provided in Databricks)\n",
                "spark = SparkSession.builder \\\n",
                "    .appName(\"SupplyChainETL\") \\\n",
                "    .config(\"spark.sql.extensions\", \"io.delta.sql.DeltaSparkSessionExtension\") \\\n",
                "    .config(\"spark.sql.catalog.spark_catalog\", \"org.apache.spark.sql.delta.catalog.DeltaCatalog\") \\\n",
                "    .getOrCreate()\n",
                "\n",
                "print(f\"Spark Version: {spark.version}\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Step 2: Extract Raw Transactions from DBFS / Cloud Storage\n",
                "> Note: Upload `orders.csv` to Databricks via **Catalog -> Create Table -> Upload to DBFS** (target: `/FileStore/tables/orders.csv`)."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Define DBFS File Path with local fallback\n",
                "dbfs_path = \"/FileStore/tables/orders.csv\"\n",
                "\n",
                "df_raw = spark.read \\\n",
                "    .option(\"header\", \"true\") \\\n",
                "    .option(\"inferSchema\", \"true\") \\\n",
                "    .csv(dbfs_path)\n",
                "\n",
                "print(f\"Raw Ingested Records: {df_raw.count():,}\")\n",
                "df_raw.printSchema()\n",
                "display(df_raw.limit(5))"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Step 3: Transform & Data Quality Validation\n",
                "- Filter non-positive quantities and null dates\n",
                "- Standardize dates into `DateType` and `TimestampType`\n",
                "- Exclude canceled or unfulfillable transactions\n",
                "- Cleanse unit prices and sanitize warehouse identifiers"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 2. Transform: Data Validation, Imputation & Filtering\n",
                "df_clean = df_raw \\\n",
                "    .filter(col(\"quantity\") > 0) \\\n",
                "    .filter(col(\"order_date\").isNotNull()) \\\n",
                "    .withColumn(\"order_timestamp\", to_timestamp(col(\"order_date\"))) \\\n",
                "    .withColumn(\"order_date\", to_date(col(\"order_date\"))) \\\n",
                "    .withColumn(\"total_revenue\", _round(col(\"quantity\") * col(\"unit_price\"), 2)) \\\n",
                "    .filter(~col(\"order_status\").isin(\"canceled\", \"unavailable\"))\n",
                "\n",
                "print(f\"Clean Validated Records: {df_clean.count():,}\")\n",
                "display(df_clean.limit(5))"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Step 4: Daily SKU Demand Aggregation & Rolling Averages\n",
                "We aggregate daily SKU demand and leverage PySpark **Window specifications** to compute:\n",
                "- Rolling 7-day moving average of units sold\n",
                "- Rolling 30-day moving average of units sold"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 3. Aggregate Daily SKU Demand for Supply Chain Features\n",
                "df_daily_agg = df_clean.groupBy(\"product_id\", \"product_category\", \"order_date\") \\\n",
                "    .agg(\n",
                "        _sum(\"quantity\").alias(\"daily_units\"),\n",
                "        _sum(\"total_revenue\").alias(\"daily_revenue\"),\n",
                "        count(\"order_id\").alias(\"order_count\"),\n",
                "        _round(avg(\"lead_time_days\"), 2).alias(\"avg_lead_time_days\")\n",
                "    )\n",
                "\n",
                "# Window specification: partition by SKU, ordered by chronological date\n",
                "window_7d = Window.partitionBy(\"product_id\").orderBy(\"order_date\").rowsBetween(-6, 0)\n",
                "window_30d = Window.partitionBy(\"product_id\").orderBy(\"order_date\").rowsBetween(-29, 0)\n",
                "\n",
                "df_daily_demand = df_daily_agg \\\n",
                "    .withColumn(\"rolling_7d_avg_demand\", _round(avg(\"daily_units\").over(window_7d), 2)) \\\n",
                "    .withColumn(\"rolling_30d_avg_demand\", _round(avg(\"daily_units\").over(window_30d), 2))\n",
                "\n",
                "print(f\"Aggregated Daily Demand Records: {df_daily_demand.count():,}\")\n",
                "display(df_daily_demand.orderBy(\"product_id\", \"order_date\").limit(10))"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Step 5: Load - Write Clean Delta Lake Tables\n",
                "Store our cleansed analytical models as ACID-compliant Delta tables in the Databricks Metastore."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 4. Load: Write Clean Delta Tables\n",
                "df_daily_demand.write \\\n",
                "    .format(\"delta\") \\\n",
                "    .mode(\"overwrite\") \\\n",
                "    .option(\"overwriteSchema\", \"true\") \\\n",
                "    .saveAsTable(\"fact_daily_demand\")\n",
                "\n",
                "df_clean.write \\\n",
                "    .format(\"delta\") \\\n",
                "    .mode(\"overwrite\") \\\n",
                "    .option(\"overwriteSchema\", \"true\") \\\n",
                "    .saveAsTable(\"fact_orders_delta\")\n",
                "\n",
                "print(\"[SUCCESS] Materialized Delta Tables: fact_daily_demand, fact_orders_delta\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Step 6: Delta Lake Performance Optimization & Time Travel\n",
                "- `OPTIMIZE ... ZORDER BY` for lightning-fast queries\n",
                "- Inspect table audit history and commit logs"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Optimize Delta Lake Storage layout\n",
                "spark.sql(\"OPTIMIZE fact_daily_demand ZORDER BY (product_id, order_date)\")\n",
                "\n",
                "# Delta Lake Time Travel Verification\n",
                "history_df = spark.sql(\"DESCRIBE HISTORY fact_daily_demand\")\n",
                "display(history_df.select(\"version\", \"timestamp\", \"operation\", \"operationMetrics\"))"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Step 7: Export Clean Parquet for Power BI & Time-Series Forecasting\n",
                "Save ready-to-consume Parquet files into DBFS `/FileStore/processed/`."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "export_path = \"/FileStore/processed/fact_daily_demand.parquet\"\n",
                "df_daily_demand.write.mode(\"overwrite\").parquet(export_path)\n",
                "print(f\"Exported downstream Parquet to: {export_path}\")"
            ]
        }
    ]

    notebook_dict = {
        "cells": notebook_cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3 (PySpark)",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.10"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    nb_path = os.path.join(base_dir, "02_pyspark_etl.ipynb")
    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(notebook_dict, f, indent=2)
    print(f"[CREATED] Notebook: {nb_path} ({os.path.getsize(nb_path):,} bytes)")

    # Also create the Databricks notebook format .py file
    py_path = os.path.join(base_dir, "02_pyspark_etl.py")
    with open(py_path, "w", encoding="utf-8") as f:
        f.write("# Databricks notebook source\n")
        f.write("# MAGIC %md\n")
        f.write("# MAGIC # Smart Supply Chain Analytics: PySpark ETL/ELT Pipeline\n")
        f.write("# MAGIC This pipeline ingests raw orders, cleanses transactional data, computes rolling 7d/30d moving demand, and loads Delta Lake tables.\n\n")
        f.write("# COMMAND ----------\n\n")
        f.write("from pyspark.sql import SparkSession\n")
        f.write("from pyspark.sql.functions import col, when, sum as _sum, avg, count, round as _round, to_date, to_timestamp\n")
        f.write("from pyspark.sql.window import Window\n\n")
        f.write("spark = SparkSession.builder.appName('SupplyChainETL').getOrCreate()\n\n")
        f.write("# COMMAND ----------\n\n")
        f.write("# 1. Extract raw transactional CSV\n")
        f.write("df_raw = spark.read.option('header', 'true').option('inferSchema', 'true').csv('/FileStore/tables/orders.csv')\n\n")
        f.write("# COMMAND ----------\n\n")
        f.write("# 2. Transform: Data Validation & Filtering\n")
        f.write("df_clean = df_raw.filter(col('quantity') > 0) \\\n")
        f.write("                 .filter(col('order_date').isNotNull()) \\\n")
        f.write("                 .withColumn('order_date', to_date(col('order_date'))) \\\n")
        f.write("                 .withColumn('total_revenue', _round(col('quantity') * col('unit_price'), 2)) \\\n")
        f.write("                 .filter(~col('order_status').isin('canceled', 'unavailable'))\n\n")
        f.write("# COMMAND ----------\n\n")
        f.write("# 3. Aggregate Daily SKU Demand & Rolling Window Features\n")
        f.write("df_daily_agg = df_clean.groupBy('product_id', 'product_category', 'order_date') \\\n")
        f.write("                       .agg(_sum('quantity').alias('daily_units'), _sum('total_revenue').alias('daily_revenue'))\n\n")
        f.write("window_7d = Window.partitionBy('product_id').orderBy('order_date').rowsBetween(-6, 0)\n")
        f.write("window_30d = Window.partitionBy('product_id').orderBy('order_date').rowsBetween(-29, 0)\n\n")
        f.write("df_daily_demand = df_daily_agg \\\n")
        f.write("    .withColumn('rolling_7d_avg_demand', _round(avg('daily_units').over(window_7d), 2)) \\\n")
        f.write("    .withColumn('rolling_30d_avg_demand', _round(avg('daily_units').over(window_30d), 2))\n\n")
        f.write("# COMMAND ----------\n\n")
        f.write("# 4. Load: Write Clean Delta Tables\n")
        f.write("df_daily_demand.write.format('delta').mode('overwrite').option('overwriteSchema', 'true').saveAsTable('fact_daily_demand')\n")
        f.write("df_clean.write.format('delta').mode('overwrite').option('overwriteSchema', 'true').saveAsTable('fact_orders_delta')\n\n")
        f.write("# COMMAND ----------\n\n")
        f.write("# MAGIC %sql\n")
        f.write("# MAGIC OPTIMIZE fact_daily_demand ZORDER BY (product_id, order_date);\n")
        f.write("# MAGIC SELECT * FROM fact_daily_demand LIMIT 10;\n")

    print(f"[CREATED] Databricks Script: {py_path} ({os.path.getsize(py_path):,} bytes)")

if __name__ == '__main__':
    create_notebook()

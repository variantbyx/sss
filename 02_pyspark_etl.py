# Databricks notebook source
# MAGIC %md
# MAGIC # Smart Supply Chain Analytics: PySpark ETL/ELT Pipeline
# MAGIC This pipeline ingests raw orders, cleanses transactional data, computes rolling 7d/30d moving demand, and loads Delta Lake tables.

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, sum as _sum, avg, count, round as _round, to_date, to_timestamp
from pyspark.sql.window import Window

spark = SparkSession.builder.appName('SupplyChainETL').getOrCreate()

# COMMAND ----------

# 1. Extract raw transactional CSV
df_raw = spark.read.option('header', 'true').option('inferSchema', 'true').csv('/FileStore/tables/orders.csv')

# COMMAND ----------

# 2. Transform: Data Validation & Filtering
df_clean = df_raw.filter(col('quantity') > 0) \
                 .filter(col('order_date').isNotNull()) \
                 .withColumn('order_date', to_date(col('order_date'))) \
                 .withColumn('total_revenue', _round(col('quantity') * col('unit_price'), 2)) \
                 .filter(~col('order_status').isin('canceled', 'unavailable'))

# COMMAND ----------

# 3. Aggregate Daily SKU Demand & Rolling Window Features
df_daily_agg = df_clean.groupBy('product_id', 'product_category', 'order_date') \
                       .agg(_sum('quantity').alias('daily_units'), _sum('total_revenue').alias('daily_revenue'))

window_7d = Window.partitionBy('product_id').orderBy('order_date').rowsBetween(-6, 0)
window_30d = Window.partitionBy('product_id').orderBy('order_date').rowsBetween(-29, 0)

df_daily_demand = df_daily_agg \
    .withColumn('rolling_7d_avg_demand', _round(avg('daily_units').over(window_7d), 2)) \
    .withColumn('rolling_30d_avg_demand', _round(avg('daily_units').over(window_30d), 2))

# COMMAND ----------

# 4. Load: Write Clean Delta Tables
df_daily_demand.write.format('delta').mode('overwrite').option('overwriteSchema', 'true').saveAsTable('fact_daily_demand')
df_clean.write.format('delta').mode('overwrite').option('overwriteSchema', 'true').saveAsTable('fact_orders_delta')

# COMMAND ----------

# MAGIC %sql
# MAGIC OPTIMIZE fact_daily_demand ZORDER BY (product_id, order_date);
# MAGIC SELECT * FROM fact_daily_demand LIMIT 10;

from pyspark.sql import SparkSession
from pyspark.sql.functions import *

spark = SparkSession.builder.appName("feature-eng").getOrCreate()

df = spark.read.csv("/opt/ml/processing/input/payments.csv", header=True, inferSchema=True)

df = df.withColumn("high_amount", when(col("txn_amount")>15000,1).otherwise(0))
df = df.withColumn("night_txn", when(col("txn_hour")<5,1).otherwise(0))
df = df.withColumn("risk_ratio", col("ip_risk_score")*col("num_failed_logins"))

df.write.mode("overwrite").parquet("/opt/ml/processing/output/")
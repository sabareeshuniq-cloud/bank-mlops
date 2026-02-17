# monitoring/baseline.py

import boto3
import sagemaker
from sagemaker.model_monitor import DefaultModelMonitor
from sagemaker.model_monitor.dataset_format import DatasetFormat

session = sagemaker.Session()
role = sagemaker.get_execution_role()

endpoint_name = "bank-churn-endpoint"
baseline_data = f"s3://{session.default_bucket()}/bank/baseline/train.csv"

monitor = DefaultModelMonitor(
    role=role,
    instance_count=1,
    instance_type="ml.m5.large",
    volume_size_in_gb=20,
    max_runtime_in_seconds=3600,
)

monitor.suggest_baseline(
    baseline_dataset=baseline_data,
    dataset_format=DatasetFormat.csv(header=False),
    output_s3_uri=f"s3://{session.default_bucket()}/bank/baseline/output",
    wait=True
)

print("Baseline created")

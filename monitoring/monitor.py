# monitoring/monitor.py

import sagemaker
from sagemaker.model_monitor import DefaultModelMonitor, CronExpressionGenerator

session = sagemaker.Session()
role = sagemaker.get_execution_role()

monitor = DefaultModelMonitor(
    role=role,
    instance_count=1,
    instance_type="ml.m5.large",
    max_runtime_in_seconds=3600,
)

monitor.create_monitoring_schedule(
    monitor_schedule_name="bank-churn-monitor",
    endpoint_input="bank-churn-endpoint",
    output_s3_uri=f"s3://{session.default_bucket()}/monitoring/reports",
    statistics=f"s3://{session.default_bucket()}/bank/baseline/output/statistics.json",
    constraints=f"s3://{session.default_bucket()}/bank/baseline/output/constraints.json",
    schedule_cron_expression=CronExpressionGenerator.hourly(),
)

from sagemaker.model_monitor import DefaultModelMonitor
from sagemaker.model_monitor.dataset_format import DatasetFormat
import os
import sagemaker
from configs.params import load_config


def create_monitor(role=None, sagemaker_session=None, config=None):
    """Create a DefaultModelMonitor instance using project config.

    Returns the monitor object. Does not create a schedule by default.
    """
    if config is None:
        config = load_config()
    if sagemaker_session is None:
        sagemaker_session = sagemaker.Session()
    if role is None:
        role = os.environ.get("SAGEMAKER_ROLE")

    monitor = DefaultModelMonitor(
        role=role,
        instance_count=1,
        instance_type=config.get("monitoring_instance", "ml.m5.large"),
        sagemaker_session=sagemaker_session,
    )
    return monitor


def suggest_baseline_and_schedule(monitor: DefaultModelMonitor, baseline_s3_prefix: str = None, endpoint_name: str = None, output_s3_uri: str = None, schedule_cron: str = "cron(0 * ? * * *)"):
    """Suggest baseline from training data and create a monitoring schedule for an endpoint.

    Parameters:
    - monitor: DefaultModelMonitor instance
    - baseline_s3_prefix: s3 path to training data (parquet)
    - endpoint_name: deployed endpoint name
    - output_s3_uri: s3 prefix to write monitor outputs
    - schedule_cron: cron expression for schedule
    """
    cfg = load_config()
    bucket = cfg.get("bucket")
    prefix = cfg.get("project")

    if baseline_s3_prefix is None:
        baseline_s3_prefix = f"s3://{bucket}/{prefix}/processed/train/"
    if output_s3_uri is None:
        output_s3_uri = f"s3://{bucket}/{prefix}/monitoring/"
    if endpoint_name is None:
        endpoint_name = cfg.get("endpoint_name", "bank-risk-endpoint")

    # suggest baseline (creates statistics and constraints under monitor.sagemaker_session default job output)
    monitor.suggest_baseline(
        baseline_dataset=baseline_s3_prefix,
        dataset_format=DatasetFormat.parquet(),
    )

    # create the monitoring schedule for a deployed endpoint
    monitor.create_monitoring_schedule(
        monitor_schedule_name=f"{endpoint_name}-monitor",
        endpoint_input=endpoint_name,
        output_s3_uri=output_s3_uri,
        statistics="baseline_statistics.json",
        constraints="baseline_constraints.json",
        schedule_cron_expression=schedule_cron,
    )


if __name__ == "__main__":
    # helper run when module executed directly
    cfg = load_config()
    sess = sagemaker.Session()
    mon = create_monitor(sagemaker_session=sess, config=cfg)
    suggest_baseline_and_schedule(mon)

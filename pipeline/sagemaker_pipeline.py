"""Starter SageMaker pipeline orchestrator.

Workflow (starter):
 - upload local sample data -> S3
 - run SparkProcessor (processing/spark_feature_engineering.py) -> processed S3 (parquet)
 - train XGBoost with training/train_xgboost.py -> model artifact to S3
 - evaluate with evaluation/evaluate.py -> write evaluation.json to S3
 - gate on AUC -> deploy endpoint if pass
 - create model monitor baseline & schedule

Before running, set environment variable SAGEMAKER_ROLE to an IAM role ARN with SageMaker and S3 access.
"""
import os
import time
import json
import boto3
import sagemaker
from sagemaker.spark import SparkProcessor
from sagemaker.processing import ProcessingInput, ProcessingOutput, ScriptProcessor
from sagemaker.xgboost import XGBoost
from sagemaker import get_execution_role

from configs.params import load_config
from monitoring.monitor import create_monitor, suggest_baseline_and_schedule


def load_cfg(env=None):
    if env is None:
        env = os.environ.get("ENV", "dev")
    return load_config(env)


def get_role():
    role = os.environ.get("SAGEMAKER_ROLE")
    if role:
        return role
    try:
        return get_execution_role()
    except Exception:
        raise RuntimeError("SAGEMAKER_ROLE not set and get_execution_role() unavailable. Set env var SAGEMAKER_ROLE to a role ARN.")


def upload_local_to_s3(local_path: str, bucket: str, prefix: str):
    s3 = boto3.client("s3")
    key = f"{prefix}/{os.path.basename(local_path)}"
    s3.upload_file(local_path, bucket, key)
    return f"s3://{bucket}/{key}"


def run_spark_processing(role, sess, input_s3_uri: str, output_s3_uri: str, instance_type: str):
    spark_processor = SparkProcessor(
        role=role,
        instance_type=instance_type,
        instance_count=1,
        base_job_name="bank-spark",
        sagemaker_session=sess,
    )

    print(f"Starting Spark processing: input={input_s3_uri} -> output={output_s3_uri}")
    spark_processor.run(
        submit_app="processing/spark_feature_engineering.py",
        arguments=[],
        inputs=[ProcessingInput(source=input_s3_uri, destination="/opt/ml/processing/input")],
        outputs=[ProcessingOutput(output_name="processed", source="/opt/ml/processing/output", destination=output_s3_uri)],
    )


def train_xgboost(role, sess, train_s3_uri: str, model_output_s3: str, instance_type: str, instance_count: int = 1):
    print("Starting training job (XGBoost)...")
    estimator = XGBoost(
        entry_point="training/train_xgboost.py",
        role=role,
        framework_version="1.6-1",
        instance_type=instance_type,
        instance_count=instance_count,
        output_path=model_output_s3,
        sagemaker_session=sess,
        hyperparameters={"max_depth": 6, "eta": 0.1, "num_round": 100},
    )

    estimator.fit({"train": train_s3_uri})
    return estimator


def evaluate_model(sess, model_artifact_s3: str, test_s3_uri: str, instance_type: str):
    print("Starting evaluation processing job...")
    image_uri = sagemaker.image_uris.retrieve(framework="sklearn", region_name=sess.boto_region_name, version="0.23-1")
    script_processor = ScriptProcessor(
        role=get_role(),
        command=["python3"],
        image_uri=image_uri,
        instance_count=1,
        instance_type=instance_type,
        sagemaker_session=sess,
    )

    eval_output = f"s3://{sess.default_bucket()}/bank-mlops/evaluation/{int(time.time())}/"

    script_processor.run(
        code="evaluation/evaluate.py",
        inputs=[
            ProcessingInput(source=test_s3_uri, destination="/opt/ml/processing/test"),
            ProcessingInput(source=model_artifact_s3, destination="/opt/ml/processing/model"),
        ],
        outputs=[ProcessingOutput(output_name="eval", source="/opt/ml/processing/evaluation", destination=eval_output)],
    )

    # Wait briefly and then read evaluation.json from eval_output
    time.sleep(10)
    s3 = boto3.client("s3")
    # evaluation writes to eval_output/evaluation.json (script should write that path)
    parsed = eval_output.replace("s3://", "").split("/", 1)
    bucket = parsed[0]
    key_prefix = parsed[1]
    # try to find evaluation.json under that prefix
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=key_prefix)
    eval_key = None
    if "Contents" in resp:
        for obj in resp["Contents"]:
            if obj["Key"].endswith("evaluation.json"):
                eval_key = obj["Key"]
                break
    if not eval_key:
        raise RuntimeError("evaluation.json not found in evaluation output S3 location")

    ev = s3.get_object(Bucket=bucket, Key=eval_key)
    metrics = json.loads(ev["Body"].read())
    return metrics


def deploy_model(estimator, endpoint_name: str, instance_type: str, initial_instance_count: int = 1):
    print(f"Deploying endpoint {endpoint_name} ...")
    predictor = estimator.deploy(initial_instance_count=initial_instance_count, instance_type=instance_type, endpoint_name=endpoint_name)
    return predictor


def run_pipeline(env: str = "dev"):
    cfg = load_cfg(env)
    role = get_role()
    sess = sagemaker.Session()
    bucket = cfg.get("bucket")
    prefix = cfg.get("project", "bank-mlops")

    # 1) upload a sample local raw data file to S3 (you can replace this with your real data path)
    local_raw = os.path.join("data", "payments.csv")
    if not os.path.exists(local_raw):
        raise FileNotFoundError(f"Local sample data not found: {local_raw}. Generate or point to real data.")
    raw_s3 = upload_local_to_s3(local_raw, bucket, f"{prefix}/raw")
    print("Uploaded raw data:", raw_s3)

    # 2) processing (Spark)
    processed_s3_prefix = f"s3://{bucket}/{prefix}/processed/train/"
    run_spark_processing(role, sess, raw_s3, processed_s3_prefix, cfg["processing"]["instance_type"])

    # 3) training
    model_output_s3 = f"s3://{bucket}/{prefix}/models/"
    estimator = train_xgboost(role, sess, processed_s3_prefix, model_output_s3, cfg["training"]["instance_type"], cfg["training"].get("instance_count", 1))

    # 4) evaluation
    metrics = evaluate_model(sess, estimator.model_data, processed_s3_prefix, instance_type="ml.m5.large")
    print("Evaluation metrics:", metrics)

    # 5) gating/approval
    threshold = cfg.get("model", {}).get("approval_threshold_auc", 0.85)
    if metrics.get("auc", 0) >= threshold:
        print(f"AUC {metrics.get('auc')} >= {threshold} -> deploying endpoint")
        endpoint_name = cfg.get("endpoint_name", "bank-risk-endpoint")
        deploy_model(estimator, endpoint_name, cfg["endpoint"]["instance_type"], cfg["endpoint"].get("min_capacity", 1))

        # 6) setup model monitor baseline & schedule
        monitor = create_monitor(role=role, sagemaker_session=sess, config=cfg)
        suggest_baseline_and_schedule(monitor, baseline_s3_prefix=processed_s3_prefix, endpoint_name=endpoint_name)
    else:
        print(f"AUC {metrics.get('auc')} below threshold {threshold} - not deploying. Consider retrain or tuning.")


if __name__ == "__main__":
    run_pipeline(os.environ.get("ENV", "dev"))

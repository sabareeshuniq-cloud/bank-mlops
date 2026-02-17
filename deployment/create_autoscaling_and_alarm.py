"""Create autoscaling target/policy for a SageMaker endpoint and a CloudWatch alarm wired to a rollback Lambda via SNS.

Usage: set environment variables ENDPOINT_NAME and ROLLBACK_LAMBDA_ARN (or pass them by editing the script).

This script will:
 - register a scalable target for the endpoint variant
 - create a target-tracking scaling policy based on InvocationsPerInstance
 - create an SNS topic and subscribe the rollback Lambda
 - create a CloudWatch alarm on ModelLatency that publishes to the SNS topic

Note: running this requires credentials with ApplicationAutoScaling, CloudWatch, SNS, and SageMaker permissions.
"""
import os
import boto3

ENDPOINT_NAME = os.environ.get("ENDPOINT_NAME", "bank-risk-endpoint")
ROLLBACK_LAMBDA_ARN = os.environ.get("ROLLBACK_LAMBDA_ARN")
MIN_CAP = int(os.environ.get("MIN_CAP", "1"))
MAX_CAP = int(os.environ.get("MAX_CAP", "5"))
TARGET_INVOCATIONS = float(os.environ.get("TARGET_INVOCATIONS_PER_INSTANCE", "50.0"))
LATENCY_THRESHOLD_MS = float(os.environ.get("LATENCY_THRESHOLD_MS", "1000"))

app_autoscaling = boto3.client("application-autoscaling")
sm = boto3.client("sagemaker")
sns = boto3.client("sns")
cw = boto3.client("cloudwatch")


def register_scalable_target(endpoint_name, min_cap=1, max_cap=5):
    resource_id = f"endpoint/{endpoint_name}/variant/AllTraffic"
    print("Registering scalable target:", resource_id)
    app_autoscaling.register_scalable_target(
        ServiceNamespace="sagemaker",
        ResourceId=resource_id,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        MinCapacity=min_cap,
        MaxCapacity=max_cap,
    )


def put_target_tracking_policy(endpoint_name, target_value=50.0):
    resource_id = f"endpoint/{endpoint_name}/variant/AllTraffic"
    policy_name = f"{endpoint_name}-invocations-policy"
    print("Creating scaling policy", policy_name)
    app_autoscaling.put_scaling_policy(
        PolicyName=policy_name,
        ServiceNamespace="sagemaker",
        ResourceId=resource_id,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        PolicyType="TargetTrackingScaling",
        TargetTrackingScalingPolicyConfiguration={
            "TargetValue": target_value,
            "PredefinedMetricSpecification": {"PredefinedMetricType": "SageMakerVariantInvocationsPerInstance"},
            "ScaleInCooldown": 300,
            "ScaleOutCooldown": 60,
        },
    )


def create_sns_and_subscribe(lambda_arn):
    topic_name = f"{ENDPOINT_NAME}-alarms"
    print("Creating SNS topic", topic_name)
    resp = sns.create_topic(Name=topic_name)
    topic_arn = resp["TopicArn"]
    if lambda_arn:
        print("Subscribing Lambda to SNS topic")
        sns.subscribe(TopicArn=topic_arn, Protocol="lambda", Endpoint=lambda_arn)
    return topic_arn


def create_latency_alarm(endpoint_name, topic_arn, threshold_ms=1000.0):
    alarm_name = f"{endpoint_name}-ModelLatency-Alarm"
    print("Creating CloudWatch alarm", alarm_name)
    cw.put_metric_alarm(
        AlarmName=alarm_name,
        Namespace="AWS/SageMaker",
        MetricName="ModelLatency",
        Dimensions=[{"Name": "EndpointName", "Value": endpoint_name}],
        Statistic="Average",
        Period=60,
        EvaluationPeriods=2,
        Threshold=threshold_ms,
        ComparisonOperator="GreaterThanThreshold",
        ActionsEnabled=True,
        AlarmActions=[topic_arn],
        TreatMissingData="breaching",
    )
    print("Alarm created")


def main():
    register_scalable_target(ENDPOINT_NAME, MIN_CAP, MAX_CAP)
    put_target_tracking_policy(ENDPOINT_NAME, TARGET_INVOCATIONS)

    topic_arn = create_sns_and_subscribe(ROLLBACK_LAMBDA_ARN)
    create_latency_alarm(ENDPOINT_NAME, topic_arn, LATENCY_THRESHOLD_MS)

    print("Done. Autoscaling and alarm configured.")


if __name__ == "__main__":
    if not ROLLBACK_LAMBDA_ARN:
        print("Warning: ROLLBACK_LAMBDA_ARN not set. SNS topic will be created but no subscription will be added.")
    main()

# deployment/create_autoscaling_and_alarm.py

import boto3

autoscaling = boto3.client("application-autoscaling")
cloudwatch = boto3.client("cloudwatch")

resource_id = "endpoint/bank-churn-endpoint/variant/AllTraffic"

autoscaling.put_scaling_policy(
    PolicyName="cpu-scaling-policy",
    ServiceNamespace="sagemaker",
    ResourceId=resource_id,
    ScalableDimension="sagemaker:variant:DesiredInstanceCount",
    PolicyType="TargetTrackingScaling",
    TargetTrackingScalingPolicyConfiguration={
        "TargetValue": 70.0,
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance"
        },
        "ScaleInCooldown": 300,
        "ScaleOutCooldown": 60
    }
)

print("Scaling policy attached")
